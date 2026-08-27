import { useState, useEffect } from 'react';

// Inline COBRA-WATCH radar-eye SVG logo
function CobraLogo({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Outer ring */}
      <circle cx="20" cy="20" r="18" stroke="rgba(0,229,255,0.5)" strokeWidth="1" fill="none" />
      {/* Inner ring */}
      <circle cx="20" cy="20" r="11" stroke="rgba(0,229,255,0.35)" strokeWidth="1" fill="none" />
      {/* Cross hairs */}
      <line x1="20" y1="2"  x2="20" y2="9"  stroke="#00e5ff" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="20" y1="31" x2="20" y2="38" stroke="#00e5ff" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="2"  y1="20" x2="9"  y2="20" stroke="#00e5ff" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="31" y1="20" x2="38" y2="20" stroke="#00e5ff" strokeWidth="1.5" strokeLinecap="round" />
      {/* Center pupil */}
      <circle cx="20" cy="20" r="4" fill="#00e5ff" opacity="0.9" />
      <circle cx="20" cy="20" r="2" fill="#080b11" />
      {/* Sweep indicator */}
      <path d="M20 20 L29 11" stroke="rgba(0,229,255,0.6)" strokeWidth="1" strokeLinecap="round" />
    </svg>
  );
}

export default function Navbar({
  selectedCity,
  onCityChange,
  layers,
  onToggleLayer,
  cities,
  satelliteMode,
  onToggleSatellite,
  showIntelPanel,
  onToggleIntelPanel,
  showDevicePanel,
  onToggleDevicePanel,
}) {
  const [timeStr, setTimeStr] = useState('');
  const [colonVisible, setColonVisible] = useState(true);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const h = String(now.getHours()).padStart(2, '0');
      const m = String(now.getMinutes()).padStart(2, '0');
      const s = String(now.getSeconds()).padStart(2, '0');
      setTimeStr(`${h}:${m}:${s}`);
      setColonVisible(prev => !prev);
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const layerBtn = (id, label, icon, layer, activeColor, activeBg, activeBorder) => (
    <button
      id={id}
      onClick={() => onToggleLayer(layer)}
      title={`Toggle ${label}`}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 5,
        padding: '5px 11px',
        background: layers[layer] ? activeBg : 'rgba(255,255,255,0.03)',
        border: layers[layer] ? `1px solid ${activeBorder}` : '1px solid rgba(255,255,255,0.09)',
        color: layers[layer] ? activeColor : 'var(--text-muted)',
        borderRadius: 5,
        cursor: 'pointer',
        fontSize: 11,
        fontFamily: 'var(--font-mono)',
        fontWeight: 700,
        letterSpacing: '0.04em',
        transition: 'all 0.2s ease',
        boxShadow: layers[layer] ? `0 0 10px ${activeBorder}` : 'none',
      }}
    >
      <span>{icon}</span>
      <span>{label}</span>
      <span style={{
        fontSize: 9,
        opacity: 0.8,
        background: layers[layer] ? `${activeBorder}` : 'rgba(255,255,255,0.06)',
        padding: '1px 5px',
        borderRadius: 3,
        marginLeft: 1,
        color: layers[layer] ? activeColor : 'var(--text-dim)',
      }}>
        {layers[layer] ? 'ON' : 'OFF'}
      </span>
    </button>
  );

  return (
    <nav style={{
      height: 'var(--header-height)',
      background: 'var(--gradient-header)',
      borderBottom: '1px solid var(--border-color)',
      display: 'flex',
      alignItems: 'center',
      padding: '0 18px',
      gap: 14,
      flexShrink: 0,
      zIndex: 1000,
      position: 'relative',
    }}>
      {/* Gradient underline accent */}
      <div style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        height: '1px',
        background: 'linear-gradient(90deg, transparent 0%, rgba(0,229,255,0.4) 20%, rgba(59,130,246,0.6) 50%, rgba(0,229,255,0.4) 80%, transparent 100%)',
        pointerEvents: 'none',
      }} />

      {/* ── Brand ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ position: 'relative', animation: 'pulse-dot 3s infinite' }}>
          <CobraLogo size={32} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <span style={{
            fontFamily: 'var(--font-display)',
            fontSize: 15,
            fontWeight: 800,
            color: '#f0f4f8',
            letterSpacing: '0.12em',
            lineHeight: 1,
            textShadow: '0 0 20px rgba(0,229,255,0.3)',
          }}>
            COBRA-WATCH
          </span>
          <span style={{
            fontSize: 8,
            color: 'var(--color-cyber)',
            fontFamily: 'var(--font-mono)',
            letterSpacing: '0.12em',
            opacity: 0.75,
          }}>
            CYBER-PHYSICAL SURVEILLANCE ENGINE
          </span>
          <span style={{
            fontSize: 7.5,
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-sans)',
            letterSpacing: '0.06em',
            marginTop: 1,
            opacity: 0.65,
          }}>
            ENTERPRISE THREAT PLATFORM · v2.0
          </span>
        </div>
      </div>

      {/* Divider */}
      <div style={{ width: 1, height: 28, background: 'var(--border-color)', flexShrink: 0 }} />

      {/* ── Zone Selector ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{
          fontSize: 10,
          fontFamily: 'var(--font-mono)',
          color: 'var(--text-muted)',
          letterSpacing: '0.08em',
        }}>ZONE:</span>
        <select
          id="city-selector-dropdown"
          value={selectedCity}
          onChange={(e) => onCityChange(e.target.value)}
          className="city-select"
        >
          {(cities || ['Mumbai', 'Delhi', 'Bangalore']).map(c => (
            <option key={c} value={c} style={{ background: '#080b11', color: '#f0f4f8' }}>
              {c === 'All India' ? '🇮🇳 All India (National Overview)' : `📍 ${c}`}
            </option>
          ))}
        </select>
      </div>

      {/* ── System Status Telemetry ── */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '4px 12px',
        background: 'rgba(8,11,17,0.8)',
        borderRadius: 6,
        border: '1px solid rgba(255,255,255,0.06)',
        fontSize: 11,
        fontFamily: 'var(--font-mono)',
      }}>
        {/* Online dot */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: '#10b981',
            boxShadow: '0 0 6px #10b981, 0 0 12px rgba(16,185,129,0.5)',
            animation: 'pulse-dot 2s infinite',
            display: 'block',
          }} />
          <span style={{ color: '#10b981', fontWeight: 700, fontSize: 10 }}>ONLINE</span>
        </div>

        <span style={{ color: 'var(--border-color)' }}>│</span>

        {/* Clock */}
        <span style={{ color: '#f0f4f8', fontWeight: 600, letterSpacing: '0.06em' }}>
          ⏱&nbsp;{timeStr || '00:00:00'}&nbsp;IST
        </span>

        <span style={{ color: 'var(--border-color)' }}>│</span>

        {/* DEFCON badge */}
        <span style={{
          fontSize: 9,
          fontWeight: 800,
          color: '#f59e0b',
          background: 'rgba(245,158,11,0.1)',
          border: '1px solid rgba(245,158,11,0.35)',
          padding: '2px 7px',
          borderRadius: 3,
          letterSpacing: '0.06em',
          animation: 'neon-pulse 3s ease-in-out infinite',
        }}>
          DEFCON 3: ELEVATED
        </span>
      </div>

      {/* ── Controls ── */}
      <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>

        {/* SAT VIEW */}
        <button
          id="satellite-view-toggle"
          onClick={onToggleSatellite}
          title="Toggle Esri High-Resolution Satellite Basemap"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            padding: '5px 11px',
            background: satelliteMode ? 'rgba(249,115,22,0.15)' : 'rgba(255,255,255,0.03)',
            border: satelliteMode ? '1px solid rgba(249,115,22,0.6)' : '1px solid rgba(255,255,255,0.09)',
            color: satelliteMode ? '#fb923c' : 'var(--text-muted)',
            borderRadius: 5,
            cursor: 'pointer',
            fontSize: 11,
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            letterSpacing: '0.04em',
            transition: 'all 0.2s ease',
            boxShadow: satelliteMode ? '0 0 10px rgba(249,115,22,0.3)' : 'none',
          }}
        >
          🛰️ SAT
          <span style={{
            fontSize: 9,
            background: satelliteMode ? 'rgba(249,115,22,0.3)' : 'rgba(255,255,255,0.06)',
            padding: '1px 5px',
            borderRadius: 3,
            color: satelliteMode ? '#fb923c' : 'var(--text-dim)',
          }}>
            {satelliteMode ? 'ON' : 'OFF'}
          </span>
        </button>

        {layerBtn('layer-toggle-devices', 'CAMERAS', '📷', 'devices',
          '#34d399', 'rgba(16,185,129,0.12)', 'rgba(16,185,129,0.45)')}

        {layerBtn('layer-toggle-heatmap', 'HEATMAP', '🔥', 'heatmap',
          '#facc15', 'rgba(234,179,8,0.12)', 'rgba(234,179,8,0.45)')}

        {layerBtn('layer-toggle-news', 'OSINT', '📰', 'news',
          '#60a5fa', 'rgba(59,130,246,0.12)', 'rgba(59,130,246,0.45)')}
      </div>
    </nav>
  );
}
