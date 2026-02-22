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

export async function streamChat(message, onToken, onDone, onError, persona = 'fred') {
  try {
    const res = await fetch(`${API_URL}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, persona }),
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

// ── Projects ─────────────────────────────────────────────────────
export const fetchProjects = () => api.get('/projects').then((r) => r.data);
export const fetchProject = (name) => api.get(`/projects/${name}`).then((r) => r.data);
export const fetchProjectCommits = (name, count = 10) =>
  api.get(`/projects/${name}/commits`, { params: { count } }).then((r) => r.data);
export const fetchProjectBranches = (name) =>
  api.get(`/projects/${name}/branches`).then((r) => r.data);

// ── Calendar ─────────────────────────────────────────────────────
export const fetchCalendarEvents = (params) => api.get('/calendar/events', { params }).then((r) => r.data);
export const fetchTodayEvents = () => api.get('/calendar/today').then((r) => r.data);
export const fetchWeekEvents = () => api.get('/calendar/week').then((r) => r.data);
export const fetchUpcomingEvents = (days = 7) =>
  api.get('/calendar/upcoming', { params: { days } }).then((r) => r.data);
export const createCalendarEvent = (data) => api.post('/calendar/events', data).then((r) => r.data);
export const updateCalendarEvent = (id, data) => api.patch(`/calendar/events/${id}`, data).then((r) => r.data);
export const deleteCalendarEvent = (id) => api.delete(`/calendar/events/${id}`);

// ── Content & Social ─────────────────────────────────────────────
export const fetchContent = (params) => api.get('/content', { params }).then((r) => r.data);
export const fetchContentSchedule = (days = 30) =>
  api.get('/content/schedule', { params: { days } }).then((r) => r.data);
export const createContent = (data) => api.post('/content', data).then((r) => r.data);
export const generateContent = (data) => api.post('/content/generate', data).then((r) => r.data);
export const updateContent = (id, data) => api.patch(`/content/${id}`, data).then((r) => r.data);
export const publishContent = (id) => api.post(`/content/${id}/publish`).then((r) => r.data);
export const deleteContent = (id) => api.delete(`/content/${id}`);
export const fetchSocialAccounts = () => api.get('/content/social/accounts').then((r) => r.data);
export const updateSocialAccount = (id, data) =>
  api.patch(`/content/social/accounts/${id}`, data).then((r) => r.data);

// ── Business Coach ───────────────────────────────────────────────
export const fetchGoals = (params) => api.get('/coach/goals', { params }).then((r) => r.data);
export const createGoal = (data) => api.post('/coach/goals', data).then((r) => r.data);
export const updateGoal = (id, data) => api.patch(`/coach/goals/${id}`, data).then((r) => r.data);
export const deleteGoal = (id) => api.delete(`/coach/goals/${id}`);
export const fetchReviews = (limit = 10) =>
  api.get('/coach/reviews', { params: { limit } }).then((r) => r.data);
export const fetchCurrentReview = () => api.get('/coach/reviews/current').then((r) => r.data);
export const generateReview = () => api.post('/coach/reviews/generate').then((r) => r.data);
export const saveReview = (data) => api.post('/coach/reviews', data).then((r) => r.data);
