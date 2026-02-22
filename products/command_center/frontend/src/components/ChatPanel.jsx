import { useState, useEffect, useRef } from 'react';
import { Send, Trash2, Loader2 } from 'lucide-react';
import { fetchPersonas, streamChat } from '../api/chat';
import useChatHistory from '../hooks/useChatHistory';
import ChatMessage from './ChatMessage';

const QUICK_ACTIONS = [
  'What should I work on today?',
  'Summarize this week',
  'Draft standup notes',
];

export default function ChatPanel() {
  const { messages, addMessage, updateLastAssistant, clearHistory } = useChatHistory();
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [personas, setPersonas] = useState([]);
  const [persona, setPersona] = useState('dev_lead');
  const scrollRef = useRef(null);

  useEffect(() => {
    fetchPersonas()
      .then(setPersonas)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (text) => {
    const msg = text || input.trim();
    if (!msg || streaming) return;

    setInput('');
    addMessage('user', msg);
    addMessage('assistant', '');
    setStreaming(true);

    let accumulated = '';

    await streamChat(
      msg,
      persona,
      (token) => {
        accumulated += token;
        updateLastAssistant(accumulated);
      },
      () => setStreaming(false),
      (err) => {
        updateLastAssistant(`Error: ${err}`);
        setStreaming(false);
      }
    );
  };

  return (
    <div className="glass h-full flex flex-col p-4">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-semibold text-gray-300">AI Chat</h2>
        <div className="flex items-center gap-2">
          <select
            value={persona}
            onChange={(e) => setPersona(e.target.value)}
            className="text-[11px] bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-gray-400 focus:outline-none focus:border-blue-500/50"
          >
            {personas.length > 0
              ? personas.map((p) => (
                  <option key={p.name} value={p.name}>{p.role || p.name}</option>
                ))
              : <option value="dev_lead">Dev Lead</option>
            }
          </select>
          <button
            onClick={clearHistory}
            className="p-1 hover:bg-white/10 rounded text-gray-600 hover:text-gray-400"
            title="Clear chat"
          >
            <Trash2 size={12} />
          </button>
        </div>
      </div>

      {/* Quick actions */}
      <div className="flex gap-1.5 mb-2 overflow-x-auto">
        {QUICK_ACTIONS.map((action) => (
          <button
            key={action}
            onClick={() => handleSend(action)}
            disabled={streaming}
            className="flex-shrink-0 text-[11px] px-2.5 py-1 rounded-full bg-white/5 text-gray-400 hover:bg-white/10 hover:text-gray-300 disabled:opacity-40 transition-colors"
          >
            {action}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-3 mb-2">
        {messages.length === 0 && (
          <div className="text-xs text-gray-700 text-center py-8">
            Ask your AI dev lead anything...
          </div>
        )}
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
          placeholder="Type a message..."
          disabled={streaming}
          className="flex-1 text-sm bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-gray-300 placeholder-gray-600 focus:outline-none focus:border-blue-500/50 disabled:opacity-50"
        />
        <button
          onClick={() => handleSend()}
          disabled={streaming || !input.trim()}
          className="px-3 py-2 rounded-lg bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {streaming ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
        </button>
      </div>
    </div>
  );
}
