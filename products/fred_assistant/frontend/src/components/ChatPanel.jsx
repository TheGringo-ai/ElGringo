import { useState, useEffect, useRef } from 'react';
import { Send, Trash2, Loader2, Bot, User } from 'lucide-react';
import { fetchChatHistory, streamChat, clearChat } from '../api';

const QUICK = ['What should I focus on today?', 'Summarize my week', 'What\'s overdue?'];

export default function ChatPanel() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    fetchChatHistory().then(setMessages).catch(() => {});
  }, []);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const send = async (text) => {
    const msg = text || input.trim();
    if (!msg || streaming) return;
    setInput('');

    const userMsg = { role: 'user', content: msg };
    const assistantMsg = { role: 'assistant', content: '' };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setStreaming(true);

    let acc = '';
    await streamChat(
      msg,
      (token) => {
        acc += token;
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { ...next[next.length - 1], content: acc };
          return next;
        });
      },
      () => setStreaming(false),
      (err) => {
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { ...next[next.length - 1], content: `Error: ${err}` };
          return next;
        });
        setStreaming(false);
      }
    );
  };

  const handleClear = async () => {
    await clearChat();
    setMessages([]);
  };

  return (
    <div className="card h-full flex flex-col p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Bot size={14} className="text-blue-400" />
          <span className="text-xs font-semibold text-gray-300">Fred</span>
        </div>
        <button onClick={handleClear} className="p-1 text-gray-600 hover:text-gray-400"><Trash2 size={11} /></button>
      </div>

      {/* Quick actions */}
      <div className="flex gap-1 mb-2 overflow-x-auto">
        {QUICK.map((q) => (
          <button key={q} onClick={() => send(q)} disabled={streaming}
            className="flex-shrink-0 text-[10px] px-2 py-0.5 rounded-full bg-white/5 text-gray-500 hover:bg-white/10 hover:text-gray-300 disabled:opacity-40">
            {q}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-2 mb-2 min-h-0">
        {messages.length === 0 && (
          <div className="text-[11px] text-gray-700 text-center py-6">Ask Fred anything...</div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'flex-row-reverse' : ''} animate-fade-in`}>
            <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${
              m.role === 'assistant' ? 'bg-blue-500/20 text-blue-400' : 'bg-white/10 text-gray-400'
            }`}>
              {m.role === 'assistant' ? <Bot size={10} /> : <User size={10} />}
            </div>
            <div className={`max-w-[85%] text-xs leading-relaxed px-2.5 py-1.5 rounded-xl whitespace-pre-wrap ${
              m.role === 'assistant' ? 'bg-white/5 text-gray-300 rounded-tl-sm' : 'bg-blue-500/15 text-blue-100 rounded-tr-sm'
            }`}>{m.content || '...'}</div>
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <input value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="Talk to Fred..." disabled={streaming} className="input flex-1 text-xs" />
        <button onClick={() => send()} disabled={streaming || !input.trim()}
          className="btn-primary disabled:opacity-40 px-2">
          {streaming ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
        </button>
      </div>
    </div>
  );
}
