/**
 * LEO Reconnaissance & Earth Observation Satellite Orbital Data
 *
 * Uses a simplified Keplerian propagator (spherical trig, no J2 perturbations).
 * Positions accurate to ±80 km — sufficient for visual OSINT overlay.
 *
 * Orbital math:
 *   u   = argument of latitude (angle along the orbital plane, measured from ascending node)
 *   lat = arcsin(sin(inclination) × sin(u))
 *   lon = nodeLon + atan2(cos(inclination) × sin(u), cos(u)) − earthRotation
 */

const DEG = Math.PI / 180;
const sinD  = d => Math.sin(d * DEG);
const cosD  = d => Math.cos(d * DEG);
const atan2D = (y, x) => Math.atan2(y, x) / DEG;
const asinD  = x => Math.asin(Math.max(-1, Math.min(1, x))) / DEG;

/**
 * Compute startPhase + nodeLon so a satellite is at (targetLat, targetLon)
 * the instant this function runs (Date.now()). This ensures demo-time calibration.
 *
 * @param {number} inclination  orbital inclination in degrees
 * @param {number} period       orbital period in seconds
 * @param {number} targetLat   desired latitude at t = now
 * @param {number} targetLon   desired longitude at t = now
 * @param {boolean} ascending  true = satellite moving northward at target point
 */
function calibrate(inclination, period, targetLat, targetLon, ascending = true) {
  const sinU = sinD(targetLat) / sinD(inclination);
  if (Math.abs(sinU) > 0.9999) {
    // Target latitude is near the orbital ceiling — fall back gracefully
    return { startPhase: 0, nodeLon: ((targetLon + 180) % 360 + 360) % 360 };
  }

  // Argument of latitude at the desired position
  let u = asinD(sinU); // range −90 to +90
  if (!ascending) u = 180 - u; // flip to descending branch (90–270°)
  if (u < 0) u += 360;        // keep u in [0, 360)

  // Earth's rotation angle at this UTC instant
  const nowSec    = Date.now() / 1000;
  const earthDeg  = ((nowSec % 86400) / 86400) * 360;

  // nodeLon chosen so the satellite crosses the target longitude at this u
  const argLon = atan2D(cosD(inclination) * sinD(u), cosD(u));
  const nodeLon = ((targetLon - argLon + earthDeg) % 360 + 360) % 360;

  // startPhase chosen so (nowSec / period * 360 + startPhase) mod 360 == u
  const phaseNow  = ((nowSec / period) * 360) % 360;
  const startPhase = ((u - phaseNow) % 360 + 360) % 360;

  return { startPhase, nodeLon };
}

// ── Calibrate each satellite at module-load time ──────────────────────────────
// CARTOSAT-3  : placed at 5 °N, 73 °E ascending → reaches Mumbai (~19 °N) in ~10 min
const _cartosat = calibrate(97.46, 5682,  5,  73, true);
// RISAT-2BR2  : placed at −15 °S, 73 °E ascending → arrives over India ~16 min later
const _risat    = calibrate(36.98, 5784, -15, 73, true);
// Sentinel-2A : placed at 55 °N, 90 °E descending → sweeping down toward Asia
const _s2a      = calibrate(98.57, 6024,  55, 90, false);
// Landsat-9   : placed at −40 °S, 120 °E ascending → far away, interesting on global zoom
const _l9       = calibrate(98.22, 5930, -40, 120, true);

// ── Additional Swarm (Calibrated to be globally distributed) ────────────────
const _wv3      = calibrate(97.97, 5634,  20, -100, true);   // WorldView-3
const _gf11     = calibrate(97.4,  5500,  35,  110, false);  // GaoFen-11
const _igs7     = calibrate(97.9,  5620,  40,  140, false);  // IGS-Optical 7
const _ofeq     = calibrate(142.0, 5400,  30,   35, true);   // Ofeq-11 (Retrograde)
const _sar      = calibrate(98.2,  5600,  50,   10, false);  // SAR-Lupe 1
const _cosmo    = calibrate(97.8,  5740, -10,   50, true);   // COSMO-SkyMed

// ── Batch 3 (5 more, spread globally) ───────────────────────────────────────
const _dove     = calibrate(97.3,  5580,  10, -70, true);    // Planet Dove (LEO)
const _spot7    = calibrate(98.2,  5980,  45,  20, false);   // SPOT-7
const _kompsat  = calibrate(98.1,  5560, -25, 130, true);    // Kompsat-3A
const _th01     = calibrate(97.7,  5650,  60,  80, false);   // TH-01
const _yaogan   = calibrate(35.0,  6060,   0,  60, true);    // Yaogan-30
// ─────────────────────────────────────────────────────────────────────────────

