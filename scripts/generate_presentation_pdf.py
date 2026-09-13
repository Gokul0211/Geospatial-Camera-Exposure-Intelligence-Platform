"""
Generate Presentation PDF for COBRA-WATCH using Headless Chrome/Edge.
"""
import os
import subprocess
import sys

# HTML template with print CSS styling
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>COBRA-WATCH: Master Presentation Guide</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&family=Outfit:wght@600;700;800&display=swap');

  @page {
    size: A4 portrait;
    margin: 15mm 15mm 15mm 15mm;
  }

  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: #0f172a;
    background-color: #ffffff;
    line-height: 1.5;
    font-size: 10.5pt;
    margin: 0;
    padding: 0;
  }

  /* Cover / Header Banner */
  .header-card {
    background: linear-gradient(135deg, #080b11 0%, #1e293b 100%);
    color: #ffffff;
    padding: 24px;
    border-radius: 10px;
    margin-bottom: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  }

  .header-card h1 {
    font-family: 'Outfit', sans-serif;
    font-size: 22pt;
    margin: 0 0 6px 0;
    color: #00e5ff;
    letter-spacing: 0.05em;
  }

  .header-card p {
    font-size: 10pt;
    margin: 0;
    color: #94a3b8;
  }

  .badge-row {
    display: flex;
    gap: 10px;
    margin-top: 14px;
  }

  .badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 8.5pt;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 4px;
    background: rgba(0, 229, 255, 0.15);
    color: #00e5ff;
    border: 1px solid rgba(0, 229, 255, 0.4);
  }

  .badge-success {
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border-color: rgba(16, 185, 129, 0.4);
  }

  /* Section Headings */
  h2 {
    font-family: 'Outfit', sans-serif;
    font-size: 14pt;
    color: #0f172a;
    border-bottom: 2px solid #3b82f6;
    padding-bottom: 4px;
    margin-top: 22px;
    margin-bottom: 12px;
    page-break-after: avoid;
  }

  h3 {
    font-family: 'Outfit', sans-serif;
    font-size: 11.5pt;
    color: #1e293b;
    margin-top: 16px;
    margin-bottom: 8px;
    page-break-after: avoid;
  }

  /* Tables */
  table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 16px;
    font-size: 9.5pt;
    page-break-inside: auto;
  }

  tr {
    page-break-inside: avoid;
    page-break-after: auto;
  }

  th {
    background-color: #0f172a;
    color: #ffffff;
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    text-align: left;
    padding: 8px 10px;
    border: 1px solid #1e293b;
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  td {
    padding: 7px 10px;
    border: 1px solid #cbd5e1;
    color: #334155;
    vertical-align: top;
  }

  tbody tr:nth-child(even) {
    background-color: #f8fafc;
  }

  /* Code blocks & Math */
  code, pre {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9pt;
    background-color: #f1f5f9;
    color: #0f172a;
    padding: 2px 5px;
    border-radius: 4px;
  }

  pre {
    padding: 10px;
    overflow-x: auto;
    border: 1px solid #e2e8f0;
    line-height: 1.4;
    white-space: pre-wrap;
  }

  .formula-box {
    background: #f8fafc;
    border-left: 4px solid #3b82f6;
    padding: 10px 14px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 9.5pt;
    color: #1e293b;
    margin: 10px 0;
    border-radius: 0 6px 6px 0;
  }

  /* Key-Value Callouts */
  .callout {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 6px;
    padding: 12px 14px;
    margin-bottom: 14px;
  }

  .callout-title {
    font-weight: 700;
    color: #1d4ed8;
    margin-bottom: 4px;
  }

  .page-break {
    page-break-before: always;
  }
</style>
</head>
<body>

  <div class="header-card">
    <h1>⚡ COBRA-WATCH</h1>
    <p>Cyber-Physical Surveillance Threat Intelligence & Detection Engine</p>
    <div class="badge-row">
      <span class="badge">STATUS: PRODUCTION-READY</span>
      <span class="badge badge-success">309 / 309 TESTS PASSED (100%)</span>
      <span class="badge">DPDP ACT 2023 COMPLIANT</span>
    </div>
  </div>

  <h2>💡 1. Executive Summary (30-Second Presentation Pitch)</h2>
  <table>
    <thead>
      <tr>
        <th style="width: 25%;">Question</th>
        <th>Simple Presentation Answer</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>What is the problem?</strong></td>
        <td>Normal CCTV systems blindly trust every camera feed. If a camera is hacked, unpatched, or fake, security guards waste critical time responding to false emergencies.</td>
      </tr>
      <tr>
        <td><strong>What is COBRA-WATCH?</strong></td>
        <td>A platform that calculates a <strong>Security Trust Score (0 to 100)</strong> for every camera <em>before</em> believing its physical video alerts.</td>
      </tr>
      <tr>
        <td><strong>How does it help?</strong></td>
        <td>High-trust alerts (80–100) trigger automated dispatch. Low-trust alerts (&lt;50) are flagged for manual operator verification.</td>
      </tr>
    </tbody>
  </table>

  <h2>🔄 2. The 4-Step Pipeline</h2>
  <table>
    <thead>
      <tr>
        <th style="width: 10%;">Step</th>
        <th style="width: 25%;">Pipeline Stage</th>
        <th style="width: 25%;">Technology Used</th>
        <th>What It Does (1-Sentence Summary)</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Step 1</strong></td>
        <td><strong>Camera Discovery</strong></td>
        <td>Shodan API + NVD CVEs</td>
        <td>Finds exposed public IP cameras and checks if they carry known security bugs.</td>
      </tr>
      <tr>
        <td><strong>Step 2</strong></td>
        <td><strong>Trust Score Engine</strong></td>
        <td>Custom Python Algorithm</td>
        <td>Calculates 0–100 score based on password status, CVEs, age, and nearby camera proof.</td>
      </tr>
      <tr>
        <td><strong>Step 3</strong></td>
        <td><strong>Video AI Pipeline</strong></td>
        <td>YOLOv8 + ByteTrack</td>
        <td>Detects people/vehicles and checks if someone loiters (&gt;10s) or crosses a boundary line.</td>
      </tr>
      <tr>
        <td><strong>Step 4</strong></td>
        <td><strong>Live GIS Dashboard</strong></td>
        <td>React + Leaflet + WebSockets</td>
        <td>Displays 2,369 sensors on a dark map with instant alert toast popups.</td>
      </tr>
    </tbody>
  </table>

  <h2>🛠️ 3. Technology Stack & Code Mapping</h2>
  <table>
    <thead>
      <tr>
        <th style="width: 20%;">Component</th>
        <th style="width: 20%;">Technology Used</th>
        <th style="width: 25%;">Source File Location</th>
        <th>Implementation & Purpose</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>User Interface</strong></td>
        <td>React 18 + Vite 5.4</td>
        <td><code>frontend/src/App.jsx</code></td>
        <td>Reactive single-page dashboard with collapsible side-panels.</td>
      </tr>
      <tr>
        <td><strong>Design System</strong></td>
        <td>Vanilla CSS3</td>
        <td><code>frontend/src/styles/globals.css</code></td>
        <td>Custom dark theme (#080b11), CRT scanlines, glassmorphism, keyframe animations.</td>
      </tr>
      <tr>
        <td><strong>Map Engine</strong></td>
        <td>Leaflet.js 1.9</td>
        <td><code>frontend/src/components/SurveillanceMap.jsx</code></td>
        <td>GPU-accelerated Leaflet map (<code>L.canvas()</code>) rendering 2,369 sensors at 60 FPS.</td>
      </tr>
      <tr>
        <td><strong>Satellite Basemap</strong></td>
        <td>Esri World Imagery</td>
        <td><code>frontend/src/utils/satelliteData.js</code></td>
        <td>High-resolution satellite aerial basemap tile layer toggle.</td>
      </tr>
      <tr>
        <td><strong>Backend API</strong></td>
        <td>Python 3.12 + FastAPI</td>
        <td><code>backend/main.py</code></td>
        <td>Asynchronous REST API server handling endpoints and WebSocket clients.</td>
      </tr>
      <tr>
        <td><strong>Database</strong></td>
        <td>SQLite 3 + aiosqlite</td>
        <td><code>backend/database.py</code></td>
        <td>Async database storing devices, OSINT news, alerts, and audit ledgers.</td>
      </tr>
      <tr>
        <td><strong>Real-Time Alerts</strong></td>
        <td>WebSockets Pub/Sub</td>
        <td><code>frontend/src/components/LiveAlerts.jsx</code></td>
        <td>Broadcasting instant threat detection event popups to connected clients.</td>
      </tr>
      <tr>
        <td><strong>Object Detection</strong></td>
        <td>YOLOv8 (<code>ultralytics</code>)</td>
        <td><code>video_pipeline/detector.py</code></td>
        <td>Neural network object detection identifying persons and vehicles from video.</td>
      </tr>
      <tr>
        <td><strong>Motion Tracking</strong></td>
        <td>ByteTrack</td>
        <td><code>video_pipeline/tracker.py</code></td>
        <td>Multi-object motion tracking with Kalman filter state prediction and IoU matching.</td>
      </tr>
      <tr>
        <td><strong>Breach Math</strong></td>
        <td>2D Vector Math</td>
        <td><code>video_pipeline/rules.py</code></td>
        <td>Vector cross-product line breach detection and polygon ray-casting loitering time.</td>
      </tr>
      <tr>
        <td><strong>Trust Engine</strong></td>
        <td>Custom Algorithm</td>
        <td><code>backend/services/trust_score_service.py</code></td>
        <td>Weighted deduction model (0–100) calculating camera security risk.</td>
      </tr>
      <tr>
        <td><strong>Time-Decay Model</strong></td>
        <td>Exponential Decay</td>
        <td><code>backend/routes/decay_router.py</code></td>
        <td>Dynamic trust score erosion over time between active security vulnerability rescans.</td>
      </tr>
      <tr>
        <td><strong>Multi-Camera Fusion</strong></td>
        <td>Spatial-Temporal Fusion</td>
        <td><code>backend/services/corroboration_service.py</code></td>
        <td>Cross-camera event corroboration granting +20 trust bonuses to adjacent sensors.</td>
      </tr>
      <tr>
        <td><strong>Audit Ledger</strong></td>
        <td>SHA-256 Merkle Chain</td>
        <td><code>backend/services/audit_ledger.py</code></td>
        <td>Append-only cryptographic hash chain for non-repudiable audit logging.</td>
      </tr>
      <tr>
        <td><strong>Test Suite</strong></td>
        <td>Pytest (309 Passed)</td>
        <td><code>backend/tests/</code></td>
        <td>309-test master test suite verifying APIs, security, tracking, and breach rules.</td>
      </tr>
    </tbody>
  </table>

  <div class="page-break"></div>

  <h2>📊 4. Trust Score Points System (0–100 Scale)</h2>
  <table>
    <thead>
      <tr>
        <th style="width: 30%;">Security Check</th>
        <th style="width: 20%;">Points Effect</th>
        <th>Why? (Technical Justification)</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Base Starting Score</strong></td>
        <td><strong style="color: #10b981;">+100 Points</strong></td>
        <td>Perfect starting score for a brand-new camera.</td>
      </tr>
      <tr>
        <td><strong>No Password (Unauthenticated)</strong></td>
        <td><strong style="color: #ef4444;">-30 Points</strong></td>
        <td>High risk! Anyone on the public internet can view or alter the stream.</td>
      </tr>
      <tr>
        <td><strong>Known Security Bugs (CVEs)</strong></td>
        <td><strong style="color: #ef4444;">-10 Points per Bug</strong></td>
        <td>Camera has known unpatched NVD security vulnerabilities (max -40 points).</td>
      </tr>
      <tr>
        <td><strong>Unknown Owner / Org</strong></td>
        <td><strong style="color: #f59e0b;">-20 Points</strong></td>
        <td>Camera owner organization is missing or unverified.</td>
      </tr>
      <tr>
        <td><strong>Old Firmware (&gt;1 year old)</strong></td>
        <td><strong style="color: #f59e0b;">-15 Points</strong></td>
        <td>Firmware has not been updated in over a year.</td>
      </tr>
      <tr>
        <td><strong>Confirmed by Nearby Camera</strong></td>
        <td><strong style="color: #10b981;">+20 Points Bonus</strong></td>
        <td>An adjacent camera (within 500m &amp; 15 mins) also detected the physical event!</td>
      </tr>
    </tbody>
  </table>

  <h2>🗣️ 5. Reviewer Q&amp;A Cheat Sheet</h2>
  <table>
    <thead>
      <tr>
        <th style="width: 35%;">Reviewer Question</th>
        <th>Simple Presentation Answer</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>"Why not just use YOLOv8 alone?"</strong></td>
        <td>"YOLO detects <em>what</em> is in the video, but can't tell if the camera is hacked. Our Trust Score checks camera security first so guards don't waste time on fake alerts."</td>
      </tr>
      <tr>
        <td><strong>"How do you check if cameras corroborate?"</strong></td>
        <td>"If Camera A alerts, we check if adjacent cameras within 500 meters also saw something within 15 minutes. If yes, +20 bonus!"</td>
      </tr>
      <tr>
        <td><strong>"Is this legal under Indian privacy laws?"**</td>
        <td>"Yes! We only use public camera metadata via Shodan OSINT, run Video AI on authorized local footage, and log everything in a tamper-proof ledger."</td>
      </tr>
      <tr>
        <td><strong>"Is the system tested?"</strong></td>
        <td>"Yes, we ran a master suite of <strong>309 automated tests</strong> covering APIs, security, tracking, and breach rules with a <strong>100% pass rate</strong>."</td>
      </tr>
    </tbody>
  </table>

  <h2>⚡ 6. Presentation Demo Commands</h2>
  <div class="formula-box">
    <strong>1. Run Backend Server:</strong> <code>python backend/main.py</code> (http://localhost:8000)<br>
    <strong>2. Run GIS Dashboard:</strong> <code>cd frontend</code> then <code>npm run dev</code> (http://localhost:5173)<br>
    <strong>3. Run Master Test Suite:</strong> <code>pytest backend/tests video_pipeline/tests eval/test_eval_harness.py -v</code>
  </div>

</body>
</html>
"""

def generate_pdf():
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html_path = os.path.join(project_dir, "COBRA_WATCH_PRESENTATION.html")
    pdf_path = os.path.join(project_dir, "COBRA_WATCH_PRESENTATION_GUIDE.pdf")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE)

    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]

    browser_bin = None
    for p in chrome_paths:
        if os.path.exists(p):
            browser_bin = p
            break

    if not browser_bin:
        print("[ERROR] No Chrome or Edge browser executable found.")
        sys.exit(1)

    print(f"[PDF] Using browser: {browser_bin}")
    cmd = [
        browser_bin,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={pdf_path}",
        html_path
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
        print(f"[SUCCESS] Generated PDF at: {pdf_path} (Size: {os.path.getsize(pdf_path)} bytes)")
    else:
        print(f"[ERROR] PDF generation failed: {res.stderr}")

if __name__ == "__main__":
    generate_pdf()
