# Censys research-access application: draft answers

_Drafted 2026-10-10 from the project record. Fill the bracketed items yourself; edit anything that is not true of your plan before sending._

## 1. Mentor
Name: [mentor name]. Department and institution: [department, institution]. Faculty page: [URL].
(Institutional e-mail omitted on request.) Role: [supervises the project / co-author].

## 2. Clarification of research question 1
**RQ1 (clarified).** Using only the longitudinal *service metadata* that Censys records for internet-exposed IP cameras (banners, HTTP
headers, firmware/version strings, TLS certificates and open-port sets), how often do host fingerprints change for benign reasons
(firmware updates, certificate renewal, address reassignment) versus patterns consistent with device substitution, and can a
statistical drift test calibrated on this history flag substitution-like changes at a controlled false-alarm rate?

**Data-handling confirmation.** The study will rely only on Censys metadata. We will not connect to, probe, authenticate to, view or
record any camera feed, and we will send no traffic of any kind to any host that appears in the dataset. Video-stream analysis is a
separate part of the wider project; it uses only public benchmark datasets and, if built, cameras owned by the researchers in a
laboratory, and never any host identified through Censys.

**Ethics.** Passive analysis only; no personal data; third-party IP addresses are hashed or aggregated (to ASN or country) in all
analysis outputs and publications; raw Censys records are not redistributed; Censys terms are followed; critical findings would be
reported to the relevant CERT before publication; results are shared with the community through publication, as the programme requires.

## 3. Target venue
No submission yet; manuscript in preparation. Primary target: *IEEE Transactions on Information Forensics and Security*.
Alternatives considered: *IEEE Transactions on Dependable and Secure Computing*, *Computers & Security*.

## Before you send
- The repository contains an optional **heartbeat module** (`backend/services/heartbeat_service.py`, routes under `/api/heartbeat/`) that opens TCP
  connections to a device IP. It is not part of scoring, but it contradicts "no traffic to any host in the dataset" if it were ever run on
  Censys-discovered hosts. It must stay unused for this study; see `TODO.md`.
- "If built, cameras owned by the researchers" reflects the proposed testbed in `Q1.md`, which is not yet decided; delete it if you do not plan it.
