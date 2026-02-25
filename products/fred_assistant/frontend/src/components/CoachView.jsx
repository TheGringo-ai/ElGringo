import { useState, useEffect } from 'react';
import { Target, Plus, Trash2, TrendingUp, Trophy, AlertTriangle, Lightbulb, RefreshCw } from 'lucide-react';
import {
  fetchGoals, createGoal, updateGoal, deleteGoal,
  fetchCurrentReview, generateReview,
} from '../api';

const CATEGORY_COLORS = {
  business: 'bg-blue-500/20 text-blue-400',
  personal: 'bg-emerald-500/20 text-emerald-400',
  health: 'bg-red-500/20 text-red-400',
  financial: 'bg-amber-500/20 text-amber-400',
  learning: 'bg-purple-500/20 text-purple-400',
};

function ProgressBar({ value }) {
  return (
    <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
      <div className="h-full bg-blue-500 rounded-full transition-all" style={{ width: `${value}%` }} />
    </div>
  );
}

function GoalCard({ goal, onUpdate, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [progress, setProgress] = useState(goal.progress);

  const handleProgress = async (val) => {
    setProgress(val);
    await onUpdate(goal.id, { progress: val, status: val >= 100 ? 'completed' : 'active' });
  };

  return (
    <div className="card-hover p-3 animate-slide-up">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <div className="flex items-center gap-1.5">
            <Target size={12} className="text-blue-400" />
            <span className={`text-xs font-medium ${goal.status === 'completed' ? 'line-through text-gray-600' : ''}`}>
              {goal.title}
            </span>
          </div>
          {goal.description && (
            <p className="text-[10px] text-gray-500 mt-1">{goal.description}</p>
          )}
        </div>
        <div className="flex items-center gap-1">
          <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${CATEGORY_COLORS[goal.category] || CATEGORY_COLORS.business}`}>
            {goal.category}
          </span>
          <button onClick={() => onDelete(goal.id)}
            className="opacity-0 group-hover:opacity-100 p-0.5 text-gray-600 hover:text-red-400">
            <Trash2 size={10} />
          </button>
        </div>
      </div>

      <div className="mt-2">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] text-gray-500">{goal.progress}%</span>
          {goal.target_date && (
            <span className="text-[10px] text-gray-600">Target: {goal.target_date}</span>
          )}
        </div>
        <ProgressBar value={goal.progress} />
      </div>

      {/* Quick progress buttons */}
      <div className="flex gap-1 mt-2">
        {[0, 25, 50, 75, 100].map((v) => (
          <button key={v} onClick={() => handleProgress(v)}
            className={`text-[9px] px-1.5 py-0.5 rounded ${
              goal.progress === v ? 'bg-blue-500/20 text-blue-400' : 'bg-white/5 text-gray-600 hover:text-gray-300'
            }`}>{v}%</button>
        ))}
      </div>

      {/* Milestones */}
      {goal.milestones?.length > 0 && (
        <div className="mt-2 space-y-0.5">
          {goal.milestones.map((m, i) => (
            <div key={i} className="flex items-center gap-1.5 text-[10px]">
              <span className={m.done ? 'text-emerald-400' : 'text-gray-600'}>
                {m.done ? '✓' : '○'}
              </span>
              <span className={m.done ? 'text-gray-500 line-through' : 'text-gray-400'}>
                {m.text || m.title || m}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function WeeklyReview({ review, onGenerate, generating }) {
  if (!review || !review.week_start) {
    return (
      <div className="card p-3 text-center">
        <p className="text-[11px] text-gray-600 mb-2">No weekly review yet</p>
        <button onClick={onGenerate} disabled={generating} className="btn-primary text-xs">
          {generating ? 'Generating...' : 'Generate Review'}
        </button>
      </div>
    );
  }

  return (
    <div className="card p-3 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
          Week of {review.week_start}
        </span>
        <button onClick={onGenerate} disabled={generating} className="btn-ghost py-0.5 px-1.5">
          <RefreshCw size={10} className={generating ? 'animate-spin' : ''} />
        </button>
      </div>

      {review.wins?.length > 0 && (
        <div>
          <div className="flex items-center gap-1 mb-1">
            <Trophy size={10} className="text-amber-400" />
            <span className="text-[10px] font-semibold text-amber-400">Wins</span>
          </div>
          {review.wins.map((w, i) => (
            <p key={i} className="text-[10px] text-gray-400 pl-4">• {w}</p>
          ))}
        </div>
      )}

      {review.challenges?.length > 0 && (
        <div>
          <div className="flex items-center gap-1 mb-1">
            <AlertTriangle size={10} className="text-red-400" />
            <span className="text-[10px] font-semibold text-red-400">Challenges</span>
          </div>
          {review.challenges.map((c, i) => (
            <p key={i} className="text-[10px] text-gray-400 pl-4">• {c}</p>
          ))}
        </div>
      )}

      {review.lessons?.length > 0 && (
        <div>
          <div className="flex items-center gap-1 mb-1">
            <Lightbulb size={10} className="text-purple-400" />
            <span className="text-[10px] font-semibold text-purple-400">Lessons</span>
          </div>
          {review.lessons.map((l, i) => (
            <p key={i} className="text-[10px] text-gray-400 pl-4">• {l}</p>
          ))}
        </div>
      )}

      {review.next_week_priorities?.length > 0 && (
        <div>
          <div className="flex items-center gap-1 mb-1">
            <Target size={10} className="text-blue-400" />
            <span className="text-[10px] font-semibold text-blue-400">Next Week</span>
          </div>
          {review.next_week_priorities.map((p, i) => (
            <p key={i} className="text-[10px] text-gray-400 pl-4">• {p}</p>
          ))}
        </div>
      )}

      {review.ai_insights && (
        <div className="text-[10px] text-gray-500 italic border-t border-white/5 pt-2">
          {review.ai_insights}
        </div>
      )}
    </div>
  );
}

export default function CoachView() {
  const [goals, setGoals] = useState([]);
  const [review, setReview] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [filter, setFilter] = useState('active');
  const [form, setForm] = useState({
    title: '', description: '', category: 'business', target_date: '',
  });

  const load = async () => {
    const [g, r] = await Promise.allSettled([fetchGoals(), fetchCurrentReview()]);
    if (g.status === 'fulfilled') setGoals(g.value);
    if (r.status === 'fulfilled') setReview(r.value);
  };

  useEffect(() => { load(); }, []);

  const handleAdd = async () => {
    if (!form.title.trim()) return;
    await createGoal(form);
    setForm({ title: '', description: '', category: 'business', target_date: '' });
    setShowAdd(false);
    load();
  };

  const handleUpdate = async (id, data) => {
    await updateGoal(id, data);
    load();
  };

  const handleDelete = async (id) => {
    setGoals((prev) => prev.filter((g) => g.id !== id));
    await deleteGoal(id);
  };

  const handleGenerateReview = async () => {
    setGenerating(true);
    try {
      const r = await generateReview();
      setReview(r);
    } finally {
      setGenerating(false);
    }
  };

  const filtered = filter === 'all' ? goals : goals.filter((g) => g.status === filter);
  const activeCount = goals.filter((g) => g.status === 'active').length;
  const completedCount = goals.filter((g) => g.status === 'completed').length;
  const avgProgress = goals.length ? Math.round(goals.reduce((sum, g) => sum + g.progress, 0) / goals.length) : 0;

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp size={14} className="text-amber-400" />
          <span className="text-xs font-semibold text-gray-300">Business Coach</span>
        </div>
        <button onClick={() => setShowAdd(!showAdd)} className="btn-ghost text-xs py-1 px-2">
          <Plus size={12} />
        </button>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-2">
        {[
          ['Active Goals', activeCount, 'text-blue-400'],
          ['Completed', completedCount, 'text-emerald-400'],
          ['Avg Progress', `${avgProgress}%`, 'text-amber-400'],
        ].map(([label, value, color]) => (
          <div key={label} className="card p-2 text-center">
            <div className={`text-sm font-bold ${color}`}>{value}</div>
            <div className="text-[9px] text-gray-600">{label}</div>
          </div>
        ))}
      </div>

      {/* Add Goal Form */}
      {showAdd && (
        <div className="card p-3 space-y-2">
          <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="Goal title..." className="input w-full text-xs"
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()} />
          <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="Description (optional)" className="input w-full text-xs" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="input text-xs">
              {Object.keys(CATEGORY_COLORS).map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <input type="date" value={form.target_date} onChange={(e) => setForm({ ...form, target_date: e.target.value })}
              className="input text-xs" />
          </div>
          <button onClick={handleAdd} className="btn-primary text-xs w-full">Set Goal</button>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-1">
        {['active', 'completed', 'all'].map((s) => (
          <button key={s} onClick={() => setFilter(s)}
            className={`text-[10px] px-2 py-0.5 rounded-full ${
              filter === s ? 'bg-white/10 text-white' : 'text-gray-500 hover:text-gray-300'
            }`}>{s}</button>
        ))}
      </div>

      {/* Goals */}
      <div className="space-y-1.5">
        {filtered.map((g) => (
          <GoalCard key={g.id} goal={g} onUpdate={handleUpdate} onDelete={handleDelete} />
        ))}
        {filtered.length === 0 && (
          <div className="text-[11px] text-gray-700 text-center py-4">
            No goals yet. Set your first goal!
          </div>
        )}
      </div>

      {/* Weekly Review */}
      <div>
        <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Weekly Review</h4>
        <WeeklyReview review={review} onGenerate={handleGenerateReview} generating={generating} />
      </div>
    </div>
  );
}
