import { useState, useEffect } from 'react';
import { fetchPlatformStatus } from '../api';

export default function PlatformStatus() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPlatformStatus()
      .then(setStatus)
      .catch(() => setStatus(null))
      .finally(() => setLoading(false));

    const interval = setInterval(() => {
      fetchPlatformStatus().then(setStatus).catch(() => {});
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading || !status) return null;

  const { services, online, total } = status;

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12, padding: '8px 16px',
      background: 'var(--bg-secondary, #1a1a2e)', borderRadius: 8,
      fontSize: 13, flexWrap: 'wrap',
    }}>
      <span style={{ fontWeight: 600, opacity: 0.7 }}>
        Platform: {online}/{total}
      </span>
      {Object.entries(services).map(([key, svc]) => (
        <span key={key} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            background: svc.healthy ? '#22c55e' : '#ef4444',
            display: 'inline-block',
          }} />
          <span style={{ opacity: svc.healthy ? 0.9 : 0.5 }}>
            {svc.label}
          </span>
        </span>
      ))}
    </div>
  );
}
