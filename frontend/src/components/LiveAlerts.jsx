import { useState, useEffect, useRef } from 'react';

const TIER_CONFIG = {
  high_trust:   { color: '#10b981', bg: 'rgba(16,185,129,0.08)',  border: 'rgba(16,185,129,0.35)', label: 'HIGH TRUST' },
  medium_trust: { color: '#f59e0b', bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.35)', label: 'MEDIUM TRUST' },
  low_trust:    { color: '#ef4444', bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.4)',   label: 'CRITICAL ALERT' },
};

const EVENT_META = {
  loitering:           { label: 'Loitering Activity Detected',    icon: '🚶' },
  perimeter_breach:    { label: 'Perimeter Line Breach',          icon: '🚨' },
  unauthorized_access: { label: 'Unauthorized Stream Access',     icon: '🔓' },
  anomalous_motion:    { label: 'Anomalous Motion Detected',      icon: '⚡' },
};

const INITIAL_DEMO_ALERTS = [
  {
    id: 'demo-alert-001',
    camera_id: 'mumbai_cam_502',
    city: 'Mumbai',
    event_type: 'perimeter_breach',
    trust_score: 20,
    action_tier: 'low_trust',
    contributing_factors: ['auth_required:false', 'known_cve_count:3', 'outdated_firmware'],
    detected_at: new Date().toISOString(),
  },
  {
    id: 'demo-alert-002',
    camera_id: 'mumbai_cam_108',
    city: 'Mumbai',
    event_type: 'loitering',
    trust_score: 65,
    action_tier: 'medium_trust',
    contributing_factors: ['known_cve_count:1'],
    detected_at: new Date(Date.now() - 60000).toISOString(),
  }
];

function formatTime(isoString) {
  try {
    return new Date(isoString).toLocaleTimeString('en-IN', { hour12: false });
  } catch {
    return '--:--:--';
  }
}

// Radar sweep icon
function RadarIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5" opacity="0.4" />
      <circle cx="12" cy="12" r="5"  stroke="currentColor" strokeWidth="1.5" opacity="0.6" />
      <circle cx="12" cy="12" r="1.5" fill="currentColor" />
      <line x1="12" y1="12" x2="19" y2="5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.8" style={{ animation: 'radar-sweep 3s linear infinite', transformOrigin: '12px 12px' }} />
    </svg>
  );
}

