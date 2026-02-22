import { Clock, ToggleLeft, ToggleRight } from 'lucide-react';
import { toggleSchedulerTask } from '../api/automation';

export default function SchedulerList({ tasks, onRefresh }) {
  const handleToggle = async (taskId) => {
    await toggleSchedulerTask(taskId);
    onRefresh();
  };

  if (!tasks || tasks.length === 0) {
    return <div className="text-xs text-gray-700 text-center py-4">No scheduled tasks</div>;
  }

  return (
    <div className="space-y-1.5">
      {tasks.map((task) => (
        <div
          key={task.id}
          className="flex items-center justify-between p-2 rounded-lg bg-white/[0.03] border border-white/5"
        >
          <div className="flex items-center gap-2 min-w-0">
            <Clock size={10} className={task.enabled ? 'text-emerald-400' : 'text-gray-600'} />
            <div className="min-w-0">
              <div className="text-xs font-medium truncate">{task.name}</div>
              <div className="text-[10px] text-gray-600">{task.cron}</div>
            </div>
          </div>
          <button
            onClick={() => handleToggle(task.id)}
            className="flex-shrink-0 text-gray-400 hover:text-white transition-colors"
          >
            {task.enabled ? (
              <ToggleRight size={18} className="text-emerald-400" />
            ) : (
              <ToggleLeft size={18} className="text-gray-600" />
            )}
          </button>
        </div>
      ))}
    </div>
  );
}
