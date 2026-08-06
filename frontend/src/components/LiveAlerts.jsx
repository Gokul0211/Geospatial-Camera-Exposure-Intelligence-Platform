import React, { useState, useEffect } from 'react';

export default function LiveAlerts() {
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    // Connect to the WebSocket endpoint
    const ws = new WebSocket(`ws://${window.location.host}/api/ws/alerts`);
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'LIVE_ALERT') {
          setAlerts(prev => [data, ...prev].slice(0, 3)); // Keep only the last 3 alerts
        }
      } catch (e) {
        console.error("Error parsing WebSocket message:", e);
      }
    };

    ws.onclose = () => {
      console.log("Live alerts disconnected");
    };

    return () => {
      ws.close();
    };
  }, []);

  if (alerts.length === 0) return null;

  return (
    <div style={{
      position: 'fixed',
      bottom: '20px',
      right: '20px',
      display: 'flex',
      flexDirection: 'column',
      gap: '10px',
      zIndex: 9999,
      pointerEvents: 'none',
    }}>
      {alerts.map((alert, index) => (
        <div key={alert.timestamp} style={{
          background: 'var(--bg-elevated)',
          borderLeft: `4px solid ${alert.severity === 'CRITICAL' ? 'var(--color-critical)' : alert.severity === 'HIGH' ? 'var(--color-high)' : 'var(--color-medium)'}`,
          padding: '12px 16px',
          borderRadius: '4px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
          maxWidth: '300px',
          animation: 'slideIn 0.3s ease-out forwards',
          opacity: 1 - (index * 0.2), // Fade older alerts slightly
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--text-muted)' }}>
              {alert.city.toUpperCase()} • {alert.severity}
            </span>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--color-critical)', animation: 'pulse 2s infinite' }} />
          </div>
          <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.4 }}>
            {alert.message}
          </p>
        </div>
      ))}
    </div>
  );
}
