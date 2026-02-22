import { PRIORITY_COLORS } from '../config';

const STATUSES = ['backlog', 'sprint', 'in_progress', 'review', 'done'];

export default function TaskCard({ task, isSelected, onSelect, onStatusChange }) {
  const priority = PRIORITY_COLORS[task.priority] || PRIORITY_COLORS[3];

  return (
    <div
      onClick={() => onSelect(task)}
      className={`p-3 rounded-lg border cursor-pointer transition-all duration-150 animate-slide-up ${
        isSelected
          ? 'bg-white/10 border-blue-500/40'
          : 'bg-white/[0.03] border-white/5 hover:bg-white/[0.06] hover:border-white/10'
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <h4 className="text-sm font-medium leading-tight flex-1 truncate">{task.title}</h4>
        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${priority.bg} ${priority.text}`}>
          {priority.label}
        </span>
      </div>

      {task.description && (
        <p className="text-xs text-gray-500 line-clamp-2 mb-2">{task.description}</p>
      )}

      <div className="flex items-center justify-between">
        <select
          value={task.status}
          onChange={(e) => {
            e.stopPropagation();
            onStatusChange(task.id, e.target.value);
          }}
          onClick={(e) => e.stopPropagation()}
          className="text-[11px] bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-gray-400 focus:outline-none focus:border-blue-500/50"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.replace('_', ' ')}
            </option>
          ))}
        </select>

        <div className="flex items-center gap-2 text-[11px] text-gray-600">
          {task.assignee && <span>{task.assignee}</span>}
          {task.estimate_hours && <span>{task.estimate_hours}h</span>}
        </div>
      </div>
    </div>
  );
}
