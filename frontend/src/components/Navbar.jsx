import React from 'react';

export default function Navbar({ selectedCity, onCityChange, layers, onToggleLayer, cities, satelliteMode, onToggleSatellite }) {
  return (
    <nav style={{
      height: 44,
      background: 'var(--bg-surface)',
      borderBottom: '1px solid var(--border)',
      display: 'flex',
      alignItems: 'center',
      padding: '0 16px',
      gap: 24,
      flexShrink: 0,
    }}>
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{
          width: 6, height: 6, borderRadius: '50%',
          background: '#1e8449',
          display: 'inline-block',
          boxShadow: '0 0 4px #1e844966',
        }} />
        <span style={{
          fontFamily: 'IBM Plex Mono, monospace',
          fontSize: 13,
          fontWeight: 500,
          color: 'var(--text-primary)',
          letterSpacing: '0.05em',
        }}>
          SURVEILLANCEWATCH
        </span>
      </div>

      {/* City selector */}
      <div style={{ display: 'flex', gap: 2, marginLeft: 8 }}>
        {(cities || ['Mumbai', 'Delhi']).map(c => (
          <button
            key={c}
            id={`city-btn-${c.toLowerCase()}`}
            onClick={() => onCityChange(c)}
            style={{
              background: selectedCity === c ? 'var(--bg-elevated)' : 'transparent',
              border: selectedCity === c ? '1px solid var(--border)' : '1px solid transparent',
              color: selectedCity === c ? 'var(--text-primary)' : 'var(--text-muted)',
              padding: '3px 10px',
              cursor: 'pointer',
              fontSize: 12,
              fontFamily: 'DM Sans, sans-serif',
              borderRadius: 2,
              transition: 'all 0.15s ease',
            }}
          >
            {c}
          </button>
        ))}
      </div>

      {/* Layer toggles + SAT VIEW */}
      <div style={{ marginLeft: 'auto', display: 'flex', gap: 16, alignItems: 'center' }}>
        {/* SAT VIEW button */}
        <button
          id="satellite-view-toggle"
          onClick={onToggleSatellite}
          title="Toggle Esri satellite imagery basemap"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            padding: '3px 10px',
            background: satelliteMode ? 'rgba(255,153,51,0.15)' : 'transparent',
            border: satelliteMode ? '1px solid #FF9933' : '1px solid rgba(255,153,51,0.35)',
            color: satelliteMode ? '#FF9933' : 'rgba(255,153,51,0.6)',
            borderRadius: 3,
            cursor: 'pointer',
            fontSize: 11,
            fontFamily: 'IBM Plex Mono, monospace',
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            transition: 'all 0.2s',
            boxShadow: satelliteMode ? '0 0 8px rgba(255,153,51,0.3)' : 'none',
          }}
        >
          🛰 SAT VIEW
        </button>

        <div style={{ width: 1, height: 16, background: 'var(--border)', opacity: 0.5 }} />
        {Object.entries(layers).map(([key, active]) => (
          <label key={key} style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
            <input
              type="checkbox"
              id={`layer-toggle-${key}`}
              checked={active}
              onChange={() => onToggleLayer(key)}
              style={{ accentColor: 'var(--text-secondary)', cursor: 'pointer' }}
            />
            <span style={{
              fontSize: 11,
              fontFamily: 'IBM Plex Mono, monospace',
              color: active ? 'var(--text-secondary)' : 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
            }}>
              {key}
            </span>
            {/* Heatmap proportionality question — only shown when active */}
            {key === 'heatmap' && active && (
              <span style={{
                fontSize: 10,
                color: 'var(--text-muted)',
                fontFamily: 'DM Sans',
                fontStyle: 'italic',
                maxWidth: 200,
                marginLeft: 4,
              }}>
                Is surveillance distributed proportionally?
              </span>
            )}
          </label>
        ))}
      </div>
    </nav>
  );
}
