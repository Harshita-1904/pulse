import { Link } from "react-router-dom";

function formatPrice(value) {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatTimestamp(timestamp) {
  if (!timestamp) return "";
  return new Date(timestamp).toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function StockRow({
  stock,
  quote,
  quoteError,
  inWatchlist,
  onToggleWatchlist,
  busy,
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-4">
      <div className="min-w-0">
        <Link
          to={`/stocks/${stock.symbol}`}
          className="font-semibold text-ink hover:text-pulse"
        >
          {stock.symbol}
        </Link>
        <div className="text-sm text-muted truncate">
          {stock.name || stock.exchange || "Market instrument"}
        </div>
        {quote && (
          <div className="mt-1 text-xs text-muted">
            {quote.is_cached ? "Cached · " : "Latest · "}
            {formatTimestamp(quote.provider_timestamp || quote.captured_at)}
          </div>
        )}
        {quoteError && !quote && (
          <div className="mt-1 text-xs text-signal-red truncate" title={quoteError}>
            Market quote unavailable
          </div>
        )}
      </div>

      <div className="shrink-0 text-right">
        {quote ? (
          <div className="text-lg font-tabular text-ink">₹{formatPrice(quote.price)}</div>
        ) : (
          <div className="text-sm text-muted">—</div>
        )}
        <button
          disabled={busy}
          onClick={() => onToggleWatchlist(stock.symbol)}
          className={`mt-1 text-sm px-3 py-1.5 border rounded whitespace-nowrap disabled:opacity-50 ${
            inWatchlist
              ? "border-signal-green text-signal-green bg-signal-greenBg"
              : "border-line text-ink hover:border-pulse hover:text-pulse"
          }`}
        >
          {inWatchlist ? "In watchlist" : "Add to watchlist"}
        </button>
      </div>
    </div>
  );
}
