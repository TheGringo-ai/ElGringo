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

export async function streamChat(message, onToken, onDone, onError, persona = 'fred', onThinking) {
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
          if (parsed.thinking !== undefined && onThinking) {
            onThinking(parsed.thinking, parsed.actions || parsed.result || '');
          } else if (parsed.token) {
            onToken(parsed.token);
          }
          if (parsed.done) { onDone(); return; }
        } catch { /* skip */ }
      }
    }
    onDone();
  } catch (err) {
    onError(err.message);
  }
}

// ── Briefing & Shutdown ─────────────────────────────────────────
export const fetchBriefing = () => api.get('/briefing/today').then((r) => r.data);
export const generateBriefing = () => api.post('/briefing').then((r) => r.data);
export const generateShutdown = () => api.post('/briefing/shutdown').then((r) => r.data);
export const fetchTomorrowTasks = () => api.get('/briefing/tomorrow').then((r) => r.data);

// ── Projects ─────────────────────────────────────────────────────
export const fetchProjects = () => api.get('/projects').then((r) => r.data);
export const fetchProject = (name) => api.get(`/projects/${name}`).then((r) => r.data);
export const fetchProjectCommits = (name, count = 10) =>
  api.get(`/projects/${name}/commits`, { params: { count } }).then((r) => r.data);
export const fetchProjectBranches = (name) =>
  api.get(`/projects/${name}/branches`).then((r) => r.data);

// ── Project File Browser ─────────────────────────────────────────
export const fetchProjectFiles = (name, path = '') =>
  api.get(`/projects/${name}/files`, { params: { path } }).then((r) => r.data);
export const readProjectFile = (name, path) =>
  api.get(`/projects/${name}/files/read`, { params: { path } }).then((r) => r.data);
export const writeProjectFile = (name, path, content) =>
  api.put(`/projects/${name}/files/write`, { content }, { params: { path } }).then((r) => r.data);
export const createProjectFile = (name, path, content = '') =>
  api.post(`/projects/${name}/files/create`, { path, content }).then((r) => r.data);
export const deleteProjectFile = (name, path) =>
  api.delete(`/projects/${name}/files/delete`, { params: { path } }).then((r) => r.data);
export const renameProjectFile = (name, oldPath, newPath) =>
  api.post(`/projects/${name}/files/rename`, { old_path: oldPath, new_path: newPath }).then((r) => r.data);
export const exportProject = (name) => `${API_URL}/projects/${name}/export`;

