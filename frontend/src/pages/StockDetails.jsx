import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getHistory, getQuote, markSeen } from "../api/client";
import PriceChart from "../components/PriceChart";
import StatusBadge from "../components/StatusBadge";
import { ErrorMessage, Loading } from "../components/State";

export default function StockDetails() {
  const { symbol } = useParams();
  const [quote, setQuote] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (refresh = false) => {
    setLoading(true);
    setError("");
    try {
      // Collect a fresh observation through FastAPI before reading the chart.
      // The chart itself uses only provider-backed observations stored by Pulse.
      const latest = await getQuote(symbol, refresh);
      const points = await getHistory(symbol, 100);
      setQuote(latest);
      setHistory(points);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    load(false);
  }, [load]);

  // Bridge the backend's { price, recorded_at } shape into what
  // PriceChart.jsx expects: { timestamp, price }. Accepts either
  // `timestamp` or `recorded_at` so it won't break if the backend
  // response shape changes later.
  const chartData = useMemo(() => {
    return history
      .map((point) => ({
        timestamp: point.timestamp ?? point.recorded_at,
        price: Number(point.price),
        volume:
          point.volume === null || point.volume === undefined
            ? null
            : Number(point.volume),
      }))
      .filter((point) => point.timestamp && Number.isFinite(point.price))
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  }, [history]);

  const chartChange = useMemo(() => {
    if (chartData.length < 2) return null;
    const first = chartData[0].price;
    const last = chartData[chartData.length - 1].price;
    return ((last - first) / first) * 100;
  }, [chartData]);

  async function seen() {
    setBusy(true);
    try {
      await markSeen(symbol);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="max-w-3xl mx-auto px-4">
      <div className="flex items-center justify-between gap-4 pt-6">
        <Link to="/" className="text-sm text-pulse hover:underline">← Back to stocks</Link>
        <button
          onClick={() => load(true)}
          disabled={loading}
          className="border border-line px-3 py-1.5 rounded text-sm disabled:opacity-50"
        >
          {loading ? "Refreshing…" : "Refresh price"}
        </button>
      </div>

      {error && <ErrorMessage error={error} retry={() => load(true)} />}

      {loading ? (
        <Loading>Loading live market data and chart…</Loading>
      ) : quote ? (
        <section className="mt-4 pb-10">
          <div className="rounded border border-line p-5">
            <div className="flex justify-between gap-4">
              <div>
                <h1 className="text-2xl font-semibold text-ink">{quote.symbol}</h1>
                <p className="mt-2 text-3xl font-tabular text-ink">
                  ₹{quote.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
                <p className="mt-2 text-sm text-muted">
                  Source: {quote.source}{quote.is_cached ? " · cached quote" : " · freshly collected"}
                </p>
              </div>
              <StatusBadge timestamp={quote.provider_timestamp || quote.captured_at} />
            </div>

            <div className="mt-6 border border-line rounded p-4">
              <div className="flex items-center justify-between gap-3 mb-2">
                <h2 className="font-medium text-ink">Price chart</h2>
                <span className="text-xs text-muted">Provider-backed observations</span>
              </div>
              <PriceChart data={chartData} symbol={quote.symbol} changePct={chartChange} />
            </div>

            <div className="mt-5 flex items-center justify-between gap-4">
              <p className="text-xs text-muted">
                Market timestamps reflect the provider. Pulse does not invent prices.
              </p>
              <button
                disabled={busy}
                onClick={seen}
                className="bg-ink text-paper px-3 py-2 rounded text-sm disabled:opacity-50"
              >
                Mark current price as seen
              </button>
            </div>
          </div>
        </section>
      ) : null}
    </main>
  );
}