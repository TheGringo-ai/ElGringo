import { useState, useEffect } from 'react';
import {
  Rocket, Plus, Play, Hammer, Upload, Archive, ExternalLink,
  CheckCircle2, Loader2, ChevronLeft,
  Globe, FolderOpen, FileCode,
} from 'lucide-react';
import {
  fetchFactoryApps, createFactoryApp, fetchFactoryApp,
  generateFactoryApp, buildFactoryApp, deployFactoryApp,
  archiveFactoryApp, fetchFactoryTemplates, fetchFactoryPortfolio,
  fetchFactoryFiles, readFactoryFile, writeFactoryFile,
  createFactoryFile, deleteFactoryFile, exportFactoryApp,
} from '../api';
import FileBrowser from './FileBrowser';

const STATUS_COLORS = {
  draft: 'bg-gray-500/20 text-gray-400',
  generating: 'bg-blue-500/20 text-blue-400',
  building: 'bg-yellow-500/20 text-yellow-400',
  deploying: 'bg-purple-500/20 text-purple-400',
  live: 'bg-emerald-500/20 text-emerald-400',
  failed: 'bg-red-500/20 text-red-400',
  archived: 'bg-gray-600/20 text-gray-500',
};

const STEP_ORDER = ['generate', 'test', 'audit', 'docker', 'deploy'];
const STEP_ICONS = { generate: FileCode, test: CheckCircle2, audit: CheckCircle2, docker: Hammer, deploy: Upload };

const LANG_MAP = {
  '.py': 'python', '.js': 'javascript', '.jsx': 'jsx', '.ts': 'typescript', '.tsx': 'tsx',
  '.html': 'html', '.css': 'css', '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
  '.md': 'markdown', '.sh': 'shell', '.sql': 'sql', '.toml': 'toml',
};

