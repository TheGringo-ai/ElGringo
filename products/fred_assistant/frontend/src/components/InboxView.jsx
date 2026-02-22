import { useState, useEffect } from 'react';
import { Inbox, AlertTriangle, UserCheck, FileCheck, Target, Timer, Calendar } from 'lucide-react';
import { fetchInbox } from '../api';

const TYPE_CONFIG = {
  overdue_task: { icon: AlertTriangle, color: 'text-red-400', bg: 'border-l-red-500', label: 'Overdue' },
  followup_due: { icon: UserCheck, color: 'text-amber-400', bg: 'border-l-amber-500', label: 'Follow Up' },
  pending_approval: { icon: FileCheck, color: 'text-blue-400', bg: 'border-l-blue-500', label: 'Approval' },
  calendar_conflict: { icon: Calendar, color: 'text-purple-400', bg: 'border-l-purple-500', label: 'Conflict' },
  stale_goal: { icon: Target, color: 'text-gray-400', bg: 'border-l-gray-500', label: 'Stale Goal' },
  incomplete_focus: { icon: Timer, color: 'text-orange-400', bg: 'border-l-orange-500', label: 'Focus' },
};

export default function InboxView() {
  const [items, setItems] = useState([]);

  const load = async () => {
    try {
      const data = await fetchInbox();
      setItems(data);
    } catch { setItems([]); }
  };

  useEffect(() => { load(); }, []);

  const grouped = {};
  items.forEach((item) => {
    const type = item.type;
    if (!grouped[type]) grouped[type] = [];
    grouped[type].push(item);
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Inbox size={14} className="text-amber-400" />
          <span className="text-xs font-semibold text-gray-300">Inbox</span>
          {items.length > 0 && (
            <span className="text-[10px] bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded-full font-bold">{items.length}</span>
          )}
        </div>
        <button onClick={load} className="btn-ghost text-xs py-1 px-2">Refresh</button>
      </div>

      {items.length === 0 && (
        <div className="card p-6 text-center">
          <div className="text-2xl mb-2">&#10003;</div>
          <div className="text-sm text-gray-400">All clear! Nothing needs your attention.</div>
        </div>
      )}

      {Object.entries(grouped).map(([type, typeItems]) => {
        const config = TYPE_CONFIG[type] || { icon: Inbox, color: 'text-gray-400', bg: 'border-l-gray-500', label: type };
        const Icon = config.icon;
        return (
          <div key={type}>
            <div className="flex items-center gap-1.5 mb-2">
              <Icon size={12} className={config.color} />
              <h4 className={`text-[11px] font-semibold uppercase tracking-wider ${config.color}`}>
                {config.label} ({typeItems.length})
              </h4>
            </div>
            <div className="space-y-1">
              {typeItems.map((item, i) => (
                <div key={`${item.entity_id}-${i}`}
                  className={`p-2.5 rounded-lg bg-white/[0.02] border-l-2 ${config.bg} animate-slide-up`}>
                  <div className="text-xs font-medium">{item.title}</div>
                  <div className="text-[10px] text-gray-600 mt-0.5">{item.description}</div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
