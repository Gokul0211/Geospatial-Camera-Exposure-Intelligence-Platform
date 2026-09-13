import { useState } from 'react';

const API_BASE = 'http://localhost:8000';

const ATTACKS = [
  {
    id: 'replay-attack',
    label: 'Replay Attack',
    icon: '🔁',
    description: 'Re-send the exact same event twice — idempotency check should block the duplicate.',
  },
  {
    id: 'timestamp-skew',
    label: 'Timestamp Skew',
    icon: '⏱️',
    description: 'Backdate a detection event 10 minutes — freshness check should reject it.',
  },
  {
    id: 'rate-flood',
    label: 'Rate Flood',
    icon: '🌊',
    description: 'Fire 13 events at one camera instantly — per-camera rate limit should cap it at 10/min.',
  },
  {
    id: 'collusion-ring',
    label: 'Collusion Ring',
    icon: '🕸️',
    description: '4 cameras manufacture corroboration in a ring — graph detector should catch it even though no single pair looks suspicious alone.',
  },
];

function VerdictBadge({ defenseWorked }) {
  return (
    <span style={{
      fontSize: 10,
      fontWeight: 800,
      padding: '3px 10px',
      borderRadius: 12,
      fontFamily: 'JetBrains Mono, monospace',
      background: defenseWorked ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
      color: defenseWorked ? '#10b981' : '#ef4444',
      border: `1px solid ${defenseWorked ? '#10b981' : '#ef4444'}`,
    }}>
      {defenseWorked ? '✓ DEFENSE WORKED' : '✗ DEFENSE FAILED'}
    </span>
  );
}

function ResultDetail({ attackId, result }) {
  if (attackId === 'replay-attack') {
    return (
      <div style={styles.detailGrid}>
        <div>1st attempt: <span style={{ color: '#10b981' }}>200 OK</span> (alert created)</div>
        <div>2nd attempt: <span style={{ color: '#ef4444' }}>{result.second_attempt.status_code} {result.second_attempt.detail}</span></div>
      </div>
    );
  }
  if (attackId === 'timestamp-skew') {
    return (
      <div style={styles.detailGrid}>
        <div style={{ color: '#ef4444' }}>{result.attempt.status_code} — {result.attempt.detail}</div>
      </div>
    );
  }
  if (attackId === 'rate-flood') {
    return (
      <div style={styles.detailGrid}>
        <div>Allowed: <span style={{ color: '#10b981' }}>{result.allowed_count}</span> / Blocked: <span style={{ color: '#ef4444' }}>{result.blocked_count}</span></div>
        <div style={{ display: 'flex', gap: 3, marginTop: 4, flexWrap: 'wrap' }}>
          {result.attempts.map(a => (
            <span key={a.n} title={a.blocked ? `#${a.n} blocked (429)` : `#${a.n} allowed`} style={{
              width: 14, height: 14, borderRadius: 3,
              background: a.blocked ? 'rgba(239,68,68,0.6)' : 'rgba(16,185,129,0.6)',
              fontSize: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff',
            }}>{a.n}</span>
          ))}
        </div>
      </div>
    );
  }
  if (attackId === 'collusion-ring') {
    const cluster = result.graph_collusion_clusters?.[0];
    return (
      <div style={styles.detailGrid}>
        <div>Events fired: {result.events_fired} across {result.ring_cameras.length} cameras</div>
        <div>Pairwise velocity tracker flagged any edge: <span style={{ color: result.pairwise_velocity_tracker_flagged_any_edge ? '#f59e0b' : '#10b981' }}>{String(result.pairwise_velocity_tracker_flagged_any_edge)}</span></div>
        {cluster && (
          <div style={{ marginTop: 4, color: '#38bdf8' }}>
            Graph detector: {cluster.node_count} cameras, {cluster.edge_count} edges, density {(cluster.density * 100).toFixed(0)}% — cycle confirmed
          </div>
        )}
      </div>
    );
  }
  return null;
}

