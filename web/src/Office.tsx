import { useCallback, useEffect, useState } from "react";
import { Activity, ArrowUpRight, Bot, Check, ClipboardCheck, Clock3, FileText, Mail, Plus, ShieldCheck, Sparkles, X } from "lucide-react";

const API = (import.meta.env.VITE_NATASHA_API_URL || "https://natasha-api.onrender.com").replace(/\/$/, "");
type Agent = {id:string;name:string;role:string;status:string;scope:string[]};
type Task = {id:string;agent:string;task_type:string;title:string;status:string;created_at:string;description?:string};
type Approval = {id:string;agent:string;action_type:string;title:string;summary:string;status:string;created_at:string};
type Content = {id:string;platform:string;account_type?:string;title:string;body:string;status:string;created_at:string};
type Overview = {tasks:number;queued_tasks:number;running_tasks:number;pending_approvals:number;content_drafts:number;agents:number;autonomy_level:string;email_provider:string};

async function api(path:string, token:string, init:RequestInit={}) {
  const res = await fetch(API+path,{...init,headers:{"Content-Type":"application/json",Authorization:`Bearer ${token}`,...(init.headers||{})}});
  const data = res.status===204?null:await res.json().catch(()=>({}));
  if(!res.ok) throw new Error(data?.detail||`Request failed (${res.status})`);
  return data;
}
const date = (s:string) => new Date(s).toLocaleString(undefined,{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"});
const names:Record<string,string>={natasha:"Natasha",marketing:"Marketing Agent",operations:"Operations Agent"};
const descriptions:Record<string,string>={
 natasha:"Finds target accounts, researches evidence, scores fit and prepares founder-reviewed outreach.",
 marketing:"Works from the approved brand strategy to prepare Instagram, LinkedIn and website content.",
 operations:"Turns project context into proposals, briefs, operating reports and delivery checklists."
};

export default function Office({token,notify}:{token:string;notify:(message:string)=>void}) {
 const [overview,setOverview]=useState<Overview|null>(null);
 const [agents,setAgents]=useState<Agent[]>([]);
 const [tasks,setTasks]=useState<Task[]>([]);
 const [approvals,setApprovals]=useState<Approval[]>([]);
 const [content,setContent]=useState<Content[]>([]);
 const [loading,setLoading]=useState(true);
 const [busy,setBusy]=useState("");
 const [error,setError]=useState("");
 const [agent,setAgent]=useState("natasha");
 const [title,setTitle]=useState("");
 const [description,setDescription]=useState("");
 const [taskType,setTaskType]=useState("research");
 const [platform,setPlatform]=useState("instagram");

 const refresh=useCallback(async()=>{
  setLoading(true);setError("");
  try{
   const [o,a,t,p,c]=await Promise.all([
    api("/api/office/overview",token),api("/api/office/agents",token),api("/api/office/tasks",token),
    api("/api/office/approvals",token),api("/api/office/content",token)
   ]);
   setOverview(o);setAgents(a);setTasks(t);setApprovals(p);setContent(c);
  }catch(e){setError(e instanceof Error?e.message:"Could not load AI Office");}
  finally{setLoading(false);}
 },[token]);
 useEffect(()=>{refresh();},[refresh]);

 async function queueTask(e:React.FormEvent){
  e.preventDefault();if(!title.trim())return;
  setBusy("queue");setError("");
  try{
   await api("/api/office/tasks",token,{method:"POST",body:JSON.stringify({agent,task_type:taskType,title,description,payload:{requested_via:"office_dashboard"},priority:3})});
   setTitle("");setDescription("");await refresh();notify("Task added to the shared office queue.");
  }catch(err){setError(err instanceof Error?err.message:"Could not queue task.");}
  finally{setBusy("");}
 }
 async function review(id:string,decision:"approved"|"rejected"){
  setBusy(id);setError("");
  try{await api(`/api/office/approvals/${id}/review`,token,{method:"POST",body:JSON.stringify({decision})});await refresh();notify(decision==="approved"?"Approval recorded. External action has not been executed.":"Request rejected.");}
  catch(err){setError(err instanceof Error?err.message:"Could not review request.");}
  finally{setBusy("");}
 }
 const pending=approvals.filter(x=>x.status==="pending");
 return <div className="office-page">
  <div className="page-heading"><div><div className="eyebrow muted">VARIA STUDIO · AI-NATIVE WORKSPACE</div><h1>Varia AI Office.</h1><p>One shared workspace. Three specialist agents. You retain control of external actions.</p></div><button className="secondary-btn" onClick={refresh}><Activity size={15}/> Refresh</button></div>
  {error&&<div className="error-banner"><span>{error}</span><button onClick={()=>setError("")}><X size={15}/></button></div>}
  <div className="office-metrics">
   <div className="metric-card"><div className="metric-top">Agents <Bot size={17}/></div><strong>{overview?.agents??3}</strong><small>Shared office team</small></div>
   <div className="metric-card"><div className="metric-top">Queued tasks <Clock3 size={17}/></div><strong>{overview?.queued_tasks??0}</strong><small>Waiting for the worker</small></div>
   <div className="metric-card"><div className="metric-top">Approvals <ClipboardCheck size={17}/></div><strong>{overview?.pending_approvals??0}</strong><small>Founder review required</small></div>
   <div className="metric-card"><div className="metric-top">Content drafts <FileText size={17}/></div><strong>{overview?.content_drafts??0}</strong><small>Not published</small></div>
  </div>
  <div className="office-policy"><ShieldCheck size={18}/><div><strong>Limited autonomy is active</strong><span>Gmail selected · first-touch emails, public posts, pricing, negotiations, contracts and financial commitments remain approval-gated.</span></div><span className="policy-chip">HUMAN CONTROL</span></div>
  <section className="office-agents">
   {agents.map(a=><article className="panel office-agent" key={a.id}><div className="office-agent-top"><div className="office-agent-icon"><Bot size={20}/></div><span className={`agent-state ${a.status}`}>{a.status==="active"?"CONNECTED":"CONFIGURED"}</span></div><h3>{a.name}</h3><div className="office-role">{a.role}</div><p>{descriptions[a.id]}</p><div className="office-scope">{a.scope.slice(0,4).map(s=><span key={s}>{s.replaceAll("_"," ")}</span>)}</div><button className="text-btn" onClick={()=>{setAgent(a.id);setTaskType(a.id==="natasha"?"research":a.id==="marketing"?"content_draft":"proposal");document.getElementById("office-task-title")?.focus();}}>Assign a task <ArrowUpRight size={14}/></button></article>)}
  </section>
  <div className="office-columns">
   <section className="panel office-task-panel"><div className="panel-head"><div><h3>Assign work</h3><p>Add a task to the shared queue.</p></div><Sparkles size={18}/></div>
    <form onSubmit={queueTask}>
     <label>Agent</label><select value={agent} onChange={e=>{setAgent(e.target.value);setTaskType(e.target.value==="natasha"?"research":e.target.value==="marketing"?"content_draft":"proposal");}}><option value="natasha">Natasha · Growth & Sales</option><option value="marketing">Marketing Agent · Brand & Content</option><option value="operations">Operations Agent · Studio Ops</option></select>
     <label>Task type</label><select value={taskType} onChange={e=>setTaskType(e.target.value)}>{(agent==="natasha"?[["research","Market research"],["lead_review","Review existing leads"],["outreach_draft","Prepare outreach draft"]]:agent==="marketing"?[["content_draft","Create content draft"],["linkedin_plan","LinkedIn planning"],["website_review","Website review"]]:[["proposal","Prepare proposal"],["project_brief","Project brief"],["operations_report","Operations report"]]).map(([v,l])=><option value={v} key={v}>{l}</option>)}</select>
     <label>Task title</label><input id="office-task-title" value={title} onChange={e=>setTitle(e.target.value)} placeholder="What needs to get done?" required/>
     <label>Context / instructions</label><textarea value={description} onChange={e=>setDescription(e.target.value)} placeholder="Add the outcome, source material or constraints…" rows={4}/>
     <button className="primary-btn full" disabled={busy==="queue"||!title.trim()}>{busy==="queue"?"Adding…":<><Plus size={15}/> Add to task queue</>}</button>
    </form>
    <div className="office-footnote"><ShieldCheck size={14}/> Task creation does not authorize external communication or publication.</div>
   </section>
   <section className="panel"><div className="panel-head"><div><h3>Recent tasks</h3><p>Shared activity across the three agents</p></div><span className="small-count">{tasks.length}</span></div>
    {tasks.slice(0,8).map(t=><div className="list-row" key={t.id}><div className="job-icon"><Bot size={16}/></div><div className="row-main"><strong>{t.title}</strong><small>{names[t.agent]||t.agent} · {date(t.created_at)}</small></div><span className={`status-text ${t.status}`}>{t.status.replaceAll("_"," ")}</span></div>)}
    {!tasks.length&&<div className="empty-note"><Clock3 size={18}/> {loading?"Loading tasks…":"No office tasks yet."}</div>}
   </section>
  </div>
  <div className="office-columns">
   <section className="panel"><div className="panel-head"><div><h3>Approval centre</h3><p>External actions are never silently executed.</p></div><span className="small-count">{pending.length} pending</span></div>
    {pending.map(p=><div className="approval-card" key={p.id}><div><span className="approval-type">{p.action_type.replaceAll("_"," ")}</span><strong>{p.title}</strong><p>{p.summary}</p><small>{names[p.agent]||p.agent} · {date(p.created_at)}</small></div><div className="approval-actions"><button className="secondary-btn" disabled={busy===p.id} onClick={()=>review(p.id,"approved")}><Check size={14}/> Approve</button><button className="icon-btn" disabled={busy===p.id} title="Reject" onClick={()=>review(p.id,"rejected")}><X size={16}/></button></div></div>)}
    {!pending.length&&<div className="empty-note"><ShieldCheck size={18}/> No pending approvals.</div>}
   </section>
   <section className="panel"><div className="panel-head"><div><h3>Content studio</h3><p>Drafts from the Marketing Agent</p></div><span className="small-count">{content.length} drafts</span></div>
    {content.slice(0,6).map(c=><div className="draft-mini" key={c.id}><strong>{c.title}</strong><small>{c.platform} · {c.status} · {date(c.created_at)}</small><p>{c.body.slice(0,180)}{c.body.length>180?"…":""}</p></div>)}
    {!content.length&&<div className="empty-note"><FileText size={18}/> No content drafts yet. Assign the Marketing Agent a content task.</div>}
   </section>
  </div>
  <div className="office-footer-note"><Mail size={15}/> Gmail is the selected provider. Connect and authorize the Gmail integration before enabling mailbox access or sending; this dashboard currently stores the provider preference only.</div>
 </div>;
}
