import { useState, useEffect, useRef } from 'react';
import { fetchNews, streamBrief } from '../utils/api';

export default function RiskBrief({ city, selected, onSelectNews, showNews, onClose }) {
  const [news, setNews] = useState([]);
  const [briefState, setBriefState] = useState({ text: '', riskLevel: 'PENDING', error: null });
  const [isStreaming, setIsStreaming] = useState(false);

  const streamAbortRef = useRef(null);

  useEffect(() => {
    fetchNews(city)
      .then(data => setNews(data.articles || []))
      .catch(console.error);
  }, [city]);

  useEffect(() => {
    if (selected && selected.type === 'device') {
      const device = selected.data;

      if (streamAbortRef.current) {
        streamAbortRef.current();
        streamAbortRef.current = null;
      }

      queueMicrotask(() => {
        setBriefState({ text: '', riskLevel: 'ANALYZING', error: null });
        setIsStreaming(true);
      });

      const req = {
        cluster_id: device.id || `${device.ip}_${city}`,
        city: city,
        area_description: `${city} urban zone`,
        device_count: 1,
        device_types: [device.device_type || 'Network Device'],
        manufacturers: [device.manufacturer || 'Unknown'],
        owner_types: { [device.owner_type || 'unknown']: 1 },
        nearby_news_headlines: [],
      };

      let isCancelled = false;
      streamAbortRef.current = () => { isCancelled = true; };

      streamBrief(req, {
        onChunk: (chunk) => {
          if (!isCancelled) setBriefState(prev => ({ ...prev, text: prev.text + chunk }));
        },
        onDone: (level) => {
          if (!isCancelled) {
            setBriefState(prev => ({ ...prev, riskLevel: level }));
            setIsStreaming(false);
          }
        },
        onError: (err) => {
          if (!isCancelled) {
            setBriefState(prev => ({ ...prev, error: err }));
            setIsStreaming(false);
          }
        }
      });
    }
  }, [selected, city]);

  const riskLevelColor = {
    CRITICAL: '#ef4444',
    HIGH:     '#f97316',
    MEDIUM:   '#eab308',
    LOW:      '#10b981',
    ANALYZING: '#3b82f6',
    PENDING:   '#4b5975',
  };

  const riskColor = riskLevelColor[briefState.riskLevel] || '#4b5975';

  const getSourceColor = (article) => {
    if (article.geo_confidence === 'manually_verified') return { color: '#34d399', bg: 'rgba(16,185,129,0.1)', border: 'rgba(16,185,129,0.25)' };
    return { color: '#60a5fa', bg: 'rgba(59,130,246,0.1)', border: 'rgba(59,130,246,0.25)' };
  };

  return (
    <section
      id="risk-brief-panel"
      style={{
        height: '100%',
        width: '320px',
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        background: 'rgba(8, 11, 17, 0.96)',
        backdropFilter: 'blur(16px)',
        border: '1px solid var(--border-color)',
        borderRadius: 8,
        overflow: 'hidden',
        boxShadow: '0 8px 32px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.04)',
      }}
    >
      {/* Amber gradient top accent */}
      <div style={{
        height: 2,
        background: 'linear-gradient(90deg, transparent, rgba(245,158,11,0.8) 30%, rgba(245,158,11,0.5) 70%, transparent)',
        flexShrink: 0,
      }} />

      {/* Panel Header */}
      <div style={{
        padding: '10px 14px',
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: 'rgba(255, 255, 255, 0.015)',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          <span style={{
            fontSize: 12,
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            color: '#f0f4f8',
            letterSpacing: '0.06em',
          }}>
            INTEL & RISK BRIEFS
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Live badge */}
          {isStreaming && (
            <span style={{
              display: 'flex', alignItems: 'center', gap: 4,
              fontSize: 9, fontFamily: 'var(--font-mono)', fontWeight: 700,
              color: '#3b82f6',
              background: 'rgba(59,130,246,0.12)',
              border: '1px solid rgba(59,130,246,0.3)',
              padding: '2px 6px', borderRadius: 3,
              letterSpacing: '0.06em',
            }}>
              <span style={{
                width: 5, height: 5, borderRadius: '50%',
                background: '#3b82f6',
                animation: 'pulse-dot 1s infinite',
                display: 'block',
              }} />
              ANALYZING
            </span>
          )}

          <span style={{
            fontSize: 9, fontFamily: 'var(--font-mono)', fontWeight: 600,
            color: '#60a5fa',
            background: 'rgba(59,130,246,0.08)',
            border: '1px solid rgba(59,130,246,0.2)',
            padding: '2px 7px', borderRadius: 3,
          }}>
            {news.length} ARTICLES
          </span>

          {onClose && (
            <button
              onClick={onClose}
              title="Minimize Intel Panel"
              style={{
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.08)',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: 12,
                padding: '2px 6px',
                borderRadius: 4,
                lineHeight: 1,
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'rgba(239,68,68,0.12)';
                e.currentTarget.style.borderColor = 'rgba(239,68,68,0.3)';
                e.currentTarget.style.color = '#ef4444';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)';
                e.currentTarget.style.color = 'var(--text-muted)';
              }}
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Panel Content */}
      <div style={{
        overflowY: 'auto',
        flex: 1,
        padding: '10px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
      }}>

        {/* Device AI Brief */}
        {selected?.type === 'device' && (
          <div style={{
            background: 'rgba(20, 28, 46, 0.7)',
            border: `1px solid ${riskColor}40`,
            borderLeft: `3px solid ${riskColor}`,
            borderRadius: 6,
            padding: '12px',
            boxShadow: `0 0 16px ${riskColor}10`,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <span style={{
                fontSize: 9,
                fontWeight: 800,
                fontFamily: 'var(--font-mono)',
                padding: '2px 8px',
                borderRadius: 3,
                background: `${riskColor}20`,
                color: riskColor,
                border: `1px solid ${riskColor}40`,
                letterSpacing: '0.08em',
              }}>
                {briefState.riskLevel} RISK
              </span>
              <span style={{ fontSize: 9, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', letterSpacing: '0.05em' }}>
                AI THREAT SYNTHESIS
              </span>
            </div>

            <div style={{
              fontSize: 10,
              fontWeight: 700,
              color: '#94a3b8',
              fontFamily: 'var(--font-mono)',
              marginBottom: 6,
              letterSpacing: '0.05em',
            }}>
              TARGET: <span style={{ color: riskColor }}>{selected.data.ip || selected.data.id}</span>
            </div>

            <div style={{
              fontSize: 11,
              color: '#cbd5e1',
              lineHeight: 1.65,
              fontFamily: 'var(--font-sans)',
            }}>
              {briefState.text || (isStreaming
                ? 'Synthesizing infrastructure risk brief via AI engine...'
                : 'No brief data generated.'
              )}
              {isStreaming && <span className="streaming-cursor" />}
            </div>
          </div>
        )}

        {/* OSINT Feed Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '2px 0',
        }}>
          <div style={{
            width: 3, height: 12, borderRadius: 2,
            background: 'linear-gradient(180deg, #3b82f6, transparent)',
            flexShrink: 0,
          }} />
          <span style={{
            fontSize: 10,
            fontWeight: 700,
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-secondary)',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
          }}>
            REGIONAL OSINT FEED ({city.toUpperCase()})
          </span>
        </div>

        {/* News Cards */}
        {news.map(article => {
          const sc = getSourceColor(article);
          return (
            <div
              key={article.id || article.url}
              onClick={() => onSelectNews(article)}
              style={{
                background: 'rgba(15, 22, 38, 0.6)',
                border: '1px solid var(--border-faint)',
                borderLeft: `3px solid ${sc.color}60`,
                borderRadius: 6,
                padding: '10px 12px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'rgba(25, 35, 58, 0.8)';
                e.currentTarget.style.transform = 'translateX(2px)';
                e.currentTarget.style.borderLeftColor = sc.color;
                e.currentTarget.style.boxShadow = `0 4px 16px rgba(0,0,0,0.4)`;
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'rgba(15, 22, 38, 0.6)';
                e.currentTarget.style.transform = 'translateX(0)';
                e.currentTarget.style.borderLeftColor = `${sc.color}60`;
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{
                  fontSize: 8.5,
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 700,
                  color: sc.color,
                  background: sc.bg,
                  border: `1px solid ${sc.border}`,
                  padding: '2px 7px',
                  borderRadius: 3,
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                }}>
                  {article.source || 'WIRE SOURCE'}
                </span>
                <span style={{ fontSize: 9, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {article.published_at || 'RECENT'}
                </span>
              </div>

              <h4 style={{
                fontSize: 11.5,
                fontWeight: 600,
                color: '#e2e8f0',
                margin: '0 0 5px 0',
                lineHeight: 1.45,
                fontFamily: 'var(--font-sans)',
              }}>
                {article.title}
              </h4>

              {article.description && (
                <p style={{
                  fontSize: 10.5,
                  color: '#64748b',
                  margin: 0,
                  lineHeight: 1.5,
                  fontFamily: 'var(--font-sans)',
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                }}>
                  {article.description}
                </p>
              )}
            </div>
          );
        })}

        {news.length === 0 && (
          <div style={{
            textAlign: 'center',
            padding: '20px',
            color: 'var(--text-muted)',
            fontSize: 11,
            fontFamily: 'var(--font-mono)',
          }}>
            No OSINT data for {city}
          </div>
        )}
      </div>
    </section>
  );
}
