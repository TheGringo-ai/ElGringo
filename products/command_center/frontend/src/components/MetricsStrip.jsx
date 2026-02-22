import { Target, ListTodo, FileText, Clock, CalendarDays } from 'lucide-react';
import MetricCard from './MetricCard';

export default function MetricsStrip({ stats, sprint, content, scheduler }) {
  const completionPct = sprint?.completion_percentage ?? 0;
  const activeTasks = (stats?.in_progress ?? 0) + (stats?.in_review ?? 0);
  const draftCount = content?.filter((c) => c.status === 'draft').length ?? 0;
  const enabledJobs = scheduler?.filter((s) => s.enabled).length ?? 0;
  const daysLeft = sprint?.days_remaining ?? 0;

  return (
    <div className="flex gap-3 px-6 py-3 overflow-x-auto">
      <MetricCard
        label="Sprint"
        value={`${Math.round(completionPct)}%`}
        subtitle={sprint?.sprint?.name}
        colorClass="text-blue-400"
        icon={Target}
      />
      <MetricCard
        label="Active Tasks"
        value={activeTasks}
        subtitle={`${stats?.tasks_total ?? 0} total`}
        colorClass="text-amber-400"
        icon={ListTodo}
      />
      <MetricCard
        label="Content Queue"
        value={draftCount}
        subtitle="drafts pending"
        colorClass="text-purple-400"
        icon={FileText}
      />
      <MetricCard
        label="Scheduled"
        value={enabledJobs}
        subtitle={`${scheduler?.length ?? 0} total jobs`}
        colorClass="text-emerald-400"
        icon={Clock}
      />
      <MetricCard
        label="Days Left"
        value={daysLeft}
        subtitle="in sprint"
        colorClass={daysLeft < 3 ? 'text-red-400' : 'text-gray-300'}
        icon={CalendarDays}
      />
    </div>
  );
}
