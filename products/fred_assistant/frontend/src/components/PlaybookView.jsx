import { useState, useEffect } from 'react';
import { BookOpen, Play, Plus, CheckCircle2, XCircle, Clock, Filter } from 'lucide-react';
import { fetchPlaybooks, createPlaybook, runPlaybook } from '../api';

const CATEGORY_COLORS = {
  autopilot: 'bg-purple-500/20 text-purple-400',
  project: 'bg-blue-500/20 text-blue-400',
  routine: 'bg-emerald-500/20 text-emerald-400',
  general: 'bg-gray-500/20 text-gray-400',
};

const STATUS_ICONS = {
  ok: <CheckCircle2 size={10} className="text-emerald-400" />,
  failed: <XCircle size={10} className="text-red-400" />,
  error: <XCircle size={10} className="text-red-400" />,
  proposed: <Clock size={10} className="text-amber-400" />,
};

export default function PlaybookView() {
  const [playbooks, setPlaybooks] = useState([]);
  const [filter, setFilter] = useState('all');
  const [showCreate, setShowCreate] = useState(false);
  const [runResults, setRunResults] = useState(null);
  const [running, setRunning] = useState(null);
  const [form, setForm] = useState({ name: '', description: '', category: 'general' });

  const load = async () => {
    try {
      const data = await fetchPlaybooks();
      setPlaybooks(data);
    } catch { setPlaybooks([]); }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!form.name.trim()) return;
    await createPlaybook(form);
    setForm({ name: '', description: '', category: 'general' });
    setShowCreate(false);
    load();
  };

  const handleRun = async (pb) => {
    setRunning(pb.id);
    setRunResults(null);
    try {
      const result = await runPlaybook(pb.id);
      setRunResults(result);
    } catch (err) {
      setRunResults({ error: err.message || 'Failed to run playbook' });
    } finally {
      setRunning(null);
    }
  };

  const categories = ['all', 'autopilot', 'project', 'routine', 'general'];
  const filtered = filter === 'all' ? playbooks : playbooks.filter((p) => p.category === filter);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BookOpen size={14} className="text-purple-400" />
          <span className="text-xs font-semibold text-gray-300">Playbooks</span>
          <span className="text-[10px] text-gray-600 bg-white/5 px-1.5 rounded-full">{playbooks.length}</span>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="btn-ghost text-xs py-1 px-2">
          <Plus size={12} />
        </button>
      </div>

      {/* Category Filters */}
      <div className="flex gap-1">
        {categories.map((c) => (
          <button key={c} onClick={() => setFilter(c)}
            className={`text-[10px] px-2 py-0.5 rounded-full ${filter === c ? 'bg-white/10 text-white' : 'text-gray-500 hover:text-gray-300'}`}>
            {c} ({c === 'all' ? playbooks.length : playbooks.filter((p) => p.category === c).length})
          </button>
        ))}
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="card p-3 space-y-2">
          <div className="text-[11px] font-semibold text-gray-400 mb-1">Create Playbook</div>
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Playbook name *" className="input text-xs w-full" />
          <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="Description" className="input text-xs w-full" />
          <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="input text-xs">
            {['general', 'autopilot', 'project', 'routine'].map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <button onClick={handleCreate} disabled={!form.name.trim()} className="btn-primary text-xs w-full disabled:opacity-40">
            Create Playbook
          </button>
        </div>
      )}

      {/* Run Results */}
      {runResults && (
        <div className="card p-3 space-y-2 border-purple-500/20">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-purple-300">
              Run Results: {runResults.playbook_name || 'Playbook'}
            </span>
            <button onClick={() => setRunResults(null)} className="text-[10px] text-gray-600 hover:text-gray-300">Close</button>
          </div>
          {runResults.error ? (
            <div className="text-[10px] text-red-400">{runResults.error}</div>
          ) : (
            <div className="space-y-1">
              {(runResults.steps || []).map((step, i) => (
                <div key={i} className="flex items-center gap-2 text-[10px]">
                  {STATUS_ICONS[step.status] || <Clock size={10} className="text-gray-500" />}
                  <span className={step.status === 'ok' ? 'text-gray-300' : step.status === 'proposed' ? 'text-amber-300' : 'text-red-300'}>
                    {step.label || step.action}
                  </span>
                  {step.status === 'proposed' && <span className="text-amber-500 text-[9px]">(needs approval)</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Playbook Grid */}
      <div className="grid grid-cols-1 gap-2">
        {filtered.map((pb) => (
          <div key={pb.id} className="card-hover p-3 animate-slide-up">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-medium">{pb.name}</span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${CATEGORY_COLORS[pb.category] || CATEGORY_COLORS.general}`}>
                    {pb.category}
                  </span>
                </div>
                {pb.description && <div className="text-[10px] text-gray-600 mb-1">{pb.description}</div>}
                <div className="text-[10px] text-gray-700">{pb.steps?.length || 0} steps</div>
              </div>
              <button
                onClick={() => handleRun(pb)}
                disabled={running === pb.id}
                className="btn-ghost text-xs py-1 px-2 flex items-center gap-1 disabled:opacity-40"
              >
                <Play size={10} className="text-emerald-400" />
                {running === pb.id ? 'Running...' : 'Run'}
              </button>
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="text-[11px] text-gray-700 text-center py-6">No playbooks found.</div>
        )}
      </div>
    </div>
  );
}
