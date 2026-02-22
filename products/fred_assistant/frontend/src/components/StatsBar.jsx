import { CheckCircle2, Clock, AlertTriangle, Flame, ListTodo, Brain } from 'lucide-react';

function Stat({ icon: Icon, label, value, color }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2">
      <Icon size={14} className={color} />
      <div>
        <div className={`text-lg font-bold leading-none ${color}`}>{value}</div>
        <div className="text-[10px] text-gray-500 uppercase tracking-wider">{label}</div>
      </div>
    </div>
  );
}

export default function StatsBar({ stats }) {
  if (!stats) return null;
  return (
    <div className="flex gap-1 overflow-x-auto">
      <Stat icon={ListTodo} label="Active" value={stats.total_tasks} color="text-blue-400" />
      <Stat icon={Clock} label="In Progress" value={stats.in_progress} color="text-amber-400" />
      <Stat icon={CheckCircle2} label="Done Today" value={stats.completed_today} color="text-emerald-400" />
      <Stat icon={AlertTriangle} label="Overdue" value={stats.overdue} color={stats.overdue > 0 ? 'text-red-400' : 'text-gray-600'} />
      <Stat icon={Flame} label="Streak" value={`${stats.streak_days}d`} color={stats.streak_days > 0 ? 'text-orange-400' : 'text-gray-600'} />
      <Stat icon={Brain} label="Memories" value={stats.memories} color="text-purple-400" />
    </div>
  );
}
