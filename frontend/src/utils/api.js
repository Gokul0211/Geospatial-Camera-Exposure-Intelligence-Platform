const BASE = '/api';

export async function fetchDevices(city) {
  const res = await fetch(`${BASE}/devices?city=${encodeURIComponent(city)}`);
  if (!res.ok) throw new Error(`Failed to fetch devices: ${res.status}`);
  return res.json();
}

export async function fetchNews(city) {
  const res = await fetch(`${BASE}/news?city=${encodeURIComponent(city)}`);
  if (!res.ok) throw new Error(`Failed to fetch news: ${res.status}`);
  return res.json();
}

export async function fetchHeatmap(city) {
  const res = await fetch(`${BASE}/heatmap?city=${encodeURIComponent(city)}`);
  if (!res.ok) throw new Error(`Failed to fetch heatmap: ${res.status}`);
  return res.json();
}

export async function fetchStats(city) {
  const res = await fetch(`${BASE}/stats?city=${encodeURIComponent(city)}`);
  if (!res.ok) throw new Error(`Failed to fetch stats: ${res.status}`);
  return res.json();
}

export async function generateBrief(briefRequest) {
  const res = await fetch(`${BASE}/brief`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(briefRequest),
  });
  if (!res.ok) throw new Error(`Failed to generate brief: ${res.status}`);
  return res.json();
}

/**
 * Stream a risk brief via SSE. Calls onChunk for each text chunk,
 * and onDone with the final risk level.
 */
export async function streamBrief(briefRequest, { onChunk, onDone, onError }) {
  try {
    const res = await fetch(`${BASE}/brief/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(briefRequest),
    });
    if (!res.ok) {
      onError?.(`HTTP ${res.status}`);
      return;
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
        try {
          const event = JSON.parse(line.slice(6));
          if (event.type === 'chunk') {
            onChunk?.(event.content);
          } else if (event.type === 'text') {
            // Full cached text — show all at once
            onChunk?.(event.content);
          } else if (event.type === 'done') {
            onDone?.(event.risk_level);
          } else if (event.type === 'error') {
            onError?.(event.message);
          }
        } catch {
          // Skip malformed events
        }
      }
    }
  } catch (e) {
    onError?.(e.message);
  }
}
