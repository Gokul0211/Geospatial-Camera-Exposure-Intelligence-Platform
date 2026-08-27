/**
 * Legal framework data per city — hardcoded from real research.
 * Sources: IT Act 2000, The Surveillance Project (India), Article 21 case law.
 * 
 * This takes 10 minutes to research and massively elevates the demo.
 * Update these before the hackathon with verified information.
 */
export const LEGAL_FRAMEWORKS = {
  Mumbai: {
    framework: 'DPDP Act 2023 & IT Act §69',
    detail: 'Surveillance data governed under Digital Personal Data Protection Act 2023 & IT Act §69. Municipal oversight via MMRDA & Mumbai Traffic Police.',
    oversight: 'State Police & IT Ministry',
    dataRetention: '30-Day Mandatory Retention',
    badge: '⚖ DPDP ACT 2023 · IT ACT §69',
    badgeColor: '#00e5ff',
  },
  Delhi: {
    framework: 'Delhi PWD CCTV Scheme & DPDP Act 2023',
    detail: 'State-funded CCTV network under PWD & Delhi Police oversight. Governed by DPDP Act 2023 baseline standards.',
    oversight: 'Delhi Police & PWD Oversight',
    dataRetention: '30-Day Policy Baseline',
    badge: '⚖ PWD SCHEME · DPDP COMPLIANT',
    badgeColor: '#00e5ff',
  },
  Bangalore: {
    framework: 'Smart City SPV & DPDP Act 2023',
    detail: 'BBMP AI-enabled Smart City surveillance under Ministry of Housing & Urban Affairs & DPDP Act 2023 privacy framework.',
    oversight: 'Smart City SPV & BTP',
    dataRetention: '30-Day Audit Baseline',
    badge: '⚖ SMART CITY GOVERNANCE',
    badgeColor: '#00e5ff',
  },
};

export function getLegalBadge(city) {
  return LEGAL_FRAMEWORKS[city] || null;
}
