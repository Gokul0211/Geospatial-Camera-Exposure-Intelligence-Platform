export const OWNER_COLORS = {
  government: '#c0392b',
  corporate:  '#d68910',
  telecom:    '#7d6608',
  unknown:    '#4a4a4a',
};

export const OWNER_LABELS = {
  government: 'Government',
  corporate:  'Corporate',
  telecom:    'Telecom',
  unknown:    'Unknown',
};

export const RISK_COLORS = {
  CRITICAL: '#922b21',
  HIGH:     '#c0392b',
  MEDIUM:   '#d68910',
  LOW:      '#1e8449',
};

export const RISK_LABELS = {
  CRITICAL: 'Critical',
  HIGH:     'High',
  MEDIUM:   'Medium',
  LOW:      'Low',
};

export function ownerColor(ownerType) {
  if (!ownerType) return OWNER_COLORS.unknown;
  return OWNER_COLORS[ownerType.toLowerCase()] || OWNER_COLORS.unknown;
}
