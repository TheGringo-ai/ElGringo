import client from './client';

export async function fetchScheduler() {
  const { data } = await client.get('/scheduler');
  return data;
}

export async function toggleSchedulerTask(taskId) {
  const { data } = await client.patch(`/scheduler/${taskId}/toggle`);
  return data;
}

export async function fetchTodayStandup() {
  const { data } = await client.get('/standups/today');
  return data;
}

export async function fetchStandups(days = 7) {
  const { data } = await client.get('/standups', { params: { days } });
  return data;
}

export async function generateStandup() {
  const { data } = await client.post('/standups/generate');
  return data;
}
