# COBRA-WATCH: Ethics, Authorization, and Data Governance Policy

**Project**: Geospatial Camera Exposure Intelligence Platform (COBRA-WATCH)  
**Academic Context**: Final Year B.Tech Research Project — Indian Institute of Technology Bombay (IIT Bombay)  
**Version**: 2.0 (Post-Red Team Hardening Release)  
**Date**: August 2026  

---

## 1. Executive Summary & Purpose

COBRA-WATCH is a research and civic-transparency platform designed to evaluate and enhance the **integrity and cyber-resilience of municipal and public surveillance infrastructures**. By analyzing open-source intelligence (OSINT), public vulnerability disclosures (NVD/CISA KEV), and spatial-temporal corroboration dynamics, the system quantifies the reliability of physical alert signals prior to operational dispatch.

This document establishes the **strict ethical boundaries, legal compliance standards, and architectural scope restrictions** governing COBRA-WATCH.

---

## 2. In-Scope vs. Out-of-Scope Data Sources

To adhere to national cyber law and international research ethics, the platform enforces strict data ingestion boundaries:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                             COBRA-WATCH SCOPE                            │
├─────────────────────────────────────┬────────────────────────────────────┤
│         PERMITTED / IN-SCOPE        │     STRICTLY PROHIBITED / OUT      │
├─────────────────────────────────────┼────────────────────────────────────┤
│ • Public OSINT metadata (Shodan API)│ • Interception of live video feeds │
│ • Public banners & port states      │ • Credential bruteforcing / VAPT   │
│ • Public NVD & CISA KEV CVE catalogs│ • Exploitation of target devices   │
│ • Public WHOIS IP registration data │ • Personally Identifiable Info     │
│ • Pre-authorized recorded footage   │ • Facial recognition / biometrics  │
│ • Synthetic & labeled eval datasets │ • Unauthorized private LAN probes  │
└─────────────────────────────────────┴────────────────────────────────────┘
```

### 2.1 Permitted Data Sources (In-Scope)
1. **Public IP Metadata**: Discovery of internet-connected CCTV interfaces indexed by commercial search engines (Shodan, Censys) using passive querying.
2. **Vulnerability Catalogs**: National Vulnerability Database (NVD) CVE entries, CWE classifications, and CISA Known Exploited Vulnerabilities (KEV) catalog.
3. **Autonomous System & WHOIS Data**: Public ARIN/APNIC IP allocation records used exclusively for broad categorization (`government`, `telecom`, `corporate`, `unknown`).
4. **Authorized Recorded Footage**: Video pipeline evaluation executed **only on pre-authorized, non-live benchmark datasets** (AVSS, PETS, labeled lab footage) to test rule-based spatio-temporal reasoning.

### 2.2 Strictly Prohibited Activities (Out-of-Scope)
- **Zero Active Exploitation**: The platform never executes exploits, shell injection, or credential attacks against identified IP cameras.
- **Zero Live Stream Interception**: The platform does not intercept or stream live video from discovered public cameras.
- **Zero Biometric / PII Processing**: No facial recognition, license plate recognition (ALPR), or personal identity tracking is implemented or permitted.

---

## 3. Architectural Restriction: Non-Live Recorded Footage Boundary

The video AI detection module (`video_pipeline/`) is architecturally decoupled from external network discovery:
1. **Air-Gapped Video Processing**: Detection models (YOLOv8, SORT, background subtraction) execute purely on local MP4/AVI files in `sample_footage/` or explicit test fixtures.
2. **Simulation Contract**: Physical detections are converted into JSON event payloads (`DetectionEvent`) that pass through the trust score engine.
3. **No Direct RTSP/HTTP Hooking**: The ingestion pipeline rejects dynamic live RTSP URLs from public devices, eliminating any risk of unauthorized visual surveillance capture.

---

## 4. Legal Compliance Framework (Indian Law)

COBRA-WATCH operates in full alignment with the following Indian statutory and constitutional frameworks:

### 4.1 Digital Personal Data Protection Act (DPDP Act 2023)
- **Data Minimization (§6)**: The platform stores only device IP, manufacturer, port, and security posture. No personal data of citizens is collected, stored, or processed.
- **Exclusion of Non-Personal Data**: Device vulnerability statistics and municipal camera locations are non-personal infrastructure data outside the scope of individual consent requirements.

### 4.2 Information Technology Act, 2000 & Amendments
- **Section 43 & Section 66**: Strict prohibition against unauthorized access, data extraction, or system damage. COBRA-WATCH performs no active port manipulation, packet injection, or penetration testing against third-party systems.
- **Section 69 & 69A Compliance**: The platform supports legitimate security auditing and defense transparency for public smart-city infrastructure.

### 4.3 Constitutional Privacy (Justice K.S. Puttaswamy v. Union of India, 2017)
- The Supreme Court of India recognized privacy as a fundamental right under Article 21, subject to the test of **legality, necessity, and proportionality**.
- COBRA-WATCH serves public necessity by identifying insecure surveillance nodes that could be weaponized by threat actors (e.g., Mirai/Moobot botnets) to violate citizen privacy or launch DDoS attacks against national critical infrastructure.

---

## 5. Dual-Use and Responsible Disclosure

### 5.1 Dual-Use Acknowledgment
Surveillance discovery platforms present inherent dual-use risks:
- **Defensive Utility**: Enables municipal authorities and security analysts to identify and patch vulnerable cameras, preventing adversarial botnet recruitment and false-alert injection.
- **Potential Offensive Abuse**: Adversaries could attempt to use aggregated vulnerability maps as target lists.

### 5.2 Mitigation by Design
To neutralize dual-use risks, COBRA-WATCH implements:
1. **API Key Authentication**: Ingestion and verdict endpoints require cryptographic API keys (`X-API-Key`).
2. **Per-Camera Rate Limiting**: Anti-flooding controls prevent automated reconnaissance abuse.
3. **Cryptographic Audit Ledger**: All decisions are permanently hashed into an immutable Merkle chain with external anchoring (`GET /api/audit/anchor`), preventing operator denial or silent data manipulation.
4. **Responsible Disclosure Commitment**: Unpatched critical vulnerabilities (CVSS $\ge 9.0$) discovered during municipal scans will be reported to CERT-In (Indian Computer Emergency Response Team) and respective city administration departments prior to public dissemination.

---

## 6. City-Specific Oversight Policies

| City | Primary Governing Bodies | Data Retention Policy | Statutory Framework |
|---|---|---|---|
| **Mumbai** | MMRDA, Mumbai Traffic Police | 30-Day Audit Baseline | DPDP Act 2023 & IT Act §69 |
| **Delhi** | PWD, Delhi Police | 30-Day Scheme Baseline | Delhi PWD CCTV Scheme & DPDP 2023 |
| **Bangalore** | BBMP, Bangalore Traffic Police (BTP) | 30-Day Audit Baseline | Smart City SPV & DPDP Act 2023 |
| **Hyderabad** | GHMC, Cyberabad Police | 30-Day Audit Baseline | Telangana Smart City Initiative |
| **Chennai** | Greater Chennai Corporation, TNeGA | 30-Day Policy Baseline | Tamil Nadu e-Governance Policy |
| **All India** | CERT-In, Ministry of Electronics & IT | Continuous Oversight | IT Act 2000 / CERT-In Directions 2022 |

---

## 7. Policy Affirmation

By deploying or extending COBRA-WATCH, researchers and operators affirm that they will not use this platform to intercept private video feeds, launch cyber attacks, or process biometric citizen data. COBRA-WATCH exists solely to make critical public infrastructure secure, trustworthy, and transparent.
