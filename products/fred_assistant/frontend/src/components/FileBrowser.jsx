import { useState, useEffect, useCallback } from 'react';
import {
  FolderOpen, File, Folder, Trash2, Download, Save, X,
  FilePlus, FolderPlus, CornerUpLeft, ChevronRight,
  FileCode, Loader2,
} from 'lucide-react';

/**
 * Reusable file browser component.
 *
 * Props:
 *   fetchFiles(path) → { entries, path }
 *   readFile(path) → { content, binary, size, ext, path }
 *   writeFile(path, content) → {}
 *   createFile(path, content) → {}
 *   deleteFile(path) → {}
 *   renameFile(oldPath, newPath) → {}
 *   exportUrl → string (download URL) or null
 */
export default function FileBrowser({ fetchFiles, readFile, writeFile, createFile, deleteFile, renameFile, exportUrl }) {
  const [currentPath, setCurrentPath] = useState('');
  const [entries, setEntries] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [fileMeta, setFileMeta] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showNewFile, setShowNewFile] = useState(false);
  const [newFileName, setNewFileName] = useState('');
  const [newFileIsDir, setNewFileIsDir] = useState(false);

  const loadDir = useCallback(async (path = '') => {
    setLoading(true);
    try {
      const data = await fetchFiles(path);
      setEntries(data.entries || []);
      setCurrentPath(data.path || '');
    } catch { setEntries([]); }
    setLoading(false);
  }, [fetchFiles]);

  useEffect(() => { loadDir(''); }, [loadDir]);

  const openFile = async (entry) => {
    if (entry.is_dir) {
      setSelectedFile(null);
      setFileContent('');
      loadDir(entry.path);
      return;
    }
    setLoading(true);
    try {
      const data = await readFile(entry.path);
      setFileMeta(data);
      if (data.binary) {
        setFileContent('(Binary file — cannot display)');
        setOriginalContent('');
      } else {
        setFileContent(data.content || '');
        setOriginalContent(data.content || '');
      }
      setSelectedFile(entry.path);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to read file');
    }
    setLoading(false);
  };

  const handleSave = async () => {
    if (!selectedFile || fileContent === originalContent) return;
    setSaving(true);
    try {
      await writeFile(selectedFile, fileContent);
      setOriginalContent(fileContent);
    } catch (err) { alert(err.response?.data?.detail || 'Failed to save'); }
    setSaving(false);
  };

  const handleDelete = async (entry) => {
    const label = entry.is_dir ? 'directory' : 'file';
    if (!confirm(`Delete ${label} "${entry.name}"?`)) return;
    try {
      await deleteFile(entry.path);
      if (selectedFile === entry.path) { setSelectedFile(null); setFileContent(''); }
      loadDir(currentPath);
    } catch (err) { alert(err.response?.data?.detail || 'Failed to delete'); }
  };

  const handleCreateFile = async () => {
    if (!newFileName.trim()) return;
    const path = currentPath && currentPath !== '.'
      ? `${currentPath}/${newFileName.trim()}${newFileIsDir ? '/' : ''}`
      : `${newFileName.trim()}${newFileIsDir ? '/' : ''}`;
    try {
      await createFile(path, '');
      setShowNewFile(false);
      setNewFileName('');
      loadDir(currentPath);
    } catch (err) { alert(err.response?.data?.detail || 'Failed to create'); }
  };

  const goUp = () => {
    if (!currentPath || currentPath === '.') return;
    const parent = currentPath.split('/').slice(0, -1).join('/');
    setSelectedFile(null);
    setFileContent('');
    loadDir(parent);
  };

  const breadcrumbs = (currentPath && currentPath !== '.') ? currentPath.split('/') : [];
  const isDirty = selectedFile && fileContent !== originalContent;

  return (
    <div className="card overflow-hidden" style={{ minHeight: 300 }}>
      {/* Toolbar */}
      <div className="flex items-center gap-1 px-3 py-2 border-b border-white/5 bg-white/[0.02]">
        <FolderOpen size={12} className="text-yellow-400 mr-1" />
        <button onClick={() => { setSelectedFile(null); setFileContent(''); loadDir(''); }}
          className="text-[10px] text-gray-400 hover:text-white">root</button>
        {breadcrumbs.map((part, i) => (
          <span key={i} className="flex items-center gap-1">
            <ChevronRight size={9} className="text-gray-600" />
            <button onClick={() => {
              const p = breadcrumbs.slice(0, i + 1).join('/');
              setSelectedFile(null); setFileContent(''); loadDir(p);
            }} className="text-[10px] text-gray-400 hover:text-white">{part}</button>
          </span>
        ))}
        <div className="flex-1" />
        <button onClick={goUp} disabled={!currentPath || currentPath === '.'} className="btn-ghost p-1" title="Go up">
          <CornerUpLeft size={11} />
        </button>
        <button onClick={() => { setNewFileIsDir(false); setShowNewFile(true); }} className="btn-ghost p-1" title="New file">
          <FilePlus size={11} />
        </button>
        <button onClick={() => { setNewFileIsDir(true); setShowNewFile(true); }} className="btn-ghost p-1" title="New folder">
          <FolderPlus size={11} />
        </button>
        {exportUrl && (
          <a href={exportUrl} className="btn-ghost p-1" title="Export as .tar.gz" download>
            <Download size={11} />
          </a>
        )}
      </div>

      {/* New file inline */}
      {showNewFile && (
        <div className="flex items-center gap-2 px-3 py-1.5 border-b border-white/5 bg-white/[0.03]">
          {newFileIsDir ? <FolderPlus size={11} className="text-yellow-400" /> : <FilePlus size={11} className="text-blue-400" />}
          <input value={newFileName} onChange={(e) => setNewFileName(e.target.value)}
            placeholder={newFileIsDir ? 'folder-name' : 'filename.py'}
            className="input text-[11px] flex-1 py-0.5" autoFocus
            onKeyDown={(e) => { if (e.key === 'Enter') handleCreateFile(); if (e.key === 'Escape') setShowNewFile(false); }} />
          <button onClick={handleCreateFile} className="btn-primary text-[10px] px-2 py-0.5">Create</button>
          <button onClick={() => setShowNewFile(false)} className="btn-ghost p-0.5"><X size={11} /></button>
        </div>
      )}

      <div className="flex" style={{ minHeight: 260 }}>
        {/* File list panel */}
        <div className="w-[220px] flex-shrink-0 border-r border-white/5 overflow-y-auto" style={{ maxHeight: 400 }}>
          {loading && entries.length === 0 && <div className="text-[10px] text-gray-600 p-3">Loading...</div>}
          {!loading && entries.length === 0 && <div className="text-[10px] text-gray-600 p-3">Empty directory</div>}
          {entries.map((entry) => (
            <div key={entry.path}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-[11px] cursor-pointer hover:bg-white/5 group ${selectedFile === entry.path ? 'bg-white/10 text-white' : 'text-gray-400'}`}
            >
              <div className="flex items-center gap-1.5 flex-1 min-w-0" onClick={() => openFile(entry)}>
                {entry.is_dir
                  ? <Folder size={12} className="text-yellow-400 flex-shrink-0" />
                  : <File size={12} className="text-gray-500 flex-shrink-0" />}
                <span className="truncate">{entry.name}</span>
                {!entry.is_dir && entry.size > 0 && (
                  <span className="text-[9px] text-gray-600 ml-auto flex-shrink-0">
                    {entry.size > 1024 ? `${(entry.size / 1024).toFixed(1)}K` : `${entry.size}B`}
                  </span>
                )}
              </div>
              <button onClick={(e) => { e.stopPropagation(); handleDelete(entry); }}
                className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 hover:text-red-400" title="Delete">
                <Trash2 size={10} />
              </button>
            </div>
          ))}
        </div>

        {/* Editor panel */}
        <div className="flex-1 flex flex-col min-w-0">
          {selectedFile ? (
            <>
              <div className="flex items-center gap-2 px-3 py-1.5 border-b border-white/5 bg-white/[0.02]">
                <File size={11} className="text-gray-500" />
                <span className="text-[10px] text-gray-400 truncate flex-1">{selectedFile}</span>
                {isDirty && <span className="text-[9px] text-yellow-400">unsaved</span>}
                {fileMeta && !fileMeta.binary && (
                  <button onClick={handleSave} disabled={saving || !isDirty}
                    className={`btn-primary text-[10px] px-2 py-0.5 flex items-center gap-1 ${!isDirty ? 'opacity-40' : ''}`}>
                    {saving ? <Loader2 size={9} className="animate-spin" /> : <Save size={9} />} Save
                  </button>
                )}
              </div>
              {fileMeta?.binary ? (
                <div className="p-4 text-xs text-gray-500 text-center">Binary file cannot be displayed</div>
              ) : (
                <textarea
                  value={fileContent}
                  onChange={(e) => setFileContent(e.target.value)}
                  className="flex-1 bg-transparent text-[11px] text-gray-300 font-mono p-3 resize-none outline-none leading-relaxed"
                  style={{ minHeight: 220, tabSize: 2 }}
                  spellCheck={false}
                  onKeyDown={(e) => {
                    if ((e.metaKey || e.ctrlKey) && e.key === 's') {
                      e.preventDefault();
                      handleSave();
                    }
                    if (e.key === 'Tab') {
                      e.preventDefault();
                      const start = e.target.selectionStart;
                      const end = e.target.selectionEnd;
                      setFileContent(fileContent.substring(0, start) + '  ' + fileContent.substring(end));
                      setTimeout(() => { e.target.selectionStart = e.target.selectionEnd = start + 2; }, 0);
                    }
                  }}
                />
              )}
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-600 text-xs">
              <div className="text-center">
                <FileCode size={24} className="mx-auto mb-2 opacity-30" />
                Select a file to view or edit
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
