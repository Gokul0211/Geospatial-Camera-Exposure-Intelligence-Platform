/**
 * LiveAlerts.jsx — Phase 4 update
 * =================================
 * Consumes the REAL WebSocket message shape from Phase 2 (main.py ConnectionManager).
 * Old fake shape: { type: 'LIVE_ALERT', city, severity, message, timestamp }
 * New real shape: { type: 'ALERT', id, camera_id, city, event_type, trust_score,
 *                   action_tier, contributing_factors, corroborated_by, detected_at }
 *
 * Design preserved: severity-colored toasts, last-3-only, slide-in animation.
 * action_tier replaces severity; event_type replaces message.
 * Auto-reconnects on disconnect (exponential backoff, max 30s).
 */
import React, { useState, useEffect, useRef } from 'react';

// Map action_tier → display color (matches existing palette from DetailPanel)
const TIER_COLORS = {
  high_trust:   'var(--color-medium, #f39c12)',   // amber — high trust = less urgent visually
  medium_trust: 'var(--color-high, #e67e22)',     // orange
  low_trust:    'var(--color-critical, #ff4444)', // red — low trust = highest visual urgency
};

const TIER_LABELS = {
  high_trust:   'HIGH TRUST',
  medium_trust: 'MED TRUST',
  low_trust:    'LOW TRUST',
};

const EVENT_LABELS = {
  loitering:            'Loitering Detected',
  perimeter_breach:     'Perimeter Breach',
  unauthorized_access:  'Unauthorized Access',
  anomalous_motion:     'Anomalous Motion',
};

function formatTime(isoString) {
  try {
    return new Date(isoString).toLocaleTimeString('en-IN', { hour12: false });
  } catch {
    return '--:--:--';
  }
}

export default function LiveAlerts() {
  const [alerts, setAlerts] = useState([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const retryRef = useRef(null);
  const retryDelay = useRef(1000);

  useEffect(() => {
    function connect() {
      // Clean up any existing connection
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }

      const ws = new WebSocket(`ws://${window.location.host}/api/ws/alerts`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        retryDelay.current = 1000; // reset backoff on successful connect
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Phase 4: consume the real ALERT shape from Phase 2
          if (data.type === 'ALERT') {
            setAlerts(prev => [data, ...prev].slice(0, 5)); // keep last 5
          }
          // Gracefully ignore any other message types
        } catch (e) {
          console.error('[LiveAlerts] Failed to parse WebSocket message:', e);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        // Exponential backoff reconnect (max 30s)
        retryRef.current = setTimeout(() => {
          retryDelay.current = Math.min(retryDelay.current * 2, 30000);
          connect();
        }, retryDelay.current);
      };

      ws.onerror = (err) => {
        console.warn('[LiveAlerts] WebSocket error:', err);
      };
    }

    connect();

    return () => {
      clearTimeout(retryRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect on intentional unmount
        wsRef.current.close();
      }
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
      {alerts.map((alert, index) => {
        const tierColor = TIER_COLORS[alert.action_tier] || 'var(--color-medium)';
        const tierLabel = TIER_LABELS[alert.action_tier] || alert.action_tier?.toUpperCase() || 'ALERT';
        const eventLabel = EVENT_LABELS[alert.event_type] || alert.event_type || 'Detection Event';

        return (
          <div
            key={alert.id || `${alert.detected_at}-${index}`}
            style={{
              background: 'var(--bg-elevated, #1a1e2e)',
              borderLeft: `4px solid ${tierColor}`,
              padding: '12px 16px',
              borderRadius: '4px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
              maxWidth: '300px',
              animation: 'slideIn 0.3s ease-out forwards',
              opacity: 1 - (index * 0.15),
            }}
          >
            {/* Header row: city + tier badge */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--text-muted, #667788)' }}>
                {(alert.city || 'UNKNOWN').toUpperCase()} • {tierLabel}
              </span>
              <span style={{
                width: '8px', height: '8px', borderRadius: '50%',
                background: tierColor,
                animation: alert.action_tier === 'low_trust' ? 'pulse 2s infinite' : 'none',
              }} />
            </div>

            {/* Event type */}
            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-primary, #e0e6f0)', lineHeight: 1.4 }}>
              {eventLabel}
            </p>

            {/* Trust score + time */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, alignItems: 'center' }}>
              <span style={{ fontSize: '0.68rem', fontFamily: 'IBM Plex Mono, monospace', color: tierColor }}>
                SCORE: {alert.trust_score ?? '—'}
              </span>
              <span style={{ fontSize: '0.65rem', color: 'var(--text-muted, #667788)', fontFamily: 'IBM Plex Mono, monospace' }}>
                {formatTime(alert.detected_at)}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
