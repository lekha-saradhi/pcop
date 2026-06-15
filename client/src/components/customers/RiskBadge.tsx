import { Badge } from "@/components/ui/badge";
import { RiskTier } from "@/types";
import { cn } from "@/lib/utils";

interface RiskBadgeProps {
    tier: RiskTier;
    className?: string;
}

export function RiskBadge({ tier, className }: RiskBadgeProps) {
    let colorClass = "";

    switch (tier) {
        case 'critical':
            colorClass = "bg-red-500 hover:bg-red-600 border-transparent text-white";
            break;
        case 'high':
            colorClass = "bg-orange-500 hover:bg-orange-600 border-transparent text-white";
            break;
        case 'medium':
            colorClass = "bg-yellow-500 hover:bg-yellow-600 border-transparent text-white";
            break;
        case 'watch':
            colorClass = "bg-blue-500 hover:bg-blue-600 border-transparent text-white";
            break;
        case 'low':
            colorClass = "bg-green-500 hover:bg-green-600 border-transparent text-white";
            break;
        default:
            colorClass = "bg-slate-500 hover:bg-slate-600 border-transparent text-white";
    }

    return (
        <Badge className={cn("uppercase text-[10px] px-2 py-0.5", colorClass, className)}>
            {tier}
        </Badge>
    );
}