function StatusBadge({ status }) {
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[status] || STATUS_COLORS.draft}`}>
      {status}
    </span>
  );
}

function PortfolioCards({ portfolio }) {
  if (!portfolio) return null;
  const cards = [
    { label: 'Total Apps', value: portfolio.total_apps, color: 'text-blue-400' },
    { label: 'Live Apps', value: portfolio.live_apps, color: 'text-emerald-400' },
    { label: 'Total MRR', value: `$${portfolio.total_mrr.toLocaleString()}`, color: 'text-emerald-400' },
    { label: 'Customers', value: portfolio.total_customers, color: 'text-purple-400' },
  ];
  return (
    <div className="grid grid-cols-4 gap-3">
      {cards.map((c) => (
        <div key={c.label} className="card p-3 text-center">
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">{c.label}</div>
          <div className={`text-xl font-bold ${c.color}`}>{c.value}</div>
        </div>
      ))}
    </div>
  );
}

function BuildPipeline({ builds }) {
  const latestByStep = {};
  (builds || []).forEach((b) => {
    if (!latestByStep[b.step] || b.version > latestByStep[b.step].version) latestByStep[b.step] = b;
  });
  return (
    <div className="flex items-center gap-1">
      {STEP_ORDER.map((step, i) => {
        const build = latestByStep[step];
        const StepIcon = STEP_ICONS[step] || CheckCircle2;
        let color = 'text-gray-600', bg = 'bg-white/5';
        if (build) {
          if (build.status === 'passed') { color = 'text-emerald-400'; bg = 'bg-emerald-500/10'; }
          else if (build.status === 'failed') { color = 'text-red-400'; bg = 'bg-red-500/10'; }
          else if (build.status === 'running') { color = 'text-blue-400'; bg = 'bg-blue-500/10'; }
        }
        return (
          <div key={step} className="flex items-center gap-1">
            <div className={`flex items-center gap-1 px-2 py-1 rounded ${bg}`} title={`${step}: ${build?.status || 'pending'}`}>
              {build?.status === 'running' ? <Loader2 size={11} className={`${color} animate-spin`} /> : <StepIcon size={11} className={color} />}
              <span className={`text-[9px] ${color}`}>{step}</span>
            </div>
            {i < STEP_ORDER.length - 1 && <span className="text-gray-700 text-[10px]">&#8594;</span>}
          </div>
        );
      })}
    </div>
  );
}

function AppCard({ app, onClick }) {
  return (
    <button onClick={() => onClick(app.id)} className="card p-4 text-left w-full hover:bg-white/5 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="text-sm font-semibold text-white">{app.display_name}</div>
          <div className="text-[10px] text-gray-500">{app.name} · {app.app_type}</div>
        </div>
        <StatusBadge status={app.status} />
      </div>
      {app.description && <p className="text-[11px] text-gray-400 mb-2 line-clamp-2">{app.description}</p>}
      {app.deploy_url && (
        <div className="text-[10px] text-blue-400 flex items-center gap-1"><Globe size={9} /> {app.deploy_url}</div>
      )}
    </button>
  );
}

function NewAppForm({ templates, onCreated, onCancel }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [appType, setAppType] = useState('fullstack');
  const [template, setTemplate] = useState('');
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!name.trim()) return;
    setCreating(true);
    try {
      await createFactoryApp({
        name: name.trim().toLowerCase().replace(/\s+/g, '-'),
        description, app_type: appType, template: template || undefined,
      });
      onCreated();
    } catch (err) { alert(err.response?.data?.detail || err.message); }
    finally { setCreating(false); }
  };

  return (
    <div className="card p-4 space-y-3">
      <div className="text-xs font-semibold text-gray-300 flex items-center gap-2"><Plus size={12} /> New App</div>
      <input value={name} onChange={(e) => setName(e.target.value)} placeholder="App name (e.g. invoice-tracker)" className="input text-xs w-full" autoFocus />
      <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Describe what this app does..." className="input text-xs w-full h-16 resize-none" />
      <div className="flex gap-2">
        <select value={appType} onChange={(e) => setAppType(e.target.value)} className="input text-xs flex-1">
          <option value="api">API Only</option>
          <option value="web">Web Frontend</option>
          <option value="fullstack">Full-Stack</option>
        </select>
        <select value={template} onChange={(e) => setTemplate(e.target.value)} className="input text-xs flex-1">
          <option value="">No template</option>
          {templates.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
      </div>
      <div className="flex gap-2 justify-end">
        <button onClick={onCancel} className="btn-ghost text-xs px-3 py-1">Cancel</button>
        <button onClick={handleCreate} disabled={!name.trim() || creating} className="btn-primary text-xs px-3 py-1">
          {creating ? <Loader2 size={11} className="animate-spin inline mr-1" /> : <Plus size={11} className="inline mr-1" />}Create
        </button>
      </div>
    </div>
  );
}

function FactoryFileBrowser({ appId }) {
  return (
    <FileBrowser
      fetchFiles={(p) => fetchFactoryFiles(appId, p)}
      readFile={(p) => readFactoryFile(appId, p)}
      writeFile={(p, c) => writeFactoryFile(appId, p, c)}
      createFile={(p, c) => createFactoryFile(appId, p, c)}
      deleteFile={(p) => deleteFactoryFile(appId, p)}
      exportUrl={exportFactoryApp(appId)}
    />
  );
}

// ── App Detail ──────────────────────────────────────────────────────

function AppDetail({ appId, onBack }) {
  const [app, setApp] = useState(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState('');
  const [activeTab, setActiveTab] = useState('files');

  const load = async () => {
    setLoading(true);
    try { setApp(await fetchFactoryApp(appId)); } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => { load(); }, [appId]);

  const runAction = async (action, fn) => {
    setActionLoading(action);
    try { await fn(appId); await load(); } catch (err) { alert(err.response?.data?.detail || err.message); }
    setActionLoading('');
  };

  if (loading && !app) return <div className="text-xs text-gray-500 p-4">Loading...</div>;
  if (!app) return <div className="text-xs text-red-400 p-4">App not found</div>;

  const tabs = [
    { id: 'files', label: 'Files', icon: FolderOpen },
    { id: 'pipeline', label: 'Pipeline', icon: Hammer },
    { id: 'info', label: 'Info', icon: Globe },
  ];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <button onClick={onBack} className="btn-ghost p-1"><ChevronLeft size={14} /></button>
        <Rocket size={14} className="text-blue-400" />
        <span className="text-sm font-semibold text-white">{app.display_name}</span>
        <StatusBadge status={app.status} />
      </div>

      {app.description && <p className="text-[11px] text-gray-400">{app.description}</p>}

      {/* Actions */}
      <div className="flex items-center gap-2 flex-wrap">
        <button onClick={() => runAction('generate', generateFactoryApp)} disabled={!!actionLoading}
          className="btn-ghost text-xs px-3 py-1.5 flex items-center gap-1">
          {actionLoading === 'generate' ? <Loader2 size={11} className="animate-spin" /> : <Play size={11} />} Generate
        </button>
        <button onClick={() => runAction('build', buildFactoryApp)} disabled={!!actionLoading}
          className="btn-ghost text-xs px-3 py-1.5 flex items-center gap-1">
          {actionLoading === 'build' ? <Loader2 size={11} className="animate-spin" /> : <Hammer size={11} />} Build
        </button>
        <button onClick={() => runAction('deploy', deployFactoryApp)} disabled={!!actionLoading}
          className="btn-ghost text-xs px-3 py-1.5 flex items-center gap-1">
          {actionLoading === 'deploy' ? <Loader2 size={11} className="animate-spin" /> : <Upload size={11} />} Deploy
        </button>
        <button onClick={() => { if (confirm('Archive this app?')) runAction('archive', archiveFactoryApp); }}
          disabled={!!actionLoading}
          className="btn-ghost text-xs px-3 py-1.5 flex items-center gap-1 text-red-400">
          <Archive size={11} /> Archive
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-white/5">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-[11px] border-b-2 transition-colors ${
              activeTab === t.id ? 'border-blue-400 text-white' : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}>
            <t.icon size={11} /> {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'files' && <FactoryFileBrowser appId={appId} />}

      {activeTab === 'pipeline' && (
        <div className="space-y-3">
          <div className="card p-3">
            <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Build Pipeline</div>
            <BuildPipeline builds={app.builds} />
          </div>
          {app.builds && app.builds.length > 0 && (
            <div className="card p-3">
              <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Build Log</div>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {app.builds.map((b) => (
                  <div key={b.id} className="text-[10px] border-b border-white/5 pb-1.5">
                    <div className="flex items-center gap-2">
                      <span className={`font-medium ${b.status === 'passed' ? 'text-emerald-400' : b.status === 'failed' ? 'text-red-400' : 'text-gray-400'}`}>
                        v{b.version} {b.step}
                      </span>
                      <span className="text-gray-600">{b.status}</span>
                      {b.completed_at && <span className="text-gray-700 ml-auto">{b.completed_at}</span>}
                    </div>
                    {b.log && <div className="text-gray-500 mt-0.5 truncate">{b.log.slice(0, 200)}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}
          {app.error_message && (
            <div className="card p-3 border border-red-500/20">
              <div className="text-[10px] text-red-400 uppercase tracking-wider mb-1">Error</div>
              <div className="text-xs text-red-300">{app.error_message}</div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'info' && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="card p-3">
              <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Type</div>
              <div className="text-xs text-white">{app.app_type}</div>
            </div>
            <div className="card p-3">
              <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Port</div>
              <div className="text-xs text-white">{app.port || '—'}</div>
            </div>
            <div className="card p-3">
              <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Customers</div>
              <div className="text-xs text-white">{app.customer_count || 0}</div>
            </div>
            <div className="card p-3">
              <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">MRR</div>
              <div className="text-xs text-emerald-400">${(app.total_mrr || 0).toLocaleString()}</div>
            </div>
          </div>
          {app.deploy_url && (
            <div className="card p-3 flex items-center gap-2">
              <Globe size={12} className="text-blue-400" />
              <a href={app.deploy_url} target="_blank" rel="noopener noreferrer"
                className="text-xs text-blue-400 hover:underline flex items-center gap-1">
                {app.deploy_url} <ExternalLink size={9} />
              </a>
            </div>
          )}
          {app.project_dir && (
            <div className="card p-3">
              <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Project Dir</div>
              <div className="text-[11px] text-gray-400 font-mono">{app.project_dir}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main View ───────────────────────────────────────────────────────

export default function FactoryView() {
  const [apps, setApps] = useState([]);
  const [portfolio, setPortfolio] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [showNew, setShowNew] = useState(false);
  const [selectedApp, setSelectedApp] = useState(null);

  const load = async () => {
    const [a, p, t] = await Promise.allSettled([
      fetchFactoryApps(), fetchFactoryPortfolio(), fetchFactoryTemplates(),
    ]);
    if (a.status === 'fulfilled') setApps(a.value);
    if (p.status === 'fulfilled') setPortfolio(p.value);
    if (t.status === 'fulfilled') setTemplates(t.value);
  };

  useEffect(() => { load(); }, []);

  if (selectedApp) {
    return <AppDetail appId={selectedApp} onBack={() => { setSelectedApp(null); load(); }} />;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Rocket size={14} className="text-blue-400" />
          <span className="text-xs font-semibold text-gray-300">App Factory</span>
          <span className="text-[10px] text-gray-600">{apps.length} apps</span>
        </div>
        <button onClick={() => setShowNew(!showNew)} className="btn-primary text-xs px-3 py-1 flex items-center gap-1">
          <Plus size={11} /> New App
        </button>
      </div>

      <PortfolioCards portfolio={portfolio} />

      {showNew && (
        <NewAppForm templates={templates} onCreated={() => { setShowNew(false); load(); }} onCancel={() => setShowNew(false)} />
      )}

      {apps.length === 0 && !showNew ? (
        <div className="card p-8 text-center">
          <Rocket size={24} className="text-gray-600 mx-auto mb-2" />
          <div className="text-xs text-gray-500 mb-2">No apps yet</div>
          <button onClick={() => setShowNew(true)} className="btn-primary text-xs px-3 py-1">Create your first app</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {apps.map((app) => <AppCard key={app.id} app={app} onClick={setSelectedApp} />)}
        </div>
      )}
    </div>
  );
}
