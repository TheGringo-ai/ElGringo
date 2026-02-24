import { useState, useEffect, useCallback } from 'react';
import {
  Rocket, Plus, Play, Hammer, Upload, Archive, ExternalLink,
  CheckCircle2, XCircle, Clock, Loader2, ChevronLeft, ChevronRight,
  DollarSign, Users, Globe, FileCode, FolderOpen, File, Folder,
  Pencil, Trash2, Download, Save, X, FilePlus, FolderPlus, CornerUpLeft,
} from 'lucide-react';
import {
  fetchFactoryApps, createFactoryApp, fetchFactoryApp,
  generateFactoryApp, buildFactoryApp, deployFactoryApp,
  archiveFactoryApp, fetchFactoryTemplates, fetchFactoryPortfolio,
  fetchFactoryFiles, readFactoryFile, writeFactoryFile,
  createFactoryFile, deleteFactoryFile, renameFactoryFile, exportFactoryApp,
} from '../api';

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

// ── File Browser ────────────────────────────────────────────────────

function FileBrowser({ appId }) {
  const [currentPath, setCurrentPath] = useState('');
  const [entries, setEntries] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [fileMeta, setFileMeta] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showNewFile, setShowNewFile] = useState(false);
  const [newFileName, setNewFileName] = useState('');
  const [newFileIsDir, setNewFileIsDir] = useState(false);

  const loadDir = useCallback(async (path = '') => {
    setLoading(true);
    try {
      const data = await fetchFactoryFiles(appId, path);
      setEntries(data.entries || []);
      setCurrentPath(data.path || '');
    } catch { setEntries([]); }
    setLoading(false);
  }, [appId]);

  useEffect(() => { loadDir(''); }, [loadDir]);

  const openFile = async (entry) => {
    if (entry.is_dir) {
      setSelectedFile(null);
      setFileContent('');
      loadDir(entry.path);
      return;
    }
    setLoading(true);
    try {
      const data = await readFactoryFile(appId, entry.path);
      setFileMeta(data);
      if (data.binary) {
        setFileContent('(Binary file — cannot display)');
        setOriginalContent('');
      } else {
        setFileContent(data.content || '');
        setOriginalContent(data.content || '');
      }
      setSelectedFile(entry.path);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to read file');
    }
    setLoading(false);
  };

  const handleSave = async () => {
    if (!selectedFile || fileContent === originalContent) return;
    setSaving(true);
    try {
      await writeFactoryFile(appId, selectedFile, fileContent);
      setOriginalContent(fileContent);
    } catch (err) { alert(err.response?.data?.detail || 'Failed to save'); }
    setSaving(false);
  };

  const handleDelete = async (entry) => {
    const label = entry.is_dir ? 'directory' : 'file';
    if (!confirm(`Delete ${label} "${entry.name}"?`)) return;
    try {
      await deleteFactoryFile(appId, entry.path);
      if (selectedFile === entry.path) { setSelectedFile(null); setFileContent(''); }
      loadDir(currentPath);
    } catch (err) { alert(err.response?.data?.detail || 'Failed to delete'); }
  };

  const handleCreateFile = async () => {
    if (!newFileName.trim()) return;
    const path = currentPath && currentPath !== '.'
      ? `${currentPath}/${newFileName.trim()}${newFileIsDir ? '/' : ''}`
      : `${newFileName.trim()}${newFileIsDir ? '/' : ''}`;
    try {
      await createFactoryFile(appId, path);
      setShowNewFile(false);
      setNewFileName('');
      loadDir(currentPath);
    } catch (err) { alert(err.response?.data?.detail || 'Failed to create'); }
  };

  const goUp = () => {
    if (!currentPath || currentPath === '.') return;
    const parent = currentPath.split('/').slice(0, -1).join('/');
    setSelectedFile(null);
    setFileContent('');
    loadDir(parent);
  };

  const breadcrumbs = (currentPath && currentPath !== '.') ? currentPath.split('/') : [];
  const isDirty = selectedFile && fileContent !== originalContent;

  return (
    <div className="card overflow-hidden" style={{ minHeight: 300 }}>
      {/* Toolbar */}
      <div className="flex items-center gap-1 px-3 py-2 border-b border-white/5 bg-white/[0.02]">
        <FolderOpen size={12} className="text-yellow-400 mr-1" />
        <button onClick={() => { setSelectedFile(null); setFileContent(''); loadDir(''); }}
          className="text-[10px] text-gray-400 hover:text-white">root</button>
        {breadcrumbs.map((part, i) => (
          <span key={i} className="flex items-center gap-1">
            <ChevronRight size={9} className="text-gray-600" />
            <button onClick={() => {
              const p = breadcrumbs.slice(0, i + 1).join('/');
              setSelectedFile(null); setFileContent(''); loadDir(p);
            }} className="text-[10px] text-gray-400 hover:text-white">{part}</button>
          </span>
        ))}
        <div className="flex-1" />
        <button onClick={goUp} disabled={!currentPath || currentPath === '.'} className="btn-ghost p-1" title="Go up">
          <CornerUpLeft size={11} />
        </button>
        <button onClick={() => { setNewFileIsDir(false); setShowNewFile(true); }} className="btn-ghost p-1" title="New file">
          <FilePlus size={11} />
        </button>
        <button onClick={() => { setNewFileIsDir(true); setShowNewFile(true); }} className="btn-ghost p-1" title="New folder">
          <FolderPlus size={11} />
        </button>
        <a href={exportFactoryApp(appId)} className="btn-ghost p-1" title="Export as .tar.gz" download>
          <Download size={11} />
        </a>
      </div>

      {/* New file inline */}
      {showNewFile && (
        <div className="flex items-center gap-2 px-3 py-1.5 border-b border-white/5 bg-white/[0.03]">
          {newFileIsDir ? <FolderPlus size={11} className="text-yellow-400" /> : <FilePlus size={11} className="text-blue-400" />}
          <input value={newFileName} onChange={(e) => setNewFileName(e.target.value)}
            placeholder={newFileIsDir ? 'folder-name' : 'filename.py'}
            className="input text-[11px] flex-1 py-0.5" autoFocus
            onKeyDown={(e) => { if (e.key === 'Enter') handleCreateFile(); if (e.key === 'Escape') setShowNewFile(false); }} />
          <button onClick={handleCreateFile} className="btn-primary text-[10px] px-2 py-0.5">Create</button>
          <button onClick={() => setShowNewFile(false)} className="btn-ghost p-0.5"><X size={11} /></button>
        </div>
      )}

      <div className="flex" style={{ minHeight: 260 }}>
        {/* File list panel */}
        <div className="w-[220px] flex-shrink-0 border-r border-white/5 overflow-y-auto" style={{ maxHeight: 400 }}>
          {loading && entries.length === 0 && <div className="text-[10px] text-gray-600 p-3">Loading...</div>}
          {!loading && entries.length === 0 && <div className="text-[10px] text-gray-600 p-3">Empty directory</div>}
          {entries.map((entry) => (
            <div key={entry.path}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-[11px] cursor-pointer hover:bg-white/5 group ${selectedFile === entry.path ? 'bg-white/10 text-white' : 'text-gray-400'}`}
            >
              <div className="flex items-center gap-1.5 flex-1 min-w-0" onClick={() => openFile(entry)}>
                {entry.is_dir
                  ? <Folder size={12} className="text-yellow-400 flex-shrink-0" />
                  : <File size={12} className="text-gray-500 flex-shrink-0" />}
                <span className="truncate">{entry.name}</span>
                {!entry.is_dir && entry.size > 0 && (
                  <span className="text-[9px] text-gray-600 ml-auto flex-shrink-0">
                    {entry.size > 1024 ? `${(entry.size / 1024).toFixed(1)}K` : `${entry.size}B`}
                  </span>
                )}
              </div>
              <button onClick={(e) => { e.stopPropagation(); handleDelete(entry); }}
                className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 hover:text-red-400" title="Delete">
                <Trash2 size={10} />
              </button>
            </div>
          ))}
        </div>

        {/* Editor panel */}
        <div className="flex-1 flex flex-col min-w-0">
          {selectedFile ? (
            <>
              <div className="flex items-center gap-2 px-3 py-1.5 border-b border-white/5 bg-white/[0.02]">
                <File size={11} className="text-gray-500" />
                <span className="text-[10px] text-gray-400 truncate flex-1">{selectedFile}</span>
                {isDirty && <span className="text-[9px] text-yellow-400">unsaved</span>}
                {fileMeta && !fileMeta.binary && (
                  <button onClick={handleSave} disabled={saving || !isDirty}
                    className={`btn-primary text-[10px] px-2 py-0.5 flex items-center gap-1 ${!isDirty ? 'opacity-40' : ''}`}>
                    {saving ? <Loader2 size={9} className="animate-spin" /> : <Save size={9} />} Save
                  </button>
                )}
              </div>
              {fileMeta?.binary ? (
                <div className="p-4 text-xs text-gray-500 text-center">Binary file cannot be displayed</div>
              ) : (
                <textarea
                  value={fileContent}
                  onChange={(e) => setFileContent(e.target.value)}
                  className="flex-1 bg-transparent text-[11px] text-gray-300 font-mono p-3 resize-none outline-none leading-relaxed"
                  style={{ minHeight: 220, tabSize: 2 }}
                  spellCheck={false}
                  onKeyDown={(e) => {
                    // Ctrl/Cmd+S to save
                    if ((e.metaKey || e.ctrlKey) && e.key === 's') {
                      e.preventDefault();
                      handleSave();
                    }
                    // Tab inserts spaces
                    if (e.key === 'Tab') {
                      e.preventDefault();
                      const start = e.target.selectionStart;
                      const end = e.target.selectionEnd;
                      setFileContent(fileContent.substring(0, start) + '  ' + fileContent.substring(end));
                      setTimeout(() => { e.target.selectionStart = e.target.selectionEnd = start + 2; }, 0);
                    }
                  }}
                />
              )}
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-600 text-xs">
              <div className="text-center">
                <FileCode size={24} className="mx-auto mb-2 opacity-30" />
                Select a file to view or edit
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
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
      {activeTab === 'files' && <FileBrowser appId={appId} />}

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
