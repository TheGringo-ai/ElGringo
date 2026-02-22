import client from './client';

export async function fetchStats() {
  const { data } = await client.get('/stats');
  return data;
}

export async function fetchCurrentSprint() {
  const { data } = await client.get('/sprints/current');
  return data;
}

export async function fetchTasks(params = {}) {
  const { data } = await client.get('/tasks', { params });
  return data;
}

export async function createTask(task) {
  const { data } = await client.post('/tasks', task);
  return data;
}

export async function updateTaskStatus(taskId, status) {
  const { data } = await client.patch(`/tasks/${taskId}/status`, { status });
  return data;
}

export async function fetchVelocity(weeks = 4) {
  const { data } = await client.get('/velocity', { params: { weeks } });
  return data;
}
