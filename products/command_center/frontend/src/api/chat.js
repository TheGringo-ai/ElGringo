import { API_URL } from '../config';

export async function fetchPersonas() {
  const res = await fetch(`${API_URL}/personas`);
  if (!res.ok) throw new Error('Failed to fetch personas');
  return res.json();
}

export async function streamChat(message, persona, onToken, onDone, onError) {
  const token = import.meta.env.VITE_API_TOKEN;
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  try {
    const res = await fetch(`${API_URL}/chat/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ message, persona }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.error || err.detail || 'Chat request failed');
    }

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
        if (payload === '[DONE]') {
          onDone();
          return;
        }
        try {
          const parsed = JSON.parse(payload);
          if (parsed.token) onToken(parsed.token);
          if (parsed.done) { onDone(); return; }
        } catch {
          // non-JSON SSE line, skip
        }
      }
    }
    onDone();
  } catch (err) {
    onError(err.message);
  }
}
