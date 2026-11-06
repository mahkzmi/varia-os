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
 useEffect(()=>{loadConversations();loadMemories();},[token]);
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
  <section className="panel hq-memory hq-memory-executive">
   <div className="panel-head"><div><span className="eyebrow">SHARED BUSINESS CONTEXT</span><h3>Founder notes</h3><p>Decisions and constraints Natasha must carry into future work.</p></div><Brain/></div>
   <form className="hq-memory-form" onSubmit={saveMemory}>
    <input value={memoryText} onChange={e=>setMemoryText(e.target.value)} placeholder="Add a decision, constraint, priority or important context…"/>
    <button className="secondary-btn" disabled={memoryBusy||!memoryText.trim()}>{memoryBusy?"Saving…":"Save context"}</button>
   </form>
   <div className="hq-memory-list">{memories.filter((m:any)=>m.agent==="shared"||m.agent==="natasha").slice(0,6).map((m:any)=><div key={m.id}><small>{m.memory_type||"Founder note"}</small><span>{m.content}</span></div>)}</div>
   <div className="office-footnote"><ShieldCheck size={14}/> Natasha can prepare work and recommendations. External messages, publishing, financial commitments and contracts still require your explicit approval.</div>
  </section>
 </main>;
}
