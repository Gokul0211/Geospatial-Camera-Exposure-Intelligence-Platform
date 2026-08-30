import { useState, useEffect, useCallback } from 'react';
import SurveillanceMap from './components/SurveillanceMap';
import DetailPanel from './components/DetailPanel';
import RiskBrief from './components/RiskBrief';
import Navbar from './components/Navbar';
import StatsBar from './components/StatsBar';
import LiveAlerts from './components/LiveAlerts';
import AnalyticsPanel from './components/AnalyticsPanel';
import ErrorBoundary from './components/ErrorBoundary';
import './styles/globals.css';
import './App.css';

const CITIES = {
  Mumbai:    { lat: 19.0760, lon: 72.8777, zoom: 12 },
  Delhi:     { lat: 28.6139, lon: 77.2090, zoom: 12 },
  Bangalore: { lat: 12.9716, lon: 77.5946, zoom: 12 },
  Hyderabad: { lat: 17.3850, lon: 78.4867, zoom: 12 },
  Chennai:   { lat: 13.0827, lon: 80.2707, zoom: 12 },
  Kolkata:   { lat: 22.5726, lon: 88.3639, zoom: 12 },
  Pune:      { lat: 18.5204, lon: 73.8567, zoom: 12 },
  Ahmedabad: { lat: 23.0225, lon: 72.5714, zoom: 12 },
  'All India': { lat: 20.5937, lon: 78.9629, zoom: 5 },
};

// ── Boot Splash Component ─────────────────────────────────────────────────────
function BootSplash({ onDone }) {
  useEffect(() => {
    const timer = setTimeout(onDone, 3200);
    return () => clearTimeout(timer);
  }, [onDone]);

  return (
    <div className="boot-splash">
      {/* Radar logo */}
      <div className="boot-splash-logo">
        <div className="boot-splash-ring" />
        <div className="boot-splash-ring-outer" />
        <svg width="52" height="52" viewBox="0 0 40 40" fill="none">
          <circle cx="20" cy="20" r="16" stroke="rgba(0,229,255,0.4)" strokeWidth="1" fill="none" />
          <circle cx="20" cy="20" r="9"  stroke="rgba(0,229,255,0.3)" strokeWidth="1" fill="none" />
          <line x1="20" y1="4"  x2="20" y2="11" stroke="#00e5ff" strokeWidth="1.5" strokeLinecap="round" />
          <line x1="20" y1="29" x2="20" y2="36" stroke="#00e5ff" strokeWidth="1.5" strokeLinecap="round" />
          <line x1="4"  y1="20" x2="11" y2="20" stroke="#00e5ff" strokeWidth="1.5" strokeLinecap="round" />
          <line x1="29" y1="20" x2="36" y2="20" stroke="#00e5ff" strokeWidth="1.5" strokeLinecap="round" />
          <circle cx="20" cy="20" r="3.5" fill="#00e5ff" />
          <circle cx="20" cy="20" r="1.5" fill="#080b11" />
          <path d="M20 20 L27 13" stroke="rgba(0,229,255,0.7)" strokeWidth="1" strokeLinecap="round" />
        </svg>
      </div>

      <div className="boot-splash-title">COBRA-WATCH</div>
      <div className="boot-splash-subtitle">
        Cyber-Physical Surveillance Intelligence Engine
      </div>
      <div className="boot-splash-compliance">
        COBRA-WATCH PLATFORM · ADVANCED SURVEILLANCE ENGINE · DPDP ACT COMPLIANT
      </div>

      {/* Loading bar */}
      <div className="boot-splash-bar-track">
        <div className="boot-splash-bar-fill" />
      </div>
    </div>
  );
}

