/**
 * TrustScoreBadge — Premium redesign for COBRA-WATCH
 * Cyber-Physical Surveillance Intelligence Engine
 *
 * Props:
 *   tier     : 'high_trust' | 'medium_trust' | 'low_trust'
 *   score    : number (0–100)
 *   factors  : string[] (optional contributing factor names)
 *   compact  : bool — small dot+score mode for map overlays
 */

import { useEffect, useRef, useState } from 'react';

const TIER_CONFIG = {
  high_trust:   {
    color:  '#00e5ff',
    label:  'HIGH TRUST',
    bg:     'rgba(0, 229, 255, 0.06)',
    border: 'rgba(0, 229, 255, 0.25)',
    glow:   'rgba(0, 229, 255, 0.2)',
    grade:  'A',
  },
  medium_trust: {
    color:  '#f59e0b',
    label:  'MEDIUM TRUST',
    bg:     'rgba(245, 158, 11, 0.06)',
    border: 'rgba(245, 158, 11, 0.25)',
    glow:   'rgba(245, 158, 11, 0.2)',
    grade:  'C',
  },
  low_trust:    {
    color:  '#ef4444',
    label:  'LOW TRUST',
    bg:     'rgba(239, 68, 68, 0.06)',
    border: 'rgba(239, 68, 68, 0.3)',
    glow:   'rgba(239, 68, 68, 0.25)',
    grade:  'F',
  },
};

const FACTOR_LABELS = {
  unauthenticated_stream: { icon: '🔓', text: 'Unauthenticated stream' },
  unpatched_cve:          { icon: '⚠️', text: 'Known unpatched CVE' },
  unknown_owner:          { icon: '❓', text: 'Unknown owner' },
  outdated_firmware:      { icon: '🕹', text: 'Outdated firmware' },
  no_corroboration:       { icon: '📷', text: 'No corroboration' },
  corroborated:           { icon: '✅', text: 'Corroborated' },
};

// Animated counter
function useCountUp(target, duration = 600) {
  const [val, setVal] = useState(0);
  const frameRef = useRef(null);
  const startRef = useRef(null);

  useEffect(() => {
    const numTarget = Number(target) || 0;
    cancelAnimationFrame(frameRef.current);
    startRef.current = null;
    const startVal = 0;

    const step = (ts) => {
      if (!startRef.current) startRef.current = ts;
      const t = Math.min((ts - startRef.current) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setVal(Math.round(startVal + (numTarget - startVal) * eased));
      if (t < 1) frameRef.current = requestAnimationFrame(step);
    };
    frameRef.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frameRef.current);
  }, [target, duration]);

  return val;
}

// Circular SVG gauge
function CircleGauge({ score, color, size = 64 }) {
  const radius = (size - 8) / 2;
  const circ   = 2 * Math.PI * radius;
  const offset = circ - (score / 100) * circ;
  const animVal = useCountUp(score);

  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        {/* Track */}
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="5"
        />
        {/* Progress */}
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none"
          stroke={color}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          style={{
            transition: 'stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
            filter: `drop-shadow(0 0 4px ${color})`,
          }}
        />
      </svg>
      {/* Center score */}
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: size > 56 ? 14 : 11,
          fontWeight: 800,
          color,
          lineHeight: 1,
        }}>
          {animVal}
        </span>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 7,
          color: 'var(--text-muted)',
          letterSpacing: '0.05em',
        }}>
          /100
        </span>
      </div>
    </div>
  );
}

