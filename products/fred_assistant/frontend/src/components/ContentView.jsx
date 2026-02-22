import { useState, useEffect } from 'react';
import { FileText, Plus, Trash2, Send, Sparkles, Clock, CheckCircle2, XCircle, Filter } from 'lucide-react';
import {
  fetchContent, createContent, generateContent, updateContent,
  publishContent, deleteContent, fetchSocialAccounts, updateSocialAccount,
} from '../api';

const PLATFORMS = ['linkedin', 'twitter', 'blog', 'newsletter', 'youtube'];
const TYPES = ['post', 'article', 'thread', 'newsletter', 'video_script'];
const STATUS_COLORS = {
  draft: 'bg-gray-500/20 text-gray-400',
  scheduled: 'bg-amber-500/20 text-amber-400',
  published: 'bg-emerald-500/20 text-emerald-400',
  rejected: 'bg-red-500/20 text-red-400',
};
const PLATFORM_ICONS = {
  linkedin: '💼', twitter: '🐦', blog: '📝', newsletter: '📧', youtube: '🎬',
};

function ContentCard({ item, onPublish, onDelete, onEdit }) {
  return (
    <div className="card-hover p-3 animate-slide-up">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <span>{PLATFORM_ICONS[item.platform] || '📄'}</span>
          <span className="text-xs font-medium">{item.title}</span>
        </div>
        <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${STATUS_COLORS[item.status] || STATUS_COLORS.draft}`}>
          {item.status}
        </span>
      </div>

      {item.body && (
        <div className="text-[11px] text-gray-500 mt-1.5 line-clamp-3 whitespace-pre-wrap">
          {item.body.slice(0, 200)}{item.body.length > 200 ? '...' : ''}
        </div>
      )}

      <div className="flex items-center justify-between mt-2">
        <div className="flex items-center gap-2 text-[10px] text-gray-600">
          <span>{item.content_type}</span>
          {item.scheduled_date && <span className="flex items-center gap-0.5"><Clock size={8} />{item.scheduled_date}</span>}
          {item.ai_generated && <span className="flex items-center gap-0.5"><Sparkles size={8} className="text-purple-400" />AI</span>}
        </div>
        <div className="flex items-center gap-1">
          {item.status === 'draft' && (
            <button onClick={() => onPublish(item.id)} className="text-[10px] text-emerald-400 hover:text-emerald-300 px-1">
              <Send size={10} />
            </button>
          )}
          <button onClick={() => onDelete(item.id)} className="text-[10px] text-gray-600 hover:text-red-400 px-1">
            <Trash2 size={10} />
          </button>
        </div>
      </div>
    </div>
  );
}

function SocialAccounts({ accounts, onUpdate }) {
  return (
    <div className="card p-3">
      <h5 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Connected Platforms</h5>
      <div className="space-y-1.5">
        {accounts.map((a) => (
          <div key={a.id} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span>{PLATFORM_ICONS[a.platform] || '📱'}</span>
              <span className="text-[11px] text-gray-400">{a.display_name || a.platform}</span>
              {a.handle && <span className="text-[10px] text-gray-600">@{a.handle}</span>}
            </div>
            <button
              onClick={() => onUpdate(a.id, { connected: !a.connected })}
              className={`text-[10px] px-2 py-0.5 rounded-full ${
                a.connected ? 'bg-emerald-500/20 text-emerald-400' : 'bg-white/5 text-gray-600'
              }`}
            >
              {a.connected ? 'Connected' : 'Connect'}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ContentView() {
  const [content, setContent] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [filter, setFilter] = useState('all');
  const [showCreate, setShowCreate] = useState(false);
  const [showGenerate, setShowGenerate] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [form, setForm] = useState({ title: '', body: '', content_type: 'post', platform: 'linkedin', scheduled_date: '' });
  const [genForm, setGenForm] = useState({ topic: '', content_type: 'post', platform: 'linkedin', tone: 'professional', length: 'medium' });

  const load = async () => {
    const [c, a] = await Promise.allSettled([fetchContent(), fetchSocialAccounts()]);
    if (c.status === 'fulfilled') setContent(c.value);
    if (a.status === 'fulfilled') setAccounts(a.value);
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!form.title.trim()) return;
    await createContent(form);
    setForm({ title: '', body: '', content_type: 'post', platform: 'linkedin', scheduled_date: '' });
    setShowCreate(false);
    load();
  };

  const handleGenerate = async () => {
    if (!genForm.topic.trim()) return;
    setGenerating(true);
    try {
      await generateContent(genForm);
      setGenForm({ ...genForm, topic: '' });
      setShowGenerate(false);
      load();
    } finally {
      setGenerating(false);
    }
  };

  const handlePublish = async (id) => {
    setContent((prev) => prev.map((c) => c.id === id ? { ...c, status: 'published' } : c));
    await publishContent(id);
  };

  const handleDelete = async (id) => {
    setContent((prev) => prev.filter((c) => c.id !== id));
    await deleteContent(id);
  };

  const handleAccountUpdate = async (id, data) => {
    await updateSocialAccount(id, data);
    load();
  };

  const filtered = filter === 'all' ? content : content.filter((c) => c.status === filter);

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText size={14} className="text-purple-400" />
          <span className="text-xs font-semibold text-gray-300">Content Hub</span>
          <span className="text-[10px] text-gray-600 bg-white/5 px-1.5 rounded-full">{content.length}</span>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={() => { setShowGenerate(!showGenerate); setShowCreate(false); }}
            className="btn-ghost text-xs py-1 px-2 flex items-center gap-1">
            <Sparkles size={11} className="text-purple-400" /> Generate
          </button>
          <button onClick={() => { setShowCreate(!showCreate); setShowGenerate(false); }}
            className="btn-ghost text-xs py-1 px-2"><Plus size={12} /></button>
        </div>
      </div>

      {/* Social Accounts */}
      <SocialAccounts accounts={accounts} onUpdate={handleAccountUpdate} />

      {/* Filters */}
      <div className="flex gap-1">
        {['all', 'draft', 'scheduled', 'published'].map((s) => (
          <button key={s} onClick={() => setFilter(s)}
            className={`text-[10px] px-2 py-0.5 rounded-full ${
              filter === s ? 'bg-white/10 text-white' : 'text-gray-500 hover:text-gray-300'
            }`}>{s} ({s === 'all' ? content.length : content.filter((c) => c.status === s).length})</button>
        ))}
      </div>

      {/* AI Generate Form */}
      {showGenerate && (
        <div className="card p-3 space-y-2 border-purple-500/20">
          <div className="flex items-center gap-1 mb-1">
            <Sparkles size={11} className="text-purple-400" />
            <span className="text-[11px] font-semibold text-purple-300">AI Content Generator</span>
          </div>
          <input value={genForm.topic} onChange={(e) => setGenForm({ ...genForm, topic: e.target.value })}
            placeholder="Topic or idea..." className="input w-full text-xs"
            onKeyDown={(e) => e.key === 'Enter' && handleGenerate()} />
          <div className="grid grid-cols-2 gap-2">
            <select value={genForm.platform} onChange={(e) => setGenForm({ ...genForm, platform: e.target.value })} className="input text-xs">
              {PLATFORMS.map((p) => <option key={p} value={p}>{PLATFORM_ICONS[p]} {p}</option>)}
            </select>
            <select value={genForm.content_type} onChange={(e) => setGenForm({ ...genForm, content_type: e.target.value })} className="input text-xs">
              {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            <select value={genForm.tone} onChange={(e) => setGenForm({ ...genForm, tone: e.target.value })} className="input text-xs">
              {['professional', 'casual', 'technical', 'inspirational', 'educational'].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <select value={genForm.length} onChange={(e) => setGenForm({ ...genForm, length: e.target.value })} className="input text-xs">
              {['short', 'medium', 'long'].map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>
          <button onClick={handleGenerate} disabled={generating || !genForm.topic.trim()}
            className="btn-primary text-xs w-full disabled:opacity-40">
            {generating ? 'Generating...' : 'Generate with AI'}
          </button>
        </div>
      )}

      {/* Manual Create Form */}
      {showCreate && (
        <div className="card p-3 space-y-2">
          <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="Content title..." className="input w-full text-xs" />
          <textarea value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })}
            placeholder="Write your content..." className="input w-full text-xs h-24 resize-none" />
          <div className="grid grid-cols-3 gap-2">
            <select value={form.platform} onChange={(e) => setForm({ ...form, platform: e.target.value })} className="input text-xs">
              {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
            <select value={form.content_type} onChange={(e) => setForm({ ...form, content_type: e.target.value })} className="input text-xs">
              {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            <input type="date" value={form.scheduled_date} onChange={(e) => setForm({ ...form, scheduled_date: e.target.value })}
              className="input text-xs" />
          </div>
          <button onClick={handleCreate} className="btn-primary text-xs w-full">Create Draft</button>
        </div>
      )}

      {/* Content List */}
      <div className="space-y-1.5">
        {filtered.map((item) => (
          <ContentCard key={item.id} item={item} onPublish={handlePublish} onDelete={handleDelete} />
        ))}
        {filtered.length === 0 && (
          <div className="text-[11px] text-gray-700 text-center py-6">
            No content yet. Create or generate some!
          </div>
        )}
      </div>
    </div>
  );
}
