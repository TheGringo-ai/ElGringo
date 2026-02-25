import { useState, useEffect } from 'react';
import { Trash2, Sparkles, ChevronDown, ChevronUp, X, FolderGit2 } from 'lucide-react';
import { fetchTasks, moveTask, deleteTask, createTask, streamTaskReview } from '../api';

const PRIORITY_COLORS = {
  1: 'border-l-red-500', 2: 'border-l-orange-400', 3: 'border-l-yellow-400',
  4: 'border-l-green-400', 5: 'border-l-gray-500',
};

function getProjectTag(task) {
  return (task.tags || []).find((t) => t.startsWith('project:'))?.replace('project:', '') || null;
}

function TaskCard({ task, onMove, onDelete }) {
  const [expanded, setExpanded] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [review, setReview] = useState('');
  const projectTag = getProjectTag(task);

  const handleReview = () => {
    setReviewing(true);
    setReview('');
    streamTaskReview(
      task.id,
      (token) => setReview((prev) => prev + token),
      () => setReviewing(false),
      (err) => { setReview(`Error: ${err}`); setReviewing(false); }
    );
  };

  return (
    <div className={`rounded-lg bg-white/[0.03] border border-white/5 border-l-2 ${PRIORITY_COLORS[task.priority] || 'border-l-gray-500'} hover:bg-white/[0.06] transition-colors animate-slide-up group`}>
      {/* Header row */}
      <div className="p-2.5">
        <div className="flex items-start justify-between gap-1">
          <button onClick={() => setExpanded(!expanded)} className="text-sm font-medium leading-snug flex-1 text-left hover:text-blue-300 transition-colors">
            {task.title}
          </button>
          <div className="flex items-center gap-0.5">
            <button onClick={() => setExpanded(!expanded)} className="opacity-0 group-hover:opacity-100 p-0.5 text-gray-600 hover:text-gray-400 transition-all">
              {expanded ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
            </button>
            <button onClick={() => onDelete(task.id)} className="opacity-0 group-hover:opacity-100 p-0.5 text-gray-600 hover:text-red-400 transition-all">
              <Trash2 size={10} />
            </button>
          </div>
        </div>
        <div className="flex items-center gap-1.5 mt-1">
          {projectTag && (
            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-blue-500/15 text-blue-400 font-medium">
              <FolderGit2 size={8} className="inline mr-0.5 -mt-px" />{projectTag}
            </span>
          )}
          {task.due_date && (
            <span className={`text-[10px] ${task.due_date < new Date().toISOString().slice(0, 10) && task.status !== 'done' ? 'text-red-400' : 'text-gray-600'}`}>
              {task.due_date}
            </span>
          )}
        </div>
        <select
          value={task.status}
          onChange={(e) => onMove(task.id, e.target.value)}
          className="mt-1.5 text-xs bg-white/5 border border-white/10 rounded px-1 py-0.5 text-gray-500 focus:outline-none"
        >
          {['todo', 'in_progress', 'review', 'done', 'backlog', 'capture', 'exploring', 'validated', 'parked'].map((s) => (
            <option key={s} value={s}>{s.replace('_', ' ')}</option>
          ))}
        </select>
      </div>

      {/* Expanded details + AI review */}
      {expanded && (
        <div className="border-t border-white/5 p-2.5 space-y-2">
          {task.description && (
            <div className="text-[10px] text-gray-400">
              <span className="text-gray-600 font-medium">Description: </span>{task.description}
            </div>
          )}
          {task.notes && (
            <div className="text-[10px] text-gray-400">
              <span className="text-gray-600 font-medium">Notes: </span>{task.notes}
            </div>
          )}

          {/* AI Review */}
          <div className="pt-1">
            {!review && !reviewing && (
              <button
                onClick={handleReview}
                className="flex items-center gap-1 text-[10px] px-2 py-1 rounded bg-purple-500/15 text-purple-400 hover:bg-purple-500/25 transition-colors font-medium"
              >
                <Sparkles size={10} /> Get AI Advice
              </button>
            )}
            {(reviewing || review) && (
              <div className="rounded bg-white/[0.03] border border-purple-500/20 p-2">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] text-purple-400 font-semibold flex items-center gap-1">
                    <Sparkles size={10} /> AI Review
                    {reviewing && <span className="animate-pulse ml-1">...</span>}
                  </span>
                  <button onClick={() => { setReview(''); setReviewing(false); }} className="text-gray-600 hover:text-gray-400">
                    <X size={10} />
                  </button>
                </div>
                <div className="text-[10px] text-gray-300 leading-relaxed whitespace-pre-wrap max-h-48 overflow-y-auto">
                  {review || 'Thinking...'}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Column({ title, tasks, onMove, onDelete }) {
  return (
    <div className="flex-1 min-w-[160px]">
      <div className="flex items-center gap-2 mb-2 px-1">
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{title.replace('_', ' ')}</h4>
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
  const [projectFilter, setProjectFilter] = useState('all');

  const load = async () => {
    const data = await fetchTasks({ board_id: board.id });
    setTasks(data);
  };

  useEffect(() => { load(); }, [board.id]);
  useEffect(() => { setProjectFilter('all'); }, [board.id]);

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

  // Extract unique project names from task tags
  const projectNames = [...new Set(
    tasks.flatMap((t) => (t.tags || [])
      .filter((tag) => tag.startsWith('project:'))
      .map((tag) => tag.replace('project:', ''))
    )
  )].sort();

  // Filter tasks by selected project
  const filteredTasks = projectFilter === 'all'
    ? tasks
    : tasks.filter((t) => (t.tags || []).includes(`project:${projectFilter}`));

  const boardCols = board.columns || ['todo', 'in_progress', 'done'];
  const matched = new Set();
  const columns = boardCols.map((col) => {
    const colTasks = filteredTasks.filter((t) => t.status === col);
    colTasks.forEach((t) => matched.add(t.id));
    return { key: col, tasks: colTasks };
  });
  const unmatched = filteredTasks.filter((t) => !matched.has(t.id));
  if (unmatched.length > 0) {
    columns[0].tasks = [...unmatched, ...columns[0].tasks];
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">{board.icon}</span>
        <h3 className="text-sm font-semibold">{board.name}</h3>
        <span className="text-[10px] text-gray-600 bg-white/5 px-1.5 py-0.5 rounded-full">
          {filteredTasks.filter((t) => t.status !== 'done').length} active
        </span>
      </div>

      {/* Project filter pills */}
      {projectNames.length > 0 && (
        <div className="flex items-center gap-1.5 mb-3 flex-wrap">
          <span className="text-xs text-gray-600 mr-0.5">
            <FolderGit2 size={10} className="inline -mt-px" /> Filter:
          </span>
          <button
            onClick={() => setProjectFilter('all')}
            className={`text-xs px-2 py-0.5 rounded-full transition-colors ${
              projectFilter === 'all'
                ? 'bg-blue-500/20 text-blue-400 font-medium'
                : 'bg-white/5 text-gray-500 hover:bg-white/10'
            }`}
          >
            All ({tasks.length})
          </button>
          {projectNames.map((name) => {
            const count = tasks.filter((t) => (t.tags || []).includes(`project:${name}`)).length;
            return (
              <button
                key={name}
                onClick={() => setProjectFilter(name)}
                className={`text-xs px-2 py-0.5 rounded-full transition-colors ${
                  projectFilter === name
                    ? 'bg-blue-500/20 text-blue-400 font-medium'
                    : 'bg-white/5 text-gray-500 hover:bg-white/10'
                }`}
              >
                {name} ({count})
              </button>
            );
          })}
        </div>
      )}

      {/* Add task inline */}
      <div className="flex gap-2 mb-3">
        <input
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          placeholder={`Add task to ${board.name}...`}
          className="input flex-1 text-sm"
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
