import { useState } from 'react';
import { Plus, Loader2 } from 'lucide-react';
import { generateContent, pollJob, approveContent, rejectContent } from '../api/content';
import { CONTENT_TYPES } from '../config';
import usePolling from '../hooks/usePolling';
import ContentItem from './ContentItem';

const FILTER_TABS = ['all', 'draft', 'approved', 'rejected'];

export default function ContentQueue({ content, onRefresh }) {
  const [filter, setFilter] = useState('all');
  const [generating, setGenerating] = useState(false);
  const [genType, setGenType] = useState('linkedin_post');
  const [genTopic, setGenTopic] = useState('');
  const [jobId, setJobId] = useState(null);
  const [showForm, setShowForm] = useState(false);

  const filtered = filter === 'all' ? content : content.filter((c) => c.status === filter);

  // Poll active job
  usePolling(
    async () => {
      if (!jobId) return;
      try {
        const job = await pollJob(jobId);
        if (job.status === 'completed' || job.status === 'failed') {
          setJobId(null);
          setGenerating(false);
          onRefresh();
        }
      } catch {
        setJobId(null);
        setGenerating(false);
      }
    },
    3000,
    !!jobId
  );

  const handleGenerate = async () => {
    if (!genTopic.trim()) return;
    setGenerating(true);
    try {
      const job = await generateContent(genType, { topic: genTopic.trim() });
      setJobId(job.job_id);
      setGenTopic('');
      setShowForm(false);
    } catch {
      setGenerating(false);
    }
  };

  const handleApprove = async (id) => {
    await approveContent(id);
    onRefresh();
  };

  const handleReject = async (id) => {
    await rejectContent(id);
    onRefresh();
  };

  return (
    <div className="glass h-full flex flex-col p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-300">Content Queue</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1 text-[11px] px-2 py-1 rounded bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 transition-colors"
        >
          {generating ? <Loader2 size={10} className="animate-spin" /> : <Plus size={10} />}
          Generate
        </button>
      </div>

      {/* Generate form */}
      {showForm && (
        <div className="mb-3 p-3 rounded-lg bg-white/[0.03] border border-white/5 space-y-2">
          <select
            value={genType}
            onChange={(e) => setGenType(e.target.value)}
            className="w-full text-xs bg-white/5 border border-white/10 rounded px-2 py-1.5 text-gray-300 focus:outline-none focus:border-purple-500/50"
          >
            {CONTENT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          <input
            type="text"
            value={genTopic}
            onChange={(e) => setGenTopic(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
            placeholder="Topic or description..."
            className="w-full text-xs bg-white/5 border border-white/10 rounded px-2 py-1.5 text-gray-300 placeholder-gray-600 focus:outline-none focus:border-purple-500/50"
          />
          <button
            onClick={handleGenerate}
            disabled={generating || !genTopic.trim()}
            className="w-full text-xs py-1.5 rounded bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {generating ? 'Generating...' : 'Create'}
          </button>
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex gap-1 mb-3">
        {FILTER_TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setFilter(tab)}
            className={`text-[11px] px-2 py-1 rounded transition-colors capitalize ${
              filter === tab
                ? 'bg-white/10 text-white'
                : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Content list */}
      <div className="flex-1 overflow-y-auto space-y-2">
        {filtered.map((item) => (
          <ContentItem
            key={item.id}
            item={item}
            onApprove={handleApprove}
            onReject={handleReject}
          />
        ))}
        {filtered.length === 0 && (
          <div className="text-xs text-gray-700 text-center py-6">No content items</div>
        )}
      </div>
    </div>
  );
}
