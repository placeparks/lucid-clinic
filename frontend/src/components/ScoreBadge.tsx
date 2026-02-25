function getColor(score: number): string {
  if (score >= 70) return "bg-green-100 text-green-800";
  if (score >= 50) return "bg-yellow-100 text-yellow-800";
  if (score >= 30) return "bg-orange-100 text-orange-800";
  return "bg-red-100 text-red-800";
}

export default function ScoreBadge({ score }: { score: number }) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-bold tabular-nums ${getColor(score)}`}>
      {score}
    </span>
  );
}
