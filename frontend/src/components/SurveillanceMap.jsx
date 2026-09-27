import { useEffect, useRef, useState, useMemo } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.heat';
import 'leaflet.markercluster';
import 'leaflet/dist/leaflet.css';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
import { createNewsIcon } from '../utils/iconFactory';
import { fetchDevices, fetchNews, fetchHeatmap } from '../utils/api';
import { getFeedsForCity } from '../utils/publicFeeds';
import OrbitalTracker from './OrbitalTracker';

/**
 * Debounce a fast-changing value (e.g. search input) so downstream work
 * (rebuilding the entire marker layer) only runs `delay`ms after the user
 * stops typing, instead of on every keystroke. Without this, typing a single
 * character tore down and rebuilt up to ~2,000 Leaflet markers per keypress.
 */
function useDebouncedValue(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

/**
 * Evenly sample `count` items out of `arr` (stride sampling, not just the
 * first N) so a reduced density slider still shows geographic spread instead
 * of an arbitrary array-order-biased subset. All underlying data stays in
 * `rawGeojson` / `filteredFeatures` — this only controls what gets mounted as
 * Leaflet layers, so dialing the density down never drops data, just render load.
 */
function sampleEvenly(arr, count) {
  // Defensive: `count` is derived from filteredFeatures.length * (pointDensity / 100)
  // via Math.ceil — guard against NaN/negative/non-finite ever reaching `new Array()`,
  // which throws RangeError: Invalid array length rather than just returning empty.
  const n = Number.isFinite(count) ? Math.floor(count) : 0;
  if (!Array.isArray(arr) || arr.length === 0) return [];
  if (n >= arr.length) return arr;
  if (n <= 0) return [];
  const step = arr.length / n;
  const result = new Array(n);
  for (let i = 0; i < n; i++) {
    result[i] = arr[Math.floor(i * step)];
  }
  return result;
}

const CITY_CENTERS = {
  Mumbai:      [19.0760, 72.8777, 12],
  Delhi:       [28.6139, 77.2090, 12],
  Bangalore:   [12.9716, 77.5946, 12],
  Hyderabad:   [17.3850, 78.4867, 12],
  Chennai:     [13.0827, 80.2707, 12],
  Kolkata:     [22.5726, 88.3639, 12],
  Pune:        [18.5204, 73.8567, 12],
  Ahmedabad:   [23.0225, 72.5714, 12],
  "All India": [20.5937, 78.9629, 5],
};

// CARTO's free anonymous basemap tiles now require an API key (policy change on
// their end — confirmed live: every {z}/{x}/{y} request returns HTTP 200 but the
// PNG content itself is a watermark reading "API KEY REQUIRED", not a real map
// tile). Switched to the standard OpenStreetMap tile server (genuinely free, no
// key, no signup) and approximate the dark theme with a CSS invert filter
// (applied to .leaflet-tile-pane in globals.css) rather than paying for a
// key-gated dark-styled provider.
const TILE_URL      = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const TILE_ATTR     = '&copy; OpenStreetMap contributors';
const SAT_TILE_URL  = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';
const SAT_TILE_ATTR = 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community';

const OWNER_CANVAS_COLORS = {
  government: { fill: '#ef4444', stroke: '#fee2e2' },
  telecom:    { fill: '#f97316', stroke: '#ffedd5' },
  commercial: { fill: '#eab308', stroke: '#fef9c3' },
  unknown:    { fill: '#3b82f6', stroke: '#dbeafe' },
};

function MapLayers({ city, layers, selected, showLinks, activeFilter, searchQuery, pointDensity, nlFilter, onSelectDevice, onSelectNews, onSelectFeed, setLoading, setTotalCount, setFilteredCount, setDisplayedCount }) {
  const map = useMap();
  const deviceLayerRef = useRef(null);
  const heatLayerRef = useRef(null);
  const newsLayerRef = useRef(null);

  const [rawGeojson, setRawGeojson] = useState(null);
  const linkLayerRef = useRef(null);
  const publicFeedLayerRef = useRef(null);

  // Re-center map when city changes
  useEffect(() => {
    const config = CITY_CENTERS[city] || [20, 78, 12];
    map.setView([config[0], config[1]], config[2], { animate: true, duration: 0.5 });
  }, [city, map]);

  // Fetch raw devices for the selected city or nationwide
  useEffect(() => {
    setLoading(true);
    fetchDevices(city)
      .then(geojson => {
        setRawGeojson(geojson);
        setTotalCount(geojson.features?.length || 0);
      })
      .catch(err => console.error('[devices]', err))
      .finally(() => setLoading(false));
  }, [city]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounce the search query — without this, every keystroke tore down and
  // rebuilt the entire marker layer (up to ~2,000 markers on "All India").
  const debouncedSearchQuery = useDebouncedValue(searchQuery, 300);

  // Filter geojson features in memory based on active filter criteria and search query
  const filteredFeatures = useMemo(() => {
    if (!rawGeojson || !rawGeojson.features) return [];

    return rawGeojson.features.filter(f => {
      const p = f.properties;
      const ownerType = (p.owner_type || '').toLowerCase();
      const ip = (p.ip || '').toLowerCase();
      const mfr = (p.manufacturer || '').toLowerCase();
      const org = (p.owner_org || '').toLowerCase();

      // 1. Category Filter Check
      if (activeFilter === 'OPEN_AUTH' && p.auth_required) return false;
      if (activeFilter === 'HIGH_RISK_CVE' && (!p.known_cve_count || p.known_cve_count === 0)) return false;
      if (activeFilter === 'GOVERNMENT' && ownerType !== 'government') return false;
      if (activeFilter === 'TELECOM' && ownerType !== 'telecom') return false;
      if (activeFilter === 'COMMERCIAL' && ownerType !== 'corporate' && ownerType !== 'commercial') return false;

      // 2. Text Search Query Check
      if (debouncedSearchQuery.trim() !== '') {
        const q = debouncedSearchQuery.toLowerCase().trim();
        const matchesIp = ip.includes(q);
        const matchesMfr = mfr.includes(q);
        const matchesOrg = org.includes(q);
        const matchesType = (p.device_type || '').toLowerCase().includes(q);
        if (!matchesIp && !matchesMfr && !matchesOrg && !matchesType) return false;
      }

      // 3. Natural-language query filter — orthogonal to the chip filter above
      // (both apply simultaneously), lets a single query express compound
      // conditions the single-select chips can't ("unauthenticated AND government").
      if (nlFilter) {
        if (nlFilter.auth_required === false && p.auth_required) return false;
        if (nlFilter.has_cve === true && (!p.known_cve_count || p.known_cve_count === 0)) return false;
        if (nlFilter.owner_type && ownerType !== nlFilter.owner_type) return false;
        if (nlFilter.search_text && nlFilter.search_text.trim() !== '') {
          const q = nlFilter.search_text.toLowerCase().trim();
          const matchesIp = ip.includes(q);
          const matchesMfr = mfr.includes(q);
          const matchesOrg = org.includes(q);
          const matchesType = (p.device_type || '').toLowerCase().includes(q);
          if (!matchesIp && !matchesMfr && !matchesOrg && !matchesType) return false;
        }
      }

      return true;
    });
  }, [rawGeojson, activeFilter, debouncedSearchQuery, nlFilter]);

  // Sync filtered count back to parent UI
  useEffect(() => {
    setFilteredCount(filteredFeatures.length);
  }, [filteredFeatures, setFilteredCount]);

  // Point-density control: ALL matched devices always stay in `rawGeojson`/
  // `filteredFeatures` (no data is ever dropped) — this only decides how many
  // get mounted as actual Leaflet layers, evenly sampled for geographic
  // spread. Lets a user with a slower machine dial down render load without
  // losing data, instead of a hardcoded ingestion cap.
  const displayedFeatures = useMemo(
    () => sampleEvenly(filteredFeatures, Math.ceil(filteredFeatures.length * (pointDensity / 100))),
    [filteredFeatures, pointDensity]
  );

  useEffect(() => {
    setDisplayedCount(displayedFeatures.length);
  }, [displayedFeatures, setDisplayedCount]);

  // Render displayed devices on Leaflet GPU Canvas, clustered so overlapping
  // points collapse into a single count badge instead of rendering thousands
  // of stacked circles — both a performance fix (chunkedLoading keeps marker
  // construction off the main thread) and a visual-accuracy fix (dense,
  // overlapping dots were themselves making the map look "fake"/noisy).
  useEffect(() => {
    if (deviceLayerRef.current) {
      map.removeLayer(deviceLayerRef.current);
      deviceLayerRef.current = null;
    }
    if (!layers.devices || displayedFeatures.length === 0) return;

    const canvasRenderer = L.canvas({ padding: 0.5 });
    const filteredGeojson = { type: 'FeatureCollection', features: displayedFeatures };

    const clusterGroup = L.markerClusterGroup({
      chunkedLoading: true,
      chunkDelay: 15,
      maxClusterRadius: 45,
      spiderfyOnMaxZoom: true,
      disableClusteringAtZoom: 17,
      iconCreateFunction: (cluster) => {
        const count = cluster.getChildCount();
        const size = count >= 100 ? 40 : count >= 25 ? 34 : 28;
        return L.divIcon({
          html: `<div style="
            width: ${size}px; height: ${size}px;
            display: flex; align-items: center; justify-content: center;
            background: rgba(15, 23, 42, 0.92);
            border: 2px solid #3b82f6;
            border-radius: 50%;
            color: #93c5fd;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            font-size: ${count >= 100 ? 11 : 10}px;
            box-shadow: 0 0 12px rgba(59,130,246,0.35);
          ">${count}</div>`,
          className: '',
          iconSize: [size, size],
        });
      },
    });

    const layer = L.geoJSON(filteredGeojson, {
      pointToLayer: (feature, latlng) => {
        const ownerType = (feature.properties.owner_type || 'unknown').toLowerCase();
        const colors = OWNER_CANVAS_COLORS[ownerType] || OWNER_CANVAS_COLORS.unknown;
        const isExposed = !feature.properties.auth_required;
        // Honest provenance styling: real (OSM-verified / live Shodan) locations
        // render as solid rings; simulated fallback locations render dimmer with
        // a dashed ring, so the map never silently implies more verified data
        // than actually exists.
        const isVerified = feature.properties.geo_source === 'osm_verified'
          || feature.properties.geo_source === 'shodan_live';

        return L.circleMarker(latlng, {
          renderer: canvasRenderer,
          radius: isExposed ? 5.5 : 4.5,
          fillColor: colors.fill,
          color: isVerified ? colors.stroke : '#475569',
          weight: isVerified ? 1.2 : 1,
          opacity: isVerified ? 0.9 : 0.55,
          fillOpacity: isVerified ? 0.85 : 0.45,
          dashArray: isVerified ? null : '2,2',
        });
      },
      onEachFeature: (feature, layer) => {
        const props = feature.properties;
        const ownerType = (props.owner_type || 'Unknown').toUpperCase();
        const mfr = props.manufacturer || 'Unknown Manufacturer';
        const ip = props.ip || 'Unknown IP';
        const authStatus = props.auth_required ? '🔒 AUTH REQUIRED' : '⚠️ OPEN / NO AUTH';
        const geoLabel = props.geo_source === 'osm_verified'
          ? '📍 OSM-verified location'
          : props.geo_source === 'shodan_live'
            ? '📍 Live Shodan geolocation'
            : '📍 Simulated location (demo fill)';

        layer.on('click', () => onSelectDevice(props));

        layer.bindTooltip(
          `<div style="font-family: 'JetBrains Mono', monospace; font-size: 11px; padding: 2px 4px;">
            <div style="font-weight: 700; color: #f8fafc;">${ip}</div>
            <div style="color: #94a3b8; font-size: 10px;">${mfr} · ${ownerType}</div>
            <div style="color: ${props.auth_required ? '#10b981' : '#ef4444'}; font-size: 9px; margin-top: 2px;">${authStatus}</div>
            <div style="color: #64748b; font-size: 8.5px; margin-top: 2px;">${geoLabel}</div>
          </div>`,
          {
            className: 'custom-leaflet-tooltip',
            direction: 'top',
            offset: [0, -6],
            sticky: true,
          }
        );

        layer.bindPopup(
          `<div style="font-family: 'Inter', sans-serif; padding: 10px; width: 230px; color: #f8fafc; background: #0f172a; border-radius: 6px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span style="font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 800; color: #38bdf8;">${ip}</span>
              <span style="font-size: 9px; font-weight: 800; padding: 2px 8px; border-radius: 4px; background: ${props.auth_required ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'}; color: ${props.auth_required ? '#34d399' : '#f87171'}; border: 1px solid ${props.auth_required ? '#10b981' : '#ef4444'};">
                ${props.auth_required ? 'AUTH REQUIRED' : '⚠️ OPEN'}
              </span>
            </div>
            <div style="font-size: 11px; color: #94a3b8; margin-bottom: 6px; line-height: 1.5;">
              <div><strong style="color: #cbd5e1;">Manufacturer:</strong> ${mfr}</div>
              <div><strong style="color: #cbd5e1;">Owner:</strong> <span style="color: #fb923c;">${ownerType}</span></div>
              <div><strong style="color: #cbd5e1;">Org:</strong> ${props.owner_org || 'Unattributed'}</div>
            </div>
            <div style="font-size: 10px; color: #facc15; font-family: 'JetBrains Mono', monospace; margin-bottom: 6px; background: rgba(234, 179, 8, 0.1); padding: 3px 6px; border-radius: 3px;">
              🛡️ KNOWN CVEs: ${props.known_cve_count || 0}
            </div>
            <div style="font-size: 9px; color: #64748b; margin-bottom: 10px;">${geoLabel}</div>
            <button id="popup-inspect-btn-${props.id}" style="width: 100%; padding: 6px 12px; background: linear-gradient(90deg, #2563eb, #1d4ed8); color: #ffffff; border: 1px solid #3b82f6; border-radius: 4px; font-size: 11px; font-family: 'JetBrains Mono', monospace; font-weight: 700; cursor: pointer; boxShadow: 0 4px 12px rgba(37, 99, 235, 0.4);">
              🔍 INSPECT INTELLIGENCE
            </button>
          </div>`,
          { className: 'custom-leaflet-popup' }
        );

        layer.on('popupopen', () => {
          const btn = document.getElementById(`popup-inspect-btn-${props.id}`);
          if (btn) {
            btn.onclick = () => {
              onSelectDevice(props);
              map.closePopup();
            };
          }
        });
      }
    });

    // Feed the geoJSON layer's markers into the cluster group (markercluster
    // recursively unpacks LayerGroup/FeatureGroup children) rather than adding
    // the raw layer straight to the map.
    clusterGroup.addLayer(layer);
    clusterGroup.addTo(map);
    deviceLayerRef.current = clusterGroup;

    return () => {
      if (deviceLayerRef.current) {
        map.removeLayer(deviceLayerRef.current);
        deviceLayerRef.current = null;
      }
    };
  }, [displayedFeatures, layers.devices, map]); // eslint-disable-line react-hooks/exhaustive-deps

  // Render Entity Link Graph
  useEffect(() => {
    if (linkLayerRef.current) {
      map.removeLayer(linkLayerRef.current);
      linkLayerRef.current = null;
    }
    if (!showLinks || !selected || selected.type !== 'device' || !rawGeojson) return;

    const sourceOrg = selected.data.org || selected.data.owner_org;
    const sourceCity = selected.data.city || city;
    if (!sourceOrg) return;

    const sourceLat = selected.data.lat;
    const sourceLon = selected.data.lon;

    const linkedDevices = rawGeojson.features.filter(f => {
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
          color: '#ef4444',
          weight: 2,
          opacity: 0.8,
          dashArray: '6, 8',
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
  }, [selected, showLinks, rawGeojson, city, map]);

  // Render public gov feed markers
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
          background: #06b6d4;
          border: 2px solid #ffffff;
          border-radius: 50%;
          box-shadow: 0 0 10px rgba(6, 182, 212, 0.8);
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
  }, [city, map, onSelectFeed]);

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
          gradient: { 0.2: '#1e293b', 0.5: '#ca8a04', 0.8: '#dc2626', 1.0: '#991b1b' },
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
  }, [city, layers.news, map, onSelectNews]);

  return null;
}

