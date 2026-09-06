export default function StatusBadge({ timestamp, status = "fresh" }) {
  const label = status === "unavailable" ? "Market data unavailable" : timestamp ? `${status === "stale" ? "Stale · " : ""}As of ${new Date(timestamp).toLocaleString()}` : "No timestamp";
  const colour = status === "fresh" ? "bg-signal-green" : status === "stale" ? "bg-signal-amber" : "bg-signal-red";
  return <span className="inline-flex items-center gap-1.5 text-xs text-muted"><span className={`w-1.5 h-1.5 rounded-full ${colour}`} />{label}</span>;
}
