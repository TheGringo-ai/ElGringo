import { useState, useEffect } from 'react';
import { Circle, CheckCircle2, Clock, AlertTriangle } from 'lucide-react';
import { fetchTodayTasks, moveTask } from '../api';

const STATUS_ICON = {
  todo: Circle,
  in_progress: Clock,
  review: Clock,
  done: CheckCircle2,
};

export default function TodayView({ onRefresh }) {
  const [tasks, setTasks] = useState([]);

  const load = async () => {
    const data = await fetchTodayTasks();
    setTasks(data);
  };

  useEffect(() => { load(); }, []);

  const toggle = async (task) => {
    const next = task.status === 'done' ? 'todo' : 'done';
    setTasks((prev) => prev.map((t) => t.id === task.id ? { ...t, status: next } : t));
    await moveTask(task.id, next);
    onRefresh?.();
    load();
  };

  const overdue = tasks.filter((t) => t.due_date && t.due_date < new Date().toISOString().slice(0, 10) && t.status !== 'done');
  const active = tasks.filter((t) => t.status !== 'done');
  const done = tasks.filter((t) => t.status === 'done');

  return (
    <div className="space-y-4">
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
