import TaskCard from './TaskCard';

export default function KanbanColumn({ title, tasks, selectedTask, onSelectTask, onStatusChange }) {
  return (
    <div className="flex-1 min-w-0 flex flex-col">
      <div className="flex items-center justify-between mb-2 px-1">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{title}</h3>
        <span className="text-[11px] text-gray-600 bg-white/5 px-1.5 py-0.5 rounded-full">
          {tasks.length}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {tasks.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            isSelected={selectedTask?.id === task.id}
            onSelect={onSelectTask}
            onStatusChange={onStatusChange}
          />
        ))}
        {tasks.length === 0 && (
          <div className="text-xs text-gray-700 text-center py-6">No tasks</div>
        )}
      </div>
    </div>
  );
}
