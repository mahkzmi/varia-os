from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Annotated
from zoneinfo import ZoneInfo
from urllib.parse import urlencode
from uuid import UUID

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client

from .settings import settings

router = APIRouter(prefix="/api/office/gmail", tags=["Gmail connection"])
bearer_scheme = HTTPBearer(auto_error=False)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
SCOPES = "openid email https://www.googleapis.com/auth/gmail.send"
FRONTEND_URL = "https://varia-os.onrender.com"
REDIRECT_URI = "https://natasha-api.onrender.com/api/office/gmail/callback"


def _user_db() -> Client:
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise HTTPException(status_code=503, detail="Supabase is not configured")
    return create_client(settings.supabase_url, settings.supabase_publishable_key)


def _service_db() -> Client:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(status_code=503, detail="Server-side database access is not configured")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer token required")
    try:
        db = _user_db()
        user = db.auth.get_user(credentials.credentials)
        if not user or not user.user:
            raise ValueError("No authenticated user")
        return str(user.user.id)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")


def _crypto_key() -> bytes:
    raw = settings.gmail_token_encryption_key
    if not raw:
        raise HTTPException(status_code=503, detail="Gmail token encryption is not configured")
    try:
        key = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    except Exception:
        raise HTTPException(status_code=503, detail="Gmail token encryption key is invalid")
    if len(key) != 32:
        raise HTTPException(status_code=503, detail="Gmail token encryption key must decode to 32 bytes")
    return key


def _seal(value: str) -> str:
    nonce = secrets.token_bytes(12)
    encrypted = AESGCM(_crypto_key()).encrypt(nonce, value.encode("utf-8"), b"varia-os:gmail:refresh-token:v1")
    return base64.urlsafe_b64encode(nonce + encrypted).decode("ascii")


def _unseal(value: str) -> str:
    try:
        raw = base64.urlsafe_b64decode(value.encode("ascii"))
        return AESGCM(_crypto_key()).decrypt(raw[:12], raw[12:], b"varia-os:gmail:refresh-token:v1").decode("utf-8")
    except Exception:
        raise HTTPException(status_code=500, detail="Stored Gmail credentials could not be decrypted")


def _state_key() -> bytes:
    return hashlib.sha256(_crypto_key() + b":oauth-state-signing").digest()


def _make_state(user_id: str) -> str:
    payload = {
        "uid": user_id,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()),
        "nonce": secrets.token_urlsafe(24),
    }
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(_state_key(), body.encode(), hashlib.sha256).digest()
    return body + "." + base64.urlsafe_b64encode(signature).decode().rstrip("=")


def _read_state(state: str) -> tuple[dict, str]:
    try:
        body, signature = state.split(".", 1)
        expected = hmac.new(_state_key(), body.encode(), hashlib.sha256).digest()
        supplied = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        if not hmac.compare_digest(expected, supplied):
            raise ValueError("Invalid state signature")
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if int(payload["exp"]) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("Expired state")
        UUID(str(payload["uid"]))
        return payload, hashlib.sha256(state.encode()).hexdigest()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired Gmail authorization state")


def _google_configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


@router.post("/connect")
def start_gmail_connection(user_id: Annotated[str, Depends(current_user_id)]) -> dict:
    if not _google_configured():
        raise HTTPException(status_code=503, detail="Google OAuth client credentials are not configured in Render")
    state = _make_state(user_id)
    state_hash = hashlib.sha256(state.encode()).hexdigest()
    service_db = _service_db()
    service_db.table("gmail_oauth_states").insert({
        "state_hash": state_hash,
        "user_id": user_id,
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
    }).execute()
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent select_account",
        "state": state,
    }
    return {"authorization_url": GOOGLE_AUTH_URL + "?" + urlencode(params), "expires_in": 600}


