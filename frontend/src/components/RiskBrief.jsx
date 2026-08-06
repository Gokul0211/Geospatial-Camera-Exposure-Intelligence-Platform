import { useState, useEffect, useRef } from 'react';
import { fetchNews, streamBrief } from '../utils/api';

export default function RiskBrief({ city, selected, onSelectNews, showNews }) {
  const [news, setNews] = useState([]);
  const [briefState, setBriefState] = useState({ text: '', riskLevel: 'PENDING', error: null });
  const [isStreaming, setIsStreaming] = useState(false);
  
  // AbortController for cancelling streams when selection changes
  const streamAbortRef = useRef(null);

  // Fetch news when city changes
  useEffect(() => {
    fetchNews(city)
      .then(data => setNews(data.articles || []))
      .catch(console.error);
  }, [city]);

  // Handle selected device -> generate brief
  useEffect(() => {
    if (selected && selected.type === 'device') {
      const device = selected.data;
      
      // Cancel any ongoing stream
      if (streamAbortRef.current) {
        streamAbortRef.current();
        streamAbortRef.current = null;
      }

      setBriefState({ text: '', riskLevel: 'ANALYZING', error: null });
      setIsStreaming(true);

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

      // We don't have true AbortController on fetch in the api.js wrapper,
      // but we can flag it to ignore responses
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

  return (
    <section className="panel" id="risk-brief-panel" style={{ height: '100%', flex: '0 0 300px', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-header" style={{ borderBottom: '1px solid var(--border)', paddingBottom: 12 }}>
        <h2 className="panel-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '4px' }}>
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
          Risk Brief
        </h2>
        <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--color-info)' }}>
          {news.length} UPDATES
        </span>
      </div>

      <div className="panel-content risk-brief" style={{ overflowY: 'auto', flex: 1 }}>
        
        {/* Dynamic Risk Brief or Selected News */}
        {selected?.type === 'device' ? (
          <div className="risk-card" style={{ borderColor: 'var(--risk-medium)', backgroundColor: 'rgba(214, 137, 16, 0.05)', marginBottom: '16px' }}>
            <div className="risk-card-header">
              <span className="risk-badge" style={{ backgroundColor: `var(--risk-${briefState.riskLevel.toLowerCase()})`, color: '#fff' }}>
                {briefState.riskLevel}
              </span>
              <span className="mono" style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                {new Date().toLocaleTimeString()}
              </span>
            </div>
            <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '4px' }}>
              Infrastructure Assessment
            </h3>
            
            {briefState.error ? (
              <p style={{ color: 'var(--risk-critical)', fontSize: '0.78rem', marginTop: 8 }}>Error: {briefState.error}</p>
            ) : (
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '8px', lineHeight: '1.4', whiteSpace: 'pre-wrap' }}>
                {briefState.text}
                {isStreaming && <span className="streaming-cursor"></span>}
              </p>
            )}
          </div>
        ) : selected?.type === 'news' ? (
          <div className="risk-card" style={{ borderColor: 'var(--color-news)', backgroundColor: 'rgba(36, 113, 163, 0.08)', marginBottom: '16px' }}>
            <div className="risk-card-header">
              <span className="risk-badge" style={{ backgroundColor: 'rgba(36, 113, 163, 0.2)', color: 'var(--color-news)' }}>
                {selected.data.source || 'News'}
              </span>
              <span className="mono" style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                {selected.data.published_at}
              </span>
            </div>
            <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '4px' }}>
              <a href={selected.data.url} target="_blank" rel="noreferrer" style={{ color: 'inherit', textDecoration: 'none' }}>
                {selected.data.title}
              </a>
            </h3>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '8px', lineHeight: '1.4' }}>
              {selected.data.description || 'No summary available. Click title to read full article.'}
            </p>
          </div>
        ) : (
          <div style={{ padding: '8px 0 16px 0', borderBottom: '1px solid var(--border-subtle)', marginBottom: '16px', color: 'var(--text-muted)', fontSize: '0.78rem', textAlign: 'center' }}>
            Select a device on the map to generate a risk brief, or click a news marker.
          </div>
        )}

        {/* List of all news items for the active city */}
        {showNews && (
          <>
            <h3 style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em', marginBottom: '8px' }}>
              Regional Feed ({city})
            </h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {news.map((n) => {
            const isSelected = selected?.type === 'news' && n.id === selected.data.id;
            return (
              <div 
                key={n.id} 
                className="risk-card" 
                onClick={() => onSelectNews(n)}
                style={{ 
                  cursor: 'pointer',
                  borderColor: isSelected ? 'var(--color-news)' : 'var(--border-subtle)',
                  backgroundColor: isSelected ? 'rgba(36, 113, 163, 0.04)' : ''
                }}
              >
                <div className="risk-card-header">
                  <span className="risk-badge low" style={{ background: n.geo_confidence === 'manually_verified' ? '#1e844944' : '' }}>
                    {n.geo_confidence === 'manually_verified' ? 'Verified' : 'Auto-Geo'}
                  </span>
                  <span className="mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    {n.published_at}
                  </span>
                </div>
                <h4 style={{ fontSize: '0.8rem', fontWeight: 500, color: isSelected ? 'var(--color-news)' : 'var(--text-primary)' }}>
                  {n.title}
                </h4>
              </div>
            );
          })}
            </div>
          </>
        )}
      </div>
    </section>
  );
}
