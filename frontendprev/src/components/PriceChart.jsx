function formatPrice(value) {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatTime(value) {
  return new Date(value).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function PriceChart({ points }) {
  if (!points.length) {
    return (
      <div className="py-8 text-center">
        <p className="text-sm text-muted">No price observations yet.</p>
        <p className="mt-1 text-xs text-muted">Refresh the stock to collect the first market observation.</p>
      </div>
    );
  }

  const prices = points.map((point) => point.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || Math.max(max * 0.01, 1);
  const path = prices
    .map((price, index) => {
      const x = points.length === 1 ? 50 : (index / (points.length - 1)) * 100;
      const y = 86 - ((price - min) / range) * 68;
      return `${index ? "L" : "M"}${x} ${y}`;
    })
    .join(" ");

  const first = points[0];
  const last = points[points.length - 1];
  const change = first.price ? ((last.price - first.price) / first.price) * 100 : 0;
  const positive = change >= 0;

  return (
    <div>
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <p className="text-sm text-muted">
            {points.length === 1 ? "1 collected observation" : `${points.length} collected observations`}
          </p>
          <p className="mt-1 text-xs text-muted">
            {formatTime(first.recorded_at)}{points.length > 1 ? ` → ${formatTime(last.recorded_at)}` : ""}
          </p>
        </div>
        {points.length > 1 && (
          <span className={`text-sm font-tabular ${positive ? "text-signal-green" : "text-signal-red"}`}>
            {positive ? "+" : ""}{change.toFixed(2)}%
          </span>
        )}
      </div>

      <div className="relative h-48 rounded bg-paper border border-line overflow-hidden">
        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          className="absolute inset-0 w-full h-full p-3"
          role="img"
          aria-label="Recorded price history"
        >
          <path d="M0 86 H100" fill="none" stroke="currentColor" strokeOpacity="0.08" vectorEffect="non-scaling-stroke" />
          <path d={path} fill="none" stroke="#3B5BA5" strokeWidth="1.8" vectorEffect="non-scaling-stroke" />
          {points.map((point, index) => {
            const x = points.length === 1 ? 50 : (index / (points.length - 1)) * 100;
            const y = 86 - ((point.price - min) / range) * 68;
            return <circle key={`${point.recorded_at}-${index}`} cx={x} cy={y} r="1.7" fill="#3B5BA5" />;
          })}
        </svg>
      </div>

      <div className="mt-3 flex items-center justify-between text-xs text-muted">
        <span>Low ₹{formatPrice(min)}</span>
        <span>High ₹{formatPrice(max)}</span>
      </div>

      {points.length === 1 && (
        <p className="mt-2 text-xs text-muted">
          The chart will become a line as more provider observations are collected. No synthetic prices are added.
        </p>
      )}
    </div>
  );
}