export default function SurveillanceMap({ city, onCityChange, layers, selected, showLinks, satelliteMode, onSelectDevice, onSelectNews, onSelectFeed, onOrbitalUpdate, onSelectSatellite }) {
  const [loading, setLoading] = useState(false);
  const [activeFilter, setActiveFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [totalCount, setTotalCount] = useState(0);
  const [filteredCount, setFilteredCount] = useState(0);
  const [displayedCount, setDisplayedCount] = useState(0);
  // 100 = plot every matched device (clustering handles visual density by
  // default). Drag down only if your machine specifically struggles — no
  // data is ever dropped, this only limits what gets mounted as map layers.
  const [pointDensity, setPointDensity] = useState(100);

  // Natural-language query state — orthogonal to the chip filter above, ANDed
  // together in the filteredFeatures memo. Chips stay for quick single clicks;
  // this handles compound requests ("unauthenticated government cameras with CVEs").
  const [nlQuery, setNlQuery] = useState('');
  const [nlFilter, setNlFilter] = useState(null);
  const [nlLoading, setNlLoading] = useState(false);

  const submitNlQuery = async () => {
    if (!nlQuery.trim()) return;
    setNlLoading(true);
    try {
      const res = await fetch('/api/nl-query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: nlQuery, current_city: city }),
      });
      const data = await res.json();
      setNlFilter(data);
      if (data.city && data.city !== city && onCityChange) {
        onCityChange(data.city);
      }
    } catch (e) {
      console.error('[nl-query]', e);
      setNlFilter({ search_text: nlQuery, explanation: 'Query failed — using plain text search.', parsed_by_ai: false });
    } finally {
      setNlLoading(false);
    }
  };

  const clearNlQuery = () => {
    setNlQuery('');
    setNlFilter(null);
  };

  const initialCityConfig = CITY_CENTERS[city] || [20, 78, 12];

  return (
    <div style={{ flex: 1, position: 'relative', height: '100%', width: '100%' }}>
      {/* ── Top Floating Filter & Precision Search Bar (Centered HUD) ── */}
      <div style={{
        position: 'absolute',
        top: 12,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        background: 'rgba(15, 23, 42, 0.95)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(255, 255, 255, 0.15)',
        padding: '6px 14px',
        borderRadius: 24,
        boxShadow: '0 8px 32px rgba(0,0,0,0.7)',
        flexWrap: 'nowrap',
        maxWidth: 'calc(100% - 340px)',
        overflowX: 'auto',
      }}>
        {/* Quick Filter Chips */}
        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          <button
            onClick={() => setActiveFilter('ALL')}
            style={{
              padding: '4px 10px',
              borderRadius: 4,
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace',
              fontWeight: 600,
              cursor: 'pointer',
              border: activeFilter === 'ALL' ? '1px solid #3b82f6' : '1px solid rgba(255,255,255,0.08)',
              background: activeFilter === 'ALL' ? 'rgba(59, 130, 246, 0.2)' : 'transparent',
              color: activeFilter === 'ALL' ? '#60a5fa' : '#94a3b8',
              transition: 'all 0.15s ease',
            }}
          >
            🌐 ALL ({totalCount})
          </button>

          <button
            onClick={() => setActiveFilter('OPEN_AUTH')}
            title="Filter to sensors with no authentication / open web ports"
            style={{
              padding: '4px 10px',
              borderRadius: 4,
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace',
              fontWeight: 600,
              cursor: 'pointer',
              border: activeFilter === 'OPEN_AUTH' ? '1px solid #ef4444' : '1px solid rgba(255,255,255,0.08)',
              background: activeFilter === 'OPEN_AUTH' ? 'rgba(239, 68, 68, 0.2)' : 'transparent',
              color: activeFilter === 'OPEN_AUTH' ? '#fca5a5' : '#94a3b8',
              transition: 'all 0.15s ease',
            }}
          >
            ⚠️ OPEN AUTH
          </button>

          <button
            onClick={() => setActiveFilter('HIGH_RISK_CVE')}
            title="Filter to sensors with known CVE vulnerabilities"
            style={{
              padding: '4px 10px',
              borderRadius: 4,
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace',
              fontWeight: 600,
              cursor: 'pointer',
              border: activeFilter === 'HIGH_RISK_CVE' ? '1px solid #eab308' : '1px solid rgba(255,255,255,0.08)',
              background: activeFilter === 'HIGH_RISK_CVE' ? 'rgba(234, 179, 8, 0.2)' : 'transparent',
              color: activeFilter === 'HIGH_RISK_CVE' ? '#fde047' : '#94a3b8',
              transition: 'all 0.15s ease',
            }}
          >
            🔥 HIGH RISK (CVEs)
          </button>

          <button
            onClick={() => setActiveFilter('GOVERNMENT')}
            style={{
              padding: '4px 10px',
              borderRadius: 4,
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace',
              fontWeight: 600,
              cursor: 'pointer',
              border: activeFilter === 'GOVERNMENT' ? '1px solid #ef4444' : '1px solid rgba(255,255,255,0.08)',
              background: activeFilter === 'GOVERNMENT' ? 'rgba(239, 68, 68, 0.15)' : 'transparent',
              color: activeFilter === 'GOVERNMENT' ? '#f87171' : '#94a3b8',
              transition: 'all 0.15s ease',
            }}
          >
            🏛️ GOVT
          </button>

          <button
            onClick={() => setActiveFilter('TELECOM')}
            style={{
              padding: '4px 10px',
              borderRadius: 4,
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace',
              fontWeight: 600,
              cursor: 'pointer',
              border: activeFilter === 'TELECOM' ? '1px solid #f97316' : '1px solid rgba(255,255,255,0.08)',
              background: activeFilter === 'TELECOM' ? 'rgba(249, 115, 22, 0.15)' : 'transparent',
              color: activeFilter === 'TELECOM' ? '#fb923c' : '#94a3b8',
              transition: 'all 0.15s ease',
            }}
          >
            📡 TELECOM
          </button>

          <button
            onClick={() => setActiveFilter('COMMERCIAL')}
            style={{
              padding: '4px 10px',
              borderRadius: 4,
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace',
              fontWeight: 600,
              cursor: 'pointer',
              border: activeFilter === 'COMMERCIAL' ? '1px solid #eab308' : '1px solid rgba(255,255,255,0.08)',
              background: activeFilter === 'COMMERCIAL' ? 'rgba(234, 179, 8, 0.15)' : 'transparent',
              color: activeFilter === 'COMMERCIAL' ? '#facc15' : '#94a3b8',
              transition: 'all 0.15s ease',
            }}
          >
            🏢 COMMERCIAL
          </button>
        </div>

        <div style={{ width: 1, height: 18, background: 'rgba(255,255,255,0.1)' }} />

        {/* Live Search Input Box */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, position: 'relative' }}>
          <span style={{ fontSize: 11, color: '#64748b' }}>🔍</span>
          <input
            type="text"
            placeholder="Search IP, Mfr, Org..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: 4,
              padding: '3px 8px',
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace',
              color: '#f8fafc',
              width: 150,
              outline: 'none',
            }}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              style={{
                background: 'none',
                border: 'none',
                color: '#94a3b8',
                fontSize: 11,
                cursor: 'pointer',
                padding: '0 4px',
              }}
            >
              ✕
            </button>
          )}
        </div>

        {/* Filtered Count Display Badge */}
        <span style={{
          fontSize: 10,
          fontFamily: 'JetBrains Mono, monospace',
          color: activeFilter !== 'ALL' || searchQuery ? '#38bdf8' : '#64748b',
          fontWeight: 600,
          marginLeft: 'auto',
        }}>
          PLOTTING {displayedCount} / {filteredCount} MATCHED ({totalCount} TOTAL)
        </span>
      </div>

      {/* ── Point Density Control ── */}
      <div style={{
        position: 'absolute',
        top: 118,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        background: 'rgba(15, 23, 42, 0.95)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(255, 255, 255, 0.15)',
        padding: '5px 14px',
        borderRadius: 20,
        boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
      }}>
        <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: '#64748b' }} title="No devices are ever dropped from the dataset — this only controls how many get rendered as map markers at once, for performance.">
          📊 DENSITY
        </span>
        <input
          type="range"
          min={1}
          max={100}
          value={pointDensity}
          onChange={(e) => setPointDensity(Number(e.target.value))}
          style={{ width: 120, height: 4, accentColor: '#3b82f6', cursor: 'pointer' }}
        />
        <span style={{
          fontSize: 10,
          fontFamily: 'JetBrains Mono, monospace',
          color: pointDensity < 100 ? '#38bdf8' : '#94a3b8',
          fontWeight: 700,
          minWidth: 34,
        }}>
          {pointDensity}%
        </span>
        {[25, 50, 100].map(preset => (
          <button
            key={preset}
            onClick={() => setPointDensity(preset)}
            style={{
              padding: '2px 7px',
              borderRadius: 4,
              fontSize: 9,
              fontFamily: 'JetBrains Mono, monospace',
              fontWeight: 600,
              cursor: 'pointer',
              border: pointDensity === preset ? '1px solid #3b82f6' : '1px solid rgba(255,255,255,0.08)',
              background: pointDensity === preset ? 'rgba(59, 130, 246, 0.2)' : 'transparent',
              color: pointDensity === preset ? '#60a5fa' : '#64748b',
            }}
          >
            {preset === 100 ? 'ALL' : `${preset}%`}
          </button>
        ))}
      </div>

      {/* ── Natural-Language Query Bar ── */}
      <div style={{
        position: 'absolute',
        top: 160,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        background: 'rgba(15, 23, 42, 0.95)',
        backdropFilter: 'blur(12px)',
        border: `1px solid ${nlFilter?.parsed_by_ai ? 'rgba(168, 85, 247, 0.5)' : 'rgba(255, 255, 255, 0.15)'}`,
        padding: '6px 10px',
        borderRadius: 20,
        boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
        maxWidth: 480,
      }}>
        <span style={{ fontSize: 12 }}>🔮</span>
        <input
          type="text"
          value={nlQuery}
          onChange={(e) => setNlQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') submitNlQuery(); }}
          placeholder="Ask in plain English: 'unauthenticated govt cameras in Delhi with CVEs'"
          style={{
            background: 'transparent',
            border: 'none',
            outline: 'none',
            fontSize: 11,
            fontFamily: 'JetBrains Mono, monospace',
            color: '#f8fafc',
            width: 320,
          }}
        />
        <button
          onClick={submitNlQuery}
          disabled={nlLoading || !nlQuery.trim()}
          style={{
            fontSize: 10,
            padding: '4px 10px',
            borderRadius: 12,
            fontFamily: 'JetBrains Mono, monospace',
            fontWeight: 700,
            cursor: nlLoading ? 'wait' : 'pointer',
            border: '1px solid rgba(168, 85, 247, 0.5)',
            background: 'rgba(168, 85, 247, 0.15)',
            color: '#c084fc',
          }}
        >
          {nlLoading ? '...' : 'ASK'}
        </button>
        {nlFilter && (
          <button
            onClick={clearNlQuery}
            title="Clear AI filter"
            style={{ background: 'none', border: 'none', color: '#64748b', fontSize: 11, cursor: 'pointer' }}
          >
            ✕
          </button>
        )}
      </div>

      {nlFilter?.explanation && (
        <div style={{
          position: 'absolute',
          top: 198,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 1000,
          fontSize: 9.5,
          fontFamily: 'JetBrains Mono, monospace',
          color: nlFilter.parsed_by_ai ? '#c084fc' : '#94a3b8',
          background: 'rgba(15, 23, 42, 0.85)',
          padding: '3px 10px',
          borderRadius: 10,
          maxWidth: 460,
          textAlign: 'center',
        }}>
          {nlFilter.parsed_by_ai ? '✨ ' : '⚠️ '}{nlFilter.explanation}
        </div>
      )}

      {loading && (
        <div style={{
          position: 'absolute',
          top: 60,
          left: '50%',
          transform: 'translateX(-50%)',
          background: 'rgba(15, 23, 42, 0.95)',
          backdropFilter: 'blur(8px)',
          padding: '6px 14px',
          borderRadius: 6,
          border: '1px solid rgba(59, 130, 246, 0.3)',
          color: '#f8fafc',
          fontSize: 11,
          fontFamily: 'JetBrains Mono, monospace',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          boxShadow: '0 4px 16px rgba(0,0,0,0.5)'
        }}>
          <span className="streaming-cursor" style={{ margin: 0, background: '#3b82f6' }}></span>
          SYNCHRONIZING SENSOR TELEMETRY...
        </div>
      )}

      {/* Map status legend overlay */}
      <div style={{
        position: 'absolute',
        bottom: 24,
        right: 16,
        zIndex: 999,
        background: 'rgba(15, 23, 42, 0.85)',
        backdropFilter: 'blur(10px)',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: 6,
        padding: '8px 12px',
        fontSize: 10,
        fontFamily: 'JetBrains Mono, monospace',
        color: '#94a3b8',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        pointerEvents: 'none',
      }}>
        <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: 11, marginBottom: 2 }}>
          SENSOR SITE TELEMETRY ({city.toUpperCase()})
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#ef4444' }} /> Govt / Law Enforcement
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#f97316' }} /> Telecom Infrastructure
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#eab308' }} /> Commercial Surveillance
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#3b82f6' }} /> Unclassified / Unknown
        </div>
        <div style={{ height: 1, background: 'rgba(255,255,255,0.08)', margin: '4px 0' }} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#94a3b8', border: '1.5px solid #cbd5e1' }} /> Solid ring: verified real location
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#94a3b8', opacity: 0.5, border: '1.5px dashed #475569' }} /> Dashed: simulated demo fill
        </div>
        <div style={{ fontSize: 8.5, color: '#475569', marginTop: 2 }}>
          Real locations © OpenStreetMap contributors (ODbL)
        </div>
      </div>

      <MapContainer
        center={[initialCityConfig[0], initialCityConfig[1]]}
        zoom={initialCityConfig[2]}
        zoomControl={true}
        scrollWheelZoom={true}
        preferCanvas={true}
        className={satelliteMode ? '' : 'map-dark-invert'}
        style={{ width: '100%', height: '100%', background: '#080b11' }}
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
          activeFilter={activeFilter}
          searchQuery={searchQuery}
          pointDensity={pointDensity}
          nlFilter={nlFilter}
          onSelectDevice={onSelectDevice}
          onSelectNews={onSelectNews}
          onSelectFeed={onSelectFeed}
          setLoading={setLoading}
          setTotalCount={setTotalCount}
          setFilteredCount={setFilteredCount}
          setDisplayedCount={setDisplayedCount}
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
