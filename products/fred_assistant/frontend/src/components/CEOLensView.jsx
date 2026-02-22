import { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, TrendingDown, DollarSign, Save } from 'lucide-react';
import { fetchCurrentMetrics, fetchMetricsHistory, saveMetricsSnapshot, logMetric } from '../api';

function MetricCard({ label, value, prefix = '', suffix = '', color = 'text-white', trend }) {
  return (
    <div className="card p-3 text-center">
      <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">{label}</div>
      <div className={`text-xl font-bold ${color}`}>
        {prefix}{typeof value === 'number' ? value.toLocaleString() : value}{suffix}
      </div>
      {trend !== undefined && (
        <div className={`flex items-center justify-center gap-0.5 text-[10px] mt-1 ${trend >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {trend >= 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
          {trend >= 0 ? '+' : ''}{trend}% vs last week
        </div>
      )}
    </div>
  );
}

export default function CEOLensView() {
  const [metrics, setMetrics] = useState(null);
  const [history, setHistory] = useState([]);
  const [showLogMRR, setShowLogMRR] = useState(false);
  const [mrrValue, setMrrValue] = useState('');

  const load = async () => {
    const [m, h] = await Promise.allSettled([fetchCurrentMetrics(), fetchMetricsHistory()]);
    if (m.status === 'fulfilled') setMetrics(m.value);
    if (h.status === 'fulfilled') setHistory(h.value);
  };

  useEffect(() => { load(); }, []);

  const handleLogMRR = async () => {
    const val = parseFloat(mrrValue);
    if (isNaN(val)) return;
    await logMetric('mrr', val);
    setMrrValue('');
    setShowLogMRR(false);
    load();
  };

  const handleSnapshot = async () => {
    await saveMetricsSnapshot();
    load();
  };

  if (!metrics) return <div className="text-xs text-gray-500 p-4">Loading metrics...</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 size={14} className="text-emerald-400" />
          <span className="text-xs font-semibold text-gray-300">CEO Lens</span>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={() => setShowLogMRR(!showLogMRR)} className="btn-ghost text-xs py-1 px-2">
            <DollarSign size={11} className="text-emerald-400 inline" /> Log MRR
          </button>
          <button onClick={handleSnapshot} className="btn-ghost text-xs py-1 px-2">
            <Save size={11} className="inline" /> Snapshot
          </button>
        </div>
      </div>

      {/* Log MRR */}
      {showLogMRR && (
        <div className="card p-3 flex items-center gap-2">
          <DollarSign size={12} className="text-emerald-400" />
          <input type="number" value={mrrValue} onChange={(e) => setMrrValue(e.target.value)}
            placeholder="Enter MRR..." className="input text-xs flex-1"
            onKeyDown={(e) => e.key === 'Enter' && handleLogMRR()} />
          <button onClick={handleLogMRR} className="btn-primary text-xs px-3">Save</button>
        </div>
      )}

      {/* MRR - Top Center */}
      <div className="card p-6 text-center">
        <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Monthly Recurring Revenue</div>
        <div className="text-4xl font-bold text-emerald-400">${metrics.mrr?.toLocaleString() || 0}</div>
      </div>

      {/* Revenue Metrics Row */}
      <div className="grid grid-cols-4 gap-2">
        <MetricCard label="Leads Contacted" value={metrics.leads_contacted} color="text-blue-400" />
        <MetricCard label="Calls Booked" value={metrics.calls_booked} color="text-orange-400" />
        <MetricCard label="Trials" value={metrics.trials_started} color="text-purple-400" />
        <MetricCard label="Deals Closed" value={metrics.deals_closed} color="text-emerald-400" />
      </div>

      {/* Productivity Row */}
      <div className="grid grid-cols-3 gap-2">
        <MetricCard label="Sprint Completion" value={metrics.sprint_completion_pct} suffix="%" color="text-blue-400" />
        <MetricCard label="Content Published" value={metrics.content_published} color="text-purple-400" />
        <MetricCard label="Focus Today" value={metrics.focus_minutes_today} suffix=" min" color="text-orange-400" />
      </div>

      {/* Alerts */}
      {metrics.overdue_tasks > 0 && (
        <div className="card p-3 border-red-500/20">
          <span className="text-[10px] text-red-400 font-semibold">
            {metrics.overdue_tasks} overdue task{metrics.overdue_tasks !== 1 ? 's' : ''} need attention
          </span>
        </div>
      )}

      {/* History */}
      {history.length > 0 && (
        <div>
          <h4 className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Snapshot History</h4>
          <div className="space-y-1">
            {history.slice(0, 7).map((s) => (
              <div key={s.id} className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02] text-[10px]">
                <span className="text-gray-400">{s.date}</span>
                <div className="flex items-center gap-3 text-gray-500">
                  <span>MRR: ${s.mrr?.toLocaleString()}</span>
                  <span>Sprint: {s.sprint_completion_pct}%</span>
                  <span>Leads: {s.leads_contacted}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
