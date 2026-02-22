import { useState, useEffect } from 'react';
import { Brain, Plus, Trash2, Search } from 'lucide-react';
import { fetchMemories, addMemory, deleteMemory, searchMemories } from '../api';

export default function MemoryPanel() {
  const [memories, setMemories] = useState([]);
  const [search, setSearch] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ category: 'preferences', key: '', value: '' });

  const load = async () => {
    const data = search.trim()
      ? await searchMemories(search.trim())
      : await fetchMemories();
    setMemories(data);
  };

  useEffect(() => { load(); }, [search]);

  const handleAdd = async () => {
    if (!form.key.trim() || !form.value.trim()) return;
    await addMemory({ category: form.category, key: form.key.trim(), value: form.value.trim(), importance: 5 });
    setForm({ category: 'preferences', key: '', value: '' });
    setShowAdd(false);
    load();
  };

  const handleDelete = async (id) => {
    setMemories((prev) => prev.filter((m) => m.id !== id));
    await deleteMemory(id);
  };

  const grouped = memories.reduce((acc, m) => {
    (acc[m.category] = acc[m.category] || []).push(m);
    return acc;
  }, {});

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain size={14} className="text-purple-400" />
          <span className="text-xs font-semibold text-gray-300">Fred's Memory</span>
        </div>
        <button onClick={() => setShowAdd(!showAdd)} className="btn-ghost text-xs py-1 px-2">
          <Plus size={12} />
        </button>
      </div>

      <div className="relative">
        <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-600" />
        <input value={search} onChange={(e) => setSearch(e.target.value)}
          placeholder="Search memories..." className="input w-full text-xs pl-8" />
      </div>

      {showAdd && (
        <div className="card p-3 space-y-2">
          <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}
            className="input w-full text-xs">
            {['preferences', 'personal', 'work', 'health', 'contacts', 'projects', 'goals'].map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <input value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })}
            placeholder="Key (e.g. 'favorite coffee')" className="input w-full text-xs" />
          <input value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })}
            placeholder="Value (e.g. 'oat milk latte')" className="input w-full text-xs"
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()} />
          <button onClick={handleAdd} className="btn-primary text-xs w-full">Remember</button>
        </div>
      )}

      <div className="space-y-3 overflow-y-auto">
        {Object.entries(grouped).map(([cat, mems]) => (
          <div key={cat}>
            <h5 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">{cat}</h5>
            {mems.map((m) => (
              <div key={m.id} className="flex items-start justify-between py-1 group">
                <div className="min-w-0">
                  <span className="text-[11px] text-gray-400 font-medium">{m.key}: </span>
                  <span className="text-[11px] text-gray-500">{m.value}</span>
                </div>
                <button onClick={() => handleDelete(m.id)}
                  className="opacity-0 group-hover:opacity-100 p-0.5 text-gray-700 hover:text-red-400 flex-shrink-0">
                  <Trash2 size={10} />
                </button>
              </div>
            ))}
          </div>
        ))}
        {memories.length === 0 && (
          <div className="text-[11px] text-gray-700 text-center py-4">
            No memories yet. Tell Fred to remember things!
          </div>
        )}
      </div>
    </div>
  );
}
