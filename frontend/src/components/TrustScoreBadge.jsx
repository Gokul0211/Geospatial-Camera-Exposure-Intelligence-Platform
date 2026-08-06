import React from 'react';

/**
 * TrustScoreBadge
 * ================
 * Small colored indicator for camera trust score.
 * Color palette matches the existing dark UI conventions from DetailPanel/LiveAlerts:
 *   high_trust   → #00e5ff  (cyan — same as the "live" badge color)
 *   medium_trust → #f39c12  (amber — same as medium severity)
 *   low_trust    → #ff4444  (red   — same as confirmed-open warning)
 *
 * Props
 * -----
 * tier        : 'high_trust' | 'medium_trust' | 'low_trust'
 * score       : number (0–100)
 * factors     : string[] (contributing factor names, optional)
 * compact     : bool — if true, show only dot + score, no label (for map overlay use)
 */

const TIER_CONFIG = {
  high_trust:   { color: '#00e5ff', label: 'HIGH TRUST',   bg: 'rgba(0, 229, 255, 0.1)',   border: 'rgba(0, 229, 255, 0.35)' },
  medium_trust: { color: '#f39c12', label: 'MED TRUST',    bg: 'rgba(243, 156, 18, 0.1)',  border: 'rgba(243, 156, 18, 0.35)' },
  low_trust:    { color: '#ff4444', label: 'LOW TRUST',    bg: 'rgba(255, 68, 68, 0.1)',   border: 'rgba(255, 68, 68, 0.35)' },
};

const FACTOR_LABELS = {
  unauthenticated_stream: '🔓 Unauthenticated stream',
  unpatched_cve:          '⚠ Known unpatched CVE',
  unknown_owner:          '❓ Unknown owner',
  outdated_firmware:      '🕹 Outdated firmware',
  no_corroboration:       '📷 No corroboration',
  corroborated:           '✅ Corroborated',
};

export default function TrustScoreBadge({ tier, score, factors = [], compact = false }) {
  const cfg = TIER_CONFIG[tier] || TIER_CONFIG.low_trust;

  if (compact) {
    return (
      <div
        title={`Trust Score: ${score} (${tier?.replace('_', ' ')})`}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          padding: '2px 6px',
          background: cfg.bg,
          border: `1px solid ${cfg.border}`,
          borderRadius: 3,
          fontSize: '0.65rem',
          fontFamily: 'IBM Plex Mono, monospace',
          color: cfg.color,
          fontWeight: 700,
          letterSpacing: '0.04em',
          lineHeight: 1,
        }}
      >
        <span style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: cfg.color,
          flexShrink: 0,
          animation: tier === 'low_trust' ? 'pulse-feed 1s infinite' : 'none',
        }} />
        {score}
      </div>
    );
  }

  return (
    <div style={{
      background: cfg.bg,
      border: `1px solid ${cfg.border}`,
      borderRadius: 4,
      padding: '10px 12px',
      marginBottom: 12,
    }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{
            width: 7,
            height: 7,
            borderRadius: '50%',
            background: cfg.color,
            animation: tier === 'low_trust' ? 'pulse-feed 1s infinite' : 'none',
            flexShrink: 0,
          }} />
          <span style={{
            fontSize: '0.7rem',
            fontWeight: 800,
            color: cfg.color,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            fontFamily: 'IBM Plex Mono, monospace',
          }}>
            {cfg.label}
          </span>
        </div>

        {/* Numeric score gauge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{
            width: 60,
            height: 4,
            background: 'var(--bg-primary, #0a0a0a)',
            borderRadius: 2,
            overflow: 'hidden',
          }}>
            <div style={{
              height: '100%',
              width: `${score}%`,
              background: cfg.color,
              borderRadius: 2,
              transition: 'width 0.4s ease',
            }} />
          </div>
          <span style={{
            fontSize: '0.75rem',
            fontFamily: 'IBM Plex Mono, monospace',
            color: cfg.color,
            fontWeight: 700,
            minWidth: 28,
            textAlign: 'right',
          }}>
            {score}
          </span>
        </div>
      </div>

      {/* Contributing factors */}
      {factors.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {factors.map(f => (
            <div key={f} style={{
              fontSize: '0.68rem',
              color: 'var(--text-secondary, #8899aa)',
              fontFamily: 'IBM Plex Mono, monospace',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}>
              {FACTOR_LABELS[f] || f}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
