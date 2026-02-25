import { useState, useRef, useEffect } from 'react';
import { Plus, Zap, X, Calendar, Tag } from 'lucide-react';
import { previewCapture, createTask } from '../api';

const PRIORITY_COLORS = {
  1: 'bg-red-500/20 text-red-400',
  2: 'bg-orange-500/20 text-orange-400',
  3: 'bg-yellow-500/20 text-yellow-400',
  4: 'bg-green-500/20 text-green-400',
  5: 'bg-gray-500/20 text-gray-400',
};

export default function QuickCapture({ onCreated }) {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState(null);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape' && preview) {
        setPreview(null);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [preview]);

  const handlePreview = async () => {
    if (!text.trim() || loading) return;
    setLoading(true);
    try {
      const parsed = await previewCapture(text.trim());
      setPreview(parsed);
    } catch { /* noop */ }
    setLoading(false);
  };

  const handleConfirm = async () => {
    if (!preview || saving) return;
    setSaving(true);
    try {
      const { _parsed_by, ...taskData } = preview;
      await createTask(taskData);
      setText('');
      setPreview(null);
      onCreated?.();
      inputRef.current?.focus();
    } catch { /* noop */ }
    setSaving(false);
  };

  const cyclePriority = () => {
    if (!preview) return;
    const next = (preview.priority % 5) + 1;
    setPreview({ ...preview, priority: next });
  };

  const removeTag = (tag) => {
    if (!preview) return;
    setPreview({ ...preview, tags: (preview.tags || []).filter((t) => t !== tag) });
  };

  const dismiss = () => {
    setPreview(null);
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Zap size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-amber-400/60" />
          <input
            ref={inputRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (preview ? handleConfirm() : handlePreview())}
            placeholder="Quick capture — type anything..."
            className="input w-full pl-9"
          />
        </div>
        <button
          onClick={preview ? handleConfirm : handlePreview}
          disabled={!text.trim() || loading || saving}
          className="btn-primary disabled:opacity-40"
        >
          <Plus size={16} />
        </button>
      </div>

      {/* Preview panel */}
      {preview && (
        <div className="card p-3 border-amber-500/10 animate-fade-in space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-gray-500 uppercase tracking-wider">Preview</span>
            <button onClick={dismiss} className="text-gray-600 hover:text-gray-400 transition-colors">
              <X size={12} />
            </button>
          </div>

          {/* Title */}
          <div className="text-sm font-medium">{preview.title || text}</div>

          {/* Badges row */}
          <div className="flex flex-wrap items-center gap-1.5">
            {/* Board */}
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-400">
              {preview.board_id}
            </span>

            {/* Priority — clickable */}
            <button
              onClick={cyclePriority}
              className={`text-[10px] font-bold px-1.5 py-0.5 rounded cursor-pointer transition-colors ${PRIORITY_COLORS[preview.priority] || PRIORITY_COLORS[3]}`}
              title="Click to cycle priority"
            >
              P{preview.priority}
            </button>

            {/* Due date */}
            {preview.due_date && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-400 flex items-center gap-0.5">
                <Calendar size={9} />
                {preview.due_date}
              </span>
            )}

            {/* Recurring */}
            {preview.recurring && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/15 text-cyan-400">
                {preview.recurring}
              </span>
            )}

            {/* Parsed by */}
            {preview._parsed_by && (
              <span className="text-[9px] px-1 py-0.5 rounded bg-white/5 text-gray-600 ml-auto">
                {preview._parsed_by}
              </span>
            )}
          </div>

          {/* Tags */}
          {preview.tags?.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {preview.tags.map((tag) => (
                <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-white/5 text-gray-400 flex items-center gap-0.5">
                  <Tag size={8} />
                  {tag}
                  <button onClick={() => removeTag(tag)} className="ml-0.5 text-gray-600 hover:text-red-400">
                    <X size={8} />
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* Confirm */}
          <button
            onClick={handleConfirm}
            disabled={saving}
            className="btn-primary w-full text-xs py-1.5 disabled:opacity-40"
          >
            {saving ? 'Adding...' : 'Add Task'}
          </button>
        </div>
      )}
    </div>
  );
}
