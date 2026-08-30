import { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://localhost:8000';

// ─── Color constants ─────────────────────────────────────────────────────────
const COLORS = {
  high:   '#10b981',
  medium: '#f59e0b',
  low:    '#f97316',
  critical: '#ef4444',
  blue:   '#3b82f6',
  purple: '#8b5cf6',
  teal:   '#14b8a6',
  muted:  '#64748b',
};

// ─── Mini SVG Bar ─────────────────────────────────────────────────────────────
function Bar({ value, max, color, label }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div style={{ marginBottom: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
        <span style={{ fontSize: '11px', color: '#94a3b8', fontFamily: 'var(--font-mono)' }}>{label}</span>
        <span style={{ fontSize: '11px', color, fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{value}</span>
      </div>
      <div style={{ height: '4px', background: '#1e293b', borderRadius: '2px', overflow: 'hidden' }}>
        <div style={{
          width: `${pct}%`, height: '100%',
          background: color,
          borderRadius: '2px',
          transition: 'width 0.5s ease',
        }} />
      </div>
    </div>
  );
}

// ─── Trust Histogram ─────────────────────────────────────────────────────────
function TrustHistogram({ data }) {
  if (!data) return <div style={styles.placeholder}>No alert data yet.</div>;
  const { buckets, averages, total_alerts } = data;
  const maxBucket = Math.max(...Object.values(buckets || {}), 1);

  const barData = [
    { label: 'Critical (0–20)', value: buckets?.critical_low || 0, color: COLORS.critical },
    { label: 'Low (21–49)',     value: buckets?.low || 0,          color: COLORS.low },
    { label: 'Medium (50–79)', value: buckets?.medium || 0,        color: COLORS.medium },
    { label: 'High (80–100)',  value: buckets?.high || 0,          color: COLORS.high },
  ];

  return (
    <div>
      <div style={styles.metaRow}>
        <span style={styles.metaLabel}>Total alerts (24h)</span>
        <span style={{ ...styles.metaBadge, background: '#1e3a5f', color: COLORS.blue }}>{total_alerts}</span>
      </div>
      <div style={{ marginBottom: '16px' }}>
        {barData.map(b => (
          <Bar key={b.label} label={b.label} value={b.value} max={maxBucket} color={b.color} />
        ))}
      </div>
      <div style={styles.divider} />
      <p style={{ ...styles.label, marginBottom: '8px' }}>Average scores (last 24h)</p>
      <div style={styles.scoreGrid}>
        {[
          { label: 'Weighted Avg', val: averages?.wa, color: COLORS.blue },
          { label: 'Bayesian', val: averages?.probabilistic, color: COLORS.purple },
          { label: 'Decayed', val: averages?.decayed, color: COLORS.teal },
        ].map(s => (
          <div key={s.label} style={styles.scoreCard}>
            <div style={{ fontSize: '22px', fontWeight: 700, color: s.color, fontFamily: 'var(--font-mono)' }}>
              {s.val !== null && s.val !== undefined ? s.val : '—'}
            </div>
            <div style={{ fontSize: '9px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Threat Timeline ─────────────────────────────────────────────────────────
function ThreatTimeline({ data }) {
  if (!data || !data.timeline || data.timeline.length === 0)
    return <div style={styles.placeholder}>No timeline data yet.</div>;

  const { timeline, total_alerts } = data;
  const maxCount = Math.max(...timeline.map(t => t.count), 1);
  const chartH = 80;

  return (
    <div>
      <div style={styles.metaRow}>
        <span style={styles.metaLabel}>Alerts in window</span>
        <span style={{ ...styles.metaBadge, background: '#1e3a5f', color: COLORS.blue }}>{total_alerts}</span>
      </div>
      {/* SVG Stacked Bar Chart */}
      <svg viewBox={`0 0 ${timeline.length * 12} ${chartH + 20}`} style={{ width: '100%', height: `${chartH + 20}px`, overflow: 'visible' }}>
        {timeline.map((t, i) => {
          const barH = maxCount > 0 ? (t.count / maxCount) * chartH : 0;
          const highH = maxCount > 0 ? (t.high_trust / maxCount) * chartH : 0;
          const medH  = maxCount > 0 ? (t.medium_trust / maxCount) * chartH : 0;
          const lowH  = maxCount > 0 ? (t.low_trust / maxCount) * chartH : 0;
          const x = i * 12 + 2;
          let yOff = chartH;
          const segs = [
            { h: highH, color: COLORS.high },
            { h: medH, color: COLORS.medium },
            { h: lowH + (barH - highH - medH - lowH), color: COLORS.low },
          ];
          return (
            <g key={i}>
              {segs.map((seg, si) => {
                if (seg.h <= 0) return null;
                yOff -= seg.h;
                return (
                  <rect key={si} x={x} y={yOff} width={8} height={seg.h}
                    fill={seg.color} rx={1} opacity={0.85} />
                );
              })}
              {i % 4 === 0 && (
                <text x={x + 4} y={chartH + 14} fontSize={7} fill="#64748b" textAnchor="middle">
                  {t.hour}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      {/* Legend */}
      <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
        {[['High Trust', COLORS.high], ['Medium', COLORS.medium], ['Low Trust', COLORS.low]].map(([l, c]) => (
          <div key={l} style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: '#94a3b8' }}>
            <div style={{ width: 8, height: 8, background: c, borderRadius: 2 }} />
            {l}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Audit Chain Tab ─────────────────────────────────────────────────────────
function AuditChain({ data, onVerify, verifyResult }) {
  if (!data) return <div style={styles.placeholder}>Loading audit chain...</div>;

  const { entries = [], chain_length, head_hash } = data;
  const isValid = verifyResult?.valid;

  return (
    <div>
      {/* Header bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: verifyResult === null ? COLORS.muted : isValid ? COLORS.high : COLORS.critical,
            boxShadow: `0 0 6px ${verifyResult === null ? COLORS.muted : isValid ? COLORS.high : COLORS.critical}`,
          }} />
          <span style={{ fontSize: '11px', color: '#94a3b8', fontFamily: 'var(--font-mono)' }}>
            {verifyResult === null ? 'Not verified' : isValid ? 'Chain VALID ✓' : 'TAMPERED ✗'}
          </span>
        </div>
        <button onClick={onVerify} style={styles.verifyBtn}>
          Verify Integrity
        </button>
      </div>

      <div style={styles.metaRow}>
        <span style={styles.metaLabel}>Chain length</span>
        <span style={{ ...styles.metaBadge, background: '#1a2a1a', color: COLORS.high }}>{chain_length}</span>
      </div>
      <div style={{ marginBottom: '12px' }}>
        <span style={styles.metaLabel}>Head hash</span>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: '#64748b', marginTop: '4px', wordBreak: 'break-all' }}>
          {head_hash?.slice(0, 32)}…
        </div>
      </div>

      {/* Entries */}
      <div style={{ maxHeight: '240px', overflowY: 'auto' }}>
        {entries.length === 0 && <div style={styles.placeholder}>No audit entries yet. Submit a detection event first.</div>}
        {entries.map((e, i) => (
          <div key={e.sequence_id || i} style={styles.auditEntry}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ fontSize: '10px', color: COLORS.blue, fontFamily: 'var(--font-mono)' }}>#{e.sequence_id}</span>
              <span style={{
                fontSize: '9px', padding: '1px 6px', borderRadius: '3px',
                background: e.payload?.action_tier === 'high_trust' ? '#0a2e1a' : e.payload?.action_tier === 'medium_trust' ? '#2e1e00' : '#2e0a0a',
                color: e.payload?.action_tier === 'high_trust' ? COLORS.high : e.payload?.action_tier === 'medium_trust' ? COLORS.medium : COLORS.critical,
              }}>
                {e.payload?.action_tier?.replace('_', ' ').toUpperCase() || 'N/A'}
              </span>
            </div>
            <div style={{ fontSize: '9px', color: '#64748b', fontFamily: 'var(--font-mono)', marginBottom: '2px' }}>
              cam: {e.payload?.camera_id?.slice(0, 12)}… · score: {e.payload?.trust_score}
              {e.payload?.probabilistic_score != null && ` · prob: ${e.payload.probabilistic_score}`}
              {e.payload?.decayed_score != null && ` · decayed: ${e.payload.decayed_score}`}
            </div>
            <div style={{ fontSize: '8px', color: '#3b4a5a', fontFamily: 'var(--font-mono)' }}>
              {e.hash?.slice(0, 24)}…
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Decay Curve Tab ─────────────────────────────────────────────────────────
function DecayCurve() {
  const [decayData, setDecayData] = useState(null);
  const [baseScore, setBaseScore] = useState(80);
  const [halfLife, setHalfLife] = useState(48);

  useEffect(() => {
    fetch(`${API_BASE}/api/decay-preview?base_score=${baseScore}&half_life_hours=${halfLife}`)
      .then(r => r.json())
      .then(setDecayData)
      .catch(() => {});
  }, [baseScore, halfLife]);

  const series = decayData?.decay_series || [];
  const chartW = 280;
  const chartH = 100;
  const pts = series.map((p, i) => {
    const x = (i / Math.max(series.length - 1, 1)) * chartW;
    const y = chartH - (p.score / 100) * chartH;
    return `${x},${y}`;
  }).join(' ');

  return (
    <div>
      <p style={{ ...styles.label, marginBottom: '10px' }}>
        S(t) = S₀ · exp(−ln(2)/T½ · t) &nbsp;·&nbsp;
        <span style={{ color: '#64748b', fontSize: '10px' }}>Griffioen & Doerr (ACM CCS, 2020)</span>
      </p>
      <div style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
        <div>
          <label style={styles.sliderLabel}>Base Score: <b style={{ color: COLORS.blue }}>{baseScore}</b></label>
          <input type="range" min={0} max={100} value={baseScore}
            onChange={e => setBaseScore(Number(e.target.value))}
            style={styles.slider} />
        </div>
        <div>
          <label style={styles.sliderLabel}>Half-life: <b style={{ color: COLORS.purple }}>{halfLife}h</b></label>
          <input type="range" min={6} max={168} step={6} value={halfLife}
            onChange={e => setHalfLife(Number(e.target.value))}
            style={styles.slider} />
        </div>
      </div>
      <svg viewBox={`0 0 ${chartW} ${chartH + 20}`} style={{ width: '100%', height: `${chartH + 20}px` }}>
        {/* Grid lines */}
        {[0, 25, 50, 75, 100].map(v => (
          <line key={v} x1={0} x2={chartW} y1={chartH - v} y2={chartH - v}
            stroke="#1e293b" strokeWidth={1} strokeDasharray="3,3" />
        ))}
        {/* Tier bands */}
        <rect x={0} y={0} width={chartW} height={chartH * 0.2} fill={COLORS.high} opacity={0.04} />
        <rect x={0} y={chartH * 0.2} width={chartW} height={chartH * 0.3} fill={COLORS.medium} opacity={0.04} />
        {/* Decay curve */}
        {series.length > 1 && (
          <polyline points={pts} fill="none" stroke={COLORS.blue} strokeWidth={2} />
        )}
        {/* Current position dot */}
        {series.length > 0 && (
          <circle cx={0} cy={chartH - (baseScore)} r={4}
            fill={COLORS.blue} stroke="#0f1523" strokeWidth={2} />
        )}
        {/* Axis labels */}
        <text x={2} y={chartH + 14} fontSize={8} fill="#64748b">0h</text>
        <text x={chartW - 14} y={chartH + 14} fontSize={8} fill="#64748b">168h</text>
      </svg>
      {/* Score at key points */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px' }}>
        {[0, 48, 96, 168].map(h => {
          const pt = series.find(p => Math.abs(p.hour - h) < 7);
          return (
            <div key={h} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '14px', fontWeight: 700, color: COLORS.blue, fontFamily: 'var(--font-mono)' }}>
                {pt?.score ?? '—'}
              </div>
              <div style={{ fontSize: '9px', color: COLORS.muted }}>t={h}h</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Live Evaluation Tab (Luna 2018, ByteTrack 2022) ─────────────────────────
function LiveEvalTab({ evalData }) {
  if (!evalData || evalData.total_labelled === 0) {
    return (
      <div style={{ padding: '16px 0', textAlign: 'center', color: '#64748b', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
        No operator ground-truth verdicts recorded yet.
        <div style={{ marginTop: '8px', color: '#94a3b8', fontSize: '10px' }}>
          Click 👍 TP or 👎 FP on active alerts to build the live evaluation dataset.
        </div>
      </div>
    );
  }

  const cm = evalData.confusion_matrix || {};

  return (
    <div>
      <div style={styles.metaRow}>
        <span style={styles.metaLabel}>Operator-Labelled Events</span>
        <span style={{ ...styles.metaBadge, background: '#1e3a5f', color: COLORS.blue }}>{evalData.total_labelled}</span>
      </div>

      <div style={styles.scoreGrid}>
        {[
          { label: 'Precision', val: `${(evalData.precision * 100).toFixed(1)}%`, color: COLORS.high },
          { label: 'Recall', val: `${(evalData.recall * 100).toFixed(1)}%`, color: COLORS.blue },
          { label: 'F1-Score', val: `${(evalData.f1_score * 100).toFixed(1)}%`, color: COLORS.purple },
          { label: 'Accuracy', val: `${(evalData.accuracy * 100).toFixed(1)}%`, color: COLORS.teal },
        ].map(s => (
          <div key={s.label} style={styles.scoreCard}>
            <div style={{ fontSize: '18px', fontWeight: 700, color: s.color, fontFamily: 'var(--font-mono)' }}>
              {s.val}
            </div>
            <div style={{ fontSize: '9px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{s.label}</div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: '12px', padding: '8px', background: 'rgba(15, 23, 42, 0.6)', borderRadius: '6px', border: '1px solid #1e293b' }}>
        <div style={{ fontSize: '10px', color: '#94a3b8', fontFamily: 'var(--font-mono)', marginBottom: '6px' }}>2×2 CONFUSION MATRIX</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '9px', fontFamily: 'var(--font-mono)' }}>
          <div style={{ background: 'rgba(16,185,129,0.08)', padding: '4px 6px', borderRadius: '4px', border: '1px solid rgba(16,185,129,0.2)' }}>
            <span style={{ color: COLORS.high }}>TP: {cm.true_positive || 0}</span> (High Trust + Verified)
          </div>
          <div style={{ background: 'rgba(239,68,68,0.08)', padding: '4px 6px', borderRadius: '4px', border: '1px solid rgba(239,68,68,0.2)' }}>
            <span style={{ color: COLORS.critical }}>FP: {cm.false_positive || 0}</span> (High Trust + False Alarm)
          </div>
          <div style={{ background: 'rgba(245,158,11,0.08)', padding: '4px 6px', borderRadius: '4px', border: '1px solid rgba(245,158,11,0.2)' }}>
            <span style={{ color: COLORS.medium }}>FN: {cm.false_negative || 0}</span> (Filtered + Genuine)
          </div>
          <div style={{ background: 'rgba(59,130,246,0.08)', padding: '4px 6px', borderRadius: '4px', border: '1px solid rgba(59,130,246,0.2)' }}>
            <span style={{ color: COLORS.blue }}>TN: {cm.true_negative || 0}</span> (Filtered + False Alarm)
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main AnalyticsPanel ──────────────────────────────────────────────────────
const TABS = [
  { id: 'trust',  label: '📊 Trust',   title: 'Trust Score Distribution' },
  { id: 'threats', label: '📈 Threats', title: 'Alert Frequency Timeline' },
  { id: 'audit',  label: '🔐 Audit',   title: 'Merkle Hash-Chain Ledger' },
  { id: 'decay',  label: '⏳ Decay',   title: 'Trust Score Decay Model' },
  { id: 'eval',   label: '🎯 Eval',    title: 'Live Ground-Truth Evaluation' },
];

export default function AnalyticsPanel({ city, visible, onClose }) {
  const [activeTab, setActiveTab] = useState('trust');
  const [trustData, setTrustData] = useState(null);
  const [timelineData, setTimelineData] = useState(null);
  const [auditData, setAuditData] = useState(null);
  const [evalData, setEvalData] = useState(null);
  const [verifyResult, setVerifyResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const cityParam = city && city !== 'All India' ? `&city=${encodeURIComponent(city)}` : '';

  const fetchAll = useCallback(() => {
    setLoading(true);
    Promise.all([
      fetch(`${API_BASE}/api/analytics/trust-distribution?hours=24${cityParam}`).then(r => r.json()),
      fetch(`${API_BASE}/api/analytics/alert-timeline?hours=24${cityParam}`).then(r => r.json()),
      fetch(`${API_BASE}/api/audit/ledger?limit=20`).then(r => r.json()),
      fetch(`${API_BASE}/api/eval/live`).then(r => r.json()),
    ]).then(([trust, timeline, audit, evalD]) => {
      setTrustData(trust);
      setTimelineData(timeline);
      setAuditData(audit);
      setEvalData(evalD);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [cityParam]);

  useEffect(() => {
    if (!visible) return;
    let isCancelled = false;
    Promise.all([
      fetch(`${API_BASE}/api/analytics/trust-distribution?hours=24${cityParam}`).then(r => r.json()),
      fetch(`${API_BASE}/api/analytics/alert-timeline?hours=24${cityParam}`).then(r => r.json()),
      fetch(`${API_BASE}/api/audit/ledger?limit=20`).then(r => r.json()),
      fetch(`${API_BASE}/api/eval/live`).then(r => r.json()),
    ]).then(([trust, timeline, audit, evalD]) => {
      if (!isCancelled) {
        setTrustData(trust);
        setTimelineData(timeline);
        setAuditData(audit);
        setEvalData(evalD);
      }
    }).catch(() => {});

    const interval = setInterval(() => {
      fetchAll();
    }, 15000);
    return () => {
      isCancelled = true;
      clearInterval(interval);
    };
  }, [visible, cityParam, fetchAll]);

  const handleVerify = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/audit/verify`);
      const data = await res.json();
      setVerifyResult(data);
    } catch {
      setVerifyResult({ valid: false, message: 'Verification request failed.' });
    }
  };

  if (!visible) return null;

  const activeTabObj = TABS.find(t => t.id === activeTab);

  return (
    <div style={styles.overlay} id="analytics-panel">
      {/* Panel header */}
      <div style={styles.header}>
        <div>
          <div style={styles.headerTitle}>⬡ ANALYTICS ENGINE</div>
          <div style={styles.headerSub}>{activeTabObj?.title}</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {loading && <div style={styles.loadingDot} />}
          <button onClick={fetchAll} style={styles.iconBtn} title="Refresh">↻</button>
          <button onClick={onClose} style={styles.iconBtn} title="Close">✕</button>
        </div>
      </div>

      {/* Tabs */}
      <div style={styles.tabBar}>
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              ...styles.tab,
              ...(activeTab === tab.id ? styles.tabActive : {}),
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={styles.content}>
        {activeTab === 'trust'   && <TrustHistogram data={trustData} />}
        {activeTab === 'threats' && <ThreatTimeline data={timelineData} />}
        {activeTab === 'audit'   && <AuditChain data={auditData} onVerify={handleVerify} verifyResult={verifyResult} />}
        {activeTab === 'decay'   && <DecayCurve />}
        {activeTab === 'eval'    && <LiveEvalTab evalData={evalData} />}
      </div>

      {/* Footer citation */}
      <div style={styles.footer}>
        <span style={styles.citation}>
          {activeTab === 'trust' && 'Swami et al. (SCI-IoT 2025) · Ferraris et al. (J. Supercomputing, 2024)'}
          {activeTab === 'threats' && 'Rasal et al. (Springer LNNS, 2025) · Luna et al. (Sensors, 2018)'}
          {activeTab === 'audit' && 'BIoT Trust Assessment SLR (MDPI, 2026) · Zhang et al. (2020)'}
          {activeTab === 'decay' && 'Griffioen & Doerr (ACM CCS, 2020): T½ = 48h reinfection half-life'}
          {activeTab === 'eval' && 'Luna et al. (Sensors, 2018) · ByteTrack (ECCV 2022)'}
        </span>
      </div>
    </div>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────
const styles = {
  overlay: {
    position: 'fixed',
    bottom: '80px',
    right: '16px',
    width: '340px',
    background: 'rgba(8, 12, 17, 0.97)',
    border: '1px solid #1e2d40',
    borderRadius: '12px',
    zIndex: 2500,
    boxShadow: '0 0 40px rgba(59,130,246,0.12), 0 16px 48px rgba(0,0,0,0.6)',
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
    borderBottom: '1px solid #1a2535',
  },
  headerTitle: {
    fontSize: '11px',
    fontWeight: 700,
    letterSpacing: '0.12em',
    color: '#3b82f6',
    fontFamily: 'var(--font-mono)',
  },
  headerSub: {
    fontSize: '10px',
    color: '#64748b',
    marginTop: '2px',
  },
  tabBar: {
    display: 'flex',
    borderBottom: '1px solid #1a2535',
    padding: '0 8px',
  },
  tab: {
    flex: 1,
    padding: '8px 4px',
    fontSize: '11px',
    color: '#64748b',
    background: 'none',
    border: 'none',
    borderBottom: '2px solid transparent',
    cursor: 'pointer',
    transition: 'all 0.2s',
    fontFamily: 'var(--font-sans)',
    whiteSpace: 'nowrap',
  },
  tabActive: {
    color: '#e2e8f0',
    borderBottom: '2px solid #3b82f6',
    fontWeight: 600,
  },
  content: {
    padding: '14px 16px',
    overflowY: 'auto',
    maxHeight: '380px',
    flex: 1,
  },
  footer: {
    padding: '8px 16px',
    borderTop: '1px solid #0f1a27',
  },
  citation: {
    fontSize: '9px',
    color: '#3b4a5a',
    fontStyle: 'italic',
    fontFamily: 'var(--font-mono)',
    lineHeight: 1.4,
  },
  placeholder: {
    fontSize: '12px',
    color: '#475569',
    textAlign: 'center',
    padding: '32px 0',
    fontStyle: 'italic',
  },
  metaRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '10px',
  },
  metaLabel: {
    fontSize: '11px',
    color: '#64748b',
  },
  metaBadge: {
    fontSize: '11px',
    fontWeight: 700,
    padding: '2px 8px',
    borderRadius: '4px',
    fontFamily: 'var(--font-mono)',
  },
  divider: {
    height: '1px',
    background: '#1e293b',
    margin: '12px 0',
  },
  scoreGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: '8px',
  },
  scoreCard: {
    background: '#0f1523',
    border: '1px solid #1e2d40',
    borderRadius: '6px',
    padding: '10px 8px',
    textAlign: 'center',
  },
  label: {
    fontSize: '11px',
    color: '#64748b',
    fontFamily: 'var(--font-mono)',
  },
  sliderLabel: {
    fontSize: '10px',
    color: '#94a3b8',
    display: 'block',
    marginBottom: '4px',
  },
  slider: {
    width: '100%',
    height: '4px',
    accentColor: '#3b82f6',
  },
  auditEntry: {
    background: '#0a1018',
    border: '1px solid #1a2535',
    borderRadius: '6px',
    padding: '8px 10px',
    marginBottom: '6px',
  },
  verifyBtn: {
    fontSize: '10px',
    padding: '4px 10px',
    background: '#0f1e30',
    border: '1px solid #1e3a5f',
    borderRadius: '4px',
    color: '#3b82f6',
    cursor: 'pointer',
    fontFamily: 'var(--font-mono)',
    transition: 'all 0.2s',
  },
  iconBtn: {
    width: '24px',
    height: '24px',
    background: '#0f1523',
    border: '1px solid #1e293b',
    borderRadius: '4px',
    color: '#64748b',
    cursor: 'pointer',
    fontSize: '12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 0,
  },
  loadingDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: '#3b82f6',
    animation: 'pulse 1s infinite',
  },
};
