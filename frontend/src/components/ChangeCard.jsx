import { Link } from "react-router-dom";
import StatusBadge from "./StatusBadge";

export default function ChangeCard({ item, onRemove, busy }) {
  const unavailable = item.data_status === "unavailable";
  const firstView = item.direction === "first_view";
  const colour = unavailable || firstView || item.direction === "unchanged" ? "amber" : item.direction === "up" ? "green" : "red";
  const bg = { green: "bg-signal-greenBg", red: "bg-signal-redBg", amber: "bg-signal-amberBg" }[colour];
  const text = { green: "text-signal-green", red: "text-signal-red", amber: "text-signal-amber" }[colour];
  return <article className={`border border-line rounded ${bg} p-4`}>
    <div className="flex justify-between gap-3"><div><Link className="font-semibold text-ink hover:text-pulse" to={`/stocks/${item.symbol}`}>{item.symbol}</Link><div className="mt-1 text-2xl text-ink font-tabular">{unavailable ? "—" : item.current_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div></div><StatusBadge timestamp={item.latest_observed_at} status={item.data_status} /></div>
    {unavailable ? <p className="mt-3 text-sm text-muted">{item.data_error}</p> : firstView ? <p className="mt-3 text-sm text-muted">New to your watchlist. This view establishes the comparison baseline.</p> : <><div className={`mt-2 text-sm ${text}`}>{item.price_change_percent === null ? "Price comparison unavailable" : `${item.price_change_percent > 0 ? "+" : ""}${item.price_change_percent.toFixed(2)}% since you last checked`}</div><div className="mt-3 text-sm text-ink"><span className="text-muted">Change score </span>{Math.round((item.change_score || 0) * 100)}/100 <span className="ml-2 text-muted">{item.severity} · {item.confidence} confidence</span></div><p className="mt-2 text-sm text-ink">{item.verdict}</p><ul className="mt-2 text-sm text-muted list-disc pl-5">{item.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></>}
    <div className="mt-4 flex gap-4 text-sm"><button disabled={busy} onClick={() => onRemove(item.symbol)} className="text-muted hover:text-signal-red disabled:opacity-50">Remove</button></div>
  </article>;
}