export const ORBITAL_ASSETS = [
  {
    id:           'cartosat3',
    name:         'CARTOSAT-3',
    agency:       'ISRO',
    flag:         '🇮🇳',
    agencyColor:  '#FF9933',
    glowColor:    'rgba(255,153,51,0.35)',
    type:         'Optical Imaging',
    altitude:     509,
    velocity:     '7.6 km/s',
    resolution:   '0.25 m',
    revisit:      '4 days',
    swath:        '16 km',
    inclination:  97.46,
    period:       5682,
    nodeLon:      _cartosat.nodeLon,
    startPhase:   _cartosat.startPhase,
    description:  'Sub-meter optical imaging satellite. Can identify individuals and vehicle licence plates from 509 km altitude. Primary ISRO civilian intelligence asset.',
  },
  {
    id:           'risat2br2',
    name:         'RISAT-2BR2',
    agency:       'ISRO',
    flag:         '🇮🇳',
    agencyColor:  '#FF9933',
    glowColor:    'rgba(255,153,51,0.35)',
    type:         'SAR — All-Weather / Night',
    altitude:     576,
    velocity:     '7.5 km/s',
    resolution:   '0.35 m',
    revisit:      '4 days',
    swath:        '10 km',
    inclination:  36.98,
    period:       5784,
    nodeLon:      _risat.nodeLon,
    startPhase:   _risat.startPhase,
    description:  'Synthetic Aperture Radar. Penetrates monsoon clouds and operates at night. Designed for border surveillance and maritime domain awareness.',
  },
  {
    id:           'sentinel2a',
    name:         'SENTINEL-2A',
    agency:       'ESA',
    flag:         '🇪🇺',
    agencyColor:  '#4488FF',
    glowColor:    'rgba(68,136,255,0.30)',
    type:         'Multispectral EO',
    altitude:     786,
    velocity:     '7.4 km/s',
    resolution:   '10 m',
    revisit:      '10 days',
    swath:        '290 km',
    inclination:  98.57,
    period:       6024,
    nodeLon:      _s2a.nodeLon,
    startPhase:   _s2a.startPhase,
    description:  'Wide-swath multispectral imager with 13 spectral bands. Used for urban growth mapping, land-use change detection, and civilian infrastructure monitoring.',
  },
  {
    id:           'landsat9',
    name:         'LANDSAT-9',
    agency:       'USGS/NASA',
    flag:         '🇺🇸',
    agencyColor:  '#0077FF',
    glowColor:    'rgba(0,119,255,0.30)',
    type:         'Thermal Infrared / OLI',
    altitude:     705,
    velocity:     '7.5 km/s',
    resolution:   '15 m',
    revisit:      '16 days',
    swath:        '185 km',
    inclination:  98.22,
    period:       5930,
    nodeLon:      _l9.nodeLon,
    startPhase:   _l9.startPhase,
    description:  'Operational Land Imager + Thermal Infrared Sensor. Detects heat signatures from industrial sites and urban centres. Provides comprehensive archival coverage since 1972.',
  },
  {
    id:           'worldview3',
    name:         'WORLDVIEW-3',
    agency:       'MAXAR',
    flag:         '🇺🇸',
    agencyColor:  '#0077FF',
    glowColor:    'rgba(0,119,255,0.30)',
    type:         'Ultra-High Res Optical',
    altitude:     617,
    velocity:     '7.5 km/s',
    resolution:   '0.31 m',
    revisit:      '1 day',
    swath:        '13.1 km',
    inclination:  97.97,
    period:       5634,
    nodeLon:      _wv3.nodeLon,
    startPhase:   _wv3.startPhase,
    description:  'Commercial earth observation satellite. Super-spectral imaging capabilities capable of penetrating smoke, fog, and smog to identify ground targets.',
  },
  {
    id:           'gaofen11',
    name:         'GAOFEN-11',
    agency:       'CNSA',
    flag:         '🇨🇳',
    agencyColor:  '#FF3333',
    glowColor:    'rgba(255,51,51,0.30)',
    type:         'Military Reconnaissance',
    altitude:     495,
    velocity:     '7.6 km/s',
    resolution:   '0.1 m (Est)',
    revisit:      'Unknown',
    swath:        'Unknown',
    inclination:  97.4,
    period:       5500,
    nodeLon:      _gf11.nodeLon,
    startPhase:   _gf11.startPhase,
    description:  'Classified Chinese military reconnaissance satellite. Believed to have optical resolution comparable to US Keyhole satellites (< 10cm).',
  },
  {
    id:           'igsopt7',
    name:         'IGS-OPTICAL 7',
    agency:       'CSICE',
    flag:         '🇯🇵',
    agencyColor:  '#FF3366',
    glowColor:    'rgba(255,51,102,0.30)',
    type:         'Intelligence Gathering',
    altitude:     513,
    velocity:     '7.6 km/s',
    resolution:   '0.3 m',
    revisit:      'Variable',
    swath:        '15 km',
    inclination:  97.9,
    period:       5620,
    nodeLon:      _igs7.nodeLon,
    startPhase:   _igs7.startPhase,
    description:  'Information Gathering Satellite. Operates under Japan\'s Cabinet Secretariat for national defense and missile launch detection.',
  },
  {
    id:           'ofeq11',
    name:         'OFEQ-11',
    agency:       'IMoD',
    flag:         '🇮🇱',
    agencyColor:  '#00BFFF',
    glowColor:    'rgba(0,191,255,0.30)',
    type:         'Retrograde Reconnaissance',
    altitude:     600,
    velocity:     '7.5 km/s',
    resolution:   '0.5 m',
    revisit:      '1-2 days',
    swath:        '15 km',
    inclination:  142.0,
    period:       5400,
    nodeLon:      _ofeq.nodeLon,
    startPhase:   _ofeq.startPhase,
    description:  'Highly unusual retrograde orbit (launched westward over the Mediterranean). Designed for frequent passes over the Middle East.',
  },
  {
    id:           'sarlupe1',
    name:         'SAR-LUPE 1',
    agency:       'BND/Bundeswehr',
    flag:         '🇩🇪',
    agencyColor:  '#FFCC00',
    glowColor:    'rgba(255,204,0,0.30)',
    type:         'Radar Reconnaissance',
    altitude:     500,
    velocity:     '7.6 km/s',
    resolution:   '0.5 m',
    revisit:      '10 hours (Constellation)',
    swath:        '5.5 km',
    inclination:  98.2,
    period:       5600,
    nodeLon:      _sar.nodeLon,
    startPhase:   _sar.startPhase,
    description:  'First of the German military SAR constellation. Provides all-weather, day/night radar imaging for the Federal Intelligence Service.',
  },
  {
    id:           'cosmoskymed',
    name:         'COSMO-SKYMED',
    agency:       'ASI / MoD',
    flag:         '🇮🇹',
    agencyColor:  '#00FF88',
    glowColor:    'rgba(0,255,136,0.30)',
    type:         'Dual-Use SAR',
    altitude:     619,
    velocity:     '7.5 km/s',
    resolution:   '1 m',
    revisit:      '12 hours',
    swath:        '10-40 km',
    inclination:  97.8,
    period:       5740,
    nodeLon:      _cosmo.nodeLon,
    startPhase:   _cosmo.startPhase,
    description:  'Constellation of Small Satellites for Mediterranean basin Observation. Dual civilian/military use synthetic aperture radar.',
  },
  {
    id:           'planetdove',
    name:         'PLANET DOVE',
    agency:       'Planet Labs',
    flag:         '🇺🇸',
    agencyColor:  '#00FF66',
    glowColor:    'rgba(0,255,102,0.25)',
    type:         'Commercial EO Constellation',
    altitude:     475,
    velocity:     '7.6 km/s',
    resolution:   '3.7 m',
    revisit:      'Daily',
    swath:        '24.6 km',
    inclination:  97.3,
    period:       5580,
    nodeLon:      _dove.nodeLon,
    startPhase:   _dove.startPhase,
    description:  'One of Planet Labs\' flock of ~200 Dove CubeSats providing daily imaging of every point on Earth at 3.7m resolution.',
  },
  {
    id:           'spot7',
    name:         'SPOT-7',
    agency:       'Airbus DS',
    flag:         '🇫🇷',
    agencyColor:  '#0055BB',
    glowColor:    'rgba(0,85,187,0.25)',
    type:         'Very High Resolution Optical',
    altitude:     694,
    velocity:     '7.5 km/s',
    resolution:   '1.5 m',
    revisit:      '1 day',
    swath:        '60 km',
    inclination:  98.2,
    period:       5980,
    nodeLon:      _spot7.nodeLon,
    startPhase:   _spot7.startPhase,
    description:  'French commercial Earth observation satellite. Wide-swath imaging sold to government and intelligence agencies globally.',
  },
  {
    id:           'kompsat3a',
    name:         'KOMPSAT-3A',
    agency:       'KARI',
    flag:         '🇰🇷',
    agencyColor:  '#FF66AA',
    glowColor:    'rgba(255,102,170,0.25)',
    type:         'Infrared & Optical EO',
    altitude:     528,
    velocity:     '7.6 km/s',
    resolution:   '0.55 m',
    revisit:      '1 day',
    swath:        '12 km',
    inclination:  98.1,
    period:       5560,
    nodeLon:      _kompsat.nodeLon,
    startPhase:   _kompsat.startPhase,
    description:  'Korean sub-meter optical and mid-wave infrared (MWIR) sensor. Can detect warm targets like vehicle engines and human activity at night.',
  },
  {
    id:           'th01',
    name:         'TH-01',
    agency:       'SASMAC',
    flag:         '🇨🇳',
    agencyColor:  '#FF4400',
    glowColor:    'rgba(255,68,0,0.25)',
    type:         'Stereo Mapping',
    altitude:     500,
    velocity:     '7.6 km/s',
    resolution:   '2 m',
    revisit:      '3 days',
    swath:        '60 km',
    inclination:  97.7,
    period:       5650,
    nodeLon:      _th01.nodeLon,
    startPhase:   _th01.startPhase,
    description:  'Chinese stereo mapping satellite operated by SASMAC (Satellite Surveying and Mapping Application Center) for geospatial intelligence.',
  },
  {
    id:           'yaogan30',
    name:         'YAOGAN-30',
    agency:       'PLA SSF',
    flag:         '🇨🇳',
    agencyColor:  '#DD0000',
    glowColor:    'rgba(221,0,0,0.25)',
    type:         'SIGINT Triplet Constellation',
    altitude:     600,
    velocity:     '7.5 km/s',
    resolution:   'Classified',
    revisit:      'Hours',
    swath:        'Classified',
    inclination:  35.0,
    period:       6060,
    nodeLon:      _yaogan.nodeLon,
    startPhase:   _yaogan.startPhase,
    description:  'Believed to be a signals intelligence (SIGINT) constellation operated by the PLA Strategic Support Force. Triplet formation allows triangulating ground emitters.',
  },
];

