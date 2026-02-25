import { useState, useEffect } from 'react';
import {
  X, Sparkles, Plus, Pin, PinOff, Pencil, Trash2, Loader2,
  StickyNote, Check, XCircle,
} from 'lucide-react';
import {
  fetchProjectNotes, createProjectNote, generateProjectNotes,
  updateProjectNote, deleteProjectNote,
} from '../api';

function NoteBadge({ type }) {
  const style = type === 'ai_generated'
    ? 'bg-purple-500/20 text-purple-400'
    : 'bg-white/5 text-gray-500';
  return (
    <span className={`text-[8px] px-1.5 py-0.5 rounded-full flex items-center gap-0.5 ${style}`}>
      {type === 'ai_generated' && <Sparkles size={7} />}
      {type === 'ai_generated' ? 'AI' : 'manual'}
    </span>
  );
}

function TagPill({ tag }) {
  return (
    <span className="text-[8px] px-1 py-0.5 rounded bg-blue-500/10 text-blue-400">{tag}</span>
  );
}

export default function ProjectNotesPanel({ projectName, onClose }) {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [editContent, setEditContent] = useState('');
  const [newTitle, setNewTitle] = useState('');
  const [newContent, setNewContent] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchProjectNotes(projectName);
      setNotes(data);
    } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => { load(); }, [projectName]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const note = await generateProjectNotes(projectName);
      if (note) setNotes((prev) => [note, ...prev]);
    } catch { /* ignore */ }
    setGenerating(false);
  };

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    try {
      const note = await createProjectNote(projectName, {
        title: newTitle.trim(),
        content: newContent,
        note_type: 'manual',
      });
      if (note) setNotes((prev) => [note, ...prev]);
      setNewTitle('');
      setNewContent('');
      setAdding(false);
    } catch { /* ignore */ }
  };

  const handlePin = async (note) => {
    try {
      const updated = await updateProjectNote(projectName, note.id, { pinned: !note.pinned });
      if (updated) {
        setNotes((prev) => prev.map((n) => (n.id === note.id ? updated : n))
          .sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0)));
      }
    } catch { /* ignore */ }
  };

  const startEdit = (note) => {
    setEditingId(note.id);
    setEditTitle(note.title);
    setEditContent(note.content);
  };

  const handleSaveEdit = async () => {
    if (!editTitle.trim()) return;
    try {
      const updated = await updateProjectNote(projectName, editingId, {
        title: editTitle.trim(),
        content: editContent,
      });
      if (updated) setNotes((prev) => prev.map((n) => (n.id === editingId ? updated : n)));
      setEditingId(null);
    } catch { /* ignore */ }
  };

  const handleDelete = async (noteId) => {
    try {
      await deleteProjectNote(projectName, noteId);
      setNotes((prev) => prev.filter((n) => n.id !== noteId));
    } catch { /* ignore */ }
  };

  return (
    <div className="mt-2 border border-white/5 rounded bg-white/[0.02] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-2 py-1.5 border-b border-white/5">
        <div className="flex items-center gap-1.5">
          <StickyNote size={10} className="text-amber-400" />
          <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
            Notes ({notes.length})
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={handleGenerate} disabled={generating}
            className="text-[9px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 disabled:opacity-40 flex items-center gap-1">
            {generating ? <Loader2 size={8} className="animate-spin" /> : <Sparkles size={8} />}
            {generating ? 'Generating...' : 'Generate Notes'}
          </button>
          <button onClick={() => { setAdding(!adding); setEditingId(null); }}
            className="text-[9px] px-2 py-0.5 rounded-full bg-white/5 text-gray-400 hover:bg-white/10 flex items-center gap-1">
            <Plus size={8} /> Add
          </button>
          <button onClick={onClose} className="text-gray-600 hover:text-gray-400 ml-1">
            <X size={10} />
          </button>
        </div>
      </div>

      {/* Add note form */}
      {adding && (
        <div className="p-2 border-b border-white/5 space-y-1.5">
          <input value={newTitle} onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Note title..."
            className="input w-full text-[10px] py-1" />
          <textarea value={newContent} onChange={(e) => setNewContent(e.target.value)}
            placeholder="Content (optional)..."
            rows={3}
            className="input w-full text-[10px] py-1 resize-none" />
          <div className="flex gap-1">
            <button onClick={handleCreate} disabled={!newTitle.trim()}
              className="text-[9px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 disabled:opacity-40 flex items-center gap-1">
              <Check size={8} /> Save
            </button>
            <button onClick={() => { setAdding(false); setNewTitle(''); setNewContent(''); }}
              className="text-[9px] px-2 py-0.5 rounded-full bg-white/5 text-gray-500 hover:bg-white/10 flex items-center gap-1">
              <XCircle size={8} /> Cancel
            </button>
          </div>
        </div>
      )}

      {/* Notes list */}
      <div className="max-h-80 overflow-y-auto">
        {loading && (
          <div className="text-[10px] text-gray-600 text-center py-4 flex items-center justify-center gap-1.5">
            <Loader2 size={10} className="animate-spin" /> Loading notes...
          </div>
        )}
        {!loading && notes.length === 0 && (
          <div className="text-[10px] text-gray-700 text-center py-4">
            No notes yet. Click "Generate Notes" for AI analysis or "Add" for a manual note.
          </div>
        )}
        {notes.map((note) => (
          <div key={note.id} className={`px-2 py-2 border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors ${
            note.pinned ? 'bg-amber-500/[0.03]' : ''
          }`}>
            {editingId === note.id ? (
              /* Edit form */
              <div className="space-y-1.5">
                <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)}
                  className="input w-full text-[10px] py-1" />
                <textarea value={editContent} onChange={(e) => setEditContent(e.target.value)}
                  rows={4}
                  className="input w-full text-[10px] py-1 resize-none" />
                <div className="flex gap-1">
                  <button onClick={handleSaveEdit}
                    className="text-[9px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 flex items-center gap-1">
                    <Check size={8} /> Save
                  </button>
                  <button onClick={() => setEditingId(null)}
                    className="text-[9px] px-2 py-0.5 rounded-full bg-white/5 text-gray-500 hover:bg-white/10 flex items-center gap-1">
                    <XCircle size={8} /> Cancel
                  </button>
                </div>
              </div>
            ) : (
              /* Display note */
              <>
                <div className="flex items-center gap-1.5 mb-1">
                  {note.pinned && <Pin size={8} className="text-amber-400 flex-shrink-0" />}
                  <span className="text-[11px] font-medium text-gray-300 flex-1 truncate">{note.title}</span>
                  <NoteBadge type={note.note_type} />
                  <div className="flex items-center gap-0.5 flex-shrink-0">
                    <button onClick={() => handlePin(note)} title={note.pinned ? 'Unpin' : 'Pin'}
                      className="p-0.5 text-gray-600 hover:text-amber-400 transition-colors">
                      {note.pinned ? <PinOff size={8} /> : <Pin size={8} />}
                    </button>
                    <button onClick={() => startEdit(note)} title="Edit"
                      className="p-0.5 text-gray-600 hover:text-blue-400 transition-colors">
                      <Pencil size={8} />
                    </button>
                    <button onClick={() => handleDelete(note.id)} title="Delete"
                      className="p-0.5 text-gray-600 hover:text-red-400 transition-colors">
                      <Trash2 size={8} />
                    </button>
                  </div>
                </div>
                {note.content && (
                  <div className="text-[10px] text-gray-400 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto bg-black/20 rounded p-1.5 mb-1">
                    {note.content}
                  </div>
                )}
                <div className="flex items-center gap-1.5">
                  <span className="text-[8px] text-gray-600">
                    {note.updated_at?.slice(0, 16).replace('T', ' ')}
                  </span>
                  {note.tags?.map((tag) => <TagPill key={tag} tag={tag} />)}
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
