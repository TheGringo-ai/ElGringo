import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Bot, User, X, ListChecks, CheckCircle2 } from 'lucide-react';
import { streamProjectChat, generateProjectTasks } from '../api';

// Strip TASK: JSON lines from displayed text (they're machine-readable, not for display)
function cleanTaskBlocks(text) {
  return text.split('\n').filter((line) => !line.trim().startsWith('TASK:')).join('\n').trimEnd();
}

const QUICK_ACTIONS = [
  'What needs fixing first?',
  'Create a TODO list for this project',
  'Analyze the architecture',
  'What are the biggest risks?',
];

export default function ProjectChatPanel({ projectName, context, onClose }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generatedTasks, setGeneratedTasks] = useState(null);
  const scrollRef = useRef(null);

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
    await streamProjectChat(
      projectName,
      msg,
      context || {},
      (token) => {
        acc += token;
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { ...next[next.length - 1], content: cleanTaskBlocks(acc) };
          return next;
        });
      },
      () => {
        // Final cleanup on stream end
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.role === 'assistant') {
            next[next.length - 1] = { ...last, content: cleanTaskBlocks(last.content) };
          }
          return next;
        });
        setStreaming(false);
      },
      (err) => {
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { ...next[next.length - 1], content: `Error: ${err}` };
          return next;
        });
        setStreaming(false);
      },
      (tasks) => {
        // Auto-created tasks from TASK: blocks in the AI response
        setGeneratedTasks({ tasks, count: tasks.length });
      },
    );
  };

  const handleGenerateTasks = async () => {
    setGenerating(true);
    setGeneratedTasks(null);
    try {
      const result = await generateProjectTasks(projectName);
      setGeneratedTasks(result);
    } catch (err) {
      setGeneratedTasks({ error: err.message });
    }
    setGenerating(false);
  };

  return (
    <div className="mt-2 border border-white/5 rounded bg-white/[0.02] overflow-hidden">
      <div className="flex items-center justify-between px-2 py-1.5 border-b border-white/5">
        <div className="flex items-center gap-1.5">
          <Bot size={10} className="text-purple-400" />
          <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
            Ask Fred about {projectName}
          </span>
        </div>
        <button onClick={onClose} className="text-gray-600 hover:text-gray-400"><X size={10} /></button>
      </div>

      {/* Quick actions */}
      <div className="flex gap-1 p-1.5 overflow-x-auto flex-wrap">
        {QUICK_ACTIONS.map((q) => (
          <button key={q} onClick={() => send(q)} disabled={streaming}
            className="flex-shrink-0 text-[9px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 disabled:opacity-40">
            {q}
          </button>
        ))}
        <button onClick={handleGenerateTasks} disabled={generating || streaming}
          className="flex-shrink-0 text-[9px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 disabled:opacity-40 flex items-center gap-1">
          <ListChecks size={8} />
          {generating ? 'Creating...' : 'Auto-Create Tasks'}
        </button>
      </div>

      {/* Generated tasks result */}
      {generatedTasks && !generatedTasks.error && (
        <div className="mx-2 mb-1.5 p-2 rounded bg-emerald-500/5 border border-emerald-500/10">
          <div className="flex items-center gap-1.5 mb-1">
            <CheckCircle2 size={10} className="text-emerald-400" />
            <span className="text-[10px] text-emerald-400 font-medium">
              {generatedTasks.count} tasks added to your boards
            </span>
          </div>
          <div className="space-y-0.5 max-h-32 overflow-y-auto">
            {generatedTasks.tasks?.map((t, i) => (
              <div key={i} className="text-[10px] text-gray-400 flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                  t.priority <= 1 ? 'bg-red-400' : t.priority <= 2 ? 'bg-amber-400' : t.priority <= 3 ? 'bg-blue-400' : 'bg-gray-500'
                }`} />
                <span className="truncate flex-1">{t.title}</span>
                <span className={`text-[8px] px-1 py-0.5 rounded flex-shrink-0 ${
                  t.priority <= 1 ? 'bg-red-500/20 text-red-400' : t.priority <= 2 ? 'bg-amber-500/20 text-amber-400' : 'bg-white/5 text-gray-500'
                }`}>P{t.priority}</span>
                {t.board_id && (
                  <span className="text-[8px] text-gray-600 bg-white/5 px-1 py-0.5 rounded flex-shrink-0">{t.board_id}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      {generatedTasks?.error && (
        <div className="mx-2 mb-1.5 p-1.5 rounded bg-red-500/5 border border-red-500/10 text-[10px] text-red-400">
          {generatedTasks.error}
        </div>
      )}

      {/* Messages */}
      <div ref={scrollRef} className="max-h-64 overflow-y-auto space-y-1.5 px-2 pb-1.5">
        {messages.length === 0 && (
          <div className="text-[10px] text-gray-700 text-center py-3">
            Ask Fred anything about this project...
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
          placeholder="Ask about the project..."
          disabled={streaming} className="input flex-1 text-[10px] py-1" />
        <button onClick={() => send()} disabled={streaming || !input.trim()}
          className="px-1.5 py-1 rounded bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 disabled:opacity-40">
          {streaming ? <Loader2 size={10} className="animate-spin" /> : <Send size={10} />}
        </button>
      </div>
    </div>
  );
}