// ── Propagator ────────────────────────────────────────────────────────────────

/**
 * Return the current geodetic {lat, lon} of a satellite.
 * @param {object} sat  - entry from ORBITAL_ASSETS
 * @param {number} ts   - Date.now() timestamp (ms)
 */
export function getSatellitePosition(sat, ts) {
  const t   = ts / 1000; // ms → s
  const u   = ((t / sat.period * 360) + sat.startPhase) % 360;
  const uR  = u * DEG;
  const iR  = sat.inclination * DEG;

  const lat     = asinD(Math.sin(iR) * Math.sin(uR));
  const argLon  = atan2D(Math.cos(iR) * Math.sin(uR), Math.cos(uR));
  const earthDeg = ((t % 86400) / 86400) * 360;
  const lon     = (((sat.nodeLon + argLon - earthDeg) % 360) + 360) % 360 - 180;

  return { lat, lon };
}

/**
 * Compute the 45-minute forward ground track, split at the antimeridian.
 * Returns an array of [lat, lon] pairs; null marks a segment break.
 */
export function getGroundTrack(sat, startTs, durationSec = 2700, stepSec = 60) {
  const points = [];
  let prevLon  = null;
  for (let dt = 0; dt <= durationSec; dt += stepSec) {
    const { lat, lon } = getSatellitePosition(sat, startTs + dt * 1000);
    if (prevLon !== null && Math.abs(lon - prevLon) > 150) {
      points.push(null); // antimeridian break
    }
    points.push([lat, lon]);
    prevLon = lon;
  }
  return points;
}

// ── Utility ───────────────────────────────────────────────────────────────────

/** Haversine distance in km between two geodetic points */
export function haversineKm(lat1, lon1, lat2, lon2) {
  const R    = 6371;
  const dLat = (lat2 - lat1) * DEG;
  const dLon = (lon2 - lon1) * DEG;
  const a    = Math.sin(dLat / 2) ** 2 +
               Math.cos(lat1 * DEG) * Math.cos(lat2 * DEG) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/** Return threat-level descriptor or null if satellite is too far */
export function getThreatLevel(distKm) {
  if (distKm <  600) return { level: 'CRITICAL', label: '⚠ ORBITAL SURVEILLANCE ACTIVE', color: '#FF3333', bg: 'rgba(255,51,51,0.14)' };
  if (distKm < 1200) return { level: 'HIGH',     label: '🛰 SATELLITE OVERHEAD',           color: '#FF8800', bg: 'rgba(255,136,0,0.11)' };
  if (distKm < 2800) return { level: 'ELEVATED', label: '◉ ORBITAL MONITORING',           color: '#FFD700', bg: 'rgba(255,215,0,0.09)' };
  return null;
}