export default function LiveAlerts({ onSelectDevice }) {
  const [alerts, setAlerts] = useState(INITIAL_DEMO_ALERTS);
  const [isOpen, setIsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const wsRef = useRef(null);
  const retryRef = useRef(null);
  const retryDelay = useRef(1000);
  const isOpenRef = useRef(isOpen);

  useEffect(() => {
    isOpenRef.current = isOpen;
  }, [isOpen]);

  useEffect(() => {
    function connect() {
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = window.location.port === '5173'
        ? `${protocol}//127.0.0.1:8000/api/ws/alerts`
        : `${protocol}//${window.location.host}/api/ws/alerts`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => { retryDelay.current = 1000; };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'ALERT') {
            setAlerts(prev => [data, ...prev].slice(0, 4));
            if (!isOpenRef.current) setUnreadCount(prev => prev + 1);
          }
        } catch (e) {
          console.error('[LiveAlerts] Failed to parse WebSocket message:', e);
        }
      };

      ws.onclose = () => {
        retryRef.current = setTimeout(() => {
          retryDelay.current = Math.min(retryDelay.current * 2, 30000);
          connect();
        }, retryDelay.current);
      };

      ws.onerror = (err) => { console.warn('[LiveAlerts] WebSocket error:', err); };
    }

    connect();
    return () => {
      clearTimeout(retryRef.current);
      if (wsRef.current) { wsRef.current.onclose = null; wsRef.current.close(); }
    };
  }, []);

  const dismissAlert = (id) => setAlerts(prev => prev.filter(a => a.id !== id));

  const triggerDemoAlert = async () => {
    const eventTypes = ['perimeter_breach', 'loitering', 'unauthorized_access', 'anomalous_motion'];
    const selectedEvent = eventTypes[Math.floor(Math.random() * eventTypes.length)];
    const camNum = Math.floor(Math.random() * 800) + 100;

    try {
      const res = await fetch('http://localhost:8000/api/detection-event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': 'dev-secret-key-12345' },
        body: JSON.stringify({
          camera_id: `mumbai_cam_${camNum}`, city: 'Mumbai',
          event_type: selectedEvent, timestamp: new Date().toISOString(),
          bounding_box: [120, 140, 220, 310], confidence: 0.96,
        })
      });
      if (!res.ok) throw new Error('API dispatch failed');
    } catch {
      const newAlert = {
        id: `sim-alert-${Date.now()}`,
        camera_id: `mumbai_cam_${camNum}`, city: 'Mumbai',
        event_type: selectedEvent,
        trust_score: Math.floor(Math.random() * 35) + 10,
        action_tier: 'low_trust',
        contributing_factors: ['auth_required:false', 'known_cve_count:3', 'outdated_firmware'],
        detected_at: new Date().toISOString(),
      };
      setAlerts(prev => [newAlert, ...prev].slice(0, 4));
      if (!isOpenRef.current) setUnreadCount(prev => prev + 1);
    }
  };

  const toggleOpen = () => {
    setIsOpen(prev => {
      if (!prev) setUnreadCount(0);
      return !prev;
    });
  };

  if (alerts.length === 0) return null;

  return (
    <div style={{
      position: 'fixed',
      bottom: '20px',
      left: '20px',
      display: 'flex',
      flexDirection: 'column-reverse',
      gap: '10px',
      zIndex: 9000,
      pointerEvents: 'none',
      maxWidth: '340px',
    }}>
      {/* ── Trigger button row ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, pointerEvents: 'auto' }}>
        <button
          onClick={toggleOpen}
          style={{
            background: isOpen
              ? 'rgba(8, 11, 17, 0.95)'
              : 'rgba(239, 68, 68, 0.92)',
            backdropFilter: 'blur(12px)',
            border: `1px solid ${isOpen ? 'rgba(255,255,255,0.1)' : 'rgba(239,68,68,0.7)'}`,
            padding: '8px 16px',
            borderRadius: '22px',
            color: '#ffffff',
            fontSize: 11,
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            cursor: 'pointer',
            boxShadow: isOpen
              ? '0 4px 20px rgba(0,0,0,0.6)'
              : '0 4px 20px rgba(239,68,68,0.4), 0 0 30px rgba(239,68,68,0.15)',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            transition: 'all 0.25s ease',
            letterSpacing: '0.06em',
          }}
        >
          {isOpen ? (
            <>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
              MINIMIZE ALERTS
            </>
          ) : (
            <>
              <span style={{
                width: 7, height: 7, borderRadius: '50%',
                background: '#fecaca',
                boxShadow: '0 0 8px #fecaca',
                animation: 'pulse-dot 1.2s infinite',
                display: 'block',
                flexShrink: 0,
              }} />
              <RadarIcon />
              THREAT ALERTS
              <span style={{
                background: 'rgba(255,255,255,0.2)',
                padding: '1px 7px', borderRadius: 10,
                fontSize: 10,
              }}>
                {unreadCount > 0 ? `${unreadCount} NEW` : alerts.length}
              </span>
            </>
          )}
        </button>

        {isOpen && (
          <button
            onClick={triggerDemoAlert}
            title="Simulate a real-time detection event"
            style={{
              background: 'rgba(59,130,246,0.15)',
              border: '1px solid rgba(59,130,246,0.4)',
              color: '#60a5fa',
              padding: '8px 14px',
              borderRadius: '22px',
              fontSize: 10,
              fontFamily: 'var(--font-mono)',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              pointerEvents: 'auto',
              backdropFilter: 'blur(10px)',
              letterSpacing: '0.05em',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'rgba(59,130,246,0.25)';
              e.currentTarget.style.boxShadow = '0 0 16px rgba(59,130,246,0.3)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'rgba(59,130,246,0.15)';
              e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.5)';
            }}
          >
            ⚡ SIMULATE
          </button>
        )}
      </div>

      {/* ── Alert Cards ── */}
      {isOpen && alerts.map((alert, index) => {
        const cfg     = TIER_CONFIG[alert.action_tier] || TIER_CONFIG.low_trust;
        const evtMeta = EVENT_META[alert.event_type] || { label: alert.event_type || 'Surveillance Event', icon: '⚠️' };

        return (
          <div
            key={alert.id || `${alert.detected_at}-${index}`}
            className="toast-alert"
            style={{
              pointerEvents: 'auto',
              background: 'rgba(8, 11, 17, 0.97)',
              backdropFilter: 'blur(16px)',
              border: `1px solid ${cfg.border}`,
              borderLeft: `4px solid ${cfg.color}`,
              padding: '12px 14px',
              borderRadius: 8,
              boxShadow: `0 8px 32px rgba(0,0,0,0.7), 0 0 20px ${cfg.color}15`,
              width: '330px',
              opacity: 1 - (index * 0.08),
            }}
          >
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                <span style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: cfg.color,
                  boxShadow: `0 0 6px ${cfg.color}`,
                  animation: alert.action_tier === 'low_trust' ? 'pulse-dot 1s infinite' : 'none',
                  display: 'block', flexShrink: 0,
                }} />
                <span style={{
                  fontSize: 9,
                  fontWeight: 800,
                  color: cfg.color,
                  fontFamily: 'var(--font-mono)',
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                }}>
                  {(alert.city || 'LOCATION').toUpperCase()} · {cfg.label}
                </span>
              </div>

              <button
                onClick={() => dismissAlert(alert.id)}
                style={{
                  background: 'none', border: 'none',
                  color: 'var(--text-muted)',
                  fontSize: 11, cursor: 'pointer', padding: '2px 4px',
                  borderRadius: 3, lineHeight: 1,
                  transition: 'color 0.15s',
                }}
                title="Dismiss Alert"
                onMouseEnter={e => e.currentTarget.style.color = '#f0f4f8'}
                onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}
              >
                ✕
              </button>
            </div>

            {/* Event */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <span style={{ fontSize: 18, lineHeight: 1 }}>{evtMeta.icon}</span>
              <span style={{
                fontSize: 13,
                fontWeight: 600,
                color: '#f0f4f8',
                fontFamily: 'var(--font-sans)',
                lineHeight: 1.3,
              }}>
                {evtMeta.label}
              </span>
            </div>

            {/* Meta row */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              paddingTop: 8,
              borderTop: '1px solid rgba(255,255,255,0.06)',
              fontSize: 10,
              fontFamily: 'var(--font-mono)',
            }}>
              <span style={{ color: 'var(--text-secondary)' }}>
                <span style={{ color: 'var(--text-muted)' }}>SENSOR:</span>&nbsp;
                <span style={{ color: '#f0f4f8', fontWeight: 700 }}>{alert.camera_id}</span>
              </span>
              <span style={{ color: 'var(--text-muted)' }}>{formatTime(alert.detected_at)}</span>
            </div>

            {/* Channel badge & Operator Verdict */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              paddingTop: 6,
              paddingBottom: 4,
              fontSize: 9,
              fontFamily: 'var(--font-mono)',
            }}>
              <span style={{
                color: alert.action_tier === 'high_trust' ? '#ef4444' : alert.action_tier === 'medium_trust' ? '#f59e0b' : '#64748b',
                background: alert.action_tier === 'high_trust' ? 'rgba(239,68,68,0.1)' : 'rgba(255,255,255,0.04)',
                border: `1px solid ${alert.action_tier === 'high_trust' ? 'rgba(239,68,68,0.3)' : 'rgba(255,255,255,0.08)'}`,
                padding: '1px 5px',
                borderRadius: 3,
                fontWeight: 700,
              }}>
                {alert.action_tier === 'high_trust' ? '🚨 EMERGENCY PUSH' : alert.action_tier === 'medium_trust' ? '⚠️ TRIAGE QUEUE' : '📁 SILENT LOG'}
              </span>

              {/* Operator Verdict Labelling (Luna 2018) */}
              <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                {alert.operator_verdict ? (
                  <span style={{
                    color: alert.operator_verdict === 'verified' ? '#10b981' : '#ef4444',
                    fontWeight: 700,
                    fontSize: 8.5,
                  }}>
                    {alert.operator_verdict === 'verified' ? '✓ VERIFIED' : '✗ FALSE ALARM'}
                  </span>
                ) : (
                  <>
                    <button
                      onClick={async (e) => {
                        e.stopPropagation();
                        try {
                          await fetch(`http://localhost:8000/api/alerts/${alert.id}/verdict`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ verdict: 'verified' }),
                          });
                          setAlerts(prev => prev.map(a => a.id === alert.id ? { ...a, operator_verdict: 'verified' } : a));
                        } catch (err) {
                          console.error('Failed to submit verdict:', err);
                        }
                      }}
                      title="Mark as Verified True Positive"
                      style={{
                        background: 'rgba(16,185,129,0.1)',
                        border: '1px solid rgba(16,185,129,0.3)',
                        color: '#10b981',
                        borderRadius: 3,
                        padding: '2px 5px',
                        fontSize: 8.5,
                        cursor: 'pointer',
                        fontWeight: 700,
                      }}
                    >
                      👍 TP
                    </button>
                    <button
                      onClick={async (e) => {
                        e.stopPropagation();
                        try {
                          await fetch(`http://localhost:8000/api/alerts/${alert.id}/verdict`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ verdict: 'false_alarm' }),
                          });
                          setAlerts(prev => prev.map(a => a.id === alert.id ? { ...a, operator_verdict: 'false_alarm' } : a));
                        } catch (err) {
                          console.error('Failed to submit verdict:', err);
                        }
                      }}
                      title="Mark as False Positive (False Alarm)"
                      style={{
                        background: 'rgba(239,68,68,0.1)',
                        border: '1px solid rgba(239,68,68,0.3)',
                        color: '#ef4444',
                        borderRadius: 3,
                        padding: '2px 5px',
                        fontSize: 8.5,
                        cursor: 'pointer',
                        fontWeight: 700,
                      }}
                    >
                      👎 FP
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Bottom: Trust + Inspect */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 6 }}>
              <div style={{ display: 'flex', flex: 1, flexDirection: 'column', gap: 3, marginRight: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 9, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', letterSpacing: '0.06em' }}>
                    TRUST SCORE
                  </span>
                  <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: cfg.color, fontWeight: 700 }}>
                    {alert.trust_score ?? '—'}/100
                  </span>
                </div>
                <div style={{ height: 2, background: 'rgba(255,255,255,0.06)', borderRadius: 1, overflow: 'hidden' }}>
                  <div style={{
                    height: '100%',
                    width: `${alert.trust_score || 0}%`,
                    background: `linear-gradient(90deg, ${cfg.color}80, ${cfg.color})`,
                    borderRadius: 1,
                    transition: 'width 0.5s ease',
                  }} />
                </div>
              </div>

              {onSelectDevice && (
                <button
                  onClick={() => onSelectDevice({ id: alert.camera_id, city: alert.city, ip: alert.camera_id })}
                  style={{
                    background: 'rgba(59,130,246,0.12)',
                    border: '1px solid rgba(59,130,246,0.3)',
                    color: '#60a5fa',
                    borderRadius: 4,
                    padding: '4px 10px',
                    fontSize: 9.5,
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 700,
                    cursor: 'pointer',
                    letterSpacing: '0.05em',
                    flexShrink: 0,
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.background = 'rgba(59,130,246,0.22)';
                    e.currentTarget.style.borderColor = 'rgba(59,130,246,0.6)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.background = 'rgba(59,130,246,0.12)';
                    e.currentTarget.style.borderColor = 'rgba(59,130,246,0.3)';
                  }}
                >
                  INSPECT →
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
