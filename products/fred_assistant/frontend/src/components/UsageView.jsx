import { useState, useEffect } from 'react';
import {
  Activity, DollarSign, Zap, Clock, AlertTriangle,
  Server, Wifi, WifiOff, RefreshCw, Settings, ChevronDown, ChevronUp,
} from 'lucide-react';
import {
  fetchUsageToday, fetchUsageSummary, fetchUsageByModel,
  fetchUsageBudget, updateUsageBudget, fetchRecentUsage,
  fetchProviders, updateProviderPrefs, fetchSyncStatus, triggerSync,
} from '../api';

// ── Helpers ──────────────────────────────────────────────────

function fmt$(v) { return v < 0.01 ? `$${v.toFixed(4)}` : `$${v.toFixed(2)}`; }
function fmtNum(v) { return (v || 0).toLocaleString(); }
function fmtMs(v) { return v < 1000 ? `${Math.round(v)}ms` : `${(v / 1000).toFixed(1)}s`; }
function pctColor(pct) {
  if (pct >= 90) return 'text-red-400';
  if (pct >= 70) return 'text-amber-400';
  return 'text-emerald-400';
}
function barColor(pct) {
  if (pct >= 90) return 'bg-red-500';
  if (pct >= 70) return 'bg-amber-500';
  return 'bg-emerald-500';
}

const PROVIDER_COLORS = {
  gemini: '#4285F4', openai: '#10a37f', anthropic: '#d4a574',
  grok: '#1DA1F2', ollama: '#8B5CF6', mlx: '#EC4899',
  llama_cloud: '#F97316', unknown: '#6B7280',
};

// ── Sub-components ───────────────────────────────────────────

function MetricCard({ icon: Icon, label, value, sub, color = 'text-white' }) {
  return (
    <div className="card p-3">
      <div className="flex items-center gap-2 mb-1">
        <Icon size={12} className="text-gray-500" />
        <span className="text-[10px] text-gray-500 uppercase tracking-wider">{label}</span>
      </div>
      <div className={`text-lg font-bold ${color}`}>{value}</div>
      {sub && <div className="text-[10px] text-gray-500 mt-0.5">{sub}</div>}
    </div>
  );
}

