import { useEffect, useRef } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import {
  ORBITAL_ASSETS,
  getSatellitePosition,
  getGroundTrack,
  haversineKm,
  getThreatLevel,
} from '../utils/satelliteData';

const CITY_CENTERS = {
  Mumbai:    [19.0760, 72.8777],
  Delhi:     [28.6139, 77.2090],
  Bangalore: [12.9716, 77.5946],
};

/**
 * OrbitalTracker — renders live satellite positions on the Leaflet map.
 * Runs imperatively inside MapContainer via useMap().
 *
 * Props:
 *   city           — currently selected city string
 *   onOrbitalUpdate(alerts[]) — called every tick with active threat objects
 *   onSelectSatellite(satInfo) — called when user clicks a satellite marker
 */
export default function OrbitalTracker({ city, onOrbitalUpdate, onSelectSatellite }) {
  const map = useMap();

  // Persistent refs — survive re-renders without triggering effects
  const markersRef    = useRef({});   // id → L.marker
  const tracksRef     = useRef({});   // id → [L.polyline, …]
  const footprintsRef = useRef({});   // id → L.circle
  const lastTrackTs   = useRef(0);    // timestamp of last ground-track redraw
  const intervalRef   = useRef(null);

  useEffect(() => {
    const cityCenter = CITY_CENTERS[city] || [20, 78];

    /* ── helpers ──────────────────────────────────────────────────────── */
    const removeLayer = l => { try { map.removeLayer(l); } catch (_) {} };

    const removeSat = id => {
      if (markersRef.current[id])    { removeLayer(markersRef.current[id]);  delete markersRef.current[id]; }
      if (tracksRef.current[id])     { tracksRef.current[id].forEach(removeLayer); delete tracksRef.current[id]; }
      if (footprintsRef.current[id]) { removeLayer(footprintsRef.current[id]); delete footprintsRef.current[id]; }
    };

    const cleanAll = () => ORBITAL_ASSETS.forEach(s => removeSat(s.id));

    /* ── icon builder ─────────────────────────────────────────────────── */
    const buildIcon = (sat, dist, threat) => {
      const pingClass = dist < 1200 ? 'sat-ping sat-ping-active' : 'sat-ping';
      const distLabel = dist < 3000
        ? `<span class="sat-dist" style="color:${threat ? threat.color : sat.agencyColor}">${Math.round(dist).toLocaleString()} km</span>`
        : '';
      const html = `
        <div class="sat-marker" style="--sat-color:${sat.agencyColor};--sat-glow:${sat.glowColor}">
          <div class="${pingClass}"></div>
          <div class="sat-icon">🛰</div>
          <div class="sat-label-block">
            <span class="sat-name">${sat.name}</span>
            <span class="sat-agency-tag">${sat.flag} ${sat.agency}</span>
            ${distLabel}
          </div>
        </div>`;
      return L.divIcon({ html, className: '', iconSize: [0, 0], iconAnchor: [10, 10] });
    };

    /* ── ground track renderer ────────────────────────────────────────── */
    const drawTrack = (sat, now) => {
      if (tracksRef.current[sat.id]) {
        tracksRef.current[sat.id].forEach(removeLayer);
      }
      const rawPts = getGroundTrack(sat, now, 2700, 60);
      // Split into segments at antimeridian nulls
      const segs = [];
      let seg = [];
      rawPts.forEach(p => {
        if (p === null) { if (seg.length) segs.push(seg); seg = []; }
        else seg.push(p);
      });
      if (seg.length) segs.push(seg);

      tracksRef.current[sat.id] = segs.map((s, i) =>
        L.polyline(s, {
          color:       sat.agencyColor,
          weight:      i === 0 ? 1.2 : 0.6,
          opacity:     i === 0 ? 0.6 : Math.max(0.08, 0.35 - i * 0.08),
          dashArray:   null,      // solid line — professional look
          smoothFactor: 2,        // simplify points for performance
          interactive: false,
        }).addTo(map)
      );
    };

    /* ── main update tick ─────────────────────────────────────────────── */
    const tick = () => {
      const now = Date.now();
      const activeAlerts = [];
      const redrawTracks = now - lastTrackTs.current > 30_000; // every 30 s

      ORBITAL_ASSETS.forEach(sat => {
        const { lat, lon } = getSatellitePosition(sat, now);
        const dist  = haversineKm(cityCenter[0], cityCenter[1], lat, lon);
        const threat = getThreatLevel(dist);
        if (threat) activeAlerts.push({ sat, dist: Math.round(dist), threat });

        /* marker */
        const icon = buildIcon(sat, dist, threat);
        if (markersRef.current[sat.id]) {
          markersRef.current[sat.id].setLatLng([lat, lon]);
          markersRef.current[sat.id].setIcon(icon);
        } else {
          const m = L.marker([lat, lon], { icon, zIndexOffset: 2000 });
          m.on('click', () => {
            const currentPos = getSatellitePosition(sat, Date.now());
            const currentDist = haversineKm(cityCenter[0], cityCenter[1], currentPos.lat, currentPos.lon);
            if (onSelectSatellite) {
              onSelectSatellite({
                ...sat,
                lat: currentPos.lat,
                lon: currentPos.lon,
                dist: Math.round(currentDist),
                threat: getThreatLevel(currentDist),
              });
            }
          });
          m.bindTooltip(
            `<b>${sat.name}</b><br>${sat.agency} · Alt ${sat.altitude} km`,
            { direction: 'top', offset: [0, -12], className: 'sat-tooltip' }
          );
          m.addTo(map);
          markersRef.current[sat.id] = m;
        }

        /* ground track */
        if (redrawTracks) drawTrack(sat, now);

        /* coverage footprint — thin ring only, no fill (much lighter) */
        if (footprintsRef.current[sat.id]) {
          footprintsRef.current[sat.id].setLatLng([lat, lon]);
        } else {
          footprintsRef.current[sat.id] = L.circle([lat, lon], {
            radius:      sat.altitude * 1800,
            color:       sat.agencyColor,
            weight:      0.6,
            fill:        false,    // no fill — purely a ring
            dashArray:   null,
            interactive: false,
          }).addTo(map);
        }
      });

      if (redrawTracks) lastTrackTs.current = now;
      if (onOrbitalUpdate) onOrbitalUpdate(activeAlerts);
    };

    cleanAll();
    tick(); // immediate first render
    intervalRef.current = setInterval(tick, 4000); // 4s tick — smooth enough, no lag

    return () => {
      clearInterval(intervalRef.current);
      cleanAll();
    };
  }, [city, map]); // re-run when city changes

  return null; // purely imperative rendering
}
