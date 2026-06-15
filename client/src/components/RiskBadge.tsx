import { RiskTier } from '@/types';

const TIER_CONFIG: Record<RiskTier, { label: string; bg: string; text: string; dot: string }> = {
  PRIORITY: { label: 'Priority',  bg: 'bg-red-50',    text: 'text-red-700',    dot: 'bg-red-500'    },
  ESCALATE: { label: 'Escalate',  bg: 'bg-orange-50', text: 'text-orange-700', dot: 'bg-orange-500' },
  STANDARD: { label: 'Standard',  bg: 'bg-amber-50',  text: 'text-amber-700',  dot: 'bg-amber-500'  },
  MONITOR:  { label: 'Monitor',   bg: 'bg-blue-50',   text: 'text-blue-700',   dot: 'bg-blue-500'   },
  NONE:     { label: 'Safe',      bg: 'bg-green-50',  text: 'text-green-700',  dot: 'bg-green-500'  },
};

interface Props {
  tier: RiskTier;
  size?: 'sm' | 'md';
  dot?: boolean;
}

export default function RiskBadge({ tier, size = 'sm', dot = true }: Props) {
  const cfg = TIER_CONFIG[tier] || TIER_CONFIG.NONE;
  return (
    <span className={`inline-flex items-center gap-1.5 font-semibold rounded-full ${cfg.bg} ${cfg.text} ${
      size === 'sm' ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1'
    }`}>
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot} shrink-0`} />}
      {cfg.label}
    </span>
  );
}

export function tierColor(tier: RiskTier): string {
  const map: Record<RiskTier, string> = {
    PRIORITY: '#dc2626',
    ESCALATE: '#ea580c',
    STANDARD: '#ca8a04',
    MONITOR:  '#2563eb',
    NONE:     '#16a34a',
  };
  return map[tier] || '#64748b';
}

export function tierBgColor(tier: RiskTier): string {
  const map: Record<RiskTier, string> = {
    PRIORITY: '#fee2e2',
    ESCALATE: '#ffedd5',
    STANDARD: '#fef9c3',
    MONITOR:  '#dbeafe',
    NONE:     '#dcfce7',
  };
  return map[tier] || '#f1f5f9';
}
