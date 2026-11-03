import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity, ArrowDownRight, ArrowUpRight, Bell, Bot, BriefcaseBusiness, Building2, CalendarClock,
  Check, ChevronDown, CircleHelp, Clock3, Command, Compass, CreditCard, FileText, Filter, FlaskConical,
  Gauge, Globe2, Leaf, LayoutDashboard, LogOut, Mail, Menu, MessageSquareText, MoreHorizontal,
  Plus, Search, Send, Settings2, ShieldCheck, Sparkles, Sprout, Target, TrendingUp, Users, X, Zap
} from "lucide-react";

const API = (import.meta.env.VITE_NATASHA_API_URL || "https://natasha-api.onrender.com").replace(/\/$/, "");
const PRODUCTS = ["Varia Vision", "Varia Carbon", "Varia Trait-Bridge"];
type AnyRow = Record<string, any>;
type Section = "Overview" | "Natasha" | "Pipeline" | "Companies" | "Contacts" | "Drafts" | "Activity";

async function request(path: string, token?: string, options: RequestInit = {}) {
  const response = await fetch(API + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {})
    }
  });
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data?.detail || data?.message || `Request failed (${response.status})`);
  return data;
}
const money = (value: number, currency = "USD") => new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(value || 0);
const dateLabel = (value?: string) => value ? new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "—";
const initials = (value = "Varia Studio") => value.split(" ").slice(0, 2).map(x => x[0]).join("").toUpperCase();