export default function AttackModePanel({ visible, onClose }) {
  const [results, setResults] = useState({});
  const [running, setRunning] = useState(null);
  const [error, setError] = useState(null);

  const runAttack = async (attackId) => {
    setRunning(attackId);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/simulate/${attackId}`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResults(prev => ({ ...prev, [attackId]: data }));
    } catch (e) {
      setError(`${attackId} failed to run: ${e.message}`);
    } finally {
      setRunning(null);
    }
  };

  const runAll = async () => {
    for (const attack of ATTACKS) {
      await runAttack(attack.id);
    }
  };

  const resetAll = async () => {
    try {
      await fetch(`${API_BASE}/api/simulate/reset`, { method: 'POST' });
      setResults({});
      setError(null);
    } catch (e) {
      setError(`Reset failed: ${e.message}`);
    }
  };

  if (!visible) return null;

  return (
    <div style={styles.overlay}>
      <div style={styles.header}>
        <div>
          <div style={styles.headerTitle}>🎯 ATTACK MODE</div>
          <div style={styles.headerSub}>Live red-team simulator — drives the real detection pipeline</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={runAll} style={styles.runAllBtn} disabled={running !== null}>
            {running ? '...' : '▶ RUN ALL'}
          </button>
          <button onClick={resetAll} style={styles.iconBtn} title="Reset simulator state">↻</button>
          <button onClick={onClose} style={styles.iconBtn} title="Close">✕</button>
        </div>
      </div>

      {error && <div style={styles.errorBanner}>{error}</div>}

      <div style={styles.content}>
        {ATTACKS.map(attack => {
          const result = results[attack.id];
          const isRunning = running === attack.id;
          return (
            <div key={attack.id} style={styles.attackCard}>
              <div style={styles.attackHeader}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 16 }}>{attack.icon}</span>
                  <span style={styles.attackLabel}>{attack.label}</span>
                </div>
                <button
                  onClick={() => runAttack(attack.id)}
                  disabled={isRunning}
                  style={styles.runBtn}
                >
                  {isRunning ? 'RUNNING...' : 'FIRE'}
                </button>
              </div>
              <div style={styles.attackDescription}>{attack.description}</div>
              {result && (
                <div style={styles.resultBox}>
                  <div style={{ marginBottom: 6 }}>
                    <VerdictBadge defenseWorked={result.defense_triggered} />
                  </div>
                  <ResultDetail attackId={attack.id} result={result} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div style={styles.footer}>
        <span style={styles.citation}>
          Every attack here exercises real backend code paths (routes/attack_simulator_router.py) — not a scripted animation.
        </span>
      </div>
    </div>
  );
}

const styles = {
  overlay: {
    position: 'fixed',
    bottom: '80px',
    right: '76px',
    width: '380px',
    maxHeight: '70vh',
    background: 'rgba(8, 12, 17, 0.97)',
    border: '1px solid #3d1f1f',
    borderRadius: '12px',
    zIndex: 2500,
    boxShadow: '0 0 40px rgba(239,68,68,0.12), 0 16px 48px rgba(0,0,0,0.6)',
    backdropFilter: 'blur(16px)',
    display: 'flex',
    flexDirection: 'column',
    fontFamily: 'var(--font-sans)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: '14px 16px 10px',
    borderBottom: '1px solid #2a1a1a',
  },
  headerTitle: {
    fontSize: '11px',
    fontWeight: 700,
    letterSpacing: '0.12em',
    color: '#ef4444',
    fontFamily: 'var(--font-mono)',
  },
  headerSub: {
    fontSize: '9px',
    color: '#64748b',
    marginTop: '2px',
    maxWidth: 220,
  },
  runAllBtn: {
    fontSize: '9px',
    padding: '5px 10px',
    background: 'rgba(239,68,68,0.15)',
    border: '1px solid #ef4444',
    borderRadius: '4px',
    color: '#f87171',
    cursor: 'pointer',
    fontFamily: 'var(--font-mono)',
    fontWeight: 700,
  },
  iconBtn: {
    width: '24px',
    height: '24px',
    background: '#1a1010',
    border: '1px solid #2a1a1a',
    borderRadius: '4px',
    color: '#64748b',
    cursor: 'pointer',
    fontSize: '12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 0,
  },
  errorBanner: {
    margin: '8px 16px 0',
    padding: '6px 10px',
    background: 'rgba(239,68,68,0.1)',
    border: '1px solid rgba(239,68,68,0.3)',
    borderRadius: '4px',
    color: '#f87171',
    fontSize: '10px',
    fontFamily: 'var(--font-mono)',
  },
  content: {
    padding: '12px 16px',
    overflowY: 'auto',
    flex: 1,
  },
  attackCard: {
    background: '#0f0a0a',
    border: '1px solid #241515',
    borderRadius: '8px',
    padding: '10px 12px',
    marginBottom: '10px',
  },
  attackHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  attackLabel: {
    fontSize: '12px',
    fontWeight: 700,
    color: '#f1f5f9',
  },
  runBtn: {
    fontSize: '9px',
    padding: '4px 10px',
    background: 'rgba(239,68,68,0.12)',
    border: '1px solid rgba(239,68,68,0.4)',
    borderRadius: '4px',
    color: '#fca5a5',
    cursor: 'pointer',
    fontFamily: 'var(--font-mono)',
    fontWeight: 700,
  },
  attackDescription: {
    fontSize: '10px',
    color: '#64748b',
    marginTop: '6px',
    lineHeight: 1.4,
  },
  resultBox: {
    marginTop: '10px',
    paddingTop: '10px',
    borderTop: '1px solid #1a1010',
  },
  detailGrid: {
    fontSize: '9.5px',
    color: '#94a3b8',
    fontFamily: 'var(--font-mono)',
    lineHeight: 1.6,
  },
  footer: {
    padding: '8px 16px',
    borderTop: '1px solid #1a1010',
  },
  citation: {
    fontSize: '9px',
    color: '#3b4a5a',
    fontStyle: 'italic',
    fontFamily: 'var(--font-mono)',
    lineHeight: 1.4,
  },
};
