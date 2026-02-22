export default function MetricCard({ label, value, subtitle, colorClass, icon: Icon }) {
  return (
    <div className="glass p-4 flex-1 min-w-[140px] animate-fade-in">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-gray-500 uppercase tracking-wider">{label}</span>
        {Icon && <Icon size={14} className="text-gray-600" />}
      </div>
      <div className={`text-2xl font-bold ${colorClass || 'text-white'}`}>{value ?? '—'}</div>
      {subtitle && <div className="text-xs text-gray-500 mt-0.5">{subtitle}</div>}
    </div>
  );
}
