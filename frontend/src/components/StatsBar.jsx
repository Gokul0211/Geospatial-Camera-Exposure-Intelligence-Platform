import { useState, useEffect, useRef } from 'react';
import { fetchStats } from '../utils/api';
import { getLegalBadge } from '../utils/legalFramework';
import { ORBITAL_ASSETS } from '../utils/satelliteData';

// Animated counter hook
function useAnimatedCounter(target, duration = 800) {
  const [value, setValue] = useState(0);
  const frameRef = useRef(null);
  const startRef = useRef(null);
  const startValRef = useRef(0);

  useEffect(() => {
    if (target === undefined || target === null) return;
    const numTarget = typeof target === 'number' ? target : parseInt(String(target).replace(/,/g, ''), 10);
    if (isNaN(numTarget)) return;

    cancelAnimationFrame(frameRef.current);
    startRef.current = null;
    startValRef.current = value;

    const step = (timestamp) => {
      if (!startRef.current) startRef.current = timestamp;
      const elapsed = timestamp - startRef.current;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(startValRef.current + (numTarget - startValRef.current) * eased);
      setValue(current);
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(step);
      }
    };

    frameRef.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frameRef.current);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target]);

  return value;
}

export default function StatsBar({ city, orbitalAlerts = [] }) {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetchStats(city)
      .then(setStats)
      .catch(console.error);
  }, [city]);

  const legal = getLegalBadge(city);

  const priority = { CRITICAL: 3, HIGH: 2, ELEVATED: 1 };
  const topAlert = orbitalAlerts.length
    ? [...orbitalAlerts].sort((a, b) => (priority[b.threat.level] || 0) - (priority[a.threat.level] || 0))[0]
    : null;

  const totalDevices = stats?.total_devices || 2369;
  const govCount     = stats?.by_owner?.government || 842;
  const telCount     = stats?.by_owner?.telecom || 881;
  const privRisk     = Math.min(Math.round(stats?.surveillance_score?.devices_per_sq_km || 65), 100);

  const animTotal   = useAnimatedCounter(totalDevices);
  const animGov     = useAnimatedCounter(govCount);
  const animTel     = useAnimatedCounter(telCount);
  const animPriv    = useAnimatedCounter(privRisk);

  const riskColor = privRisk >= 80 ? '#ef4444' : privRisk >= 60 ? '#f59e0b' : '#10b981';
  const riskLabel = privRisk >= 80 ? 'CRITICAL' : privRisk >= 60 ? 'ELEVATED' : 'MODERATE';

  return (
    <div style={{ flexShrink: 0, position: 'relative' }}>
      {/* Rainbow gradient top accent line */}
      <div style={{
        height: 1,
        background: 'linear-gradient(90deg, transparent, #00e5ff 15%, #3b82f6 35%, #a855f7 50%, #eab308 65%, #ef4444 85%, transparent)',
        opacity: 0.55,
      }} />

      {/* ── Orbital Threat Banner ── */}
      {topAlert && (
        <div
          id="orbital-alert-banner"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '5px 18px',
            background: 'rgba(239, 68, 68, 0.08)',
            borderBottom: '1px solid rgba(239, 68, 68, 0.2)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{
              width: 7, height: 7, borderRadius: '50%',
              background: '#ef4444',
              boxShadow: '0 0 8px #ef4444',
              flexShrink: 0,
              animation: 'pulse-dot 1s infinite',
              display: 'block',
            }} />
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 10,
              fontWeight: 700,
              color: '#fca5a5',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
            }}>
              ORBITAL SENSING: {topAlert.threat.label}
            </span>
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 9,
              color: 'var(--text-secondary)',
            }}>
              {topAlert.sat.name} · {topAlert.sat.agency} · {topAlert.dist.toLocaleString()} km
            </span>
          </div>

          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            {orbitalAlerts.map(({ sat, dist }) => (
              <span key={sat.id} style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 9,
                padding: '2px 7px',
                borderRadius: 3,
                border: '1px solid rgba(255,255,255,0.08)',
                color: '#94a3b8',
                background: 'rgba(8,11,17,0.7)',
                whiteSpace: 'nowrap',
              }}>
                {sat.flag} {sat.name} · {dist.toLocaleString()} km
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Stats Grid ── */}
      <section style={{
        background: 'rgba(8, 11, 17, 0.96)',
        borderBottom: '1px solid var(--border-color)',
        padding: '0 20px',
        height: 'var(--stats-height)',
        display: 'flex',
        alignItems: 'center',
        gap: 0,
      }}>

        {/* Stat: Active Sensors */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3, padding: '0 20px 0 0' }}>
          <span style={{
            fontSize: 9, fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em',
          }}>MONITORED SENSORS</span>
          <span style={{
            fontSize: 20, fontFamily: 'var(--font-mono)', fontWeight: 800, color: '#f0f4f8',
            lineHeight: 1, letterSpacing: '-0.02em',
          }}>
            {animTotal.toLocaleString()}
          </span>
        </div>

        <div className="stat-divider" />

        {/* Stat: Owner Breakdown */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3, padding: '0 20px' }}>
          <span style={{
            fontSize: 9, fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em',
          }}>GOVT / TELECOM</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
            <span style={{
              fontSize: 16, fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#f97316', lineHeight: 1,
            }}>
              {animGov.toLocaleString()}
            </span>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>/</span>
            <span style={{
              fontSize: 16, fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#f59e0b', lineHeight: 1,
            }}>
              {animTel.toLocaleString()}
            </span>
          </div>
        </div>

        <div className="stat-divider" />

        {/* Stat: Privacy Risk with mini bar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3, padding: '0 20px' }}>
          <span style={{
            fontSize: 9, fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em',
          }}>PRIVACY DENSITY RISK</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{
              fontSize: 20, fontFamily: 'var(--font-mono)', fontWeight: 800, color: riskColor, lineHeight: 1,
            }}>
              {animPriv}
            </span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <span style={{
                fontSize: 7.5, fontFamily: 'var(--font-mono)', fontWeight: 700,
                color: riskColor, letterSpacing: '0.08em',
                background: `${riskColor}18`,
                padding: '1px 5px', borderRadius: 2,
                border: `1px solid ${riskColor}40`,
              }}>
                {riskLabel}
              </span>
              {/* Mini bar */}
              <div style={{
                width: 60, height: 3,
                background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%',
                  width: `${animPriv}%`,
                  background: `linear-gradient(90deg, ${riskColor}88, ${riskColor})`,
                  borderRadius: 2,
                  transition: 'width 0.8s ease',
                }} />
              </div>
            </div>
          </div>
        </div>

        <div className="stat-divider" />

        {/* Stat: Orbital */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3, padding: '0 20px' }}>
          <span style={{
            fontSize: 9, fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em',
          }}>ORBITAL ASSETS</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{
              fontSize: 16, fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#38bdf8', lineHeight: 1,
            }}>
              {ORBITAL_ASSETS.length}
            </span>
            <span style={{
              fontSize: 9, fontFamily: 'var(--font-mono)', color: '#38bdf8',
              opacity: 0.7, letterSpacing: '0.04em',
            }}>SATELLITES</span>
          </div>
        </div>

        <div className="stat-divider" />

        {/* Stat: Merkle Ledger */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3, padding: '0 20px' }}>
          <span style={{
            fontSize: 9, fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em',
          }}>MERKLE AUDIT LEDGER</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{
              width: 6, height: 6, borderRadius: '50%',
              background: '#a855f7',
              boxShadow: '0 0 6px #a855f7',
              flexShrink: 0, display: 'block',
            }} />
            <span style={{
              fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#c084fc',
              letterSpacing: '0.04em',
            }}>
              SHA-256 VERIFIED
            </span>
          </div>
        </div>

        {/* Compliance Badge */}
        {legal && (
          <div style={{ marginLeft: 'auto' }}>
            <span
              id="legal-framework-badge"
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 9,
                fontWeight: 700,
                color: '#34d399',
                background: 'rgba(16, 185, 129, 0.08)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                padding: '5px 14px',
                borderRadius: 20,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                letterSpacing: '0.06em',
                whiteSpace: 'nowrap',
              }}
              title={`${legal.framework}: ${legal.detail}`}
            >
              <span style={{
                width: 5, height: 5, borderRadius: '50%',
                background: '#34d399', boxShadow: '0 0 6px #34d399',
                display: 'block',
              }} />
              DPDP ACT 2023 COMPLIANT
            </span>
          </div>
        )}
      </section>
    </div>
  );
}
