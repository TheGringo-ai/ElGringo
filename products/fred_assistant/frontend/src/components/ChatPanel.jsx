import { useState, useEffect, useRef } from 'react';
import { Send, Trash2, Loader2, Bot, User, TrendingUp, Zap } from 'lucide-react';
import { fetchChatHistory, streamChat, clearChat } from '../api';

const PERSONAS = [
  { id: 'fred', label: 'Fred', icon: Bot, color: 'text-blue-400' },
  { id: 'coach', label: 'Coach', icon: TrendingUp, color: 'text-amber-400' },
];

const QUICK_FRED = ['What should I focus on today?', 'Summarize my week', 'What\'s overdue?'];
const QUICK_COACH = ['Review my goals', 'What should I prioritize?', 'Hold me accountable'];

export default function ChatPanel() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [thinking, setThinking] = useState(null); // null or string describing actions
  const [persona, setPersona] = useState('fred');
  const scrollRef = useRef(null);

  useEffect(() => {
    fetchChatHistory().then(setMessages).catch(() => {});
  }, []);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, thinking]);

  const quickActions = persona === 'coach' ? QUICK_COACH : QUICK_FRED;

  const send = async (text) => {
    const msg = text || input.trim();
    if (!msg || streaming) return;
    setInput('');

    const userMsg = { role: 'user', content: msg };
    const assistantMsg = { role: 'assistant', content: '', persona };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setStreaming(true);
    setThinking(null);

    let acc = '';
    await streamChat(
      msg,
      (token) => {
        acc += token;
        setThinking(null);
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { ...next[next.length - 1], content: acc };
          return next;
        });
      },
      () => {
        setStreaming(false);
        setThinking(null);
      },
      (err) => {
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { ...next[next.length - 1], content: `Error: ${err}` };
          return next;
        });
        setStreaming(false);
        setThinking(null);
      },
      persona,
      (isThinking, detail) => {
        setThinking(isThinking ? detail : null);
      },
    );
  };

  const handleClear = async () => {
    await clearChat();
    setMessages([]);
  };

  const PersonaIcon = PERSONAS.find((p) => p.id === persona)?.icon || Bot;
  const personaColor = PERSONAS.find((p) => p.id === persona)?.color || 'text-blue-400';

  return (
    <div className="card h-full flex flex-col p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {/* Persona selector */}
          {PERSONAS.map((p) => (
            <button key={p.id} onClick={() => setPersona(p.id)}
              className={`flex items-center gap-1 text-xs px-2 py-1 rounded-lg transition-colors ${
                persona === p.id ? 'bg-white/10 text-white' : 'text-gray-500 hover:text-gray-300'
              }`}>
              <p.icon size={12} className={persona === p.id ? p.color : ''} />
              {p.label}
            </button>
          ))}
        </div>
        <button onClick={handleClear} className="p-1 text-gray-600 hover:text-gray-400"><Trash2 size={11} /></button>
      </div>

      {/* Quick actions */}
      <div className="flex gap-1 mb-2 overflow-x-auto">
        {quickActions.map((q) => (
          <button key={q} onClick={() => send(q)} disabled={streaming}
            className="flex-shrink-0 text-[10px] px-2 py-0.5 rounded-full bg-white/5 text-gray-500 hover:bg-white/10 hover:text-gray-300 disabled:opacity-40">
            {q}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-2 mb-2 min-h-0">
        {messages.length === 0 && (
          <div className="text-[11px] text-gray-700 text-center py-6">
            {persona === 'coach' ? 'Ask your business coach anything...' : 'Ask Fred anything...'}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'flex-row-reverse' : ''} animate-fade-in`}>
            <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${
              m.role === 'assistant'
                ? m.persona === 'coach' ? 'bg-amber-500/20 text-amber-400' : 'bg-blue-500/20 text-blue-400'
                : 'bg-white/10 text-gray-400'
            }`}>
              {m.role === 'assistant'
                ? m.persona === 'coach' ? <TrendingUp size={10} /> : <Bot size={10} />
                : <User size={10} />}
            </div>
            <div className={`max-w-[85%] text-xs leading-relaxed px-2.5 py-1.5 rounded-xl whitespace-pre-wrap ${
              m.role === 'assistant' ? 'bg-white/5 text-gray-300 rounded-tl-sm' : 'bg-blue-500/15 text-blue-100 rounded-tr-sm'
            }`}>{m.content || '...'}</div>
          </div>
        ))}

        {/* Thinking indicator */}
        {thinking && (
          <div className="flex gap-2 animate-fade-in">
            <div className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 bg-purple-500/20 text-purple-400">
              <Zap size={10} />
            </div>
            <div className="text-xs text-purple-300/80 bg-purple-500/10 px-2.5 py-1.5 rounded-xl rounded-tl-sm flex items-center gap-1.5">
              <Loader2 size={10} className="animate-spin" />
              Fred is working: {thinking}
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <input value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder={persona === 'coach' ? 'Ask your coach...' : 'Talk to Fred...'}
          disabled={streaming} className="input flex-1 text-xs" />
        <button onClick={() => send()} disabled={streaming || !input.trim()}
          className="btn-primary disabled:opacity-40 px-2">
          {streaming ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
        </button>
      </div>
    </div>
  );
}
