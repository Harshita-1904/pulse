export default function MissedChanges({ alerts = [] }) {
  if (!alerts.length) {
    return (
      <div className="border border-gray-200 rounded-lg bg-white p-5">
        <h2 className="text-lg font-semibold text-gray-900">
          What You Missed
        </h2>

        <p className="text-sm text-gray-500 mt-2">
          Nothing significant changed since your last check.
        </p>
      </div>
    );
  }

  return (
    <section className="border border-gray-200 rounded-lg bg-white p-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            What You Missed
          </h2>

          <p className="text-sm text-gray-500 mt-1">
            Significant movements since you last checked.
          </p>
        </div>

        <span className="text-sm text-gray-500">
          {alerts.length} alert
          {alerts.length !== 1 ? "s" : ""}
        </span>
      </div>

      <div className="mt-4 space-y-3">
        {alerts.map((alert) => {
          const positive = alert.direction === "positive";

          return (
            <div
              key={alert.symbol}
              className="border border-gray-100 rounded-lg p-4"
            >
              <div className="flex items-center justify-between">
                <div className="font-semibold text-gray-900">
                  {positive ? "🟢" : "🔴"} {alert.symbol}
                </div>

                <div
                  className={
                    positive
                      ? "text-emerald-600 font-medium"
                      : "text-red-600 font-medium"
                  }
                >
                  {positive ? "+" : ""}
                  {Number(alert.change_pct).toFixed(2)}%
                </div>
              </div>

              <p className="text-sm text-gray-600 mt-2">
                {alert.message}
              </p>

              <div className="text-xs text-gray-500 mt-2">
                Change Score:{" "}
                {Number(alert.change_score).toFixed(2)}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}