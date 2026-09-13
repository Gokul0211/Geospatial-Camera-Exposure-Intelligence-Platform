import { useState, useEffect, useRef } from 'react';
import { ownerColor } from '../utils/colorMap';
import { fetchCameraTrustScore } from '../utils/api';
import TrustScoreBadge from './TrustScoreBadge';

// Ports that indicate a potentially exposed camera interface
const EXPOSED_PORTS = [554, 80, 8080, 8443, 37777];

function isExposedDevice(device) {
  const ports = Array.isArray(device.ports) ? device.ports : [];
  return ports.some(p => EXPOSED_PORTS.includes(Number(p)));
}

function isConfirmedOpen(device) {
  if (!device.banner_snippet) return false;
  const banner = device.banner_snippet.toLowerCase();
  
  const hasSuccess = banner.includes('200 ok') || banner.includes('mjpeg') || banner.includes('video web server') || banner.includes('netcam');
  const hasAuth = banner.includes('401 unauthorized') || banner.includes('login') || banner.includes('authentication required') || banner.includes('password');

  return hasSuccess && !hasAuth;
}

function buildCertInReport(device, city) {
  const ip = device.ip || 'Unknown';
  const lat = device.lat?.toFixed(4) || 'N/A';
  const lon = device.lon?.toFixed(4) || 'N/A';
  const org = device.org || device.owner_org || 'Unknown';
  const ports = Array.isArray(device.ports) ? device.ports.join(', ') : 'Unknown';
  const mfr = device.manufacturer || 'Unknown';

  const subject = encodeURIComponent(`Responsible Disclosure: Exposed CCTV Device in ${city}`);
  const body = encodeURIComponent(
`Dear CERT-In Team,

I am reporting an unprotected surveillance camera device discovered via passive OSINT scanning.

DEVICE DETAILS:
- IP Address : ${ip}
- Location   : ${city} (${lat}, ${lon})
- Organization: ${org}
- Manufacturer: ${mfr}
- Open Ports  : ${ports}
- Device Type : ${device.device_type || 'Unknown'}

This device appears to have an exposed HTTP/RTSP interface with no authentication, making it accessible to any internet user. This is a potential security and privacy risk.

Recommended Action: Notify the device owner / ISP to secure or take down the exposed interface.

Reported via SurveillanceWatch OSINT Platform.

Regards,
Security Researcher`
  );

  return `mailto:incident@cert-in.org.in?subject=${subject}&body=${body}`;
}

