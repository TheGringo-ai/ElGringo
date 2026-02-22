import { X } from 'lucide-react';
import { PRIORITY_COLORS } from '../config';

export default function TaskDetailPanel({ task, onClose, onStatusChange }) {
  if (!task) return null;

  const priority = PRIORITY_COLORS[task.priority] || PRIORITY_COLORS[3];

  return (
    <div className="glass p-4 animate-fade-in">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${priority.bg} ${priority.text}`}>
              {priority.label}
            </span>
            <span className="text-xs text-gray-500">{task.id}</span>
          </div>
          <h3 className="text-sm font-semibold">{task.title}</h3>
        </div>
        <button onClick={onClose} className="p-1 hover:bg-white/10 rounded text-gray-500">
          <X size={14} />
        </button>
      </div>

      {task.description && (
        <p className="text-xs text-gray-400 mb-3 leading-relaxed">{task.description}</p>
      )}

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-gray-600">Status</span>
          <select
            value={task.status}
            onChange={(e) => onStatusChange(task.id, e.target.value)}
            className="block w-full mt-1 bg-white/5 border border-white/10 rounded px-2 py-1 text-gray-300 focus:outline-none focus:border-blue-500/50"
          >
            {['backlog', 'sprint', 'in_progress', 'review', 'done'].map((s) => (
              <option key={s} value={s}>{s.replace('_', ' ')}</option>
            ))}
          </select>
        </div>
        <div>
          <span className="text-gray-600">Assignee</span>
          <p className="mt-1 text-gray-300">{task.assignee || 'Unassigned'}</p>
        </div>
        <div>
          <span className="text-gray-600">Estimate</span>
          <p className="mt-1 text-gray-300">{task.estimate_hours ? `${task.estimate_hours}h` : '—'}</p>
        </div>
        <div>
          <span className="text-gray-600">Project</span>
          <p className="mt-1 text-gray-300">{task.project || '—'}</p>
        </div>
      </div>
    </div>
  );
}
