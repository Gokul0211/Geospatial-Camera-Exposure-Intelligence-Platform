/**
 * Legal framework data per city — hardcoded from real research.
 * Sources: IT Act 2000, The Surveillance Project (India), Article 21 case law.
 * 
 * This takes 10 minutes to research and massively elevates the demo.
 * Update these before the hackathon with verified information.
 */
export const LEGAL_FRAMEWORKS = {
  Mumbai: {
    framework: 'No dedicated CCTV regulation',
    detail: 'Governed by IT Act 2000 §69, Telegraph Act 1885 §5(2). No specific municipal CCTV oversight law.',
    oversight: 'Limited',
    dataRetention: 'No mandated policy',
    badge: '⚠ No CCTV-specific regulation',
    badgeColor: '#d68910',
  },
  Delhi: {
    framework: 'Delhi CCTV Camera Scheme (state-funded)',
    detail: 'Largest state-funded CCTV program in India. 1.4L cameras installed. Limited public audit mechanism.',
    oversight: 'State government oversight',
    dataRetention: '30 days (reported, not verified)',
    badge: '⚠ Limited public audit',
    badgeColor: '#d68910',
  },
  Bangalore: {
    framework: 'Smart City Mission guidelines',
    detail: 'BBMP Smart City program. AI-enabled cameras under central Smart City Mission. No state-specific surveillance law.',
    oversight: 'Smart City SPV',
    dataRetention: 'Not publicly disclosed',
    badge: '⚠ No state surveillance law',
    badgeColor: '#c0392b',
  },
};

export function getLegalBadge(city) {
  return LEGAL_FRAMEWORKS[city] || null;
}
