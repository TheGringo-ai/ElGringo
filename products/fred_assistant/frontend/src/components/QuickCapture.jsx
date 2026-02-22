import { useState } from 'react';
import { Plus, Zap } from 'lucide-react';
import { quickCapture } from '../api';

export default function QuickCapture({ onCreated }) {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!text.trim() || loading) return;
    setLoading(true);
    try {
      await quickCapture(text.trim());
      setText('');
      onCreated?.();
    } catch { /* noop */ }
    setLoading(false);
  };

  return (
    <div className="flex gap-2">
      <div className="relative flex-1">
        <Zap size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-amber-400/60" />
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          placeholder="Quick capture — type anything..."
          className="input w-full pl-9"
        />
      </div>
      <button onClick={handleSubmit} disabled={!text.trim() || loading} className="btn-primary disabled:opacity-40">
        <Plus size={16} />
      </button>
    </div>
  );
}
