export default function RelevanceBadge({ score }) {
  if (score === null || score === undefined)
    return (
      <span className="inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold bg-slate-200 text-slate-600">
        not scored
      </span>
    );
  const cls =
    score > 75
      ? "bg-green-100 text-green-800"
      : score >= 40
        ? "bg-amber-100 text-amber-800"
        : "bg-red-100 text-red-800";
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold ${cls}`}>
      relevance {score}
    </span>
  );
}