export default function TrustScoreBadge({ tier, score, factors = [], compact = false }) {
  const cfg = TIER_CONFIG[tier] || TIER_CONFIG.low_trust;
  const isLowTrust = tier === 'low_trust';

  // Compact mode: just a dot + score chip
  if (compact) {
    return (
      <div
        title={`Trust Score: ${score} · ${cfg.label}`}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          padding: '2px 7px',
          background: cfg.bg,
          border: `1px solid ${cfg.border}`,
          borderRadius: 3,
          fontSize: '0.6rem',
          fontFamily: 'var(--font-mono)',
          color: cfg.color,
          fontWeight: 700,
          letterSpacing: '0.05em',
          lineHeight: 1,
        }}
      >
        <span style={{
          width: 5, height: 5,
          borderRadius: '50%',
          background: cfg.color,
          boxShadow: `0 0 4px ${cfg.color}`,
          flexShrink: 0,
          display: 'block',
          animation: isLowTrust ? 'pulse-feed 1.2s infinite' : 'none',
        }} />
        {score}
      </div>
    );
  }

  return (
    <div style={{
      background: cfg.bg,
      border: `1px solid ${cfg.border}`,
      borderLeft: `3px solid ${cfg.color}`,
      borderRadius: 6,
      padding: '12px',
      marginBottom: 12,
      boxShadow: isLowTrust ? `0 0 20px ${cfg.glow}, inset 0 0 20px ${cfg.glow}` : 'none',
      animation: isLowTrust ? 'glow-border-pulse 2s ease-in-out infinite' : 'none',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Subtle shimmer background for low trust */}
      {isLowTrust && (
        <div style={{
          position: 'absolute', inset: 0,
          background: 'linear-gradient(90deg, transparent 0%, rgba(239,68,68,0.04) 50%, transparent 100%)',
          backgroundSize: '200% 100%',
          animation: 'shimmer 2s linear infinite',
          pointerEvents: 'none',
        }} />
      )}

      {/* Top row: gauge + label + grade */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10, position: 'relative' }}>
        <CircleGauge score={score} color={cfg.color} size={60} />

        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Tier label */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
            <span style={{
              width: 6, height: 6, borderRadius: '50%',
              background: cfg.color,
              boxShadow: `0 0 6px ${cfg.color}`,
              flexShrink: 0, display: 'block',
              animation: isLowTrust ? 'pulse-dot 1s infinite' : 'none',
            }} />
            <span style={{
              fontSize: '0.65rem',
              fontWeight: 800,
              color: cfg.color,
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              fontFamily: 'var(--font-mono)',
            }}>
              {cfg.label}
            </span>
          </div>

          {/* Linear bar */}
          <div style={{
            width: '100%', height: 4,
            background: 'rgba(255,255,255,0.05)',
            borderRadius: 2, overflow: 'hidden',
            marginBottom: 4,
          }}>
            <div style={{
              height: '100%',
              width: `${score}%`,
              background: `linear-gradient(90deg, ${cfg.color}60, ${cfg.color})`,
              borderRadius: 2,
              transition: 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
              boxShadow: `0 0 6px ${cfg.color}`,
            }} />
          </div>

          {/* Grade chip */}
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            background: `${cfg.color}15`,
            border: `1px solid ${cfg.border}`,
            borderRadius: 3,
            padding: '1px 7px',
            fontSize: '0.65rem',
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            color: cfg.color,
            letterSpacing: '0.06em',
          }}>
            GRADE {cfg.grade}
          </div>
        </div>
      </div>

      {/* Contributing factors */}
      {factors.length > 0 && (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 4,
          paddingTop: 8,
          borderTop: `1px solid ${cfg.border}`,
          position: 'relative',
        }}>
          <span style={{
            fontSize: 8.5, fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)', textTransform: 'uppercase',
            letterSpacing: '0.1em', marginBottom: 2,
          }}>
            CONTRIBUTING FACTORS
          </span>
          {factors.map(f => {
            const meta = FACTOR_LABELS[f] || { icon: '•', text: f };
            return (
              <div key={f} style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontSize: '0.65rem',
                color: 'var(--text-secondary)',
                fontFamily: 'var(--font-mono)',
              }}>
                <span style={{ fontSize: 10, flexShrink: 0 }}>{meta.icon}</span>
                <span>{meta.text}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
