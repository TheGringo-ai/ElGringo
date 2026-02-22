import { Check, X, FileText } from 'lucide-react';

const STATUS_BADGE = {
  draft: 'bg-yellow-500/20 text-yellow-400',
  approved: 'bg-green-500/20 text-green-400',
  rejected: 'bg-red-500/20 text-red-400',
  pending: 'bg-blue-500/20 text-blue-400',
};

export default function ContentItem({ item, onApprove, onReject }) {
  const badgeClass = STATUS_BADGE[item.status] || STATUS_BADGE.draft;
  const preview = item.data?.content || item.data?.text || item.data?.title || '';

  return (
    <div className="p-3 rounded-lg bg-white/[0.03] border border-white/5 hover:bg-white/[0.06] transition-colors animate-slide-up">
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-2 min-w-0">
          <FileText size={12} className="text-purple-400 flex-shrink-0" />
          <span className="text-xs font-medium truncate">
            {item.type?.replace('_', ' ') || 'Content'}
          </span>
        </div>
        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${badgeClass}`}>
          {item.status}
        </span>
      </div>

      {preview && (
        <p className="text-xs text-gray-500 line-clamp-3 mb-2 leading-relaxed">{preview}</p>
      )}

      {item.status === 'draft' && (
        <div className="flex gap-2">
          <button
            onClick={() => onApprove(item.id)}
            className="flex items-center gap-1 text-[11px] px-2 py-1 rounded bg-green-500/10 text-green-400 hover:bg-green-500/20 transition-colors"
          >
            <Check size={10} /> Approve
          </button>
          <button
            onClick={() => onReject(item.id)}
            className="flex items-center gap-1 text-[11px] px-2 py-1 rounded bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
          >
            <X size={10} /> Reject
          </button>
        </div>
      )}

      <div className="text-[10px] text-gray-700 mt-1.5">
        {item.created_at && new Date(item.created_at).toLocaleDateString()}
      </div>
    </div>
  );
}
