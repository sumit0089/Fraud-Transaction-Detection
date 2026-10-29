import React, {useEffect, useRef, useState} from 'react';
import {MessageCircle, Send, X} from 'lucide-react';
import {request} from './api';
import {Button} from './components/ui/button';

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const launcher = useRef(null);
  const input = useRef(null);
  const log = useRef(null);
  useEffect(() => { if (open) input.current?.focus(); }, [open]);
  useEffect(() => { if (log.current) log.current.scrollTop = log.current.scrollHeight; }, [messages, busy, error, open]);
  function close() {setOpen(false); launcher.current?.focus();}
  async function send(event) {
    event.preventDefault();
    if (busy || !question.trim()) return;
    const text = question.trim();
    setBusy(true); setError('');
    try {
      const {data} = await request('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:text})});
      setMessages(items => [...items, {question:text, answer:data.answer}].slice(-10));
      setQuestion('');
    } catch (err) {setError(err.message);}
    finally {setBusy(false);}
  }
  return <div className="chat-widget">
    {open && <section className="chat-panel" aria-labelledby="chat-title" onKeyDown={e=>{if(e.key==='Escape') close();}}>
      <header className="chat-header"><div><h2 id="chat-title">SafePay assistant</h2><small>Ask a question</small></div><Button variant="ghost" className="icon-button" aria-label="Close chat" onClick={close}><X size={20}/></Button></header>
      <div className="chat-messages" ref={log} role="log" aria-label="Chat messages" aria-live="polite">
        {!messages.length && <p>Hi! How can I help? Ask a question to get started. Each question is answered independently.</p>}
        {messages.map((item,index)=><div className="chat-exchange" key={index}><p className="chat-question"><strong>You</strong>{item.question}</p><p className="chat-answer"><strong>SafePay assistant</strong>{item.answer}</p></div>)}
        {busy && <p role="status" className="chat-thinking"><span>Thinking</span><span className="typing-dots" aria-hidden="true"><i/><i/><i/></span></p>}
      </div>
      {error && <p className="chat-error" role="alert">{error}</p>}
      <form onSubmit={send} className="chat-form"><label htmlFor="chat-question">Your question</label><textarea id="chat-question" ref={input} value={question} onChange={e=>setQuestion(e.target.value)} maxLength={1200} rows={3} required disabled={busy}/><div><small>{question.length}/1200 · AI answers can be wrong</small><Button type="submit" className="chat-send" disabled={busy || !question.trim()}><Send size={15}/>Send</Button></div></form>
    </section>}
    <Button variant="ghost" ref={launcher} className="chat-launcher" aria-label={open?'Close SafePay assistant':'Open SafePay assistant'} aria-expanded={open} onClick={()=>open?close():setOpen(true)}>{open?<X size={23}/>:<MessageCircle size={25}/>}</Button>
  </div>;
}
