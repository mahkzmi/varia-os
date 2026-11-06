import { useEffect, useState } from "react";
import { Bot, MessageSquare, Send, Sparkles, ShieldCheck, Brain } from "lucide-react";

const API=(import.meta.env.VITE_NATASHA_API_URL||"https://natasha-api.onrender.com").replace(/\/$/,"");
async function call(path:string,token:string,body?:unknown){
 const response=await fetch(API+path,{method:body?"POST":"GET",headers:{"Content-Type":"application/json",Authorization:"Bearer "+token},body:body?JSON.stringify(body):undefined});
 const data=await response.json().catch(()=>({}));
 if(!response.ok)throw new Error(data.detail||"Request failed");
 return data;
}
export default function Office({token,notify}:{token:string;notify:(s:string)=>void}){
 const [conversations,setConversations]=useState<any[]>([]);
 const [activeConversation,setActiveConversation]=useState<any>(null);
 const [messages,setMessages]=useState<any[]>([]);
 const [chatText,setChatText]=useState("");
 const [chatBusy,setChatBusy]=useState(false);
 const [error,setError]=useState("");
 const [memories,setMemories]=useState<any[]>([]);
 const [tasks,setTasks]=useState<any[]>([]);
 const [approvals,setApprovals]=useState<any[]>([]);
 const [contentDrafts,setContentDrafts]=useState<any[]>([]);
 const [officeOverview,setOfficeOverview]=useState<any>({});
 const [memoryText,setMemoryText]=useState("");
 const [memoryBusy,setMemoryBusy]=useState(false);

 async function loadConversations(){
  try{
   const rows=await call("/api/office/conversations",token);
   setConversations(rows);
   setActiveConversation((current:any)=>current||(rows.length?rows[0]:null));
  }catch(e){setError(e instanceof Error?e.message:"Could not load conversations");}
 }
 async function loadMemories(){
  try{setMemories(await call("/api/office/memories",token));}
  catch(e){setError(e instanceof Error?e.message:"Could not load founder context");}
 }
 async function loadStudioWork(){
  try{
   const [t,a,d,o]=await Promise.all([call("/api/office/tasks",token),call("/api/office/approvals",token),call("/api/office/content",token),call("/api/office/overview",token)]);
   setTasks(t);setApprovals(a);setContentDrafts(d);setOfficeOverview(o);
  }catch(e){setError(e instanceof Error?e.message:"Could not load studio work");}
 }
 useEffect(()=>{loadConversations();loadMemories();loadStudioWork();},[token]);
 useEffect(()=>{
  if(!activeConversation?.id){setMessages([]);return;}
  let alive=true;
  call("/api/office/conversations/"+activeConversation.id+"/messages",token)
   .then(rows=>{if(alive)setMessages(rows);})
   .catch(e=>setError(e instanceof Error?e.message:"Could not load conversation"));
  return()=>{alive=false;};
 },[activeConversation?.id,token]);

 async function startConversation(){
  setChatBusy(true);setError("");
  try{
   const row=await call("/api/office/conversations",token,{agent:"natasha"});
   setActiveConversation(row);setConversations(prev=>[row,...prev]);setMessages([]);
  }catch(e){setError(e instanceof Error?e.message:"Could not start conversation");}
  finally{setChatBusy(false);}
 }
 async function sendChat(e:React.FormEvent){
  e.preventDefault();const content=chatText.trim();
  if(!content||chatBusy)return;
  setChatBusy(true);setError("");
  try{
   let conv=activeConversation;
   if(!conv){
    conv=await call("/api/office/conversations",token,{agent:"natasha"});
    setActiveConversation(conv);setConversations(prev=>[conv,...prev]);
   }
   setChatText("");
   const result=await call("/api/office/conversations/"+conv.id+"/messages",token,{content});
   setMessages((prev:any[])=>[...prev,{role:"founder",content},result.message]);
   await loadConversations();
  }catch(e){setError(e instanceof Error?e.message:"Message failed");}
  finally{setChatBusy(false);}
 }
 async function reviewApproval(id:string,decision:"approved"|"rejected"){
  try{await call("/api/office/approvals/"+id+"/review",token,{decision});await loadStudioWork();notify(decision==="approved"?"Decision recorded. No external action was sent.":"Request rejected.");}
  catch(e){setError(e instanceof Error?e.message:"Could not record decision");}
 }
 async function saveMemory(e:React.FormEvent){
  e.preventDefault();if(!memoryText.trim())return;
  setMemoryBusy(true);
  try{
   await call("/api/office/memories",token,{agent:"shared",memory_type:"founder_note",content:memoryText.trim(),importance:5});
   setMemoryText("");await loadMemories();notify("Founder context saved for Natasha.");
  }catch(e){setError(e instanceof Error?e.message:"Could not save context");}
  finally{setMemoryBusy(false);}
 }
 return <main className="office-page hq hq-single">
  <section className="hq-hero hq-hero-single">
   <div><span className="eyebrow">VARIA STUDIO · EXECUTIVE DESK</span>
    <h1>Natasha.<br/><i>Your operating partner.</i></h1>
    <p>Strategy, growth, product, brand and operations — one mind, one context, one accountable workflow.</p>
    <span className="hq-live"><span className="live-dot"/> Executive workspace</span>
   </div>
   <div className="hq-executive-mark"><Bot size={54}/><span>ONE PARTNER<br/>ALL WORKSTREAMS</span></div>
  </section>
  {error&&<div className="error-banner">{error}</div>}
  <section className="panel hq-chat hq-chat-executive">
   <div className="panel-head"><div><span className="eyebrow">PRIVATE FOUNDER CHANNEL</span><h2>Talk to Natasha</h2><p>She should challenge assumptions, make recommendations and turn decisions into next actions.</p></div><MessageSquare/></div>
   <div className="hq-chat-layout hq-chat-layout-single">
    <aside className="hq-chat-people hq-chat-history-only">
     <div className="hq-chat-avatar hq-chat-avatar-large">N</div>
     <b>Natasha</b><small>AI Executive Partner</small>
     <span className="hq-chat-description">Growth · Sales · Product · Brand · Operations</span>
     <button className="secondary-btn" onClick={startConversation} disabled={chatBusy}>New conversation</button>
     <div className="hq-chat-history"><b>Conversation history</b>
      {conversations.map(cv=><button key={cv.id} className={activeConversation?.id===cv.id?"selected":""} onClick={()=>setActiveConversation(cv)}>{cv.title||"Founder conversation"}</button>)}
     </div>
    </aside>
    <div className="hq-chat-main">
     <div className="hq-chat-stream">
      {messages.length?messages.map((m:any,i:number)=><div key={m.id||i} className={"hq-chat-bubble "+(m.role==="founder"?"founder":"agent")}><small>{m.role==="founder"?"YOU":"NATASHA"}</small><p>{m.content}</p></div>):
       <div className="hq-chat-empty"><Sparkles/><b>{activeConversation?"Natasha is ready.":"Start with the decision in front of you."}</b><span>Business context and conversation history stay connected.</span></div>}
     </div>
     <form className="hq-chat-compose" onSubmit={sendChat}>
      <textarea rows={2} value={chatText} onChange={e=>setChatText(e.target.value)} placeholder="What are we solving, deciding or building?"/>
      <button className="primary-btn" disabled={chatBusy||!chatText.trim()}>{chatBusy?"Thinking…":<><Send size={14}/> Send</>}</button>
     </form>
    </div>
   </div>
  </section>
  <section className="panel hq-queue-panel">
   <div className="panel-head"><div><span className="eyebrow">AUTONOMY · OPERATING CONTROL</span><h3>Natasha is configured to operate independently.</h3><p>Internal work runs around the clock. External actions remain channel- and policy-gated.</p></div><ShieldCheck/></div>
   <div className="hq-task"><span className="hq-task-dot"/><div><b>High autonomy · {officeOverview.active_hours||"24/7"}</b><small>Maximum {officeOverview.max_initial_messages_per_day??15} first-touch messages per day · only through a connected permitted channel</small></div></div>
   <div className="hq-task"><span className="hq-task-dot"/><div><b>{officeOverview.sales_qualified_leads??0} qualified · {officeOverview.sales_won_leads??0} won</b><small>{officeOverview.sales_open_leads??0} open sales leads · unpriced leads are not counted as revenue</small></div></div>
   <div className="hq-task"><span className="hq-task-dot"/><div><b>Outbound and publishing status</b><small>Not connected: external messages and social publishing are blocked until an approved account integration is connected.</small></div></div>
   {(()=>{const cycle=tasks.find((t:any)=>t.task_type==="autonomous_cycle"&&!String(t.title||"").toLowerCase().includes("acceptance test"));return <div className="hq-task"><span className="hq-task-dot"/><div><b>Latest daily operating report · {cycle?.status||"not run"}</b><small>{cycle?.completed_at?new Date(cycle.completed_at).toLocaleString():cycle?.created_at?new Date(cycle.created_at).toLocaleString():"No report recorded yet"}</small>{cycle?.result?.summary&&<p>{cycle.result.summary}</p>}</div></div>;})()}
  </section>
  <section className="hq-work-grid hq-work-grid-single">
   <div className="panel hq-queue-panel">
    <div className="panel-head"><div><span className="eyebrow">EXECUTION</span><h3>Work queue</h3></div><span className="small-count">{tasks.length}</span></div>
    {tasks.slice(0,4).map((t:any)=><div className="hq-task" key={t.id}><span className="hq-task-dot"/><div><b>{t.title}</b><small>Natasha · {t.status}</small>{t.result?.summary&&<p>{t.result.summary}</p>}</div></div>)}
    {!tasks.length&&<div className="empty-note">No queued studio tasks.</div>}
   </div>
   <div className="panel hq-queue-panel">
    <div className="panel-head"><div><span className="eyebrow">FOUNDER CONTROL</span><h3>Approval queue</h3></div><span className="small-count">{approvals.filter((a:any)=>a.status==="pending").length}</span></div>
    {approvals.filter((a:any)=>a.status==="pending").slice(0,3).map((a:any)=><div className="hq-approval" key={a.id}><b>{a.title}</b><p>{a.summary}</p><small>Natasha · {a.action_type}</small><div><button className="secondary-btn" onClick={()=>reviewApproval(a.id,"approved")}>Approve</button><button className="quiet-link" onClick={()=>reviewApproval(a.id,"rejected")}>Reject</button></div></div>)}
    {!approvals.some((a:any)=>a.status==="pending")&&<div className="empty-note">Nothing needs your decision.</div>}
   </div>
   <div className="panel hq-queue-panel">
    <div className="panel-head"><div><span className="eyebrow">CREATIVE OUTPUT</span><h3>Content drafts</h3></div><span className="small-count">{contentDrafts.length}</span></div>
    {contentDrafts.slice(0,3).map((d:any)=><div className="hq-content-draft" key={d.id}><b>{d.title}</b><small>{d.platform} · {d.status}</small><p>{d.body?.slice(0,180)}{(d.body?.length||0)>180?"…":""}</p></div>)}
    {!contentDrafts.length&&<div className="empty-note">No content drafts yet.</div>}
   </div>
  </section>
  <section className="panel hq-memory hq-memory-executive">
   <div className="panel-head"><div><span className="eyebrow">SHARED BUSINESS CONTEXT</span><h3>Founder notes</h3><p>Decisions and constraints Natasha must carry into future work.</p></div><Brain/></div>
   <form className="hq-memory-form" onSubmit={saveMemory}>
    <input value={memoryText} onChange={e=>setMemoryText(e.target.value)} placeholder="Add a decision, constraint, priority or important context…"/>
    <button className="secondary-btn" disabled={memoryBusy||!memoryText.trim()}>{memoryBusy?"Saving…":"Save context"}</button>
   </form>
   <div className="hq-memory-list">{memories.filter((m:any)=>m.agent==="shared"||m.agent==="natasha").slice(0,6).map((m:any)=><div key={m.id}><small>{m.memory_type||"Founder note"}</small><span>{m.content}</span></div>)}</div>
   <div className="office-footnote"><ShieldCheck size={14}/> High autonomy is active for internal work. Up to 15 first-touch messages/day are authorised only after a permitted channel is connected. Pricing exceptions, negotiations, contracts, financial commitments and website changes require founder approval.</div>
  </section>
 </main>;
}