// ── Project AI Chat & Tasks ─────────────────────────────────────────
export async function streamProjectChat(name, message, context, onToken, onDone, onError, onTasksCreated) {
  try {
    const res = await fetch(`${API_URL}/projects/${name}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, context }),
    });
    if (!res.ok) throw new Error(`Stream failed: ${res.statusText}`);

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
        try {
          const parsed = JSON.parse(line.slice(6).trim());
          if (parsed.tasks_created && onTasksCreated) onTasksCreated(parsed.tasks_created);
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

export const generateProjectTasks = (name, instructions = '', boardId = 'work') =>
  api.post(`/projects/${name}/generate-tasks`, { instructions, board_id: boardId }).then((r) => r.data);

// ── Project Notes ───────────────────────────────────────────────
export const fetchProjectNotes = (name) =>
  api.get(`/projects/${name}/notes`).then((r) => r.data);
export const createProjectNote = (name, data) =>
  api.post(`/projects/${name}/notes`, data).then((r) => r.data);
export const generateProjectNotes = (name) =>
  api.post(`/projects/${name}/notes/generate`).then((r) => r.data);
export const updateProjectNote = (name, noteId, data) =>
  api.patch(`/projects/${name}/notes/${noteId}`, data).then((r) => r.data);
export const deleteProjectNote = (name, noteId) =>
  api.delete(`/projects/${name}/notes/${noteId}`);

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
export const approveContent = (id) => api.post(`/content/${id}/approve`).then((r) => r.data);
export const rejectContent = (id, reason = '') =>
  api.post(`/content/${id}/reject`, { reason }).then((r) => r.data);
export const publishContentTo = (id, platform, dryRun = true) =>
  api.post(`/content/${id}/publish_to`, null, { params: { platform, dry_run: dryRun } }).then((r) => r.data);

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

// ── Focus Mode ──────────────────────────────────────────────────
export const startFocus = (taskId, minutes = 25) =>
  api.post('/focus/start', { task_id: taskId, planned_minutes: minutes }).then((r) => r.data);
export const stopFocus = (sessionId, completed = true, notes = '') =>
  api.post('/focus/stop', { session_id: sessionId, completed, notes }).then((r) => r.data);
export const fetchActiveSession = () => api.get('/focus/active').then((r) => r.data);
export const fetchFocusStats = (days = 7) =>
  api.get('/focus/stats', { params: { days } }).then((r) => r.data);
export const fetchFocusSessions = (days = 7) =>
  api.get('/focus/sessions', { params: { days } }).then((r) => r.data);

// ── CRM ─────────────────────────────────────────────────────────
export const fetchLeads = (stage, source) =>
  api.get('/crm/leads', { params: { stage, source } }).then((r) => r.data);
export const fetchLead = (id) => api.get(`/crm/leads/${id}`).then((r) => r.data);
export const createLead = (data) => api.post('/crm/leads', data).then((r) => r.data);
export const updateLead = (id, data) => api.patch(`/crm/leads/${id}`, data).then((r) => r.data);
export const deleteLead = (id) => api.delete(`/crm/leads/${id}`);
export const logOutreach = (leadId, data) =>
  api.post(`/crm/leads/${leadId}/outreach`, data).then((r) => r.data);
export const fetchOutreach = (leadId) =>
  api.get(`/crm/leads/${leadId}/outreach`).then((r) => r.data);
export const scheduleFollowup = (leadId, date, notes = '') =>
  api.post(`/crm/leads/${leadId}/followup`, { date, notes }).then((r) => r.data);
export const fetchPipeline = () => api.get('/crm/pipeline').then((r) => r.data);
export const fetchFollowups = (days = 3) =>
  api.get('/crm/followups', { params: { days } }).then((r) => r.data);

// ── CEO Lens Metrics ────────────────────────────────────────────
export const fetchCurrentMetrics = () => api.get('/metrics/current').then((r) => r.data);
export const fetchMetricsHistory = (days = 30) =>
  api.get('/metrics/history', { params: { days } }).then((r) => r.data);
export const saveMetricsSnapshot = () => api.post('/metrics/snapshot').then((r) => r.data);
export const logMetric = (name, value) =>
  api.post('/metrics/log', { name, value }).then((r) => r.data);

// ── Inbox ───────────────────────────────────────────────────────
export const fetchInbox = () => api.get('/inbox').then((r) => r.data);
export const fetchInboxCount = () => api.get('/inbox/count').then((r) => r.data);

// ── Playbooks ───────────────────────────────────────────────────
export const fetchPlaybooks = (category) =>
  api.get('/playbooks', { params: category ? { category } : {} }).then((r) => r.data);
export const fetchPlaybook = (id) => api.get(`/playbooks/${id}`).then((r) => r.data);
export const createPlaybook = (data) => api.post('/playbooks', data).then((r) => r.data);
export const updatePlaybook = (id, data) => api.patch(`/playbooks/${id}`, data).then((r) => r.data);
export const deletePlaybook = (id) => api.delete(`/playbooks/${id}`);
export const runPlaybook = (id) => api.post(`/playbooks/${id}/run`).then((r) => r.data);

// ── Repo Intelligence ──────────────────────────────────────────
export const analyzeRepo = (name, depth = 'quick') =>
  api.post(`/repo-intel/${name}/analyze`, { depth }).then((r) => r.data);
export const fetchLatestAnalysis = (name) =>
  api.get(`/repo-intel/${name}/latest`).then((r) => r.data);
export const generateRepoTasks = (name, createTasks = false) =>
  api.post(`/repo-intel/${name}/generate-tasks`, { create_tasks: createTasks }).then((r) => r.data);
export const fetchAnalyses = (projectName, limit = 20) =>
  api.get('/repo-intel/analyses', { params: { project_name: projectName, limit } }).then((r) => r.data);
export const reviewRepo = (name) =>
  api.post(`/repo-intel/${name}/review`).then((r) => r.data);

// ── Platform Services ─────────────────────────────────────────
export const fetchPlatformStatus = () =>
  api.get('/platform/status').then((r) => r.data);
export const auditProject = (name, auditType = 'full') =>
  api.post(`/platform/${name}/audit`, { audit_type: auditType }).then((r) => r.data);
export const generateProjectTests = (name) =>
  api.post(`/platform/${name}/tests`).then((r) => r.data);
export const generateProjectDocs = (name, docType = 'readme') =>
  api.post(`/platform/${name}/docs`, { doc_type: docType }).then((r) => r.data);
export const fullProjectReview = (name) =>
  api.post(`/platform/${name}/full-review`).then((r) => r.data);
export const fetchServiceResults = (projectName, service) =>
  api.get('/platform/results', { params: { project_name: projectName, service } }).then((r) => r.data);

// ── AI Usage ────────────────────────────────────────────────
export const fetchUsageToday = () => api.get('/usage/today').then((r) => r.data);
export const fetchUsageSummary = (days = 30) =>
  api.get('/usage/summary', { params: { days } }).then((r) => r.data);
export const fetchUsageByModel = (days = 30) =>
  api.get('/usage/by-model', { params: { days } }).then((r) => r.data);
export const fetchUsageBudget = () => api.get('/usage/budget').then((r) => r.data);
export const updateUsageBudget = (daily_limit, monthly_limit) =>
  api.post('/usage/budget', { daily_limit, monthly_limit }).then((r) => r.data);
export const fetchRecentUsage = (limit = 50) =>
  api.get('/usage/recent', { params: { limit } }).then((r) => r.data);
export const fetchProviders = () => api.get('/usage/providers').then((r) => r.data);
export const updateProviderPrefs = (preferred_provider, enabled_providers) =>
  api.post('/usage/providers/preferences', { preferred_provider, enabled_providers }).then((r) => r.data);
export const fetchSyncStatus = () => api.get('/usage/sync/status').then((r) => r.data);

// ── Sync ────────────────────────────────────────────────────
export const triggerSync = () => api.post('/sync/now').then((r) => r.data);
export const configureSyncRemote = (remote_url, token) =>
  api.post('/sync/configure', { remote_url, token }).then((r) => r.data);

// ── Audit Insights ───────────────────────────────────────────
export const parseAuditFindings = (projectName, rawFindings, language = 'python') =>
  api.post(`/platform/${projectName}/audit/parse`, {
    raw_findings: rawFindings, project_name: projectName, language,
  }).then((r) => r.data);

export const applyAuditFix = (projectName, filePath, findingId, codeSnippet, suggestedFix, description = '') =>
  api.post(`/platform/${projectName}/audit/fix`, {
    project_name: projectName, file_path: filePath, finding_id: findingId,
    code_snippet: codeSnippet, suggested_fix: suggestedFix, description,
  }, { timeout: 60000 }).then((r) => r.data);

async function _streamSSE(url, body, onToken, onDone, onError) {
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`Stream failed: ${res.statusText}`);

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
        try {
          const parsed = JSON.parse(line.slice(6).trim());
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

export const streamAuditChat = (projectName, message, findings, findingId, onToken, onDone, onError) =>
  _streamSSE(`${API_URL}/platform/${projectName}/audit/chat`, {
    message, project_name: projectName, audit_findings: findings, finding_id: findingId,
  }, onToken, onDone, onError);

export const streamReviewChat = (projectName, message, reviewData, onToken, onDone, onError) =>
  _streamSSE(`${API_URL}/platform/${projectName}/review/chat`, {
    message, project_name: projectName, review_data: reviewData,
  }, onToken, onDone, onError);

// ── Task AI Review ──────────────────────────────────────────────
export const streamTaskReview = (taskId, onToken, onDone, onError) =>
  _streamSSE(`${API_URL}/tasks/${taskId}/review`, {}, onToken, onDone, onError);

// ── App Factory ────────────────────────────────────────────────
export const fetchFactoryApps = () => api.get('/factory/apps').then((r) => r.data);
export const createFactoryApp = (data) => api.post('/factory/apps', data).then((r) => r.data);
export const fetchFactoryApp = (id) => api.get(`/factory/apps/${id}`).then((r) => r.data);
export const updateFactoryApp = (id, data) => api.patch(`/factory/apps/${id}`, data).then((r) => r.data);
export const generateFactoryApp = (id, data = {}) =>
  api.post(`/factory/apps/${id}/generate`, data, { timeout: 120000 }).then((r) => r.data);
export const buildFactoryApp = (id) =>
  api.post(`/factory/apps/${id}/build`, {}, { timeout: 300000 }).then((r) => r.data);
export const deployFactoryApp = (id) =>
  api.post(`/factory/apps/${id}/deploy`).then((r) => r.data);
export const archiveFactoryApp = (id) => api.delete(`/factory/apps/${id}`);
export const fetchFactoryBuilds = (id) => api.get(`/factory/apps/${id}/builds`).then((r) => r.data);
export const fetchFactoryTemplates = () => api.get('/factory/templates').then((r) => r.data);
export const fetchFactoryPortfolio = () => api.get('/factory/portfolio').then((r) => r.data);

// ── Factory File Browser ──────────────────────────────────────
export const fetchFactoryFiles = (id, path = '') =>
  api.get(`/factory/apps/${id}/files`, { params: { path } }).then((r) => r.data);
export const readFactoryFile = (id, path) =>
  api.get(`/factory/apps/${id}/files/read`, { params: { path } }).then((r) => r.data);
export const writeFactoryFile = (id, path, content) =>
  api.put(`/factory/apps/${id}/files/write`, { content }, { params: { path } }).then((r) => r.data);
export const createFactoryFile = (id, path, content = '') =>
  api.post(`/factory/apps/${id}/files/create`, { path, content }).then((r) => r.data);
export const deleteFactoryFile = (id, path) =>
  api.delete(`/factory/apps/${id}/files/delete`, { params: { path } }).then((r) => r.data);
export const renameFactoryFile = (id, oldPath, newPath) =>
  api.post(`/factory/apps/${id}/files/rename`, { old_path: oldPath, new_path: newPath }).then((r) => r.data);
export const exportFactoryApp = (id) => `${API_URL}/factory/apps/${id}/export`;

// ── Billing ────────────────────────────────────────────────────
export const createBillingCustomer = (data) => api.post('/billing/customers', data).then((r) => r.data);
export const fetchBillingRevenue = () => api.get('/billing/revenue').then((r) => r.data);
