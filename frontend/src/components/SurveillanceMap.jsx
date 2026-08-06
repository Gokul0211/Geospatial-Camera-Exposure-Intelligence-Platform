import { useEffect, useRef, useState } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.heat';
import 'leaflet/dist/leaflet.css';
import { createDeviceIcon, createNewsIcon } from '../utils/iconFactory';
import { fetchDevices, fetchNews, fetchHeatmap } from '../utils/api';
import { getFeedsForCity } from '../utils/publicFeeds';
import OrbitalTracker from './OrbitalTracker';

const CITY_CENTERS = {
  Mumbai:    [19.0760, 72.8777],
  Delhi:     [28.6139, 77.2090],
  Bangalore: [12.9716, 77.5946],
};

const TILE_URL      = 'https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png';
const TILE_ATTR     = '&copy; OpenStreetMap &copy; CARTO';
const SAT_TILE_URL  = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
const SAT_TILE_ATTR = 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community';

function MapLayers({ city, layers, selected, showLinks, onSelectDevice, onSelectNews, onSelectFeed, setLoading }) {
  const map = useMap();
  const deviceLayerRef = useRef(null);
  const heatLayerRef = useRef(null);
  const newsLayerRef = useRef(null);

  const [devicesData, setDevicesData] = useState(null);
  const linkLayerRef = useRef(null);
  const publicFeedLayerRef = useRef(null);

  // Re-center when city changes
  useEffect(() => {
    const center = CITY_CENTERS[city] || [20, 78];
    map.setView(center, 12, { animate: true, duration: 0.5 });
  }, [city, map]);

  // Fetch and render devices
  useEffect(() => {
    if (deviceLayerRef.current) {
      map.removeLayer(deviceLayerRef.current);
      deviceLayerRef.current = null;
    }
    if (!layers.devices) return;

    setLoading(true);
    fetchDevices(city)
      .then(geojson => {
        setDevicesData(geojson);
        const layer = L.geoJSON(geojson, {
          pointToLayer: (feature, latlng) => {
            return L.marker(latlng, {
              icon: createDeviceIcon(
                feature.properties.owner_type,
                feature.properties.device_type
              ),
            });
          },
          onEachFeature: (feature, layer) => {
            layer.on('click', () => onSelectDevice(feature.properties));
            layer.bindTooltip(
              `${feature.properties.ip} · ${feature.properties.manufacturer || 'Unknown'}`,
              {
                className: 'device-tooltip',
                direction: 'top',
                offset: [0, -6],
              }
            );
          }
        });
        layer.addTo(map);
        deviceLayerRef.current = layer;
      })
      .catch(err => console.error('[devices]', err))
      .finally(() => setLoading(false));

    return () => {
      if (deviceLayerRef.current) {
        map.removeLayer(deviceLayerRef.current);
        deviceLayerRef.current = null;
      }
    };
  }, [city, layers.devices]); // eslint-disable-line react-hooks/exhaustive-deps

  // Render Entity Link Graph (only when user clicks the Show Links button)
  useEffect(() => {
    if (linkLayerRef.current) {
      map.removeLayer(linkLayerRef.current);
      linkLayerRef.current = null;
    }
    if (!showLinks || !selected || selected.type !== 'device' || !devicesData) return;

    const sourceOrg = selected.data.org || selected.data.owner_org;
    const sourceCity = selected.data.city || city;  // keep within current city
    if (!sourceOrg) return;

    const sourceLat = selected.data.lat;
    const sourceLon = selected.data.lon;

    const linkedDevices = devicesData.features.filter(f => {
      const org = f.properties.org || f.properties.owner_org;
      const devCity = f.properties.city || city;
      return org === sourceOrg
        && devCity === sourceCity
        && (f.properties.lat !== sourceLat || f.properties.lon !== sourceLon);
    });

    if (linkedDevices.length === 0) return;

    const layer = L.layerGroup();
    linkedDevices.forEach(f => {
      const polyline = L.polyline(
        [[sourceLat, sourceLon], [f.properties.lat, f.properties.lon]],
        {
          color: '#e74c3c',
          weight: 1.5,
          opacity: 0.7,
          dashArray: '5, 10',
          className: 'animated-laser-line',
        }
      );
      polyline.addTo(layer);
    });

    layer.addTo(map);
    linkLayerRef.current = layer;

    return () => {
      if (linkLayerRef.current) {
        map.removeLayer(linkLayerRef.current);
        linkLayerRef.current = null;
      }
    };
  }, [selected, showLinks, devicesData, city, map]); // eslint-disable-line react-hooks/exhaustive-deps

  // Render public gov feed markers (cyan)
  useEffect(() => {
    if (publicFeedLayerRef.current) {
      map.removeLayer(publicFeedLayerRef.current);
      publicFeedLayerRef.current = null;
    }
    const feeds = getFeedsForCity(city);
    if (feeds.length === 0) return;

    const layer = L.layerGroup();
    feeds.forEach(feed => {
      const icon = L.divIcon({
        className: '',
        html: `<div style="
          width: 14px; height: 14px;
          background: #00e5ff;
          border: 2px solid #fff;
          border-radius: 50%;
          box-shadow: 0 0 8px #00e5ff, 0 0 16px #00e5ff88;
          animation: pulse-feed 1.5s infinite;
        "></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      });
      const marker = L.marker([feed.lat, feed.lon], { icon, zIndexOffset: 500 });
      marker.on('click', () => onSelectFeed(feed));
      marker.bindTooltip(`📡 ${feed.label} · ${feed.authority}`, {
        direction: 'top', offset: [0, -10],
      });
      marker.addTo(layer);
    });

    layer.addTo(map);
    publicFeedLayerRef.current = layer;

    return () => {
      if (publicFeedLayerRef.current) {
        map.removeLayer(publicFeedLayerRef.current);
        publicFeedLayerRef.current = null;
      }
    };
  }, [city, map]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch and render heatmap
  useEffect(() => {
    if (heatLayerRef.current) {
      map.removeLayer(heatLayerRef.current);
      heatLayerRef.current = null;
    }
    if (!layers.heatmap) return;

    fetchHeatmap(city)
      .then(data => {
        const heat = L.heatLayer(data.points, {
          radius: 25,
          blur: 20,
          maxZoom: 17,
          gradient: { 0.2: '#2c3e50', 0.5: '#7d6608', 0.8: '#c0392b', 1.0: '#922b21' },
        });
        heat.addTo(map);
        heatLayerRef.current = heat;
      })
      .catch(err => console.error('[heatmap]', err));

    return () => {
      if (heatLayerRef.current) {
        map.removeLayer(heatLayerRef.current);
        heatLayerRef.current = null;
      }
    };
  }, [city, layers.heatmap, map]);

  // Fetch and render news pins
  useEffect(() => {
    if (newsLayerRef.current) {
      map.removeLayer(newsLayerRef.current);
      newsLayerRef.current = null;
    }
    if (!layers.news) return;

    fetchNews(city)
      .then(data => {
        const layer = L.layerGroup();
        (data.articles || []).forEach(article => {
          if (!article.lat || !article.lon) return;
          const isVerified = article.geo_confidence === 'manually_verified';
          const marker = L.marker([article.lat, article.lon], {
            icon: createNewsIcon(isVerified),
            zIndexOffset: isVerified ? 200 : 100,
          });
          marker.on('click', () => onSelectNews(article));
          marker.bindTooltip(
            article.title?.slice(0, 60) + '...',
            { direction: 'top', offset: [0, -8] }
          );
          marker.addTo(layer);
        });
        layer.addTo(map);
        newsLayerRef.current = layer;
      })
      .catch(err => console.error('[news]', err));

    return () => {
      if (newsLayerRef.current) {
        map.removeLayer(newsLayerRef.current);
        newsLayerRef.current = null;
      }
    };
  }, [city, layers.news, map]);

  return null;
}

export default function SurveillanceMap({ city, layers, selected, showLinks, satelliteMode, onSelectDevice, onSelectNews, onSelectFeed, onOrbitalUpdate, onSelectSatellite }) {
  const [loading, setLoading] = useState(false);

  return (
    <div style={{ flex: 1, position: 'relative' }}>
      {loading && (
        <div style={{
          position: 'absolute',
          top: 12,
          left: '50%',
          transform: 'translateX(-50%)',
          background: 'var(--bg-surface)',
          padding: '4px 12px',
          border: '1px solid var(--border)',
          color: 'var(--text-primary)',
          fontSize: 12,
          fontFamily: 'IBM Plex Mono',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
        }}>
          <span className="streaming-cursor" style={{ margin: 0 }}></span>
          SYNCHRONIZING ORBITAL DATA...
        </div>
      )}

      <MapContainer
        center={CITY_CENTERS[city] || [20, 78]}
        zoom={12}
        zoomControl={true}
        scrollWheelZoom={true}
        style={{ width: '100%', height: '100%', background: '#0a0a0a' }}
      >
        <TileLayer
          key={satelliteMode ? 'sat' : 'dark'}
          attribution={satelliteMode ? SAT_TILE_ATTR : TILE_ATTR}
          url={satelliteMode ? SAT_TILE_URL : TILE_URL}
          maxZoom={19}
        />
        
        <MapLayers
          city={city}
          layers={layers}
          selected={selected}
          showLinks={showLinks}
          onSelectDevice={onSelectDevice}
          onSelectNews={onSelectNews}
          onSelectFeed={onSelectFeed}
          setLoading={setLoading}
        />

        <OrbitalTracker
          city={city}
          onOrbitalUpdate={onOrbitalUpdate}
          onSelectSatellite={onSelectSatellite}
        />
      </MapContainer>
    </div>
  );
}
