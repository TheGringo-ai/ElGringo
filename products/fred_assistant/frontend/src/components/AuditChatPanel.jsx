import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Bot, User, X } from 'lucide-react';
import { streamAuditChat } from '../api';

const QUICK_ACTIONS = [
  'Explain the most critical finding',
  'Prioritize by impact',
  'Suggest a fix plan',
];

const FINDING_QUICK_ACTIONS = [
  'Explain this vulnerability',
  'Show the complete fix',
  'How severe is this?',
];

export default function AuditChatPanel({ projectName, findings, focusedFinding, onClose }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const quickActions = focusedFinding ? FINDING_QUICK_ACTIONS : QUICK_ACTIONS;

  const send = async (text) => {
    const msg = text || input.trim();
    if (!msg || streaming) return;
    setInput('');

    const userMsg = { role: 'user', content: msg };
    const assistantMsg = { role: 'assistant', content: '' };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setStreaming(true);

    let acc = '';
    await streamAuditChat(
      projectName,
      msg,
      findings,
      focusedFinding?.id || null,
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
      },
    );
  };

  return (
    <div className="mt-2 border border-white/5 rounded bg-white/[0.02] overflow-hidden">
      <div className="flex items-center justify-between px-2 py-1.5 border-b border-white/5">
        <div className="flex items-center gap-1.5">
          <Bot size={10} className="text-purple-400" />
          <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
            {focusedFinding ? `Discuss: ${focusedFinding.title}` : 'Audit Chat'}
          </span>
        </div>
        <button onClick={onClose} className="text-gray-600 hover:text-gray-400"><X size={10} /></button>
      </div>

      {/* Quick actions */}
      <div className="flex gap-1 p-1.5 overflow-x-auto">
        {quickActions.map((q) => (
          <button key={q} onClick={() => send(q)} disabled={streaming}
            className="flex-shrink-0 text-[9px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 disabled:opacity-40">
            {q}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="max-h-48 overflow-y-auto space-y-1.5 px-2 pb-1.5">
        {messages.length === 0 && (
          <div className="text-[10px] text-gray-700 text-center py-3">
            Ask about the audit findings...
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-1.5 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 ${
              m.role === 'assistant' ? 'bg-purple-500/20 text-purple-400' : 'bg-white/10 text-gray-400'
            }`}>
              {m.role === 'assistant' ? <Bot size={8} /> : <User size={8} />}
            </div>
            <div className={`max-w-[85%] text-[10px] leading-relaxed px-2 py-1 rounded-lg whitespace-pre-wrap ${
              m.role === 'assistant' ? 'bg-white/5 text-gray-300 rounded-tl-sm' : 'bg-purple-500/15 text-purple-100 rounded-tr-sm'
            }`}>{m.content || '...'}</div>
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="flex gap-1.5 p-1.5 border-t border-white/5">
        <input value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="Ask about findings..."
          disabled={streaming} className="input flex-1 text-[10px] py-1" />
        <button onClick={() => send()} disabled={streaming || !input.trim()}
          className="px-1.5 py-1 rounded bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 disabled:opacity-40">
          {streaming ? <Loader2 size={10} className="animate-spin" /> : <Send size={10} />}
        </button>
      </div>
    </div>
  );
}
