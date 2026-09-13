import L from 'leaflet';
import { ownerColor } from './colorMap';

export function createDeviceIcon(ownerType, deviceType) {
  const color = ownerColor(ownerType);
  const size = (deviceType === 'IP Camera' || deviceType === 'DVR/NVR') ? 10 : 8;
  const r = size / 2 - 1;

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}">
      <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="${color}" stroke="${color}" stroke-opacity="0.3" stroke-width="2"/>
    </svg>`;
  return L.divIcon({
    html: svg,
    className: '',
    iconSize: [size, size],
    iconAnchor: [size/2, size/2],
  });
}

export function createNewsIcon(isVerified) {
  const size = isVerified ? 20 : 16;
  const fill = isVerified ? '#00e5ff' : '#00a8cc'; // Bright neon cyan
  const opacity = isVerified ? '1' : '0.9';
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}">
      <rect x="0" y="0" width="${size}" height="${size}" fill="${fill}" opacity="${opacity}" rx="3" stroke="#fff" stroke-width="1.5"/>
      <path d="M4 ${size/2} L${size-4} ${size/2} M4 ${size/2-3} L${size-4} ${size/2-3} M4 ${size/2+3} L${size-8} ${size/2+3}" stroke="#111" stroke-width="1.5"/>
    </svg>`;
  return L.divIcon({
    html: `<div style="filter: drop-shadow(0 0 6px ${fill});">${svg}</div>`,
    className: 'news-marker-icon',
    iconSize: [size, size],
    iconAnchor: [size/2, size/2],
  });
}
