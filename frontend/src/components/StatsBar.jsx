import { useState, useEffect } from 'react';
import { fetchStats } from '../utils/api';
import { getLegalBadge } from '../utils/legalFramework';
import { ORBITAL_ASSETS } from '../utils/satelliteData';

export default function StatsBar({ city, orbitalAlerts = [] }) {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetchStats(city)
      .then(setStats)
      .catch(console.error);
  }, [city]);

  const legal = getLegalBadge(city);

  // Pick the highest-priority alert (CRITICAL > HIGH > ELEVATED)
  const priority = { CRITICAL: 3, HIGH: 2, ELEVATED: 1 };
  const topAlert = orbitalAlerts.length
    ? orbitalAlerts.sort((a, b) => (priority[b.threat.level] || 0) - (priority[a.threat.level] || 0))[0]
    : null;

  return (
    <div style={{ flexShrink: 0 }}>
      {/* ── Orbital alert banner ── */}
      {topAlert && (
        <div
          id="orbital-alert-banner"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '5px 16px',
            background: topAlert.threat.bg,
            borderBottom: `1px solid ${topAlert.threat.color}55`,
            animation: topAlert.threat.level === 'CRITICAL' ? 'orbital-pulse 1.4s infinite' : 'none',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {/* Pulsing dot */}
            <div style={{
              width: 7, height: 7, borderRadius: '50%',
              background: topAlert.threat.color,
              boxShadow: `0 0 6px ${topAlert.threat.color}`,
              flexShrink: 0,
              animation: 'pulse-dot 1s infinite',
            }} />
            <span style={{
              fontFamily: 'IBM Plex Mono, monospace',
              fontSize: 11,
              fontWeight: 700,
              color: topAlert.threat.color,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
            }}>
              {topAlert.threat.label}
            </span>
            <span style={{
              fontFamily: 'IBM Plex Mono, monospace',
              fontSize: 10,
              color: 'var(--text-secondary)',
              letterSpacing: '0.04em',
            }}>
              {topAlert.sat.name} · {topAlert.sat.agency} · {topAlert.dist.toLocaleString()} km
            </span>
          </div>

          {/* Right-side satellite info chips */}
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {orbitalAlerts.map(({ sat, dist, threat }) => (
              <span key={sat.id} style={{
                fontFamily: 'IBM Plex Mono, monospace',
                fontSize: 9,
                padding: '2px 7px',
                borderRadius: 3,
                border: `1px solid ${threat.color}66`,
                color: threat.color,
                background: threat.bg,
                whiteSpace: 'nowrap',
              }}>
                {sat.flag} {sat.name} · {sat.resolution} · {dist.toLocaleString()} km
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Main stats row ── */}
      <section className="stats-bar" id="surveillance-stats-bar">
        <div className="stat-item">
          <span className="stat-label">Active Sensors</span>
          <span className="stat-value">{stats?.total_devices || '--'}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label" style={{ color: 'var(--color-critical)' }}>Govt/Telecom</span>
          <span className="stat-value" style={{ color: 'var(--color-critical)' }}>
            {stats ? `${stats.by_owner?.government || 0} / ${stats.by_owner?.telecom || 0}` : '--'}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Privacy Risk Score</span>
          <span className="stat-value" style={{ color: (stats?.surveillance_score?.devices_per_sq_km || 0) > 50 ? '#ff3366' : 'var(--color-medium)' }}>
            {Math.min(Math.round(stats?.surveillance_score?.devices_per_sq_km || 0), 100)}<span style={{fontSize: 12, color: 'var(--text-muted)'}}>/100</span>
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label" style={{ color: '#00e5ff' }}>Orbital Assets</span>
          <span className="stat-value" style={{ color: '#00e5ff' }}>{ORBITAL_ASSETS.length}</span>
        </div>

        {legal && (
          <div style={{ marginLeft: 'auto', flex: '0 0 auto' }}>
            <span
              id="legal-framework-badge"
              style={{
                fontFamily: 'IBM Plex Mono', fontSize: 10,
                color: legal.badgeColor,
                border: `1px solid ${legal.badgeColor}44`,
                padding: '4px 8px',
                borderRadius: 4,
                whiteSpace: 'nowrap',
              }}
              title={legal.detail}
            >
              {legal.badge}
            </span>
          </div>
        )}
      </section>
    </div>
  );
}


