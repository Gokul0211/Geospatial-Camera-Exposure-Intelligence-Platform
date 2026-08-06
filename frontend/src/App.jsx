import { useState, useEffect } from 'react';
import SurveillanceMap from './components/SurveillanceMap';
import DetailPanel from './components/DetailPanel';
import RiskBrief from './components/RiskBrief';
import Navbar from './components/Navbar';
import StatsBar from './components/StatsBar';
import LiveAlerts from './components/LiveAlerts';
import ErrorBoundary from './components/ErrorBoundary';
import './styles/globals.css';
import './App.css'; // preserve friend's styling

const CITIES = {
  Mumbai:    { lat: 19.0760, lon: 72.8777, zoom: 12 },
  Delhi:     { lat: 28.6139, lon: 77.2090, zoom: 12 },
  Bangalore: { lat: 12.9716, lon: 77.5946, zoom: 12 },
};

export default function App() {
  const [city, setCity] = useState('Mumbai');
  const [selected, setSelected] = useState(null);  // { type: 'device'|'news', data: {} }
  const [showLinks, setShowLinks] = useState(false);
  const [satelliteMode, setSatelliteMode] = useState(false);
  const [orbitalAlerts, setOrbitalAlerts] = useState([]);
  const [layers, setLayers] = useState({
    devices: true,
    heatmap: false,
    news: true,
  });

  // Clear selected item when city changes — prevent stale panel data
  useEffect(() => {
    setSelected(null);
    setShowLinks(false);
  }, [city]);

  useEffect(() => {
    function handleKeyDown(e) {
      // Escape closes detail panel
      if (e.key === 'Escape') {
        setSelected(null);
      }
      // 1, 2, 3 switch cities (when not focused on an input)
      if (e.target.tagName === 'INPUT') return;
      const cityKeys = Object.keys(CITIES);
      if (e.key === '1' && cityKeys[0]) setCity(cityKeys[0]);
      if (e.key === '2' && cityKeys[1]) setCity(cityKeys[1]);
      if (e.key === '3' && cityKeys[2]) setCity(cityKeys[2]);
      // H toggles heatmap
      if (e.key === 'h' || e.key === 'H') setLayers(prev => ({ ...prev, heatmap: !prev.heatmap }));
      // N toggles news
      if (e.key === 'n' || e.key === 'N') setLayers(prev => ({ ...prev, news: !prev.news }));
      // D toggles devices
      if (e.key === 'd' || e.key === 'D') setLayers(prev => ({ ...prev, devices: !prev.devices }));
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const toggleLayer = (layer) => setLayers(prev => ({ ...prev, [layer]: !prev[layer] }));

  return (
    <div className="dashboard-container" id="surveillance-watch-root">
      <Navbar
        selectedCity={city}
        onCityChange={setCity}
        layers={layers}
        onToggleLayer={toggleLayer}
        cities={Object.keys(CITIES)}
        satelliteMode={satelliteMode}
        onToggleSatellite={() => setSatelliteMode(prev => !prev)}
      />
      
      <div className="dashboard-content">
        <StatsBar city={city} orbitalAlerts={orbitalAlerts} />
        
        <main className="main-grid" id="dashboard-main-view">
          <RiskBrief 
            city={city}
            selected={selected}
            showNews={layers.news}
            onSelectNews={(article) => setSelected({ type: 'news', data: article })}
          />
          
          <ErrorBoundary>
            <SurveillanceMap
              city={city}
              layers={layers}
              selected={selected}
              showLinks={showLinks}
              satelliteMode={satelliteMode}
              onSelectDevice={(device) => { setSelected({ type: 'device', data: device }); setShowLinks(false); }}
              onSelectNews={(article) => setSelected({ type: 'news', data: article })}
              onSelectFeed={(feed) => setSelected({ type: 'public_feed', data: feed })}
              onOrbitalUpdate={setOrbitalAlerts}
              onSelectSatellite={(sat) => { setSelected({ type: 'satellite', data: sat }); setShowLinks(false); }}
            />
          </ErrorBoundary>
          
          <DetailPanel
            selected={selected}
            city={city}
            showLinks={showLinks}
            onToggleLinks={() => setShowLinks(prev => !prev)}
            onClose={() => { setSelected(null); setShowLinks(false); }}
          />
        </main>
      </div>
      <LiveAlerts />
    </div>
  );
}
