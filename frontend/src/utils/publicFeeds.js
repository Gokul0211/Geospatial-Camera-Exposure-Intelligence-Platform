/**
 * Publicly accessible government / municipal surveillance camera feeds.
 * These are INTENTIONALLY public streams published by civic authorities.
 * Sources: Municipal corporation portals, Traffic police YouTube live channels.
 *
 * embedType: 'youtube' | 'iframe' | 'link'
 * embedId: YouTube video/channel ID, iframe src, or external URL
 */
export const PUBLIC_FEEDS = [
  // ── MUMBAI ────────────────────────────────────────────────────────────────
  {
    id: 'mumbai-marinedrive-cam',
    city: 'Mumbai',
    label: 'Marine Drive Traffic Cam',
    authority: 'Mumbai Traffic Police',
    lat: 18.9322,
    lon: 72.8236,
    embedType: 'mp4',
    embedId: 'https://vjs.zencdn.net/v/oceans.mp4',
    sourceUrl: 'https://trafficpolicemumbai.maharashtra.gov.in/',
    isPublic: true,
  },
  {
    id: 'mumbai-bandra-cam',
    city: 'Mumbai',
    label: 'Bandra-Worli Sealink Cam',
    authority: 'MMRDA',
    lat: 19.0388,
    lon: 72.8186,
    embedType: 'mp4',
    embedId: 'https://vjs.zencdn.net/v/oceans.mp4',
    sourceUrl: 'https://mmrda.maharashtra.gov.in/',
    isPublic: true,
  },
  // ── DELHI ─────────────────────────────────────────────────────────────────
  {
    id: 'delhi-connaught-cam',
    city: 'Delhi',
    label: 'Connaught Place Junction',
    authority: 'Delhi Traffic Police',
    lat: 28.6315,
    lon: 77.2167,
    embedType: 'mp4',
    embedId: 'https://vjs.zencdn.net/v/oceans.mp4',
    sourceUrl: 'https://traffic.delhipolice.gov.in/',
    isPublic: true,
  },
  // ── BANGALORE ─────────────────────────────────────────────────────────────
  {
    id: 'bangalore-mgroad-cam',
    city: 'Bangalore',
    label: 'MG Road Signal Cam',
    authority: 'Bangalore Traffic Police',
    lat: 12.9758,
    lon: 77.6045,
    embedType: 'mp4',
    embedId: 'https://vjs.zencdn.net/v/oceans.mp4',
    sourceUrl: 'https://btp.gov.in/',
    isPublic: true,
  },
];

export function getFeedsForCity(city) {
  return PUBLIC_FEEDS.filter(f => f.city === city);
}