@router.get("/callback")
async def gmail_oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    if error:
        return RedirectResponse(FRONTEND_URL + "/?gmail=denied", status_code=303)
    if not code or not state:
        return RedirectResponse(FRONTEND_URL + "/?gmail=invalid_callback", status_code=303)
    try:
        payload, state_hash = _read_state(state)
        service_db = _service_db()
        state_rows = (service_db.table("gmail_oauth_states").select("user_id,consumed_at,expires_at")
            .eq("state_hash", state_hash).limit(1).execute().data or [])
        if not state_rows or state_rows[0].get("consumed_at"):
            raise HTTPException(status_code=400, detail="Gmail authorization state was already used or not found")
        if str(state_rows[0]["user_id"]) != str(payload["uid"]):
            raise HTTPException(status_code=400, detail="Gmail authorization state owner mismatch")
        service_db.table("gmail_oauth_states").update({
            "consumed_at": datetime.now(timezone.utc).isoformat()
        }).eq("state_hash", state_hash).is_("consumed_at", "null").execute()

        async with httpx.AsyncClient(timeout=25.0) as client:
            token_response = await client.post(GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            })
            token_response.raise_for_status()
            token_data = token_response.json()
            access_token = token_data["access_token"]
            info_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            info_response.raise_for_status()
            google_user = info_response.json()

        email = str(google_user.get("email") or "").strip().lower()
        if not email or not google_user.get("email_verified", False):
            raise HTTPException(status_code=400, detail="Google did not return a verified email address")
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            previous = (service_db.table("gmail_connections").select("refresh_token_ciphertext")
                .eq("user_id", str(payload["uid"])).limit(1).execute().data or [])
            if previous:
                refresh_token = _unseal(previous[0]["refresh_token_ciphertext"])
        if not refresh_token:
            raise HTTPException(status_code=400, detail="Google did not issue a refresh token; reconnect and grant offline access")
        service_db.table("gmail_connections").upsert({
            "user_id": str(payload["uid"]),
            "email": email,
            "refresh_token_ciphertext": _seal(refresh_token),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="user_id").execute()
        return RedirectResponse(FRONTEND_URL + "/?gmail=connected", status_code=303)
    except HTTPException as exc:
        reason = "setup_error" if exc.status_code >= 500 else "authorization_error"
        return RedirectResponse(FRONTEND_URL + "/?gmail=" + reason, status_code=303)
    except Exception:
        return RedirectResponse(FRONTEND_URL + "/?gmail=authorization_error", status_code=303)


@router.get("/status")
def gmail_connection_status(user_id: Annotated[str, Depends(current_user_id)]) -> dict:
    if not settings.google_client_id or not settings.google_client_secret or not settings.gmail_token_encryption_key:
        return {"configured": False, "connected": False, "email": None}
    rows = (_service_db().table("gmail_connections").select("email,updated_at")
        .eq("user_id", user_id).limit(1).execute().data or [])
    return {
        "configured": True,
        "connected": bool(rows),
        "email": rows[0]["email"] if rows else None,
        "updated_at": rows[0].get("updated_at") if rows else None,
    }


@router.post("/test")
async def send_gmail_self_test(user_id: Annotated[str, Depends(current_user_id)]) -> dict:
    """Send a one-time connection test only to the currently authenticated founder."""
    auth_db = _user_db()
    # Resolve the current account from the same bearer-authenticated request.
    # The dependency has already validated the caller; read the matching auth user via service role.
    user_rows = (_service_db().table("gmail_connections").select("email,refresh_token_ciphertext")
        .eq("user_id", user_id).limit(1).execute().data or [])
    if not user_rows:
        raise HTTPException(status_code=409, detail="Connect Gmail before running the test")
    connection = user_rows[0]
    # The destination is the connected, verified Google account itself. No arbitrary recipient is accepted.
    destination = connection["email"]
    refresh_token = _unseal(connection["refresh_token_ciphertext"])
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_response = await client.post(GOOGLE_TOKEN_URL, data={
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        })
        if token_response.is_error:
            raise HTTPException(status_code=502, detail="Google token refresh failed; reconnect Gmail")
        access_token = token_response.json()["access_token"]
        message = EmailMessage()
        message["To"] = destination
        message["Subject"] = "Varia OS — Gmail connection test"
        message.set_content(
            "Gmail is connected to Varia OS. This is a self-test message sent only to the connected account. "
            "External prospect sending remains disabled until its safeguards are verified."
        )
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii").rstrip("=")
        send_response = await client.post(
            GMAIL_SEND_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"raw": raw},
        )
        if send_response.is_error:
            raise HTTPException(status_code=502, detail="Gmail API rejected the self-test message")
    return {"status": "sent", "to": destination, "scope": "self_test_only"}


