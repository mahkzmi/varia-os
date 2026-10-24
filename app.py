import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import plotly.express as px

# --- ۱. تنظیمات اولیه و تم ---
st.set_page_config(page_title="Varia Studio | Founder OS", layout="wide", page_icon="🌱")

FOREST = "#2F4F3A"
CREAM = "#F5F0E8"
GOLD = "#D4A24C"
INK = "#1A1A1A"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background-color: {INK}; }}
    h1, h2, h3 {{ color: {CREAM} !important; font-weight: 600; }}
    div[data-testid="stMetric"] {{
        background-color: {FOREST};
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid {GOLD};
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }}
    div[data-testid="stMetricValue"] {{ color: {GOLD} !important; font-size: 2rem !important; }}
    div[data-testid="stMetricLabel"] {{ color: {CREAM} !important; }}
    .stTabs [data-baseweb="tab"] {{ color: {CREAM}; font-weight: 600; }}
    .stTabs [aria-selected="true"] {{ color: {GOLD} !important; border-bottom-color: {GOLD} !important; }}
    .stButton>button, .stFormSubmitButton>button {{
        background-color: {GOLD} !important;
        color: {INK} !important;
        border-radius: 8px !important;
        font-weight: 700;
        border: none;
        width: 100%;
    }}
    .stButton>button:hover, .stFormSubmitButton>button:hover {{
        background-color: {CREAM} !important;
        color: {FOREST} !important;
    }}
