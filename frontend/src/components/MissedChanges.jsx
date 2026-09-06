export default function MissedChanges({ alerts = [] }) {
  return (
    <section className="border border-line rounded-lg bg-white p-5">
      <div>
        <h2 className="text-lg font-semibold text-ink">What You Missed</h2>
        <p className="mt-1 text-sm text-muted">Significant movements since your last check.</p>
      </div>

      {alerts.length === 0 ? (
        <p className="mt-4 text-sm text-muted">Nothing significant changed since your last check.</p>
      ) : (
        <div className="mt-4 space-y-3">
          {alerts.map((alert) => {
            const isUp = alert.direction === "up";
            return (
              <div key={alert.symbol} className="border border-line rounded-lg p-4">
                <div className="flex items-center justify-between gap-4">
                  <div className="font-semibold text-ink">{isUp ? "🟢" : "🔴"} {alert.symbol}</div>
                  <div className={`font-mono font-medium ${isUp ? "text-emerald-600" : "text-red-600"}`}>
                    {isUp ? "+" : ""}{alert.change_pct == null ? "—" : Number(alert.change_pct).toFixed(2)}%
                  </div>
                </div>
                <p className="mt-2 text-sm text-muted">{alert.message}</p>
                {alert.reasons?.length > 0 && (
                  <div className="mt-3 space-y-1">
                    {alert.reasons.map((reason) => <p key={reason} className="text-xs text-muted">• {reason}</p>)}
                  </div>
                )}
                {alert.change_score != null && <div className="mt-3 text-xs text-muted">Change Score: <span className="font-mono text-ink">{Number(alert.change_score).toFixed(2)}</span></div>}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