@router.post("/send-approved/{draft_id}")
async def send_approved_draft(
    draft_id: UUID,
    user_id: Annotated[str, Depends(current_user_id)],
) -> dict:
    """Send only a founder-approved draft to a verified, non-opted-out CRM contact."""
    db = _service_db()
    draft_rows = (db.table("natasha_message_drafts").select("*")
        .eq("id", str(draft_id)).eq("user_id", user_id).limit(1).execute().data or [])
    if not draft_rows:
        raise HTTPException(status_code=404, detail="Email draft not found")
    draft = draft_rows[0]
    if draft.get("status") != "approved":
        raise HTTPException(status_code=409, detail="Only founder-approved drafts can be sent")

    lead_rows = (db.table("natasha_leads").select("id,primary_contact_id")
        .eq("id", str(draft.get("lead_id"))).eq("user_id", user_id).limit(1).execute().data or [])
    if not lead_rows or not lead_rows[0].get("primary_contact_id"):
        raise HTTPException(status_code=409, detail="Draft must be linked to a CRM lead with a primary contact")
    lead = lead_rows[0]
    contact_rows = (db.table("natasha_contacts").select("id,email,email_verified,email_opted_out,timezone")
        .eq("id", str(lead["primary_contact_id"])).eq("user_id", user_id).limit(1).execute().data or [])
    if not contact_rows:
        raise HTTPException(status_code=409, detail="CRM contact not found")
    contact = contact_rows[0]
    recipient = str(contact.get("email") or "").strip().lower()
    if not contact.get("email_verified") or contact.get("email_opted_out"):
        raise HTTPException(status_code=403, detail="Recipient email is not verified or has opted out")
    if not recipient or recipient != str(draft.get("recipient") or "").strip().lower():
        raise HTTPException(status_code=409, detail="Draft recipient does not match the verified CRM contact")

    try:
        local_now = datetime.now(timezone.utc).astimezone(ZoneInfo(contact.get("timezone") or "UTC"))
    except Exception:
        raise HTTPException(status_code=422, detail="Contact timezone is invalid; update the CRM contact")
    if local_now.weekday() >= 5 or local_now.hour < 9 or local_now.hour >= 17:
        raise HTTPException(status_code=403, detail="Recipient local sending window is weekdays 09:00–17:00")

    connection_rows = (db.table("gmail_connections").select("email,refresh_token_ciphertext")
        .eq("user_id", user_id).limit(1).execute().data or [])
    if not connection_rows:
        raise HTTPException(status_code=409, detail="Connect Gmail before sending")
    connection = connection_rows[0]
    refresh_token = _unseal(connection["refresh_token_ciphertext"])

    send_date = datetime.now(timezone.utc).date().isoformat()
    reserved = db.rpc("gmail_reserve_send_slot", {
        "p_user_id": user_id, "p_send_date": send_date
    }).execute().data
    if reserved is not True:
        raise HTTPException(status_code=429, detail="Daily first-touch limit of 15 messages reached")

    claimed = (db.table("natasha_message_drafts").update({"status": "sending"})
        .eq("id", str(draft_id)).eq("user_id", user_id).eq("status", "approved").execute().data or [])
    if not claimed:
        db.rpc("gmail_release_send_slot", {"p_user_id": user_id, "p_send_date": send_date}).execute()
        raise HTTPException(status_code=409, detail="Draft was already claimed or changed")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            token_response = await client.post(GOOGLE_TOKEN_URL, data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            })
            if token_response.is_error:
                db.table("natasha_message_drafts").update({"status": "approved"}).eq("id", str(draft_id)).eq("status", "sending").execute()
                db.rpc("gmail_release_send_slot", {"p_user_id": user_id, "p_send_date": send_date}).execute()
                raise HTTPException(status_code=502, detail="Google token refresh failed; reconnect Gmail")
            access_token = token_response.json()["access_token"]
            message = EmailMessage()
            message["To"] = recipient
            message["Subject"] = str(draft.get("subject") or "").strip() or "Varia Studio"
            message.set_content(str(draft.get("body") or ""))
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii").rstrip("=")
            send_response = await client.post(
                GMAIL_SEND_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                json={"raw": raw},
            )
            if send_response.is_error:
                db.table("natasha_message_drafts").update({"status": "approved"}).eq("id", str(draft_id)).eq("status", "sending").execute()
                db.rpc("gmail_release_send_slot", {"p_user_id": user_id, "p_send_date": send_date}).execute()
                raise HTTPException(status_code=502, detail="Gmail rejected the message; draft returned to approved")
            provider_message_id = send_response.json().get("id")
    except HTTPException:
        raise
    except Exception:
        # Delivery outcome may be ambiguous after a network failure. Keep the
        # draft in 'sending' and reserve the quota to prevent accidental duplicates.
        raise HTTPException(status_code=502, detail="Gmail send outcome is uncertain; draft locked to prevent duplicate delivery")

    sent_at = datetime.now(timezone.utc).isoformat()
    db.table("natasha_message_drafts").update({
        "status": "sent",
        "sent_at": sent_at,
        "provider_message_id": provider_message_id,
        "updated_at": sent_at,
    }).eq("id", str(draft_id)).eq("status", "sending").execute()
    db.table("natasha_leads").update({
        "stage": "contacted",
        "last_contacted_at": sent_at,
        "updated_at": sent_at,
    }).eq("id", str(lead["id"])).eq("user_id", user_id).execute()
    db.table("natasha_activities").insert({
        "user_id": user_id,
        "lead_id": lead["id"],
        "contact_id": contact["id"],
        "activity_type": "email_sent",
        "subject": draft.get("subject"),
        "body": draft.get("body"),
        "occurred_at": sent_at,
        "metadata": {"draft_id": str(draft_id), "provider": "gmail", "provider_message_id": provider_message_id},
    }).execute()
    db.table("natasha_audit_events").insert({
        "user_id": user_id,
        "entity_type": "email_draft",
        "entity_id": str(draft_id),
        "action": "gmail_email_sent",
        "details": {"recipient": recipient, "provider_message_id": provider_message_id},
    }).execute()
    return {"status": "sent", "to": recipient, "provider_message_id": provider_message_id}
