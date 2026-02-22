import { useState, useEffect } from 'react';
import { Trash2, GripVertical } from 'lucide-react';
import { fetchTasks, moveTask, deleteTask, createTask } from '../api';

const PRIORITY_COLORS = {
  1: 'border-l-red-500', 2: 'border-l-orange-400', 3: 'border-l-yellow-400',
  4: 'border-l-green-400', 5: 'border-l-gray-500',
};

function TaskCard({ task, onMove, onDelete }) {
  return (
    <div className={`p-2.5 rounded-lg bg-white/[0.03] border border-white/5 border-l-2 ${PRIORITY_COLORS[task.priority] || 'border-l-gray-500'} hover:bg-white/[0.06] transition-colors animate-slide-up group`}>
      <div className="flex items-start justify-between gap-1">
        <span className="text-xs font-medium leading-snug flex-1">{task.title}</span>
        <button onClick={() => onDelete(task.id)} className="opacity-0 group-hover:opacity-100 p-0.5 text-gray-600 hover:text-red-400 transition-all">
          <Trash2 size={10} />
        </button>
      </div>
      {task.due_date && (
        <div className={`text-[10px] mt-1 ${task.due_date < new Date().toISOString().slice(0, 10) && task.status !== 'done' ? 'text-red-400' : 'text-gray-600'}`}>
          {task.due_date}
        </div>
      )}
      <select
        value={task.status}
        onChange={(e) => onMove(task.id, e.target.value)}
        className="mt-1.5 text-[10px] bg-white/5 border border-white/10 rounded px-1 py-0.5 text-gray-500 focus:outline-none"
      >
        {['todo', 'in_progress', 'review', 'done', 'backlog', 'capture', 'exploring', 'validated', 'parked'].map((s) => (
          <option key={s} value={s}>{s.replace('_', ' ')}</option>
        ))}
      </select>
    </div>
  );
}

function Column({ title, tasks, onMove, onDelete }) {
  return (
    <div className="flex-1 min-w-[160px]">
      <div className="flex items-center gap-2 mb-2 px-1">
        <h4 className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">{title.replace('_', ' ')}</h4>
        <span className="text-[10px] text-gray-700 bg-white/5 px-1.5 rounded-full">{tasks.length}</span>
      </div>
      <div className="space-y-1.5 min-h-[80px]">
        {tasks.map((t) => <TaskCard key={t.id} task={t} onMove={onMove} onDelete={onDelete} />)}
      </div>
    </div>
  );
}

export default function BoardView({ board, onRefresh }) {
  const [tasks, setTasks] = useState([]);
  const [newTitle, setNewTitle] = useState('');

  const load = async () => {
    const data = await fetchTasks({ board_id: board.id });
    setTasks(data);
  };

  useEffect(() => { load(); }, [board.id]);

  const handleMove = async (taskId, status) => {
    setTasks((prev) => prev.map((t) => t.id === taskId ? { ...t, status } : t));
    await moveTask(taskId, status);
    onRefresh?.();
  };

  const handleDelete = async (taskId) => {
    setTasks((prev) => prev.filter((t) => t.id !== taskId));
    await deleteTask(taskId);
    onRefresh?.();
  };

  const handleAdd = async () => {
    if (!newTitle.trim()) return;
    await createTask({ board_id: board.id, title: newTitle.trim() });
    setNewTitle('');
    load();
    onRefresh?.();
  };

  const columns = (board.columns || ['todo', 'in_progress', 'done']).map((col) => ({
    key: col,
    tasks: tasks.filter((t) => t.status === col),
  }));

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">{board.icon}</span>
        <h3 className="text-sm font-semibold">{board.name}</h3>
        <span className="text-[10px] text-gray-600 bg-white/5 px-1.5 py-0.5 rounded-full">
          {tasks.filter((t) => t.status !== 'done').length} active
        </span>
      </div>

      {/* Add task inline */}
      <div className="flex gap-2 mb-3">
        <input
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          placeholder={`Add task to ${board.name}...`}
          className="input flex-1 text-xs"
        />
      </div>

      {/* Kanban columns */}
      <div className="flex gap-3 flex-1 overflow-x-auto overflow-y-auto">
        {columns.map((col) => (
          <Column key={col.key} title={col.key} tasks={col.tasks} onMove={handleMove} onDelete={handleDelete} />
        ))}
      </div>
    </div>
  );
}
