import { useState, useEffect } from 'react';
import {
  GitBranch, GitCommit, FolderGit2, ExternalLink, RefreshCw,
  ChevronDown, ChevronRight, Activity, Zap, ListChecks, Search,
  FileCode, AlertTriangle, ShieldAlert, Wrench, CheckCircle2,
  Shield, TestTube2, BookOpen, Rocket, Layers,
} from 'lucide-react';
import {
  fetchProjects, fetchProjectCommits, fetchProjectBranches,
  analyzeRepo, fetchLatestAnalysis, generateRepoTasks, reviewRepo,
  auditProject, generateProjectTests, generateProjectDocs, fullProjectReview,
} from '../api';
import PlatformStatus from './PlatformStatus';

const STATUS_DOT = { clean: 'bg-emerald-400', dirty: 'bg-amber-400' };

const SEVERITY_STYLE = {
  high: 'bg-red-500/20 text-red-400',
  medium: 'bg-amber-500/20 text-amber-400',
  low: 'bg-gray-500/20 text-gray-400',
};

const TODO_TYPE_STYLE = {
  TODO: 'bg-blue-500/20 text-blue-400',
  FIXME: 'bg-red-500/20 text-red-400',
  HACK: 'bg-amber-500/20 text-amber-400',
  XXX: 'bg-purple-500/20 text-purple-400',
};

const CATEGORY_ICON = {
  testing: '🧪', devops: '⚙️', documentation: '📄', security: '🔒',
  dependencies: '📦', refactoring: '🔧', optimization: '⚡', tech_debt: '🧹',
};

function healthColor(score) {
  if (score >= 70) return 'text-emerald-400';
  if (score >= 40) return 'text-amber-400';
  return 'text-red-400';
}

function healthBg(score) {
  if (score >= 70) return 'bg-emerald-400';
  if (score >= 40) return 'bg-amber-400';
  return 'bg-red-400';
}

function TechBadge({ tech }) {
  const colors = {
    Python: 'bg-blue-500/20 text-blue-400', React: 'bg-cyan-500/20 text-cyan-400',
    'Node.js': 'bg-green-500/20 text-green-400', Docker: 'bg-blue-400/20 text-blue-300',
    TypeScript: 'bg-blue-600/20 text-blue-400', Vite: 'bg-purple-500/20 text-purple-400',
    Tailwind: 'bg-teal-500/20 text-teal-400', 'Next.js': 'bg-white/10 text-gray-300',
  };
  return (
    <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${colors[tech] || 'bg-white/5 text-gray-500'}`}>
      {tech}
    </span>
  );
}

function HealthBadge({ score }) {
  if (score === null || score === undefined) return null;
  return (
    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${healthColor(score)} bg-white/5`}>
      {score}
    </span>
  );
}

/* ── Service Result Panel ────────────────────────────────────────── */

function ServiceResultPanel({ title, icon, result, onClose }) {
  if (!result) return null;
  const content = result.findings || result.result || result.content || result.readme ||
    result.docs || result.architecture || result.tests || result.analysis || '';
  return (
    <div className="mt-2 p-2 rounded bg-white/[0.02] border border-white/5">
      <div className="flex items-center justify-between mb-1.5">
        <h5 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1">
          {icon} {title}
        </h5>
        <button onClick={onClose} className="text-[9px] text-gray-600 hover:text-gray-400">dismiss</button>
      </div>
      {result.agents_used?.length > 0 && (
        <div className="text-[9px] text-gray-600 mb-1">
          Agents: {result.agents_used.join(', ')} | {result.total_time?.toFixed(1)}s
        </div>
      )}
      <pre className="text-[10px] text-gray-400 whitespace-pre-wrap max-h-60 overflow-y-auto bg-black/20 rounded p-2 font-mono">
        {typeof content === 'string' ? content.slice(0, 3000) : JSON.stringify(content, null, 2).slice(0, 3000)}
        {content.length > 3000 && '\n\n... (truncated)'}
      </pre>
    </div>
  );
}