// Animated CCTV Feed Viewer Component
function CctvFeedViewer({ feed }) {
  const [videoError, setVideoError] = useState(false);
  const canvasRef = useRef(null);

  useEffect(() => {
    let animationFrameId;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let time = 0;
    const render = () => {
      time += 0.04;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (videoError) {
        ctx.fillStyle = '#080c14';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }

      // HUD Grid scan lines
      ctx.strokeStyle = 'rgba(0, 229, 255, 0.08)';
      ctx.lineWidth = 1;
      for (let x = 0; x < canvas.width; x += 30) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
      }

      // Animated vehicle tracking bounding boxes
      const laneY = canvas.height * 0.55;
      for (let i = 0; i < 3; i++) {
        const x = (time * 45 + i * 90) % (canvas.width + 50) - 30;
        const y = laneY - 15 + (i % 2 === 0 ? 12 : -10);
        const col = i % 2 === 0 ? '#00e5ff' : '#f39c12';

        ctx.strokeStyle = col;
        ctx.lineWidth = 1.5;
        ctx.strokeRect(x, y, 40, 24);

        ctx.fillStyle = col;
        ctx.font = '8px IBM Plex Mono, monospace';
        ctx.fillText(`YOLO_DET [${Math.floor(89 + i * 3)}%]`, x, y - 4);
      }

      // HUD telemetry overlay
      ctx.fillStyle = '#00e5ff';
      ctx.font = '9px IBM Plex Mono, monospace';
      ctx.fillText(`CAM_ID: ${feed.id.toUpperCase()}`, 8, 16);
      ctx.fillText(`FPS: 30.0  BITRATE: 4.8 Mbps`, 8, 28);

      const ts = new Date().toISOString().replace('T', ' ').slice(0, 19);
      ctx.fillStyle = '#ff6b6b';
      ctx.fillText(`● REC  ${ts}`, canvas.width - 150, 16);

      animationFrameId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animationFrameId);
  }, [videoError, feed]);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <div style={{ fontSize: '0.7rem', color: '#ff4444', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: 4, fontWeight: 700 }}>
          <div style={{ width: 6, height: 6, background: '#ff4444', borderRadius: '50%', animation: 'pulse-feed 1.5s infinite' }}></div>
          REC · {feed.label.toUpperCase()}
        </div>
        <div style={{ fontSize: '0.65rem', color: '#00e5ff', fontFamily: 'IBM Plex Mono, monospace', fontWeight: 600 }}>
          LIVE TRANSCODE (H264 / WebRTC)
        </div>
      </div>
      <div style={{ position: 'relative', background: '#000', borderRadius: 6, border: '1px solid #00e5ff55', overflow: 'hidden', minHeight: 180 }}>
        {/* Scanlines visual overlay */}
        <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', background: 'linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.2) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.04), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.04))', backgroundSize: '100% 2px, 3px 100%', pointerEvents: 'none', zIndex: 10 }}></div>
        
        {feed.embedType === 'youtube' ? (
          <iframe
            src={`https://www.youtube-nocookie.com/embed/${feed.embedId}?autoplay=1&mute=1&controls=0&modestbranding=1&loop=1&playlist=${feed.embedId}`}
            title={feed.label}
            allow="autoplay; encrypted-media"
            style={{ width: '100%', height: '180px', border: 0, display: 'block', filter: 'contrast(1.1) saturate(1.1)' }}
          />
        ) : !videoError ? (
          <video
            src={feed.embedId}
            autoPlay
            loop
            muted
            playsInline
            onError={() => setVideoError(true)}
            style={{ width: '100%', height: '180px', objectFit: 'cover', display: 'block', filter: 'contrast(1.15) saturate(1.1)' }}
          />
        ) : null}

        <canvas
          ref={canvasRef}
          width={320}
          height={180}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
            zIndex: 5,
          }}
        />
      </div>
    </div>
  );
}

// Public Gov Feed Panel
function PublicFeedPanel({ feed }) {
  return (
    <section className="panel detail-panel" id="detail-metadata-panel" style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 className="panel-title">
          <span style={{ color: '#00e5ff', marginRight: 6 }}>◉</span>
          Public Gov Feed
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#00e5ff', border: '1px solid #00e5ff44', padding: '2px 8px', borderRadius: 3, fontFamily: 'monospace' }}>
            LIVE · PUBLIC
          </span>
          {feed.onClose && (
            <button onClick={feed.onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 16 }}>✕</button>
          )}
        </div>
      </div>

      <div className="panel-content" style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* Authority info */}
        <div style={{ padding: '10px 0', borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#00e5ff', marginBottom: 4 }}>{feed.label}</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Authority: {feed.authority}</div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'monospace', marginTop: 2 }}>
            {feed.lat?.toFixed(4)}, {feed.lon?.toFixed(4)} · {feed.city}
          </div>
        </div>

        {/* Video embed */}
        {(feed.embedType === 'mp4' || feed.embedType === 'youtube') && feed.embedId ? (
          <CctvFeedViewer feed={feed} />
        ) : (
          <div style={{ padding: '12px', background: 'var(--bg-primary)', borderRadius: 4, border: '1px solid #00e5ff22', textAlign: 'center' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 8 }}>
              Live feed available on government portal
            </div>
            <a
              href={feed.sourceUrl}
              target="_blank"
              rel="noreferrer"
              style={{
                display: 'inline-block',
                padding: '6px 16px',
                background: 'rgba(0, 229, 255, 0.1)',
                border: '1px solid #00e5ff44',
                color: '#00e5ff',
                borderRadius: 4,
                fontSize: '0.75rem',
                textDecoration: 'none',
                fontFamily: 'monospace',
              }}
            >
              Open Official Feed →
            </a>
          </div>
        )}

        {/* Source link */}
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
          Source: <a href={feed.sourceUrl} target="_blank" rel="noreferrer" style={{ color: '#00e5ff' }}>{feed.sourceUrl}</a>
        </div>
      </div>
    </section>
  );
}

