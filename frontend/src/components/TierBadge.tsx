const TIER_STYLES: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  warm: "bg-yellow-100 text-yellow-800",
  cool: "bg-orange-100 text-orange-800",
  cold: "bg-red-100 text-red-800",
  dormant: "bg-gray-100 text-gray-600",
  unknown: "bg-gray-100 text-gray-400",
};

export default function TierBadge({ tier }: { tier: string | null }) {
  const t = tier || "unknown";
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize ${TIER_STYLES[t] || TIER_STYLES.unknown}`}>
      {t}
    </span>
  );
}
