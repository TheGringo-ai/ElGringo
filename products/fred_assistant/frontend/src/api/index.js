import api, { API_URL } from './client';

// ── Stats & Dashboard ────────────────────────────────────────────
export const fetchStats = () => api.get('/tasks/stats').then((r) => r.data);
export const fetchTodayTasks = () => api.get('/tasks/today').then((r) => r.data);

// ── Boards ───────────────────────────────────────────────────────
export const fetchBoards = () => api.get('/boards').then((r) => r.data);
export const fetchBoard = (id) => api.get(`/boards/${id}`).then((r) => r.data);

// ── Tasks ────────────────────────────────────────────────────────
export const fetchTasks = (params) => api.get('/tasks', { params }).then((r) => r.data);
export const createTask = (data) => api.post('/tasks', data).then((r) => r.data);
export const updateTask = (id, data) => api.patch(`/tasks/${id}`, data).then((r) => r.data);
export const moveTask = (id, status) => api.patch(`/tasks/${id}/move`, { status }).then((r) => r.data);
export const deleteTask = (id) => api.delete(`/tasks/${id}`);

// ── Quick Capture ────────────────────────────────────────────────
export const quickCapture = (text, board_id) =>
  api.post('/capture', { text, board_id }).then((r) => r.data);

// ── Memory ───────────────────────────────────────────────────────
export const fetchMemories = (category) =>
  api.get('/memory', { params: category ? { category } : {} }).then((r) => r.data);
export const addMemory = (data) => api.post('/memory', data).then((r) => r.data);
export const deleteMemory = (id) => api.delete(`/memory/${id}`);
export const searchMemories = (q) => api.get('/memory/search', { params: { q } }).then((r) => r.data);

// ── Chat ─────────────────────────────────────────────────────────
export const fetchChatHistory = () => api.get('/chat/history').then((r) => r.data);
export const clearChat = () => api.delete('/chat/history');

export async function streamChat(message, onToken, onDone, onError) {
  try {
    const res = await fetch(`${API_URL}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, persona: 'fred' }),
    });
    if (!res.ok) throw new Error(`Chat failed: ${res.statusText}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6).trim();
        try {
          const parsed = JSON.parse(payload);
          if (parsed.token) onToken(parsed.token);
          if (parsed.done) { onDone(); return; }
        } catch { /* skip */ }
      }
    }
    onDone();
  } catch (err) {
    onError(err.message);
  }
}

// ── Briefing ─────────────────────────────────────────────────────
export const fetchBriefing = () => api.get('/briefing/today').then((r) => r.data);
export const generateBriefing = () => api.post('/briefing').then((r) => r.data);