function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem("varia_access_token") || "");
  const [userEmail, setUserEmail] = useState(() => sessionStorage.getItem("varia_user_email") || "");
  const [section, setSection] = useState<Section>("Overview");
  const [data, setData] = useState<{leads:AnyRow[];companies:AnyRow[];contacts:AnyRow[];drafts:AnyRow[];followUps:AnyRow[];jobs:AnyRow[]}>({
    leads: [], companies: [], contacts: [], drafts: [], followUps: [], jobs: []
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [search, setSearch] = useState("");
  const [mobileNav, setMobileNav] = useState(false);
  const [showCompany, setShowCompany] = useState(false);
  const [showLead, setShowLead] = useState(false);
  const [showContact, setShowContact] = useState(false);

  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [authBusy, setAuthBusy] = useState(false);
  const [mission, setMission] = useState({ product: "Varia Vision", target_market: "Netherlands", ideal_customer: "Agricultural technology companies, crop consultants, and precision-agriculture providers that use drone or field imagery and may need crop/weed detection.", max_companies: 5 });
  const [missionBusy, setMissionBusy] = useState(false);
  const [companyForm, setCompanyForm] = useState({name:"",website:"",industry:"",country:"",notes:""});
  const [leadForm, setLeadForm] = useState({product:"Varia Vision",stage:"new",source:"manual",notes:"",next_action:""});
  const [contactForm, setContactForm] = useState({full_name:"",company_id:"",role:"",email:"",linkedin_url:"",is_decision_maker:false});

  const notify = (message: string) => { setToast(message); window.setTimeout(() => setToast(""), 3200); };
  const loadData = useCallback(async () => {
    if (!token) return;
    setLoading(true); setError("");
    try {
      const [leads, companies, contacts, drafts, followUps, jobs] = await Promise.all([
        request("/api/leads", token), request("/api/companies", token), request("/api/contacts", token),
        request("/api/drafts", token), request("/api/follow-ups", token), request("/api/jobs", token)
      ]);
      setData({leads, companies, contacts, drafts, followUps, jobs});
    } catch (e) {
      const message = e instanceof Error ? e.message : "Could not load workspace";
      setError(message);
      if (/token|auth|401|unauthorized/i.test(message)) logout();
    } finally { setLoading(false); }
  }, [token]);

  useEffect(() => { if (token) loadData(); }, [token, loadData]);
  useEffect(() => {
    if (!toast) return;
    const id = window.setTimeout(() => setToast(""), 3200);
    return () => window.clearTimeout(id);
  }, [toast]);

  function logout() {
    sessionStorage.removeItem("varia_access_token"); sessionStorage.removeItem("varia_user_email");
    setToken(""); setUserEmail(""); setOtpSent(false); setOtp(""); setData({leads:[],companies:[],contacts:[],drafts:[],followUps:[],jobs:[]});
  }
  async function sendOtp() {
    if (!email.includes("@")) { setError("Enter a valid email address."); return; }
    setAuthBusy(true); setError("");
    try { await request("/api/auth/otp/request", undefined, {method:"POST",body:JSON.stringify({email})}); setOtpSent(true); notify("A sign-in code has been sent."); }
    catch(e) { setError(e instanceof Error ? e.message : "Could not send code."); }
    finally { setAuthBusy(false); }
  }
  async function verifyOtp() {
    setAuthBusy(true); setError("");
    try {
      const result = await request("/api/auth/otp/verify", undefined, {method:"POST",body:JSON.stringify({email,token:otp})});
      sessionStorage.setItem("varia_access_token",result.access_token); sessionStorage.setItem("varia_user_email",result.user?.email || email);
      setUserEmail(result.user?.email || email); setToken(result.access_token); notify("Welcome to Varia OS.");
    } catch(e) { setError(e instanceof Error ? e.message : "Invalid or expired code."); }
    finally { setAuthBusy(false); }
  }
  async function runMission() {
    setMissionBusy(true); setError("");
    try {
      const result = await request("/api/agent/run", token, {method:"POST",body:JSON.stringify(mission)});
      notify(result.status === "no_results" ? "No qualified research results this time." : `Research complete · ${result.leads_created || 0} leads created`);
      await loadData();
    } catch(e) { setError(e instanceof Error ? e.message : "Research failed."); }
    finally { setMissionBusy(false); }
  }
  async function createRecord(path: string, payload: AnyRow, close: () => void) {
    try { await request(path, token, {method:"POST",body:JSON.stringify(payload)}); close(); await loadData(); notify("Saved to Varia OS."); }
    catch(e) { setError(e instanceof Error ? e.message : "Could not save record."); }
  }
  async function approveDraft(id: string) {
    try { await request(`/api/drafts/${id}/approve`,token,{method:"POST"}); await loadData(); notify("Draft approved. It has not been sent."); }
    catch(e) { setError(e instanceof Error ? e.message : "Could not approve draft."); }
  }

  const companyMap = useMemo(() => Object.fromEntries(data.companies.map(c => [c.id,c])), [data.companies]);
  const stats = useMemo(() => ({
    leads: data.leads.length, qualified: data.leads.filter(x => ["qualified","proposal","pilot","won"].includes(x.stage)).length,
    companies: data.companies.length, drafts: data.drafts.filter(x => x.status === "draft").length,
    pipeline: data.leads.reduce((sum,x) => sum + Number(x.estimated_value || 0),0)
  }), [data]);
  const nav: {label:Section;icon:any;group:string}[] = [
    {label:"Overview",icon:LayoutDashboard,group:"WORKSPACE"},
    {label:"Natasha",icon:Bot,group:"WORKSPACE"},
    {label:"Pipeline",icon:Target,group:"GROWTH"},
    {label:"Companies",icon:Building2,group:"GROWTH"},
    {label:"Contacts",icon:Users,group:"GROWTH"},
    {label:"Drafts",icon:MessageSquareText,group:"GROWTH"},
    {label:"Activity",icon:Activity,group:"SYSTEM"}
  ];
  const filteredLeads = data.leads.filter(x => [x.product,x.stage,x.notes,companyMap[x.company_id]?.name].join(" ").toLowerCase().includes(search.toLowerCase()));

  if (!token) return <div className="auth-shell">
    <div className="auth-visual">
      <div className="auth-brand"><span className="brand-mark"><Sprout size={22}/></span><span>VARIA<span className="brand-light"> OS</span></span></div>
      <div className="auth-message"><div className="eyebrow"><span className="live-dot"/> STUDIO OPERATING SYSTEM</div><h1>Build with<br/><em>intelligence.</em></h1><p>One calm, focused workspace for the work that moves Varia forward.</p></div>
      <div className="auth-foot"><span>INDEPENDENT AGTECH STUDIO</span><span>FROM IRAN · FOR THE WORLD</span></div>
    </div>
    <div className="auth-panel">
      <div className="auth-form">
        <div className="mobile-brand"><Sprout/> VARIA OS</div>
        <span className="eyebrow muted">YOUR WORKSPACE</span><h2>{otpSent ? "Check your inbox." : "Welcome back."}</h2>
        <p>{otpSent ? `We sent a sign-in code to ${email}. Enter it below to continue.` : "Sign in to your studio workspace. No password required."}</p>
        {!otpSent ? <><label>Email address</label><input type="email" placeholder="you@company.com" value={email} onChange={e=>setEmail(e.target.value)} onKeyDown={e=>e.key==="Enter"&&sendOtp()}/><button className="primary-btn full" onClick={sendOtp} disabled={authBusy}>{authBusy?"Sending code…":"Continue with email"} <ArrowUpRight size={17}/></button></> :
          <><label>6-digit verification code</label><input className="otp-input" inputMode="numeric" autoFocus maxLength={8} placeholder="000000" value={otp} onChange={e=>setOtp(e.target.value.replace(/\D/g,""))} onKeyDown={e=>e.key==="Enter"&&verifyOtp()}/><button className="primary-btn full" onClick={verifyOtp} disabled={authBusy || otp.length<6}>{authBusy?"Verifying…":"Verify and enter"} <ArrowUpRight size={17}/></button><button className="text-btn" onClick={()=>{setOtpSent(false);setOtp("");}}>Use a different email</button></>}
        {error && <div className="error-box">{error}</div>}
        <div className="auth-secure"><ShieldCheck size={15}/> Secure, passwordless access powered by Supabase Auth</div>
      </div>
      <div className="auth-copyright">© 2026 Varia Studio. All systems thoughtfully built.</div>
    </div>
  </div>;

  return <div className="app-shell">
    <aside className={`sidebar ${mobileNav?"open":""}`}>
      <div className="sidebar-brand"><span className="brand-mark"><Sprout size={21}/></span><span>VARIA<span className="brand-light"> OS</span></span><button className="icon-btn mobile-close" onClick={()=>setMobileNav(false)}><X size={18}/></button></div>
      <div className="workspace-switch"><div className="workspace-avatar">V</div><div><strong>Varia Studio</strong><small>Founder workspace</small></div><ChevronDown size={15}/></div>
      {["WORKSPACE","GROWTH","SYSTEM"].map(group=><div className="nav-group" key={group}><div className="nav-label">{group}</div>{nav.filter(item=>item.group===group).map(item=><button key={item.label} className={`nav-item ${section===item.label?"active":""}`} onClick={()=>{setSection(item.label);setMobileNav(false);}}><item.icon size={17}/><span>{item.label}</span>{item.label==="Natasha"&&<span className="nav-pill">AI</span>}{item.label==="Drafts"&&stats.drafts>0&&<span className="nav-count">{stats.drafts}</span>}</button>)}</div>)}
      <div className="sidebar-bottom"><div className="sidebar-status"><span className="live-dot"/> All systems operational</div><div className="profile-row"><div className="profile-avatar">{initials(userEmail)}</div><div className="profile-meta"><strong>{userEmail.split("@")[0]}</strong><small>Founder · Admin</small></div><button className="icon-btn" title="Sign out" onClick={logout}><LogOut size={16}/></button></div></div>
    </aside>
    {mobileNav&&<div className="mobile-scrim" onClick={()=>setMobileNav(false)}/>}
    <main className="main-area">
      <header className="topbar"><div className="topbar-left"><button className="icon-btn mobile-menu" onClick={()=>setMobileNav(true)}><Menu size={19}/></button><div className="breadcrumb">Varia Studio <span>/</span> <strong>{section}</strong></div></div><div className="topbar-right"><div className="system-chip"><span className="live-dot"/> LIVE</div><button className="icon-btn" title="Refresh workspace" onClick={loadData}><Activity size={17}/></button><div className="top-avatar">{initials(userEmail)}</div></div></header>
      <div className="content-wrap">
        {error&&<div className="error-banner"><span>{error}</span><button onClick={()=>setError("")}><X size={16}/></button></div>}
        {section==="Overview"&&<Overview stats={stats} data={data} companyMap={companyMap} setSection={setSection} loading={loading}/>}
        {section==="Natasha"&&<Natasha mission={mission} setMission={setMission} runMission={runMission} busy={missionBusy} jobs={data.jobs} drafts={data.drafts} leads={data.leads} companies={data.companies} companyMap={companyMap} approveDraft={approveDraft} setSection={setSection}/>}
        {section==="Pipeline"&&<Pipeline leads={filteredLeads} companies={data.companies} companyMap={companyMap} search={search} setSearch={setSearch} onAdd={()=>setShowLead(true)}/>}
        {section==="Companies"&&<Companies companies={data.companies} search={search} setSearch={setSearch} onAdd={()=>setShowCompany(true)}/>}
        {section==="Contacts"&&<Contacts contacts={data.contacts} companies={data.companies} search={search} setSearch={setSearch} onAdd={()=>setShowContact(true)}/>}
        {section==="Drafts"&&<Drafts drafts={data.drafts} approveDraft={approveDraft} companyMap={companyMap}/>}
        {section==="Activity"&&<ActivityView jobs={data.jobs} followUps={data.followUps}/>}
      </div>
      <footer className="footer"><span>VARIA OS <span className="footer-dot">·</span> BUILT FOR THE FIELD</span><span>Independent intelligence for modern agriculture</span></footer>
    </main>
    {showCompany&&<Modal title="Add company" onClose={()=>setShowCompany(false)}><form onSubmit={e=>{e.preventDefault();createRecord("/api/companies",companyForm,()=>setShowCompany(false));}}><Field label="Company name" value={companyForm.name} onChange={v=>setCompanyForm({...companyForm,name:v})} required/><Field label="Website" value={companyForm.website} onChange={v=>setCompanyForm({...companyForm,website:v})} placeholder="https://"/><div className="form-grid"><Field label="Industry" value={companyForm.industry} onChange={v=>setCompanyForm({...companyForm,industry:v})}/><Field label="Country" value={companyForm.country} onChange={v=>setCompanyForm({...companyForm,country:v})}/></div><Field label="Notes" value={companyForm.notes} onChange={v=>setCompanyForm({...companyForm,notes:v})}/><button className="primary-btn full">Save company</button></form></Modal>}
    {showLead&&<Modal title="Create lead" onClose={()=>setShowLead(false)}><form onSubmit={e=>{e.preventDefault();createRecord("/api/leads",{...leadForm,estimated_value:null,currency:"USD"},()=>setShowLead(false));}}><label>Product</label><select value={leadForm.product} onChange={e=>setLeadForm({...leadForm,product:e.target.value})}>{PRODUCTS.map(x=><option key={x}>{x}</option>)}</select><label>Stage</label><select value={leadForm.stage} onChange={e=>setLeadForm({...leadForm,stage:e.target.value})}>{["new","researching","qualified","contacted","replied","meeting","proposal","pilot","won","disqualified","lost"].map(x=><option key={x}>{x}</option>)}</select><Field label="Next action" value={leadForm.next_action} onChange={v=>setLeadForm({...leadForm,next_action:v})}/><label>Notes</label><textarea value={leadForm.notes} onChange={e=>setLeadForm({...leadForm,notes:e.target.value})}/><button className="primary-btn full">Create lead</button></form></Modal>}
    {showContact&&<Modal title="Add contact" onClose={()=>setShowContact(false)}><form onSubmit={e=>{e.preventDefault();createRecord("/api/contacts",{...contactForm,company_id:contactForm.company_id||null},()=>setShowContact(false));}}><Field label="Full name" value={contactForm.full_name} onChange={v=>setContactForm({...contactForm,full_name:v})} required/><label>Company</label><select value={contactForm.company_id} onChange={e=>setContactForm({...contactForm,company_id:e.target.value})}><option value="">No company linked</option>{data.companies.map(c=><option value={c.id} key={c.id}>{c.name}</option>)}</select><Field label="Role" value={contactForm.role} onChange={v=>setContactForm({...contactForm,role:v})}/><Field label="Email" value={contactForm.email} onChange={v=>setContactForm({...contactForm,email:v})}/><Field label="LinkedIn URL" value={contactForm.linkedin_url} onChange={v=>setContactForm({...contactForm,linkedin_url:v})}/><button className="primary-btn full">Save contact</button></form></Modal>}
    {toast&&<div className="toast"><Check size={16}/>{toast}</div>}
  </div>;
}

function PageHeading({eyebrow,title,subtitle,action}:{eyebrow:string;title:string;subtitle:string;action?:any}) {
  return <div className="page-heading"><div><div className="eyebrow muted">{eyebrow}</div><h1>{title}</h1><p>{subtitle}</p></div>{action}</div>;
}
function Overview({stats,data,companyMap,setSection,loading}:any) {
  const latest = [...data.leads].slice(0,5);
  const pending = data.drafts.filter((x:AnyRow)=>x.status==="draft").slice(0,3);
  return <><PageHeading eyebrow="MONDAY, NOVEMBER 03 · STUDIO SNAPSHOT" title="Good work starts with clarity." subtitle="Your studio, your pipeline, and the next move — all in one place." action={<button className="secondary-btn" onClick={()=>setSection("Natasha")}><Sparkles size={16}/> Ask Natasha</button>}/>
    <div className="hero-panel"><div className="hero-copy"><div className="hero-kicker"><span className="live-dot"/> YOUR STUDIO AT A GLANCE</div><h2>Build deliberately.<br/><em>Grow intelligently.</em></h2><p>Small, focused moves compound. Here’s where Varia stands today.</p><button className="hero-link" onClick={()=>setSection("Natasha")}>Launch a research mission <ArrowUpRight size={16}/></button></div><div className="hero-art"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="orbit-core"><Sprout size={42}/></div><span className="orbit-tag tag-one">SOIL INTELLIGENCE</span><span className="orbit-tag tag-two">COMPUTER VISION</span><span className="orbit-tag tag-three">DECISION SUPPORT</span></div></div>
    <div className="metric-grid"><Metric icon={Target} label="Active leads" value={stats.leads} note={`${stats.qualified} qualified opportunities`} accent="green"/><Metric icon={Building2} label="Companies tracked" value={stats.companies} note="Across your target markets"/><Metric icon={MessageSquareText} label="Drafts to review" value={stats.drafts} note="Human approval required" accent="gold"/><Metric icon={TrendingUp} label="Pipeline value" value={money(stats.pipeline)} note="Estimated opportunity value"/></div>
    <div className="section-grid"><section className="panel"><div className="panel-head"><div><h3>Recent pipeline</h3><p>Your latest opportunities</p></div><button className="quiet-link" onClick={()=>setSection("Pipeline")}>View all <ArrowUpRight size={14}/></button></div>{loading?<Skeleton/>:latest.length?latest.map((lead:AnyRow)=><div className="list-row" key={lead.id}><div className="row-avatar">{initials(companyMap[lead.company_id]?.name || lead.product)}</div><div className="row-main"><strong>{companyMap[lead.company_id]?.name || lead.product}</strong><small>{lead.product} · {dateLabel(lead.created_at)}</small></div><Stage stage={lead.stage}/></div>):<Empty title="No leads yet" body="Start by asking Natasha to research your next market." action={()=>setSection("Natasha")}/>}</section>
      <section className="panel"><div className="panel-head"><div><h3>Needs your attention</h3><p>Human decisions, not autopilot</p></div><span className="small-count">{pending.length} pending</span></div>{pending.length?pending.map((draft:AnyRow)=><div className="attention-row" key={draft.id}><div className="attention-icon"><Mail size={17}/></div><div className="row-main"><strong>{draft.subject || "Outreach draft"}</strong><small>{draft.recipient || "Recipient not verified"}</small></div><button className="round-arrow" onClick={()=>setSection("Drafts")}><ArrowUpRight size={16}/></button></div>):<div className="empty-note"><ShieldCheck size={22}/><span>All caught up. New drafts will appear here for your review.</span></div>}</section></div>
    <div className="bottom-note"><div className="note-icon"><Leaf size={18}/></div><div><strong>From Iran · For the world</strong><span>Independent AI tools for modern agriculture. Soil intelligence, computer vision, and decision support.</span></div><span className="note-tag">VARIA STUDIO</span></div>
  </>;
}
function Metric({icon:Icon,label,value,note,accent}:any){return <div className="metric-card"><div className="metric-top"><span>{label}</span><div className={`metric-icon ${accent||""}`}><Icon size={17}/></div></div><strong>{value}</strong><small>{note}</small></div>}
function Natasha({mission,setMission,runMission,busy,jobs,drafts,leads,companies,companyMap,approveDraft,setSection}:any) {
  const pending=drafts.filter((x:AnyRow)=>x.status==="draft");
  return <><PageHeading eyebrow="INTELLIGENCE LAYER · NATASHA" title="Your research partner." subtitle="Find the right companies, understand their fit, and prepare thoughtful founder-led outreach." action={<div className="agent-status"><span className="live-dot"/> AGENT ONLINE</div>}/>
    <div className="natasha-layout"><div className="natasha-main"><div className="agent-banner"><div className="agent-avatar"><Bot size={27}/><span/></div><div><div className="agent-name">Natasha <span className="agent-badge">AI AGENT</span></div><p>Research-led sales intelligence for Varia Studio</p></div><div className="agent-banner-right"><span>HUMAN-IN-THE-LOOP</span><ShieldCheck size={18}/></div></div>
      <div className="panel mission-panel"><div className="panel-head"><div><div className="eyebrow muted">NEW WORKFLOW</div><h3>Launch a research mission</h3><p>Natasha will search, qualify, and prepare a first-touch draft.</p></div><div className="mission-symbol"><Compass size={22}/></div></div>
        <div className="form-grid"><div><label>Product focus</label><select value={mission.product} onChange={e=>setMission({...mission,product:e.target.value})}>{PRODUCTS.map(x=><option key={x}>{x}</option>)}</select></div><div><label>Target market</label><input value={mission.target_market} onChange={e=>setMission({...mission,target_market:e.target.value})} placeholder="e.g. Netherlands"/></div></div>
        <label>Ideal customer profile</label><textarea className="mission-textarea" value={mission.ideal_customer} onChange={e=>setMission({...mission,ideal_customer:e.target.value})}/>
        <div className="mission-bottom"><div><label>Companies to research</label><select value={mission.max_companies} onChange={e=>setMission({...mission,max_companies:Number(e.target.value)})}>{[1,2,3,4,5,6,7,8,9,10].map(x=><option key={x} value={x}>{x} companies</option>)}</select></div><button className="primary-btn" onClick={runMission} disabled={busy}>{busy?<><span className="spinner"/> Researching…</>:<><Sparkles size={16}/> Start research <ArrowUpRight size={16}/></>}</button></div>
        <div className="privacy-note"><ShieldCheck size={14}/> Natasha never invents evidence. Every outreach draft waits for your approval.</div>
      </div>
      <div className="panel"><div className="panel-head"><div><h3>Mission history</h3><p>Recent research jobs</p></div><span className="small-count">{jobs.length} jobs</span></div>{jobs.length?jobs.slice(0,5).map((job:AnyRow)=><div className="list-row" key={job.id}><div className="job-icon"><Zap size={16}/></div><div className="row-main"><strong>{job.payload?.product || "Research mission"}</strong><small>{job.payload?.target_market || "Market not specified"} · {dateLabel(job.created_at)}</small></div><span className={`status-text ${job.status}`}>{job.status}</span></div>):<Empty title="No missions yet" body="Your completed and queued missions will be tracked here."/>}</div>
    </div><div className="natasha-side"><div className="panel agent-profile"><div className="profile-glow"><div className="agent-avatar large"><Bot size={31}/></div></div><h3>Natasha</h3><p>Sales intelligence agent</p><div className="profile-divider"/><div className="profile-stat"><span>Leads sourced</span><strong>{leads.length}</strong></div><div className="profile-stat"><span>Companies in CRM</span><strong>{companies.length}</strong></div><div className="profile-stat"><span>Drafts awaiting you</span><strong>{pending.length}</strong></div><div className="profile-divider"/><div className="capability"><Search size={15}/> Market & company research</div><div className="capability"><Gauge size={15}/> ICP fit qualification</div><div className="capability"><Mail size={15}/> Founder-voice outreach drafts</div><div className="capability"><ShieldCheck size={15}/> Human approval workflow</div></div>
      <div className="panel"><div className="panel-head"><div><h3>Review queue</h3><p>Drafts waiting for your decision</p></div><button className="quiet-link" onClick={()=>setSection("Drafts")}>Open <ArrowUpRight size={14}/></button></div>{pending.length?pending.slice(0,3).map((d:AnyRow)=><div className="draft-mini" key={d.id}><strong>{d.subject}</strong><small>{d.recipient}</small><button className="text-btn" onClick={()=>approveDraft(d.id)}>Approve draft <Check size={14}/></button></div>):<div className="empty-note"><Check size={18}/> No pending drafts</div>}</div>
    </div></div>
  </>;
}
function Pipeline({leads,companies,companyMap,search,setSearch,onAdd}:any){return <><PageHeading eyebrow="GROWTH · CRM" title="Pipeline." subtitle="Track every opportunity from first signal to signed pilot." action={<button className="primary-btn" onClick={onAdd}><Plus size={16}/> Add lead</button>}/><div className="toolbar"><div className="searchbox"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search leads, products, notes…"/></div><div className="toolbar-meta"><Filter size={15}/>{leads.length} records</div></div><div className="panel table-panel"><div className="table-wrap"><table><thead><tr><th>COMPANY / OPPORTUNITY</th><th>PRODUCT</th><th>STAGE</th><th>FIT SCORE</th><th>VALUE</th><th>NEXT ACTION</th><th>CREATED</th></tr></thead><tbody>{leads.map((x:AnyRow)=><tr key={x.id}><td><div className="table-primary">{companyMap[x.company_id]?.name || "Unlinked opportunity"}</div><div className="table-secondary">{x.source || "Manual entry"}</div></td><td>{x.product}</td><td><Stage stage={x.stage}/></td><td><FitScore score={x.fit_score}/></td><td>{x.estimated_value?money(x.estimated_value,x.currency):"—"}</td><td>{x.next_action || "—"}</td><td>{dateLabel(x.created_at)}</td></tr>)}</tbody></table>{!leads.length&&<Empty title="Your pipeline is clear." body="Add your first lead or let Natasha discover new opportunities."/>}</div></div></>}
function Companies({companies,search,setSearch,onAdd}:any){const filtered=companies.filter((c:AnyRow)=>[c.name,c.industry,c.country].join(" ").toLowerCase().includes(search.toLowerCase()));return <><PageHeading eyebrow="GROWTH · ACCOUNTS" title="Companies." subtitle="A living map of the organizations Varia wants to work with." action={<button className="primary-btn" onClick={onAdd}><Plus size={16}/> Add company</button>}/><div className="toolbar"><div className="searchbox"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search organizations…"/></div><div className="toolbar-meta">{filtered.length} companies</div></div><div className="company-grid">{filtered.map((c:AnyRow)=><div className="panel company-card" key={c.id}><div className="company-card-top"><div className="company-symbol">{initials(c.name)}</div><span className="company-country">{c.country||"—"}</span></div><h3>{c.name}</h3><p>{c.industry||"Industry not specified"}</p>{c.website&&<a href={c.website.startsWith("http")?c.website:`https://${c.website}`} target="_blank" rel="noreferrer">{c.website.replace(/^https?:\/\//,"")} <ArrowUpRight size={13}/></a>}<div className="company-foot"><span>ADDED {dateLabel(c.created_at)}</span><span>{c.source||"CRM"}</span></div></div>)}{!filtered.length&&<div className="panel empty-company"><Empty title="No companies found" body="Add an account or start a Natasha research mission."/></div>}</div></>}
function Contacts({contacts,companies,search,setSearch,onAdd}:any){const map=Object.fromEntries(companies.map((c:AnyRow)=>[c.id,c.name]));const filtered=contacts.filter((c:AnyRow)=>[c.full_name,c.role,c.email,map[c.company_id]].join(" ").toLowerCase().includes(search.toLowerCase()));return <><PageHeading eyebrow="GROWTH · RELATIONSHIPS" title="People behind the companies." subtitle="Keep decision-makers, champions, and conversations connected." action={<button className="primary-btn" onClick={onAdd}><Plus size={16}/> Add contact</button>}/><div className="toolbar"><div className="searchbox"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search people…"/></div><div className="toolbar-meta">{filtered.length} contacts</div></div><div className="panel table-panel"><div className="table-wrap"><table><thead><tr><th>CONTACT</th><th>COMPANY</th><th>ROLE</th><th>EMAIL</th><th>LINKEDIN</th></tr></thead><tbody>{filtered.map((c:AnyRow)=><tr key={c.id}><td><div className="contact-cell"><div className="row-avatar">{initials(c.full_name)}</div><div className="table-primary">{c.full_name}</div></div></td><td>{map[c.company_id]||"—"}</td><td>{c.role||"—"}</td><td>{c.email||"—"}</td><td>{c.linkedin_url?<a href={c.linkedin_url} target="_blank" rel="noreferrer">Open profile <ArrowUpRight size={13}/></a>:"—"}</td></tr>)}</tbody></table>{!filtered.length&&<Empty title="No contacts yet" body="Add a person and connect them to a company."/></div></div></>}
function Drafts({drafts,approveDraft}:any){return <><PageHeading eyebrow="GROWTH · COMMUNICATION" title="Words worth sending." subtitle="Founder-led outreach, prepared by Natasha and reviewed by you."/><div className="draft-list">{drafts.map((d:AnyRow)=><article className="panel draft-card" key={d.id}><div className="draft-card-head"><div className="draft-type"><Mail size={16}/> OUTREACH DRAFT</div><span className={`status-badge ${d.status}`}>{d.status}</span></div><h3>{d.subject}</h3><div className="draft-to">TO <strong>{d.recipient}</strong></div><div className="draft-body">{d.body}</div><div className="draft-card-foot"><span>Created {dateLabel(d.created_at)}</span>{d.status==="draft"?<button className="secondary-btn" onClick={()=>approveDraft(d.id)}><Check size={15}/> Approve draft</button>:<span className="approved-note"><ShieldCheck size={14}/> Approved · not sent</span>}</div></article>)}{!drafts.length&&<div className="panel"><Empty title="No drafts waiting." body="Run a Natasha mission and review the outreach she prepares."/></div>}</div></>}
function ActivityView({jobs,followUps}:any){return <><PageHeading eyebrow="SYSTEM · OPERATIONS" title="Activity & follow-ups." subtitle="A clear record of background work and the next commitments."/><div className="section-grid"><section className="panel"><div className="panel-head"><div><h3>Research jobs</h3><p>Natasha mission execution</p></div></div>{jobs.map((j:AnyRow)=><div className="list-row" key={j.id}><div className="job-icon"><Zap size={16}/></div><div className="row-main"><strong>{j.payload?.product||"Agent run"} · {j.payload?.target_market||"Market"}</strong><small>{dateLabel(j.created_at)}</small></div><span className={`status-text ${j.status}`}>{j.status}</span></div>)}{!jobs.length&&<Empty title="No job activity" body="Queued missions will appear here."/ >}</section><section className="panel"><div className="panel-head"><div><h3>Follow-ups</h3><p>Keep momentum with timely next steps</p></div></div>{followUps.map((f:AnyRow)=><div className="list-row" key={f.id}><div className="attention-icon"><CalendarClock size={16}/></div><div className="row-main"><strong>{f.title}</strong><small>Due {dateLabel(f.due_at)}</small></div></div>)}{!followUps.length&&<Empty title="No follow-ups scheduled" body="Create follow-ups as your pipeline grows."/ >}</section></div></>}
function Stage({stage}:any){const s=String(stage||"new").toLowerCase();return <span className={`stage stage-${s}`}>{s.replace("_"," ")}</span>}
function FitScore({score}:any){return score===null||score===undefined?<span className="muted-text">—</span>:<span className={`fit-score ${score>=75?"high":score>=50?"mid":"low"}`}>{score}</span>}
function Empty({title,body,action}:any){return <div className="empty-state"><div className="empty-mark"><Sprout size={19}/></div><strong>{title}</strong><p>{body}</p>{action&&<button className="quiet-link" onClick={action}>Get started <ArrowUpRight size={14}/></button>}</div>}
function Skeleton(){return <div className="skeleton-block"/>}
function Field({label,value,onChange,placeholder,required}:any){return <><label>{label}</label><input required={required} value={value} onChange={e=>onChange(e.target.value)} placeholder={placeholder||""}/></>}
function Modal({title,onClose,children}:any){return <div className="modal-backdrop" onMouseDown={e=>e.target===e.currentTarget&&onClose()}><div className="modal"><div className="modal-head"><h3>{title}</h3><button className="icon-btn" onClick={onClose}><X size={18}/></button></div>{children}</div></div>}
export default App;
