import { STATUS_COLUMNS } from '../config';
import KanbanColumn from './KanbanColumn';
import TaskDetailPanel from './TaskDetailPanel';

export default function SprintBoard({ tasks, selectedTask, onSelectTask, onStatusChange }) {
  const columns = Object.entries(STATUS_COLUMNS).map(([key, col]) => ({
    key,
    label: col.label,
    tasks: tasks.filter((t) => col.statuses.includes(t.status)),
  }));

  return (
    <div className="glass h-full flex flex-col p-4">
      <h2 className="text-sm font-semibold mb-3 text-gray-300">Sprint Board</h2>

      <div className="flex gap-3 flex-1 min-h-0 overflow-hidden">
        {columns.map((col) => (
          <KanbanColumn
            key={col.key}
            title={col.label}
            tasks={col.tasks}
            selectedTask={selectedTask}
            onSelectTask={onSelectTask}
            onStatusChange={onStatusChange}
          />
        ))}
      </div>

      {selectedTask && (
        <div className="mt-3 border-t border-white/5 pt-3">
          <TaskDetailPanel
            task={selectedTask}
            onClose={() => onSelectTask(null)}
            onStatusChange={onStatusChange}
          />
        </div>
      )}
    </div>
  );
}