function BudgetBar({ label, spent, limit, pct }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-[10px] text-gray-500 w-14">{label}</span>
      <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${barColor(pct)}`}
             style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className={`text-[10px] font-mono ${pctColor(pct)}`}>
        {fmt$(spent)} / {fmt$(limit)}
      </span>
    </div>
  );
}

function MiniChart({ data }) {
  if (!data || data.length === 0) return <div className="text-[10px] text-gray-600">No data yet</div>;
  const max = Math.max(...data.map((d) => d.cost), 0.001);
  return (
    <div className="flex items-end gap-[2px] h-20">
      {data.slice(-30).map((d, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-0.5">
          <div className="w-full bg-emerald-500/60 rounded-t-sm transition-all hover:bg-emerald-400"
               style={{ height: `${Math.max((d.cost / max) * 100, 2)}%` }}
               title={`${d.date}: ${fmt$(d.cost)} (${d.requests} reqs)`} />
        </div>
      ))}
    </div>
  );
}

function ModelTable({ models }) {
  if (!models || models.length === 0) return <div className="text-[10px] text-gray-600">No usage data</div>;
  return (
    <div className="space-y-1.5">
      {models.map((m, i) => {
        const color = PROVIDER_COLORS[m.provider] || PROVIDER_COLORS.unknown;
        const totalTokens = (m.input_tokens || 0) + (m.output_tokens || 0);
        return (
          <div key={i} className="flex items-center gap-2 text-[11px]">
            <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
            <span className="text-gray-300 flex-1 truncate">{m.model}</span>
            <span className="text-gray-500 w-12 text-right">{m.requests}x</span>
            <span className="text-gray-400 w-16 text-right font-mono">{fmtNum(totalTokens)}</span>
            <span className="text-emerald-400 w-16 text-right font-mono">{fmt$(m.cost)}</span>
          </div>
        );
      })}
    </div>
  );
}

function RecentTable({ recent }) {
  if (!recent || recent.length === 0) return <div className="text-[10px] text-gray-600">No recent requests</div>;
  return (
    <div className="space-y-0.5 max-h-48 overflow-y-auto">
      {recent.slice(0, 20).map((r) => (
        <div key={r.id} className="flex items-center gap-2 text-[10px] py-1 border-b border-white/5">
          <div className="w-2 h-2 rounded-full flex-shrink-0"
               style={{ backgroundColor: PROVIDER_COLORS[r.provider] || PROVIDER_COLORS.unknown }} />
          <span className="text-gray-400 w-28 truncate">{r.model}</span>
          <span className="text-gray-500 w-12 hidden md:inline">{r.feature}</span>
          <span className="text-gray-500 w-16 text-right font-mono hidden md:inline">{fmtNum((r.input_tokens || 0) + (r.output_tokens || 0))}</span>
          <span className="text-emerald-400 w-14 text-right font-mono">{fmt$(r.cost_usd)}</span>
          <span className="text-gray-600 w-12 text-right hidden md:inline">{fmtMs(r.latency_ms)}</span>
          {r.error && <AlertTriangle size={10} className="text-red-400" />}
          <span className="text-gray-600 ml-auto text-[9px]">
            {new Date(r.created_at + 'Z').toLocaleTimeString()}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Provider Config (Phase 2) ────────────────────────────────

function ProviderConfig({ providers, preferences, onSave }) {
  const [preferred, setPreferred] = useState(preferences?.preferred_provider || '');
  const [enabled, setEnabled] = useState(preferences?.enabled_providers || []);

  useEffect(() => {
    setPreferred(preferences?.preferred_provider || '');
    setEnabled(preferences?.enabled_providers || []);
  }, [preferences]);

  const toggleProvider = (name) => {
    setEnabled((prev) =>
      prev.includes(name) ? prev.filter((p) => p !== name) : [...prev, name]
    );
  };

  const save = () => onSave(preferred, enabled);

  if (!providers || providers.length === 0) {
    return <div className="text-[10px] text-gray-600">No providers available</div>;
  }

  return (
    <div className="space-y-2">
      {providers.map((p) => (
        <div key={p.name} className="flex items-center gap-2 text-[11px]">
          <button onClick={() => toggleProvider(p.name)}
                  className={`w-3 h-3 rounded border ${enabled.includes(p.name)
                    ? 'bg-emerald-500 border-emerald-500' : 'border-gray-600'}`} />
          <div className="w-2 h-2 rounded-full"
               style={{ backgroundColor: PROVIDER_COLORS[p.name] || PROVIDER_COLORS.unknown }} />
          <span className="text-gray-300 flex-1">{p.name}</span>
          <span className={`text-[9px] px-1.5 py-0.5 rounded ${
            p.available ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
          }`}>{p.available ? 'online' : 'offline'}</span>
          <button onClick={() => setPreferred(p.name)}
                  className={`text-[9px] px-1.5 py-0.5 rounded ${
                    preferred === p.name ? 'bg-blue-500/20 text-blue-400' : 'bg-white/5 text-gray-500'
                  }`}>
            {preferred === p.name ? 'default' : 'set default'}
          </button>
        </div>
      ))}
      <button onClick={save}
              className="text-[10px] bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1 rounded mt-1">
        Save Preferences
      </button>
    </div>
  );
}

// ── Sync Status (Phase 3) ────────────────────────────────────

function SyncIndicator({ syncData, onSync }) {
  if (!syncData || !syncData.configured) {
    return (
      <div className="flex items-center gap-1.5 text-[10px] text-gray-600">
        <WifiOff size={10} /> Sync not configured
      </div>
    );
  }
  const ago = syncData.last_sync
    ? `${Math.round((Date.now() - new Date(syncData.last_sync + 'Z').getTime()) / 60000)}m ago`
    : 'never';

  return (
    <div className="flex items-center gap-2 text-[10px]">
      <Wifi size={10} className={syncData.status === 'ok' ? 'text-emerald-400' : 'text-amber-400'} />
      <span className="text-gray-400">Synced {ago}</span>
      {syncData.pending > 0 && (
        <span className="text-amber-400">{syncData.pending} pending</span>
      )}
      <button onClick={onSync} className="text-gray-500 hover:text-white">
        <RefreshCw size={10} />
      </button>
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────

export default function UsageView() {
  const [today, setToday] = useState(null);
  const [summary, setSummary] = useState([]);
  const [byModel, setByModel] = useState([]);
  const [budget, setBudget] = useState(null);
  const [recent, setRecent] = useState([]);
  const [providers, setProviders] = useState(null);
  const [syncData, setSyncData] = useState(null);
  const [showBudget, setShowBudget] = useState(false);
  const [showProviders, setShowProviders] = useState(false);
  const [budgetDaily, setBudgetDaily] = useState('');
  const [budgetMonthly, setBudgetMonthly] = useState('');

  const load = async () => {
    const [t, s, m, b, r] = await Promise.allSettled([
      fetchUsageToday(), fetchUsageSummary(), fetchUsageByModel(),
      fetchUsageBudget(), fetchRecentUsage(),
    ]);
    if (t.status === 'fulfilled') setToday(t.value);
    if (s.status === 'fulfilled') setSummary(s.value);
    if (m.status === 'fulfilled') setByModel(m.value);
    if (b.status === 'fulfilled') {
      setBudget(b.value);
      setBudgetDaily(String(b.value.daily_limit));
      setBudgetMonthly(String(b.value.monthly_limit));
    }
    if (r.status === 'fulfilled') setRecent(r.value);

    // Phase 2+3 — best-effort
    const [p, sy] = await Promise.allSettled([fetchProviders(), fetchSyncStatus()]);
    if (p.status === 'fulfilled') setProviders(p.value);
    if (sy.status === 'fulfilled') setSyncData(sy.value);
  };

  useEffect(() => { load(); }, []);
  useEffect(() => { const id = setInterval(load, 60000); return () => clearInterval(id); }, []);

  const saveBudget = async () => {
    const d = parseFloat(budgetDaily), m = parseFloat(budgetMonthly);
    if (isNaN(d) || isNaN(m)) return;
    await updateUsageBudget(d, m);
    load();
  };

  const saveProviderPrefs = async (preferred, enabled) => {
    await updateProviderPrefs(preferred, enabled);
    load();
  };

  const handleSync = async () => {
    try { await triggerSync(); } catch { /* ignore */ }
    load();
  };

  const monthlyCost = summary.reduce((s, d) => s + (d.cost || 0), 0);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity size={14} className="text-emerald-400" />
          <span className="text-xs font-semibold text-gray-300">AI Usage</span>
        </div>
        <div className="flex items-center gap-3">
          <SyncIndicator syncData={syncData} onSync={handleSync} />
          <button onClick={load} className="text-gray-500 hover:text-white">
            <RefreshCw size={12} />
          </button>
        </div>
      </div>

      {/* Budget Alert */}
      {budget && budget.daily_pct >= 70 && (
        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-[11px] ${
          budget.daily_pct >= 90 ? 'bg-red-500/10 text-red-400 border border-red-500/20'
            : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
        }`}>
          <AlertTriangle size={12} />
          <span>
            Daily budget {budget.daily_pct >= 90 ? 'exceeded' : 'warning'}: {fmt$(budget.daily_spent)} / {fmt$(budget.daily_limit)}
            {budget.monthly_pct >= 70 && ` | Monthly: ${fmt$(budget.monthly_spent)} / ${fmt$(budget.monthly_limit)}`}
          </span>
        </div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-4 gap-3">
        <MetricCard icon={DollarSign} label="Today's Cost"
                    value={today ? fmt$(today.cost || 0) : '—'}
                    sub={today ? `${fmtNum(today.requests)} requests` : ''}
                    color="text-emerald-400" />
        <MetricCard icon={DollarSign} label="Monthly Cost"
                    value={fmt$(monthlyCost)}
                    sub={`${summary.length} days tracked`}
                    color="text-blue-400" />
        <MetricCard icon={Zap} label="Tokens Today"
                    value={today ? fmtNum((today.input_tokens || 0) + (today.output_tokens || 0)) : '—'}
                    sub={today ? `${fmtNum(today.input_tokens || 0)} in / ${fmtNum(today.output_tokens || 0)} out` : ''} />
        <MetricCard icon={Clock} label="Avg Latency"
                    value={today && today.avg_latency ? fmtMs(today.avg_latency) : '—'}
                    sub={today?.errors > 0 ? `${today.errors} errors` : 'No errors'} />
      </div>

      {/* Budget Bars */}
      {budget && (
        <div className="card p-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-gray-500 uppercase tracking-wider">Budget</span>
            <button onClick={() => setShowBudget(!showBudget)}
                    className="text-gray-500 hover:text-white">
              {showBudget ? <ChevronUp size={12} /> : <Settings size={12} />}
            </button>
          </div>
          <BudgetBar label="Daily" spent={budget.daily_spent} limit={budget.daily_limit} pct={budget.daily_pct} />
          <BudgetBar label="Monthly" spent={budget.monthly_spent} limit={budget.monthly_limit} pct={budget.monthly_pct} />
          {showBudget && (
            <div className="flex items-center gap-2 mt-2 pt-2 border-t border-white/5">
              <input value={budgetDaily} onChange={(e) => setBudgetDaily(e.target.value)}
                     className="bg-white/5 border border-white/10 rounded px-2 py-1 text-[11px] w-20 text-white"
                     placeholder="Daily $" />
              <input value={budgetMonthly} onChange={(e) => setBudgetMonthly(e.target.value)}
                     className="bg-white/5 border border-white/10 rounded px-2 py-1 text-[11px] w-20 text-white"
                     placeholder="Monthly $" />
              <button onClick={saveBudget}
                      className="text-[10px] bg-emerald-600 hover:bg-emerald-500 text-white px-2 py-1 rounded">
                Save
              </button>
            </div>
          )}
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-2 gap-3">
        <div className="card p-3">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Cost Over Time (30d)</div>
          <MiniChart data={summary} />
          {summary.length > 0 && (
            <div className="flex justify-between mt-1 text-[9px] text-gray-600">
              <span>{summary[0]?.date}</span>
              <span>{summary[summary.length - 1]?.date}</span>
            </div>
          )}
        </div>
        <div className="card p-3">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">By Model</div>
          <ModelTable models={byModel} />
        </div>
      </div>

      {/* Provider Config (Phase 2) */}
      {providers && providers.providers && providers.providers.length > 0 && (
        <div className="card p-3">
          <button onClick={() => setShowProviders(!showProviders)}
                  className="flex items-center justify-between w-full">
            <div className="flex items-center gap-2">
              <Server size={12} className="text-gray-500" />
              <span className="text-[10px] text-gray-500 uppercase tracking-wider">AI Providers</span>
            </div>
            {showProviders ? <ChevronUp size={12} className="text-gray-500" /> : <ChevronDown size={12} className="text-gray-500" />}
          </button>
          {showProviders && (
            <div className="mt-3 pt-2 border-t border-white/5">
              <ProviderConfig
                providers={providers.providers}
                preferences={providers.preferences}
                onSave={saveProviderPrefs}
              />
            </div>
          )}
        </div>
      )}

      {/* Recent Requests */}
      <div className="card p-3">
        <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Recent Requests</div>
        <RecentTable recent={recent} />
      </div>
    </div>
  );
}
