import { useState, useEffect } from 'react';
import { Circle, CheckCircle2, Clock, AlertTriangle, Sun, Moon } from 'lucide-react';
import { fetchTodayTasks, moveTask, fetchBriefing, generateBriefing, generateShutdown } from '../api';

const STATUS_ICON = {
  todo: Circle,
  in_progress: Clock,
  review: Clock,
  done: CheckCircle2,
};

export default function TodayView({ onRefresh }) {
  const [tasks, setTasks] = useState([]);
  const [briefing, setBriefing] = useState(null);
  const [loadingBriefing, setLoadingBriefing] = useState(false);
  const [loadingShutdown, setLoadingShutdown] = useState(false);
  const [shutdown, setShutdown] = useState(null);

  const load = async () => {
    const [td, br] = await Promise.allSettled([fetchTodayTasks(), fetchBriefing()]);
    if (td.status === 'fulfilled') setTasks(td.value);
    if (br.status === 'fulfilled' && br.value?.content && br.value?.date) setBriefing(br.value);
  };

  useEffect(() => { load(); }, []);

  const toggle = async (task) => {
    const next = task.status === 'done' ? 'todo' : 'done';
    setTasks((prev) => prev.map((t) => t.id === task.id ? { ...t, status: next } : t));
    await moveTask(task.id, next);
    onRefresh?.();
    load();
  };

  const handleBriefing = async () => {
    setLoadingBriefing(true);
    try {
      const data = await generateBriefing();
      setBriefing(data);
    } finally { setLoadingBriefing(false); }
  };

  const handleShutdown = async () => {
    setLoadingShutdown(true);
    try {
      const data = await generateShutdown();
      setShutdown(data);
    } finally { setLoadingShutdown(false); }
  };

  const overdue = tasks.filter((t) => t.due_date && t.due_date < new Date().toISOString().slice(0, 10) && t.status !== 'done');
  const active = tasks.filter((t) => t.status !== 'done');
  const done = tasks.filter((t) => t.status === 'done');
  const isEvening = new Date().getHours() >= 17;

  return (
    <div className="space-y-4">
      {/* Daily Briefing */}
      {briefing ? (
        <div className="card p-3 border-emerald-500/10">
          <div className="flex items-center gap-1.5 mb-2">
            <Sun size={12} className="text-amber-400" />
            <span className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider">Daily Briefing</span>
          </div>
          <div className="text-[11px] text-gray-400 whitespace-pre-wrap leading-relaxed">{briefing.content}</div>
        </div>
      ) : (
        <button onClick={handleBriefing} disabled={loadingBriefing}
          className="card p-3 w-full text-left hover:bg-white/5 transition-colors">
          <div className="flex items-center gap-1.5">
            <Sun size={12} className="text-amber-400" />
            <span className="text-xs text-amber-400">{loadingBriefing ? 'Generating...' : 'Generate Daily Briefing'}</span>
          </div>
        </button>
      )}

      {overdue.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <AlertTriangle size={12} className="text-red-400" />
            <h4 className="text-[11px] font-semibold text-red-400 uppercase tracking-wider">Overdue</h4>
          </div>
          {overdue.map((t) => (
            <TaskRow key={t.id} task={t} onToggle={toggle} isOverdue />
          ))}
        </div>
      )}

      <div>
        <h4 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Today's Focus</h4>
        {active.length === 0 && <div className="text-xs text-gray-700 py-3">Nothing scheduled. Add tasks or use quick capture!</div>}
        {active.map((t) => <TaskRow key={t.id} task={t} onToggle={toggle} />)}
      </div>

      {done.length > 0 && (
        <div>
          <h4 className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Completed</h4>
          {done.map((t) => <TaskRow key={t.id} task={t} onToggle={toggle} />)}
        </div>
      )}

      {/* Shutdown Review */}
      {isEvening && !shutdown && (
        <button onClick={handleShutdown} disabled={loadingShutdown}
          className="card p-3 w-full text-left hover:bg-white/5 transition-colors">
          <div className="flex items-center gap-1.5">
            <Moon size={12} className="text-indigo-400" />
            <span className="text-xs text-indigo-400">{loadingShutdown ? 'Generating...' : 'Daily Shutdown Review'}</span>
          </div>
        </button>
      )}
      {shutdown && (
        <div className="card p-3 border-indigo-500/10">
          <div className="flex items-center gap-1.5 mb-2">
            <Moon size={12} className="text-indigo-400" />
            <span className="text-[10px] font-semibold text-indigo-400 uppercase tracking-wider">Shutdown Review</span>
          </div>
          <div className="text-[11px] text-gray-400 whitespace-pre-wrap leading-relaxed">{shutdown.content}</div>
        </div>
      )}
    </div>
  );
}

function TaskRow({ task, onToggle, isOverdue }) {
  const Icon = STATUS_ICON[task.status] || Circle;
  const isDone = task.status === 'done';

  return (
    <div
      onClick={() => onToggle(task)}
      className={`flex items-center gap-2.5 p-2 rounded-lg cursor-pointer transition-colors animate-fade-in ${
        isDone ? 'opacity-50' : 'hover:bg-white/5'
      } ${isOverdue ? 'border-l-2 border-l-red-500 pl-3' : ''}`}
    >
      <Icon size={14} className={isDone ? 'text-emerald-400' : isOverdue ? 'text-red-400' : 'text-gray-500'} />
      <div className="flex-1 min-w-0">
        <span className={`text-xs ${isDone ? 'line-through text-gray-600' : ''}`}>{task.title}</span>
        <div className="flex gap-2 text-[10px] text-gray-600">
          <span>{task.board_id}</span>
          {task.due_date && <span>{task.due_date}</span>}
        </div>
      </div>
      <span className={`text-[9px] font-bold px-1 rounded ${
        { 1: 'bg-red-500/20 text-red-400', 2: 'bg-orange-500/20 text-orange-400', 3: 'bg-yellow-500/20 text-yellow-400' }[task.priority] || 'text-gray-600'
      }`}>P{task.priority}</span>
    </div>
  );
}
