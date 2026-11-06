import { useEffect, useState } from "react";
import { Activity, ArrowUpRight, Bot, Check, Clock3, MessageSquare, Send, ShieldCheck, Sparkles, Users } from "lucide-react";

const API=(import.meta.env.VITE_NATASHA_API_URL||"https://natasha-api.onrender.com").replace(/\/$/,"");
const crew=[
 {id:"natasha",name:"Natasha",role:"Growth & Sales",focus:"Market research, prospects, partnerships",line:"I find the right doors to knock on.",initial:"N"},
 {id:"marketing",name:"Tony",role:"Creative Lead",focus:"Brand, content, campaigns",line:"Good work deserves a good story.",initial:"T"},
 {id:"operations",name:"Edith",role:"Chief of Staff",focus:"Planning, delivery, coordination",line:"I keep the moving parts together.",initial:"E"}
];
async function call(path:string,token:string,body?:unknown){
 const r=await fetch(API+path,{method:body?"POST":"GET",headers:{"Content-Type":"application/json",Authorization:"Bearer "+token},body:body?JSON.stringify(body):undefined});
 const data=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(data.detail||"Request failed");
 return data;
}
export default function Office({token,notify}:{token:string;notify:(s:string)=>void}){
 const [brief,setBrief]=useState("");
 const [agent,setAgent]=useState("natasha");
 const [task,setTask]=useState("");
 const [context,setContext]=useState("");
 const [tasks,setTasks]=useState<any[]>([]);
 const [approvals,setApprovals]=useState<any[]>([]);
 const [drafts,setDrafts]=useState<any[]>([]);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState("");
 const [conversations,setConversations]=useState<any[]>([]);
 const [activeConversation,setActiveConversation]=useState<any>(null);
 const [messages,setMessages]=useState<any[]>([]);
 const [chatText,setChatText]=useState("");
 const [chatBusy,setChatBusy]=useState(false);
 async function refresh(){
  try{
   const [t,a,d]=await Promise.all([call("/api/office/tasks",token),call("/api/office/approvals",token),call("/api/office/content",token)]);
   setTasks(t);setApprovals(a);setDrafts(d);
  }catch(e){setError(e instanceof Error?e.message:"Could not load office");}
 }
 useEffect(()=>{refresh();loadConversations();const id=window.setInterval(()=>{refresh();loadConversations();},30000);return()=>window.clearInterval(id);},[token]);
 async function loadConversations(){try{const rows=await call("/api/office/conversations",token);setConversations(rows);if(!activeConversation&&rows.length)setActiveConversation(rows[0]);}catch(e){setError(e instanceof Error?e.message:"Could not load conversations");}}
 useEffect(()=>{if(!activeConversation?.id){setMessages([]);return;}let alive=true;call("/api/office/conversations/"+activeConversation.id+"/messages",token).then(rows=>{if(alive)setMessages(rows);}).catch(e=>setError(e instanceof Error?e.message:"Could not load chat"));return()=>{alive=false;};},[activeConversation?.id,token]);
 async function startConversation(agentId:string){setChatBusy(true);try{const row=await call("/api/office/conversations",token,{agent:agentId});setActiveConversation(row);setConversations(prev=>[row,...prev]);setMessages([]);}catch(e){setError(e instanceof Error?e.message:"Could not start conversation");}finally{setChatBusy(false);}}
 async function sendChat(e:React.FormEvent){e.preventDefault();const content=chatText.trim();if(!content||chatBusy)return;setChatBusy(true);setError("");try{let conv=activeConversation;if(!conv){const agentId=agent;conv=await call("/api/office/conversations",token,{agent:agentId});setActiveConversation(conv);setConversations(prev=>[conv,...prev]);}setChatText("");const result=await call("/api/office/conversations/"+conv.id+"/messages",token,{content});setMessages(prev=>[...prev,{role:"founder",content},result.message]);await loadConversations();}catch(e){setError(e instanceof Error?e.message:"Message failed");}finally{setChatBusy(false);}}
 async function huddle(e:React.FormEvent){
  e.preventDefault();if(!brief.trim())return;setBusy(true);setError("");
  const b=brief.trim();
  const jobs=[
   {agent:"natasha",task_type:"research",title:"Find pilot customers for Varia Vision",description:"FOUNDER TEAM BRIEF: "+b+". Find real agricultural drone and aerial imagery providers, crop scouting and agronomy services, and AgTech crop-monitoring platforms. Return evidence-backed pilot prospects. Do not invent contacts or buyer intent.",payload:{product:"Varia Vision",target_market:"Global",max_companies:5}},
   {agent:"marketing",task_type:"content_draft",title:"Prepare Varia Vision pilot campaign",description:"FOUNDER TEAM BRIEF: "+b+". Prepare a factual sales/content asset to support pilot conversations. Describe Varia Vision as a computer-vision prototype for weed/crop detection in aerial imagery. Do not claim field validation or guaranteed performance.",payload:{platform:"linkedin",account_type:"company"}},
   {agent:"operations",task_type:"project_brief",title:"Coordinate Varia Vision pilot sprint",description:"FOUNDER TEAM BRIEF: "+b+". Create a practical coordinated sprint plan with dependencies, acceptance criteria, risks and founder decisions. Do not invent budgets or commitments.",payload:{workstream:"Varia Vision pilot acquisition",coordinate_agents:["natasha","marketing"]}}
  ];
  try{for(const j of jobs)await call("/api/office/tasks",token,{...j,priority:1,payload:{...j.payload,team_brief:b,initiated_by:"founder_huddle"}});setBrief("");await refresh();notify("All three teammates received the briefing.");}
  catch(e){setError(e instanceof Error?e.message:"Could not brief the team.");}finally{setBusy(false);}
 }
 async function assign(e:React.FormEvent){
  e.preventDefault();if(!task.trim())return;setBusy(true);setError("");
  try{await call("/api/office/tasks",token,{agent,task_type:agent==="natasha"?"research":agent==="marketing"?"content_draft":"project_brief",title:task.trim(),description:context,payload:{requested_via:"founder_desk"},priority:2});setTask("");setContext("");await refresh();notify("Assignment sent.");}
  catch(e){setError(e instanceof Error?e.message:"Could not send assignment.");}finally{setBusy(false);}
 }
 const pending=approvals.filter((x:any)=>x.status==="pending");
 return <main className="office-page hq">
  <section className="hq-hero"><div><span className="eyebrow">VARIA STUDIO · PRIVATE HQ</span><h1>Your studio.<br/><i>Your team.</i></h1><p>Set the direction. Your team will work out the next steps.</p><span className="hq-live"><span className="live-dot"/> {tasks.filter((t:any)=>["queued","running"].includes(t.status)).length} active assignments</span></div><div className="hq-room"><div className="hq-window"/><div className="hq-shelf"/><div className="hq-desk"><span/><span/></div><div className="hq-plant">✳</div></div></section>
  {error&&<div className="error-banner">{error}</div>}
  <section className="panel hq-chat"><div className="panel-head"><div><span className="eyebrow">YOUR TEAM, ONE CONVERSATION AT A TIME</span><h2>Private office chat</h2><p>Talk to Natasha, Tony or Edith. Conversations are saved and recalled next time.</p></div><MessageSquare/></div><div className="hq-chat-layout"><aside className="hq-chat-people">{crew.map(p=><button className={activeConversation?.agent===p.id?"hq-chat-person selected":"hq-chat-person"} key={p.id} onClick={()=>startConversation(p.id)}><span className="hq-chat-avatar">{p.initial}</span><span><b>{p.name}</b><small>{p.role}</small></span></button>)}<div className="hq-chat-history"><b>Recent conversations</b>{conversations.map(cv=><button key={cv.id} className={activeConversation?.id===cv.id?"selected":""} onClick={()=>setActiveConversation(cv)}>{crew.find(p=>p.id===cv.agent)?.name}: {cv.title}</button>)}</div></aside><div className="hq-chat-main"><div className="hq-chat-stream">{messages.length?messages.map((m:any,i:number)=><div key={m.id||i} className={"hq-chat-bubble "+(m.role==="founder"?"founder":"agent")}><small>{m.role==="founder"?"You":crew.find(p=>p.id===m.agent)?.name||"Teammate"}</small><p>{m.content}</p></div>):<div className="hq-chat-empty"><Sparkles/><b>{activeConversation?crew.find(p=>p.id===activeConversation.agent)?.name+" is ready.":"Choose a teammate to start."}</b><span>Your conversation history will stay here.</span></div>}</div><form className="hq-chat-compose" onSubmit={sendChat}><textarea rows={2} value={chatText} onChange={e=>setChatText(e.target.value)} placeholder="Write a message to your teammate…"/><button className="primary-btn" disabled={chatBusy||!chatText.trim()}>{chatBusy?"Thinking…":<><Send size={14}/> Send</>}</button></form></div></div></section>
  <header className="hq-heading"><div><span className="eyebrow muted">THE PEOPLE BEHIND THE WORK</span><h2>Meet your team</h2></div><button className="secondary-btn" onClick={refresh}><Activity size={15}/> Refresh</button></header>
  <section className="hq-team">{crew.map((p,i)=><article className={"hq-person p"+i} key={p.id}><div className="hq-person-top"><span className="hq-presence"><i/> Ready for work</span><Bot size={18}/></div><div className="hq-avatar">{p.initial}</div><h3>{p.name}</h3><b>{p.role}</b><p>{p.line}</p><small>{p.focus}</small></article>)}</section>
  <section className="panel hq-huddle"><div className="hq-huddle-title"><span className="hq-icon"><Users/></span><div><span className="eyebrow">FOUNDER → WHOLE TEAM</span><h2>Call a team huddle</h2><p>One briefing. Three perspectives. One coordinated mission.</p></div></div><form onSubmit={huddle}><textarea rows={3} value={brief} onChange={e=>setBrief(e.target.value)} placeholder="What should the team focus on today? e.g. Find pilot customers for Varia Vision."/><div className="hq-submit"><span><ShieldCheck size={14}/> External actions require your approval.</span><button className="primary-btn" disabled={busy||!brief.trim()}>{busy?"Briefing the team…":<>Bring everyone in <ArrowUpRight size={15}/></>}</button></div></form><div className="hq-roster"><span>Natasha · Research</span><span>Tony · Creative</span><span>Edith · Coordination</span></div></section>
  <section className="hq-work-grid"><section className="panel"><div className="panel-head"><div><h3>Studio activity</h3><p>Recent work across the team</p></div><span className="small-count">{tasks.length}</span></div>{tasks.slice(0,8).map((t:any)=><div className="hq-task" key={t.id}><span className="hq-task-dot"/><div><b>{t.title}</b><small>{crew.find(p=>p.id===t.agent)?.name||t.agent} · {t.status}</small>{t.result?.summary&&<p>{t.result.summary}</p>}</div></div>)}{!tasks.length&&<div className="empty-note"><Clock3/> Your team's activity will appear here.</div>}</section>
  <section className="panel hq-assign"><div className="panel-head"><div><h3>Talk to a teammate</h3><p>Give one person a focused assignment</p></div><MessageSquare/></div><form onSubmit={assign}><label>Teammate</label><select value={agent} onChange={e=>setAgent(e.target.value)}>{crew.map(p=><option value={p.id} key={p.id}>{p.name} · {p.role}</option>)}</select><label>Your message</label><input value={task} onChange={e=>setTask(e.target.value)} placeholder="What do you want to work on?" required/><label>More context</label><textarea rows={3} value={context} onChange={e=>setContext(e.target.value)} placeholder="Optional details…"/><button className="primary-btn full" disabled={busy||!task.trim()}><Send size={14}/> Send assignment</button></form></section></section>
  <section className="hq-work-grid"><section className="panel"><div className="panel-head"><div><h3>Founder decisions</h3><p>Requests awaiting your review</p></div><span className="small-count">{pending.length}</span></div>{pending.map((p:any)=><div className="approval-card" key={p.id}><div><b>{p.title}</b><p>{p.summary}</p><small>{p.agent}</small></div><button className="secondary-btn" onClick={async()=>{try{await call("/api/office/approvals/"+p.id+"/review",token,{decision:"approved"});await refresh();}catch(e){setError(String(e));}}}><Check size={14}/> Review</button></div>)}{!pending.length&&<div className="empty-note"><ShieldCheck/> Nothing waiting for your decision.</div>}</section><section className="panel"><div className="panel-head"><div><h3>Tony's creative desk</h3><p>Drafts awaiting review</p></div><Sparkles/></div>{drafts.slice(0,5).map((d:any)=><div className="hq-task" key={d.id}><div><b>{d.title}</b><small>{d.platform} · {d.status}</small><p>{d.body?.slice(0,160)}</p></div></div>)}{!drafts.length&&<div className="empty-note">No drafts yet.</div>}</section></section>
  <footer className="hq-foot">Varia Studio HQ · A human-led, AI-powered team. No external messages or posts are sent automatically.</footer>
 </main>;
}