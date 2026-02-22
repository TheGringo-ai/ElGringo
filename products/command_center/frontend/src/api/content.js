import client from './client';

export async function fetchContent(status) {
  const params = status ? { status } : {};
  const { data } = await client.get('/content', { params });
  return data;
}

export async function generateContent(type, params = {}) {
  const { data } = await client.post('/content/generate', { type, params });
  return data;
}

export async function pollJob(jobId) {
  const { data } = await client.get(`/content/jobs/${jobId}`);
  return data;
}

export async function approveContent(itemId) {
  const { data } = await client.post(`/content/${itemId}/approve`);
  return data;
}

export async function rejectContent(itemId) {
  const { data } = await client.post(`/content/${itemId}/reject`);
  return data;
}
