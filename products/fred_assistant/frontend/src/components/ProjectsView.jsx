import { useState, useEffect } from 'react';
import { GitBranch, GitCommit, FolderGit2, ExternalLink, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';
import { fetchProjects, fetchProjectCommits, fetchProjectBranches } from '../api';

const STATUS_DOT = { clean: 'bg-emerald-400', dirty: 'bg-amber-400' };

function TechBadge({ tech }) {
  const colors = {
    Python: 'bg-blue-500/20 text-blue-400',
    React: 'bg-cyan-500/20 text-cyan-400',
    'Node.js': 'bg-green-500/20 text-green-400',
    Docker: 'bg-blue-400/20 text-blue-300',
    TypeScript: 'bg-blue-600/20 text-blue-400',
    Vite: 'bg-purple-500/20 text-purple-400',
    Tailwind: 'bg-teal-500/20 text-teal-400',
    'Next.js': 'bg-white/10 text-gray-300',
  };
  return (
    <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${colors[tech] || 'bg-white/5 text-gray-500'}`}>
      {tech}
    </span>
  );
}

function ProjectCard({ project, expanded, onToggle }) {
  const [commits, setCommits] = useState([]);
  const [branches, setBranches] = useState([]);
  const [loaded, setLoaded] = useState(false);

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

  return (
    <div className="card-hover p-3 animate-slide-up">
      <div className="flex items-center gap-2 cursor-pointer" onClick={onToggle}>
        {expanded ? <ChevronDown size={12} className="text-gray-500" /> : <ChevronRight size={12} className="text-gray-500" />}
        <FolderGit2 size={14} className="text-blue-400" />
        <span className="text-xs font-medium flex-1">{project.name}</span>
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
      </div>

      <div className="flex gap-1 mt-1.5 flex-wrap">
        {project.tech_stack.map((t) => <TechBadge key={t} tech={t} />)}
      </div>

      {project.last_commit_msg && (
        <div className="mt-1.5 text-[10px] text-gray-600 truncate">
          {project.last_commit_date} — {project.last_commit_msg}
        </div>
      )}

      {expanded && project.is_git && (
        <div className="mt-3 space-y-3 border-t border-white/5 pt-3">
          {/* Recent Commits */}
          <div>
            <h5 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              Recent Commits
            </h5>
            {commits.map((c, i) => (
              <div key={i} className="flex items-center gap-2 py-0.5">
                <GitCommit size={10} className="text-gray-600 flex-shrink-0" />
                <span className="text-[10px] text-gray-500 font-mono flex-shrink-0">{c.hash}</span>
                <span className="text-[10px] text-gray-400 truncate flex-1">{c.message}</span>
                <span className="text-[10px] text-gray-600 flex-shrink-0">{c.date}</span>
              </div>
            ))}
            {commits.length === 0 && <span className="text-[10px] text-gray-700">No commits found</span>}
          </div>

          {/* Branches */}
          <div>
            <h5 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              Branches
            </h5>
            <div className="flex flex-wrap gap-1">
              {branches.map((b, i) => (
                <span key={i} className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                  b.current ? 'bg-blue-500/20 text-blue-400' : 'bg-white/5 text-gray-500'
                }`}>
                  <GitBranch size={8} className="inline mr-0.5" />
                  {b.name}
                </span>
              ))}
            </div>
          </div>

          {/* Remote */}
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

export default function ProjectsView() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);
  const [filter, setFilter] = useState('all');

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchProjects();
      setProjects(data);
    } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const filtered = filter === 'all'
    ? projects
    : filter === 'git'
      ? projects.filter((p) => p.is_git)
      : projects.filter((p) => p.uncommitted_changes > 0);

  const gitCount = projects.filter((p) => p.is_git).length;
  const dirtyCount = projects.filter((p) => p.uncommitted_changes > 0).length;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FolderGit2 size={14} className="text-blue-400" />
          <span className="text-xs font-semibold text-gray-300">Dev Projects</span>
          <span className="text-[10px] text-gray-600 bg-white/5 px-1.5 rounded-full">
            {projects.length} total
          </span>
        </div>
        <button onClick={load} className="btn-ghost text-xs py-1 px-2" disabled={loading}>
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-1">
        {[
          ['all', `All (${projects.length})`],
          ['git', `Git (${gitCount})`],
          ['dirty', `Uncommitted (${dirtyCount})`],
        ].map(([key, label]) => (
          <button key={key} onClick={() => setFilter(key)}
            className={`text-[10px] px-2 py-0.5 rounded-full transition-colors ${
              filter === key ? 'bg-white/10 text-white' : 'text-gray-500 hover:text-gray-300'
            }`}>{label}</button>
        ))}
      </div>

      {/* Project List */}
      <div className="space-y-1.5">
        {filtered.map((p) => (
          <ProjectCard
            key={p.name}
            project={p}
            expanded={expanded === p.name}
            onToggle={() => setExpanded(expanded === p.name ? null : p.name)}
          />
        ))}
        {filtered.length === 0 && !loading && (
          <div className="text-[11px] text-gray-700 text-center py-6">
            No projects found in ~/Development/Projects
          </div>
        )}
      </div>
    </div>
  );
}