</style>
""", unsafe_allow_html=True)

# --- ۲. اتصال به Supabase ---
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
    key = st.secrets["connections"]["supabase"]["SUPABASE_PUBLISHABLE_KEY"]
    return create_client(url, key)

supabase = get_supabase()
today = datetime.now().strftime("%Y-%m-%d")

# --- ۳. هدر و شاخص‌های کلیدی (KPIs) ---
col_logo, col_title = st.columns([1, 8])
with col_logo:
    st.markdown(f"<h1 style='color:{GOLD}; font-size: 3rem;'>🌱</h1>", unsafe_allow_html=True)
with col_title:
    st.markdown(f"<h1>Varia Studio <span style='color:{GOLD}; font-size: 1.2rem; font-weight:400;'>| Founder OS</span></h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{CREAM}; opacity:0.7;'>Mission: $1,000 MRR. Build. Sell. Learn.</p>", unsafe_allow_html=True)

st.divider()

# گرفتن آمار از Supabase
try:
    rev_data = supabase.table("revenue").select("amount").execute().data
    total_revenue = sum(item['amount'] for item in rev_data) if rev_data else 0
    
    leads_data = supabase.table("leads").select("status").execute().data
    pilots_sold = len([l for l in leads_data if l['status'] == 'Pilot Paid']) if leads_data else 0
    total_leads = len(leads_data) if leads_data else 0
    
    tasks_data = supabase.table("tasks").select("id").eq("date", today).execute().data
    tasks_today = len(tasks_data) if tasks_data else 0
except Exception as e:
    st.error(f"Database connection error: {e}")
    total_revenue, pilots_sold, total_leads, tasks_today = 0, 0, 0, 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("💰 Revenue", f"${total_revenue:,.0f} / $1k", delta=f"{int((total_revenue/1000)*100)}% Complete" if total_revenue < 1000 else "Goal Reached!")
c2.metric("🎯 Pilots Signed", f"{pilots_sold} / 5", delta="Target: 5")
c3.metric("📋 Tasks Today", tasks_today)
c4.metric("🏢 Leads Pipeline", total_leads)

st.divider()

# --- ۴. تب‌های اصلی ---
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Sales & CRM", "📅 Daily Execution", "📸 Content Studio", "📈 Analytics"])

# ==========================================
# تب ۱: فروش و مدیریت مشتریان (CRM)
# ==========================================
with tab1:
    st.subheader("Lead Pipeline (B2B)")
    
    with st.expander("➕ Add New Lead", expanded=False):
        with st.form("crm_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                company = st.text_input("Company Name (e.g., Kilter)")
                person = st.text_input("Contact Person (e.g., Tore)")
            with col2:
                email = st.text_input("Email")
                status = st.selectbox("Status", ["Contacted", "Follow-up Sent", "Meeting Scheduled", "Pilot Paid", "Lost / Rejected"])
            
            notes = st.text_area("Notes (e.g., Sent YOLOv8 proposal, waiting for reply)")
            
            if st.form_submit_button("Save Lead"):
                if company:
                    try:
                        supabase.table("leads").insert({
                            "company": company, "person": person, "email": email, 
                            "status": status, "notes": notes, "date": today
                        }).execute()
                        st.success("Lead saved to pipeline!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving lead: {e}")

    try:
        leads_res = supabase.table("leads").select("*").order("id", desc=True).execute()
        leads_df = pd.DataFrame(leads_res.data)
        
        if not leads_df.empty:
            def color_status(val):
                if val == "Pilot Paid": return 'background-color: #2F4F3A; color: #D4A24C'
                if val == "Lost / Rejected": return 'background-color: #8B0000; color: white'
                return ''
            
            # نکته مهم: در پانداس جدید به جای applymap از map استفاده می‌شود
            st.dataframe(leads_df[['company', 'person', 'email', 'status', 'notes', 'date']].style.map(color_status, subset=['status']), 
                         use_container_width=True, hide_index=True)
        else:
            st.info("Pipeline is empty. Start hunting!")
    except Exception as e:
        st.error(f"Error loading leads: {e}")

# ==========================================
# تب ۲: اجرای روزانه (تسک‌ها)
# ==========================================
with tab2:
    st.subheader("Today's Focus (3 Max)")
    
    with st.form("task_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([4, 2, 1])
        with col1:
            task_desc = st.text_input("What needs to be done?")
        with col2:
            task_cat = st.selectbox("Category", ["Sales/Outreach", "Product/Code", "Content/Brand", "Learning"])
        with col3:
            priority = st.selectbox("Priority", ["🔥 High", "⚡ Medium", "☕ Low"])
            
        if st.form_submit_button("Add Task"):
            if task_desc:
                try:
                    supabase.table("tasks").insert({
                        "task": task_desc, "category": task_cat, 
                        "priority": priority, "status": "Pending", "date": today
                    }).execute()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving task: {e}")

    try:
        tasks_res = supabase.table("tasks").select("*").eq("date", today).order("id", desc=True).execute()
        tasks_df = pd.DataFrame(tasks_res.data)
        
        if tasks_df.empty:
            st.info("No tasks for today. What's the plan?")
        else:
            for index, row in tasks_df.iterrows():
                col1, col2, col3, col4 = st.columns([1, 5, 2, 1])
                with col1:
                    is_done = row['status'] == 'Done'
                    if st.checkbox("", value=is_done, key=f"task_{row['id']}"):
                        if not is_done:
                            try:
                                supabase.table("tasks").update({"status": "Done"}).eq("id", row['id']).execute()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating task: {e}")
                with col2:
                    st.write(f"**{row['priority']}** | {row['task']}")
                with col3:
                    st.caption(f"{row['category']}")
                with col4:
                    if row['status'] == 'Done':
                        st.success("✅")
                    else:
                        st.warning("⏳")
    except Exception as e:
        st.error(f"Error loading tasks: {e}")

# ==========================================
# تب ۳: استودیوی محتوا (Content Studio)
# ==========================================
with tab3:
    st.subheader("Content Pipeline")
    st.write("Draft your LinkedIn posts and Instagram captions here before publishing.")
    
    with st.form("content_form", clear_on_submit=True):
        platform = st.selectbox("Platform", ["LinkedIn", "Instagram (Feed)", "Instagram (Story)", "X (Twitter)"])
        draft_text = st.text_area("Draft (Hook + Body + CTA)", height=150)
        
        if st.form_submit_button("Save Draft"):
            if draft_text:
                try:
                    supabase.table("content_drafts").insert({
                        "platform": platform, "draft_text": draft_text, 
                        "status": "Draft", "date": today
                    }).execute()
                    st.success("Draft saved!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving draft: {e}")
                
    try:
        drafts_res = supabase.table("content_drafts").select("*").order("id", desc=True).execute()
        drafts_df = pd.DataFrame(drafts_res.data)
        
        if not drafts_df.empty:
            for index, row in drafts_df.iterrows():
                with st.expander(f"{row['platform']} - {row['date']}"):
                    st.write(row['draft_text'])
                    if st.button("Mark as Published", key=f"pub_{row['id']}"):
                        try:
                            supabase.table("content_drafts").update({"status": "Published"}).eq("id", row['id']).execute()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating draft: {e}")
    except Exception as e:
        st.error(f"Error loading drafts: {e}")

# ==========================================
# تب ۴: آنالیتیکس و درآمد
# ==========================================
with tab4:
    st.subheader("Revenue & Analytics")
    
    with st.form("revenue_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input("Pilot Amount (USD)", min_value=50.0, step=50.0, value=200.0)
        with col2:
            source = st.text_input("Client (e.g., Kilter Pilot)")
            
        if st.form_submit_button("Log Payment"):
            if source:
                try:
                    supabase.table("revenue").insert({
                        "amount": amount, "source": source, "date": today
                    }).execute()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving payment: {e}")
                
    try:
        rev_res = supabase.table("revenue").select("*").order("date", asc=True).execute()
        rev_df = pd.DataFrame(rev_res.data)
        
        if not rev_df.empty:
            st.dataframe(rev_df, use_container_width=True, hide_index=True)
            
            rev_df['cum_sum'] = rev_df['amount'].cumsum()
            fig = px.line(rev_df, x='date', y='cum_sum', markers=True, 
                          title="Cumulative Revenue Progress",
                          labels={'cum_sum': 'Total Revenue ($)', 'date': 'Date'})
            fig.update_traces(line_color=GOLD, marker_color=CREAM)
            fig.update_layout(plot_bgcolor=INK, paper_bgcolor=INK, font_color=CREAM, title_font_color=CREAM)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No revenue logged yet. The first $200 is the hardest.")
    except Exception as e:
        st.error(f"Error loading revenue: {e}")