/* ── Code Review Panel (expanded below project card) ────────────── */

function CodeReviewPanel({ review, projectName, onFixIssues }) {
  const [fixing, setFixing] = useState(false);
  const [fixResult, setFixResult] = useState(null);
  const [showAllTodos, setShowAllTodos] = useState(false);

  if (!review) return null;

  const todos = review.todo_items || [];
  const actions = review.action_items || [];
  const score = review.health_score;
  const visibleTodos = showAllTodos ? todos : todos.slice(0, 8);

  const handleFix = async () => {
    setFixing(true);
    try {
      const result = await generateRepoTasks(projectName, true);
      setFixResult(result);
      if (onFixIssues) onFixIssues(result);
    } catch { /* ignore */ }
    setFixing(false);
  };

  return (
    <div className="mt-3 space-y-3 border-t border-white/5 pt-3">
      <div className="flex items-center gap-2">
        <Activity size={10} className={healthColor(score)} />
        <span className={`text-[10px] font-bold ${healthColor(score)}`}>{score}/100</span>
        <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
          <div className={`h-full rounded-full transition-all ${healthBg(score)}`} style={{ width: `${score}%` }} />
        </div>
      </div>

      {actions.length > 0 && (
        <div>
          <h5 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5 flex items-center gap-1">
            <AlertTriangle size={10} /> Action Items ({actions.length})
          </h5>
          <div className="space-y-1">
            {actions.map((a, i) => (
              <div key={i} className="flex items-start gap-2 py-1 px-2 rounded bg-white/[0.02] hover:bg-white/[0.04] transition-colors">
                <span className={`text-[9px] px-1.5 py-0.5 rounded-full mt-0.5 flex-shrink-0 ${SEVERITY_STYLE[a.severity]}`}>
                  {a.severity}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-[11px] text-gray-300 font-medium flex items-center gap-1.5">
                    <span>{CATEGORY_ICON[a.category] || '📋'}</span>
                    {a.title}
                    {a.revenue_impact && (
                      <span className="text-[8px] px-1 py-0.5 rounded bg-amber-500/20 text-amber-400 flex-shrink-0">
                        {a.revenue_impact}
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] text-gray-600 mt-0.5 whitespace-pre-line line-clamp-2">{a.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {actions.length === 0 && (
        <div className="flex items-center gap-2 py-2 px-3 rounded bg-emerald-500/5">
          <CheckCircle2 size={12} className="text-emerald-400" />
          <span className="text-[11px] text-emerald-400">No issues found</span>
        </div>
      )}

      {todos.length > 0 && (
        <div>
          <h5 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5 flex items-center gap-1">
            <FileCode size={10} /> TODOs & FIXMEs ({todos.length})
          </h5>
          <div className="space-y-0.5">
            {visibleTodos.map((t, i) => (
              <div key={i} className="flex items-center gap-1.5 py-0.5">
                <span className={`text-[8px] px-1 py-0.5 rounded ${TODO_TYPE_STYLE[t.type] || 'bg-white/5 text-gray-500'}`}>
                  {t.type}
                </span>
                <span className="text-[10px] text-gray-500 font-mono flex-shrink-0 w-[120px] truncate" title={`${t.file}:${t.line}`}>
                  {t.file}{t.line ? `:${t.line}` : ''}
                </span>
                <span className="text-[10px] text-gray-400 truncate flex-1" title={t.text}>{t.text}</span>
              </div>
            ))}
          </div>
          {todos.length > 8 && (
            <button onClick={() => setShowAllTodos(!showAllTodos)} className="text-[9px] text-blue-400 hover:text-blue-300 mt-1">
              {showAllTodos ? 'Show less' : `Show all ${todos.length}`}
            </button>
          )}
        </div>
      )}

      <div className="flex items-center gap-2 pt-1">
        {!fixResult && (
          <button onClick={handleFix} disabled={fixing}
            className="text-[10px] px-3 py-1 rounded-full bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors flex items-center gap-1">
            <Wrench size={10} />
            {fixing ? 'Creating tasks...' : 'Fix Issues & Create TODO List'}
          </button>
        )}
      </div>

      {fixResult?.tasks && (
        <div className="space-y-1.5 p-2 rounded bg-emerald-500/5 border border-emerald-500/10">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 size={11} className="text-emerald-400" />
            <span className="text-[11px] text-emerald-400 font-medium">Created {fixResult.count} tasks</span>
          </div>
          <div className="space-y-0.5 max-h-40 overflow-y-auto">
            {fixResult.tasks.map((t, i) => (
              <div key={i} className="text-[10px] text-gray-400 flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                  t.priority === 1 ? 'bg-red-400' : t.priority === 2 ? 'bg-amber-400' : 'bg-gray-500'
                }`} />
                <span className="truncate">{t.title}</span>
                {t.task_id && <span className="text-[8px] text-gray-600 font-mono flex-shrink-0">{t.task_id}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="text-[9px] text-gray-700">
        Reviewed: {review.created_at?.slice(0, 16).replace('T', ' ')}
      </div>
    </div>
  );
}

/* ── Project Card ────────────────────────────────────────────────── */

function ProjectCard({ project, expanded, onToggle, analysis }) {
  const [commits, setCommits] = useState([]);
  const [branches, setBranches] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [review, setReview] = useState(null);
  const [localAnalysis, setLocalAnalysis] = useState(analysis);
  // Platform service states
  const [activeAction, setActiveAction] = useState(null);  // 'audit' | 'tests' | 'docs' | 'full'
  const [serviceResult, setServiceResult] = useState(null);
  const [serviceType, setServiceType] = useState(null);

  useEffect(() => { setLocalAnalysis(analysis); }, [analysis]);

  const loadDetails = async () => {
    if (loaded) return;
    const [c, b] = await Promise.allSettled([
      fetchProjectCommits(project.name, 5),
      fetchProjectBranches(project.name),
    ]);
    if (c.status === 'fulfilled') setCommits(c.value);
    if (b.status === 'fulfilled') setBranches(b.value);
    setLoaded(true);
  };

  useEffect(() => {
    if (expanded && project.is_git) loadDetails();
  }, [expanded]);

  const handleReview = async (e) => {
    e.stopPropagation();
    setReviewing(true);
    try {
      const result = await reviewRepo(project.name);
      if (!result.error) { setReview(result); setLocalAnalysis(result); }
    } catch { /* ignore */ }
    setReviewing(false);
  };

  const handlePlatformAction = async (type, fn) => {
    setActiveAction(type);
    setServiceResult(null);
    setServiceType(null);
    try {
      const result = await fn(project.name);
      if (!result.error) { setServiceResult(result); setServiceType(type); }
      else { setServiceResult({ error: result.error }); setServiceType(type); }
    } catch (err) {
      setServiceResult({ error: err.message }); setServiceType(type);
    }
    setActiveAction(null);
  };

  const serviceIcons = { audit: <Shield size={8} />, tests: <TestTube2 size={8} />, docs: <BookOpen size={8} />, full: <Layers size={8} /> };
  const serviceTitles = { audit: 'Code Audit', tests: 'Generated Tests', docs: 'Documentation', full: 'Full Review' };

  return (
    <div className="card-hover p-3 animate-slide-up">
      <div className="flex items-center gap-2 cursor-pointer" onClick={onToggle}>
        {expanded ? <ChevronDown size={12} className="text-gray-500" /> : <ChevronRight size={12} className="text-gray-500" />}
        <FolderGit2 size={14} className="text-blue-400" />
        <span className="text-xs font-medium flex-1">{project.name}</span>
        <HealthBadge score={localAnalysis?.health_score} />
        {project.is_git && (
          <>
            <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[project.git_status]}`} />
            <span className="text-[10px] text-gray-500">{project.git_branch}</span>
          </>
        )}
        {project.uncommitted_changes > 0 && (
          <span className="text-[9px] bg-amber-500/20 text-amber-400 px-1.5 rounded-full">
            {project.uncommitted_changes} changes
          </span>
        )}
        {project.is_git && (
          <button onClick={handleReview} disabled={reviewing}
            className="text-[9px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors flex items-center gap-1">
            <Search size={8} className={reviewing ? 'animate-pulse' : ''} />
            {reviewing ? 'Reviewing...' : 'Review'}
          </button>
        )}
      </div>

      {/* Tech badges */}
      <div className="flex gap-1 mt-1.5 flex-wrap">
        {project.tech_stack.map((t) => <TechBadge key={t} tech={t} />)}
      </div>

      {project.last_commit_msg && (
        <div className="mt-1.5 text-[10px] text-gray-600 truncate">
          {project.last_commit_date} — {project.last_commit_msg}
        </div>
      )}

      {/* ── Platform Service Buttons ─────────────────────────────────── */}
      {project.is_git && (
        <div className="flex gap-1 mt-2 flex-wrap">
          {[
            { key: 'audit', icon: <Shield size={8} />, label: 'Audit', fn: auditProject },
            { key: 'tests', icon: <TestTube2 size={8} />, label: 'Tests', fn: generateProjectTests },
            { key: 'docs', icon: <BookOpen size={8} />, label: 'Docs', fn: generateProjectDocs },
            { key: 'full', icon: <Layers size={8} />, label: 'Full Review', fn: fullProjectReview },
          ].map(({ key, icon, label, fn }) => (
            <button key={key}
              onClick={(e) => { e.stopPropagation(); handlePlatformAction(key, fn); }}
              disabled={activeAction !== null}
              className={`text-[9px] px-2 py-0.5 rounded-full transition-colors flex items-center gap-1 ${
                activeAction === key
                  ? 'bg-purple-500/30 text-purple-300 animate-pulse'
                  : 'bg-white/5 text-gray-500 hover:bg-white/10 hover:text-gray-300'
              }`}>
              {icon}
              {activeAction === key ? `Running...` : label}
            </button>
          ))}
        </div>
      )}

      {/* ── Service Result Panel ──────────────────────────────────────── */}
      {serviceResult && serviceType && !serviceResult.error && (
        <ServiceResultPanel
          title={serviceTitles[serviceType]}
          icon={serviceIcons[serviceType]}
          result={serviceResult}
          onClose={() => { setServiceResult(null); setServiceType(null); }}
        />
      )}
      {serviceResult?.error && (
        <div className="mt-2 p-2 rounded bg-red-500/5 border border-red-500/10 text-[10px] text-red-400">
          {serviceResult.error}
          <button onClick={() => { setServiceResult(null); setServiceType(null); }}
            className="ml-2 text-gray-600 hover:text-gray-400">dismiss</button>
        </div>
      )}

      {/* ── Code Review panel ────────────────────────────────────────── */}
      {review && <CodeReviewPanel review={review} projectName={project.name} />}

      {/* ── Expanded details ─────────────────────────────────────────── */}
      {expanded && project.is_git && (
        <div className="mt-3 space-y-3 border-t border-white/5 pt-3">
          <div>
            <h5 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Recent Commits</h5>
            {commits.map((c, i) => (
              <div key={i} className="flex items-center gap-2 py-0.5">
                <GitCommit size={10} className="text-gray-600 flex-shrink-0" />
                <span className="text-[10px] text-gray-500 font-mono flex-shrink-0">{c.hash}</span>
                <span className="text-[10px] text-gray-400 truncate flex-1">{c.message}</span>
                <span className="text-[10px] text-gray-600 flex-shrink-0">{c.date}</span>
              </div>
            ))}
            {commits.length === 0 && <span className="text-[10px] text-gray-700">No commits</span>}
          </div>
          <div>
            <h5 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Branches</h5>
            <div className="flex flex-wrap gap-1">
              {branches.map((b, i) => (
                <span key={i} className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                  b.current ? 'bg-blue-500/20 text-blue-400' : 'bg-white/5 text-gray-500'
                }`}>
                  <GitBranch size={8} className="inline mr-0.5" />{b.name}
                </span>
              ))}
            </div>
          </div>
          {project.remote_url && (
            <div className="text-[10px] text-gray-600 flex items-center gap-1">
              <ExternalLink size={9} />
              <span className="truncate">{project.remote_url}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Main Projects View ──────────────────────────────────────────── */

export default function ProjectsView() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);
  const [filter, setFilter] = useState('all');
  const [analyses, setAnalyses] = useState({});
  const [analyzingAll, setAnalyzingAll] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchProjects();
      setProjects(data);
      const analysisMap = {};
      await Promise.allSettled(
        data.filter((p) => p.is_git).map(async (p) => {
          try {
            const a = await fetchLatestAnalysis(p.name);
            if (a && !a.error) analysisMap[p.name] = a;
          } catch { /* ignore */ }
        })
      );
      setAnalyses(analysisMap);
    } catch { /* ignore */ }
    setLoading(false);
  };

  const handleAnalyzeAll = async () => {
    setAnalyzingAll(true);
    const gitProjects = projects.filter((p) => p.is_git);
    const newAnalyses = { ...analyses };
    for (const p of gitProjects) {
      try {
        const result = await analyzeRepo(p.name, 'quick');
        if (!result.error) newAnalyses[p.name] = result;
      } catch { /* ignore */ }
    }
    setAnalyses(newAnalyses);
    setAnalyzingAll(false);
  };

  useEffect(() => { load(); }, []);

  const filtered = filter === 'all' ? projects
    : filter === 'git' ? projects.filter((p) => p.is_git)
    : filter === 'dirty' ? projects.filter((p) => p.uncommitted_changes > 0)
    : projects.filter((p) => { const a = analyses[p.name]; return a && a.health_score < 50; });

  const gitCount = projects.filter((p) => p.is_git).length;
  const dirtyCount = projects.filter((p) => p.uncommitted_changes > 0).length;
  const needsAttentionCount = projects.filter((p) => {
    const a = analyses[p.name]; return a && a.health_score < 50;
  }).length;

  return (
    <div className="space-y-3">
      {/* Platform Status Bar */}
      <PlatformStatus />

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FolderGit2 size={14} className="text-blue-400" />
          <span className="text-xs font-semibold text-gray-300">Dev Projects</span>
          <span className="text-[10px] text-gray-600 bg-white/5 px-1.5 rounded-full">{projects.length} total</span>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={handleAnalyzeAll} disabled={analyzingAll || loading}
            className="btn-ghost text-[10px] py-0.5 px-2">
            <Zap size={10} className={`inline mr-0.5 ${analyzingAll ? 'animate-pulse' : ''}`} />
            {analyzingAll ? 'Analyzing...' : 'Analyze All'}
          </button>
          <button onClick={load} className="btn-ghost text-xs py-1 px-2" disabled={loading}>
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      <div className="flex gap-1">
        {[
          ['all', `All (${projects.length})`],
          ['git', `Git (${gitCount})`],
          ['dirty', `Uncommitted (${dirtyCount})`],
          ['attention', `Needs Attention (${needsAttentionCount})`],
        ].map(([key, label]) => (
          <button key={key} onClick={() => setFilter(key)}
            className={`text-[10px] px-2 py-0.5 rounded-full transition-colors ${
              filter === key ? 'bg-white/10 text-white' : 'text-gray-500 hover:text-gray-300'
            }`}>{label}</button>
        ))}
      </div>

      <div className="space-y-1.5">
        {filtered.map((p) => (
          <ProjectCard key={p.name} project={p}
            expanded={expanded === p.name}
            onToggle={() => setExpanded(expanded === p.name ? null : p.name)}
            analysis={analyses[p.name]} />
        ))}
        {filtered.length === 0 && !loading && (
          <div className="text-[11px] text-gray-700 text-center py-6">No projects found</div>
        )}
      </div>
    </div>
  );
}