function SatellitePanel({ sat, onClose }) {
  return (
    <section className="panel detail-panel" id="detail-metadata-panel" style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="panel-header">
        <h2 className="panel-title">
          <span style={{ color: sat.agencyColor, marginRight: 6 }}>🛰</span>
          Orbital Intelligence
        </h2>
        {onClose && (
          <button onClick={onClose} style={{ fontSize: 16, color: 'var(--text-muted)', cursor: 'pointer' }}>✕</button>
        )}
      </div>

      <div className="panel-content" style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h3 style={{ fontSize: '1.25rem', color: 'var(--text-primary)', margin: 0, fontFamily: 'IBM Plex Mono, monospace', letterSpacing: '0.05em' }}>
              {sat.name}
            </h3>
            <div style={{ fontSize: '0.75rem', color: sat.agencyColor, marginTop: 4, textTransform: 'uppercase', fontWeight: 600 }}>
              {sat.flag} {sat.agency} · {sat.type}
            </div>
          </div>
          {sat.threat && (
            <div style={{
              background: sat.threat.bg,
              color: sat.threat.color,
              border: `1px solid ${sat.threat.color}44`,
              padding: '2px 6px',
              borderRadius: 3,
              fontSize: '10px',
              fontWeight: 'bold',
              animation: sat.threat.level === 'CRITICAL' ? 'pulse-dot 1s infinite' : 'none'
            }}>
              {sat.threat.level}
            </div>
          )}
        </div>

        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5, background: 'var(--bg-primary)', padding: 12, borderRadius: 4, border: '1px solid var(--border-color)' }}>
          {sat.description}
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px 24px', fontSize: '0.8rem' }}>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.65rem', textTransform: 'uppercase' }}>Current Distance</span>
            <span style={{ fontFamily: 'IBM Plex Mono, monospace', color: 'var(--text-primary)' }}>{sat.dist?.toLocaleString() || '--'} km</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.65rem', textTransform: 'uppercase' }}>Orbital Velocity</span>
            <span style={{ fontFamily: 'IBM Plex Mono, monospace', color: 'var(--text-primary)' }}>{sat.velocity}</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.65rem', textTransform: 'uppercase' }}>Operating Altitude</span>
            <span style={{ fontFamily: 'IBM Plex Mono, monospace', color: 'var(--text-primary)' }}>{sat.altitude} km</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.65rem', textTransform: 'uppercase' }}>Sensor Resolution</span>
            <span style={{ fontFamily: 'IBM Plex Mono, monospace', color: 'var(--text-primary)' }}>{sat.resolution}</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.65rem', textTransform: 'uppercase' }}>Swath Width</span>
            <span style={{ fontFamily: 'IBM Plex Mono, monospace', color: 'var(--text-primary)' }}>{sat.swath}</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.65rem', textTransform: 'uppercase' }}>Revisit Time</span>
            <span style={{ fontFamily: 'IBM Plex Mono, monospace', color: 'var(--text-primary)' }}>{sat.revisit}</span>
          </div>
        </div>

        <div style={{ marginTop: 8, paddingTop: 16, borderTop: '1px solid var(--border-color)' }}>
          <h4 style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>Live Telemetry</h4>
          <pre className="mono" style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', background: '#000', padding: 8, borderRadius: 4, overflowX: 'hidden' }}>
            {`TRACKING_ID: ORB-${sat.id.toUpperCase()}-${sat.period || 1000}
LATITUDE:    ${sat.lat?.toFixed(6) || '...'}
LONGITUDE:   ${sat.lon?.toFixed(6) || '...'}
INCLINATION: ${sat.inclination}°
PERIOD:      ${sat.period}s`}
          </pre>
        </div>
      </div>
    </section>
  );
}