// ── Analytics Icon ────────────────────────────────────────────────────────────
function AnalyticsIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4"  />
      <line x1="6"  y1="20" x2="6"  y2="14" />
    </svg>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [splashDone, setSplashDone]         = useState(false);
  const [city, setCity]                     = useState('Mumbai');
  const [selected, setSelected]             = useState(null);
  const [showLinks, setShowLinks]           = useState(false);
  const [satelliteMode, setSatelliteMode]   = useState(false);
  const [orbitalAlerts, setOrbitalAlerts]   = useState([]);
  const [showAnalytics, setShowAnalytics]   = useState(false);
  const [showIntelPanel, setShowIntelPanel] = useState(false);
  const [showDevicePanel, setShowDevicePanel] = useState(false);

  const [layers, setLayers] = useState({
    devices: true,
    heatmap: false,
    news: true,
  });

  // Clear selected item when city changes
  useEffect(() => {
    queueMicrotask(() => {
      setSelected(null);
      setShowLinks(false);
    });
  }, [city]);

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        setSelected(null);
        setShowIntelPanel(false);
        setShowDevicePanel(false);
      }
      if (e.target.tagName === 'INPUT') return;
      const cityKeys = Object.keys(CITIES);
      if (e.key === '1' && cityKeys[0]) setCity(cityKeys[0]);
      if (e.key === '2' && cityKeys[1]) setCity(cityKeys[1]);
      if (e.key === '3' && cityKeys[2]) setCity(cityKeys[2]);
      if (e.key === 'h' || e.key === 'H') setLayers(prev => ({ ...prev, heatmap: !prev.heatmap }));
      if (e.key === 'n' || e.key === 'N') setLayers(prev => ({ ...prev, news: !prev.news }));
      if (e.key === 'd' || e.key === 'D') setLayers(prev => ({ ...prev, devices: !prev.devices }));
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const toggleLayer = useCallback((layer) => setLayers(prev => ({ ...prev, [layer]: !prev[layer] })), []);

  const handleSelectDevice = useCallback((device) => {
    setSelected({ type: 'device', data: device });
    setShowLinks(false);
    setShowDevicePanel(true);
    setShowIntelPanel(true);
  }, []);

  const handleSelectNews = useCallback((article) => {
    setSelected({ type: 'news', data: article });
    setShowIntelPanel(true);
  }, []);

  const handleSelectFeed = useCallback((feed) => {
    setSelected({ type: 'public_feed', data: feed });
    setShowDevicePanel(true);
  }, []);

  const handleSelectSatellite = useCallback((sat) => {
    setSelected({ type: 'satellite', data: sat });
    setShowLinks(false);
    setShowDevicePanel(true);
  }, []);

  const gridStyle = {
    display: 'grid',
    gridTemplateColumns: showIntelPanel && showDevicePanel
      ? '320px 1fr 360px'
      : showIntelPanel
      ? '320px 1fr'
      : showDevicePanel
      ? '1fr 360px'
      : '1fr',
    gap: '12px',
    padding: '12px',
    overflow: 'hidden',
    height: 'calc(100vh - var(--header-height) - var(--stats-height))',
    position: 'relative',
    transition: 'grid-template-columns 0.35s cubic-bezier(0.4, 0, 0.2, 1)',
  };

  return (
    <>
      {/* ── Boot Splash ── */}
      {!splashDone && <BootSplash onDone={() => setSplashDone(true)} />}

      {/* ── CRT Scanline Overlay ── */}
      <div className="scanline-overlay" aria-hidden="true" />

      <div className="dashboard-container" id="surveillance-watch-root">
        <Navbar
          selectedCity={city}
          onCityChange={setCity}
          layers={layers}
          onToggleLayer={toggleLayer}
          cities={Object.keys(CITIES)}
          satelliteMode={satelliteMode}
          onToggleSatellite={() => setSatelliteMode(prev => !prev)}
          showIntelPanel={showIntelPanel}
          onToggleIntelPanel={() => setShowIntelPanel(prev => !prev)}
          showDevicePanel={showDevicePanel}
          onToggleDevicePanel={() => setShowDevicePanel(prev => !prev)}
        />

        <div className="dashboard-content">
          <StatsBar city={city} orbitalAlerts={orbitalAlerts} />

          <main style={gridStyle} id="dashboard-main-view">
            {/* Left Panel: Intel & Risk Briefs */}
            {showIntelPanel && (
              <RiskBrief
                city={city}
                selected={selected}
                showNews={layers.news}
                onSelectNews={handleSelectNews}
                onClose={() => setShowIntelPanel(false)}
              />
            )}

            {/* Center: GIS Map */}
            <div style={{ position: 'relative', height: '100%', width: '100%', overflow: 'hidden', borderRadius: 8 }}>

              {/* Dock button — Intel Panel */}
              {!showIntelPanel && (
                <button
                  onClick={() => setShowIntelPanel(true)}
                  title="Expand Intel & Risk Briefs Panel"
                  className="dock-button dock-button-intel"
                  style={{ position: 'absolute', top: '12px', left: '12px', zIndex: 2000 }}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                  </svg>
                  INTEL BRIEF
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </button>
              )}

              {/* Dock button — Device Panel */}
              {!showDevicePanel && (
                <button
                  onClick={() => setShowDevicePanel(true)}
                  title="Expand Device Intelligence Panel"
                  className="dock-button dock-button-device"
                  style={{ position: 'absolute', top: '12px', right: '12px', zIndex: 2000 }}
                >
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                    <polyline points="15 18 9 12 15 6" />
                  </svg>
                  DEVICE INTEL
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                    <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
                  </svg>
                </button>
              )}

              <ErrorBoundary>
                <SurveillanceMap
                  city={city}
                  layers={layers}
                  selected={selected}
                  showLinks={showLinks}
                  satelliteMode={satelliteMode}
                  onSelectDevice={handleSelectDevice}
                  onSelectNews={handleSelectNews}
                  onSelectFeed={handleSelectFeed}
                  onOrbitalUpdate={setOrbitalAlerts}
                  onSelectSatellite={handleSelectSatellite}
                />
              </ErrorBoundary>
            </div>

            {/* Right Panel: Device Intelligence */}
            {showDevicePanel && (
              <DetailPanel
                selected={selected}
                city={city}
                showLinks={showLinks}
                onToggleLinks={() => setShowLinks(prev => !prev)}
                onClose={() => {
                  setShowDevicePanel(false);
                  setSelected(null);
                  setShowLinks(false);
                }}
              />
            )}
          </main>
        </div>

        <LiveAlerts onSelectDevice={handleSelectDevice} />

        <AnalyticsPanel
          city={city}
          visible={showAnalytics}
          onClose={() => setShowAnalytics(false)}
        />

        {/* Analytics FAB */}
        <button
          id="analytics-toggle-btn"
          onClick={() => setShowAnalytics(prev => !prev)}
          title="Toggle Analytics Panel"
          style={{
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            width: '46px',
            height: '46px',
            background: showAnalytics
              ? 'linear-gradient(135deg, rgba(59,130,246,0.3), rgba(59,130,246,0.15))'
              : 'rgba(8, 11, 17, 0.9)',
            border: `1px solid ${showAnalytics ? '#3b82f6' : 'rgba(255,255,255,0.1)'}`,
            borderRadius: '50%',
            zIndex: 3000,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: showAnalytics ? '#60a5fa' : '#4b5975',
            boxShadow: showAnalytics
              ? '0 0 20px rgba(59,130,246,0.4), 0 4px 16px rgba(0,0,0,0.6)'
              : '0 4px 16px rgba(0,0,0,0.5)',
            backdropFilter: 'blur(12px)',
          }}
        >
          <AnalyticsIcon active={showAnalytics} />
        </button>
      </div>
    </>
  );
}