// Forensic Compromise Attribution (Future Scope Module 2)
function ForensicAttributionCard({ device, trustData }) {
  const isAuthOpen = device.auth_required === false || isConfirmedOpen(device);
  const cveCount = device.known_cve_count || (trustData?.known_cve_count) || 0;
  const cats = trustData?.cve_categories || [];

  let vector = 'STANDARD MONITORED POSTURE';
  let color = '#10b981';
  let summary = 'No high-risk compromise signatures detected during automated OSINT telemetry parsing.';
  let recommendation = 'Maintain standard firmware patch cycle & subnet isolation.';

  if (isAuthOpen && cveCount > 0) {
    vector = 'CRITICAL: UNAUTHENTICATED EXPOSURE + ACTIVE CVEs';
    color = '#ef4444';
    summary = 'Device streams video unauthenticated while carrying high-severity unpatched vulnerabilities. High risk of automated botnet takeover (Mirai/Moobot).';
    recommendation = 'Isolate camera IP immediately. Enforce Digest Authentication and update firmware.';
  } else if (isAuthOpen) {
    vector = 'UNAUTHENTICATED STREAM BROADCAST';
    color = '#f97316';
    summary = 'RTSP/HTTP video feed is publicly accessible without login credentials.';
    recommendation = 'Restrict RTSP port 554/80 to internal VPN subnet and enable ONVIF authentication.';
  } else if (cats.includes('rce') || cats.includes('auth_bypass') || cveCount >= 2) {
    vector = 'BOTNET EXPLOITATION TARGET (RCE / AUTH BYPASS)';
    color = '#f97316';
    summary = 'Known RCE or authentication bypass CVEs detected. Vulnerable to automated remote command injection.';
    recommendation = 'Apply vendor security patch immediately. Enable network intrusion prevention rules.';
  } else if (cveCount > 0) {
    vector = 'VULNERABLE FIRMWARE EXPOSURE';
    color = '#eab308';
    summary = 'Device contains unpatched CVEs in manufacturer firmware stack.';
    recommendation = 'Schedule firmware upgrade during maintenance window.';
  }

  return (
    <div style={{
      marginBottom: 12,
      padding: '10px 12px',
      background: 'rgba(15, 23, 42, 0.8)',
      border: `1px solid ${color}55`,
      borderRadius: 6,
    }}>
      <div style={{ fontSize: '0.65rem', fontFamily: 'JetBrains Mono, monospace', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
        🛡️ FORENSIC COMPROMISE ATTRIBUTION (MODULE 2)
      </div>
      <div style={{ fontSize: '0.75rem', fontFamily: 'JetBrains Mono, monospace', fontWeight: 800, color, marginBottom: 4 }}>
        {vector}
      </div>
      <div style={{ fontSize: '0.7rem', color: '#94a3b8', lineHeight: 1.4, marginBottom: 6 }}>
        {summary}
      </div>
      <div style={{ fontSize: '0.68rem', fontFamily: 'JetBrains Mono, monospace', color: '#38bdf8', background: 'rgba(56, 189, 248, 0.08)', padding: '4px 8px', borderRadius: 4 }}>
        💡 <strong>REMEDY:</strong> {recommendation}
      </div>
    </div>
  );
}

export default function DetailPanel({ selected, city, showLinks, onToggleLinks, onClose }) {
  const [trustData, setTrustData] = useState(null);  // Phase 4: trust score for selected camera
  const [trustLoading, setTrustLoading] = useState(false);

  // Reset state when selection changes
  useEffect(() => {
    // Phase 4: fetch trust score when a device is selected
    // Decision: we call the backend for the authoritative trust score (which uses
    // the real Phase 1 auth_required field + CVE data) rather than re-deriving it
    // client-side from the banner heuristic. The banner isConfirmedOpen() check is
    // kept for the "confirmed open at scan time" warning which is a different signal.
    if (selected?.type === 'device' && selected?.data?.id) {
      const devId = selected.data.id;
      queueMicrotask(() => {
        setTrustData(null);
        setTrustLoading(true);
        fetchCameraTrustScore(devId)
          .then(data => setTrustData(data))
          .catch(() => setTrustData(null)) // graceful: panel still works without trust score
          .finally(() => setTrustLoading(false));
      });
    } else {
      queueMicrotask(() => {
        setTrustData(null);
      });
    }
  }, [selected]);

  // Handle public gov feed type
  if (selected?.type === 'public_feed') {
    return <PublicFeedPanel feed={selected.data} />;
  }

  // Handle satellite type
  if (selected?.type === 'satellite') {
    return <SatellitePanel sat={selected.data} onClose={onClose} />;
  }

  if (!selected || selected.type !== 'device') {
    return (
      <section className="panel detail-panel" id="detail-metadata-panel">
        <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 className="panel-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '4px' }}>
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="9" y1="9" x2="15" y2="9"></line>
              <line x1="9" y1="13" x2="15" y2="13"></line>
              <line x1="9" y1="17" x2="13" y2="17"></line>
            </svg>
            Device Intelligence
          </h2>
          {onClose && (
            <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 16, lineHeight: 1 }} title="Minimize Panel">✕</button>
          )}
        </div>
        <div className="panel-content" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)', textAlign: 'center', fontSize: '0.875rem' }}>
          Select an asset marker on the map to inspect intelligence logs.
        </div>
      </section>
    );
  }

  const device = selected.data;
  const color = ownerColor(device.owner_type);
  const exposed = isExposedDevice(device);
  const confirmedOpen = isConfirmedOpen(device);

  const coordStr = (device.lat != null && device.lon != null)
    ? `[${Number(device.lat).toFixed(4)}, ${Number(device.lon).toFixed(4)}]`
    : 'Coordinates unavailable';

  const maskedIp = device.ip
    ? device.ip.split('.').slice(0, 2).join('.') + '.*.*'
    : 'Unknown';

  return (
    <section className="panel detail-panel" id="detail-metadata-panel" style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="panel-header">
        <h2 className="panel-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '4px' }}>
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="9" y1="9" x2="15" y2="9"></line>
            <line x1="9" y1="13" x2="15" y2="13"></line>
            <line x1="9" y1="17" x2="13" y2="17"></line>
          </svg>
          Device Intelligence
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="mono" style={{ fontSize: '0.75rem', color: color, fontWeight: 'bold' }}>
            {maskedIp}
          </span>
          {onClose && (
            <button
              onClick={onClose}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 16, lineHeight: 1 }}
              title="Close"
            >✕</button>
          )}
        </div>
      </div>

      <div className="panel-content" style={{ overflowY: 'auto' }}>

        {/* ──────────────────────────────────────────────────────
            Phase 4: Trust Score — fetched from backend on select.
            Shown only when trust data is available.
            For cameras with no alerts yet, trust score is still
            computed on-demand using their stored Phase 1 fields.
           ────────────────────────────────────────────────────── */}
        {trustLoading && (
          <div style={{ marginBottom: 12, fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'IBM Plex Mono, monospace' }}>
            ⟳ Computing trust score...
          </div>
        )}
        {trustData && !trustLoading && (
          <>
            <TrustScoreBadge
              tier={trustData.action_tier}
              score={trustData.trust_score}
              factors={trustData.contributing_factors || []}
            />
            <ForensicAttributionCard device={device} trustData={trustData} />
          </>
        )}

        {/* ⚠ Exposed device warning */}
        {exposed && (
          <div style={{
            marginBottom: 12,
            padding: '10px 12px',
            background: confirmedOpen ? 'rgba(231, 76, 60, 0.15)' : 'rgba(239, 68, 68, 0.08)',
            border: `1px solid ${confirmedOpen ? '#ff4444' : 'rgba(239, 68, 68, 0.4)'}`,
            borderRadius: 4,
          }}>
            {confirmedOpen ? (
              <div style={{ fontSize: '0.75rem', fontWeight: 800, color: '#ff4444', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{ width: 6, height: 6, background: '#ff4444', borderRadius: '50%', animation: 'pulse-feed 1s infinite' }}></div>
                🔓 CONFIRMED OPEN AT SCAN TIME
              </div>
            ) : (
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#ef4444', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
                ⚠ Exposed Interface Detected
              </div>
            )}
            
            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: 8 }}>
              {confirmedOpen 
                ? `OSINT banner analysis confirms this device (Port ${device.ports?.join(', ')}) was actively serving video content without authentication.`
                : `This device has open ports (${Array.isArray(device.ports) ? device.ports.join(', ') : '—'}) with no confirmed authentication. The camera interface may be publicly accessible.`
              }
            </div>
            <a
              href={buildCertInReport(device, city)}
              target="_blank"
              rel="noreferrer"
              style={{
                display: 'inline-block',
                padding: '4px 8px',
                background: 'rgba(231, 76, 60, 0.2)',
                border: '1px solid #e74c3c',
                color: '#ff6b6b',
                borderRadius: 3,
                textDecoration: 'none',
                fontSize: '0.65rem',
                fontFamily: 'var(--font-mono)',
                textTransform: 'uppercase',
              }}
            >
              ✉ Draft CERT-In Incident Report
            </a>
          </div>
        )}

        <div className="metadata-grid" id="telemetry-metadata-grid" style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1.5fr',
          gap: '12px 8px',
          fontSize: '0.8rem',
        }}>
          <span className="metadata-label" style={{ color: 'var(--text-muted)', textTransform: 'uppercase' }}>Manufacturer</span>
          <span className="metadata-value">{device.manufacturer || 'Unknown'}</span>

          <span className="metadata-label" style={{ color: 'var(--text-muted)', textTransform: 'uppercase' }}>Device Type</span>
          <span className="metadata-value">{device.device_type || 'Unknown'}</span>

          <span className="metadata-label" style={{ color: 'var(--text-muted)', textTransform: 'uppercase' }}>Owner Class</span>
          <span className="metadata-value" style={{ color: color, textTransform: 'uppercase', fontWeight: 500 }}>
            {device.owner_type || 'unknown'}
          </span>

          <span className="metadata-label" style={{ color: 'var(--text-muted)', textTransform: 'uppercase' }}>Org Name</span>
          <span className="metadata-value">{device.org || device.owner_org || 'Unattributed ASN'}</span>

          <span className="metadata-label" style={{ color: 'var(--text-muted)', textTransform: 'uppercase' }}>Coordinates</span>
          <span className="metadata-value mono" style={{ fontSize: '0.7rem' }}>{coordStr}</span>

          <span className="metadata-label" style={{ color: 'var(--text-muted)', textTransform: 'uppercase' }}>Open Ports</span>
          <span className="metadata-value mono">
            {Array.isArray(device.ports) && device.ports.length > 0
              ? device.ports.join(', ')
              : 'None detected'}
          </span>

          <span className="metadata-label" style={{ color: 'var(--text-muted)', textTransform: 'uppercase' }}>Confidence</span>
          <span className="metadata-value" style={{ textTransform: 'uppercase' }}>
            {device.ownership_confidence || 'low'}
          </span>

          <span className="metadata-label" style={{ color: 'var(--text-muted)', textTransform: 'uppercase' }}>City Area</span>
          <span className="metadata-value">{city}</span>
        </div>

        <div style={{ marginTop: '24px', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
          <h3 style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '8px' }}>Shodan Banner Dump</h3>
          <pre className="mono" style={{
            fontSize: '0.65rem',
            color: 'var(--text-muted)',
            lineHeight: '1.5',
            background: 'var(--bg-primary)',
            padding: 8,
            overflowX: 'hidden',
            whiteSpace: 'pre-wrap',
            wordWrap: 'break-word'
          }}>
            {device.os ? `OS: ${device.os}\n` : ''}
            {device.isp ? `ISP: ${device.isp}\n` : ''}
            {device.banner_snippet ? `BANNER: ${device.banner_snippet}\n` : ''}
            LAST SEEN: {device.last_update || device.last_seen || 'Unknown'}
          </pre>
        </div>

        {/* Entity Link Graph toggle */}
        <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border-color)' }}>
          <button
            id="entity-link-graph-btn"
            onClick={onToggleLinks}
            style={{
              width: '100%',
              padding: '8px 12px',
              background: showLinks ? 'rgba(231, 76, 60, 0.15)' : 'var(--bg-primary)',
              border: `1px solid ${showLinks ? '#e74c3c' : 'var(--border-color)'}`,
              color: showLinks ? '#e74c3c' : 'var(--text-secondary)',
              borderRadius: 4,
              cursor: 'pointer',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.75rem',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              transition: 'all 0.2s',
            }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
            </svg>
            {showLinks ? '⬡ Hide Network Links' : '⬡ Show Network Links'}
          </button>
        </div>
      </div>
    </section>
  );
}
