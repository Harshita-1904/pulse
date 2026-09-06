import { useCallback, useEffect, useMemo, useState } from "react";
import { addToWatchlist, getDefaultWatchlist, getQuote, getStocks, removeFromWatchlist } from "../api/client";
import StockRow from "../components/StockRow";
import { Empty, ErrorMessage, Loading } from "../components/State";

export default function Home() {
  const [stocks, setStocks] = useState([]);
  const [quotes, setQuotes] = useState({});
  const [quoteErrors, setQuoteErrors] = useState({});
  const [watchlist, setWatchlist] = useState(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshingQuotes, setRefreshingQuotes] = useState(false);
  const [busy, setBusy] = useState("");

  const load = useCallback(async (forceRefresh = false) => {
    setLoading(true);
    setError("");
    try {
      const [catalogue, list] = await Promise.all([getStocks(), getDefaultWatchlist()]);
      setStocks(catalogue);
      setWatchlist(list);

      setRefreshingQuotes(true);
      const results = await Promise.all(
        catalogue.map(async (stock) => {
          try {
            const quote = await getQuote(stock.symbol, forceRefresh);
            return { symbol: stock.symbol, quote, error: null };
          } catch (err) {
            return { symbol: stock.symbol, quote: null, error: err.message };
          }
        }),
      );

      const nextQuotes = {};
      const nextErrors = {};
      results.forEach(({ symbol, quote, error: quoteError }) => {
        if (quote) nextQuotes[symbol] = quote;
        if (quoteError) nextErrors[symbol] = quoteError;
      });
      setQuotes(nextQuotes);
      setQuoteErrors(nextErrors);
    } catch (err) {
      setError(err.message);
    } finally {
      setRefreshingQuotes(false);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(false);
  }, [load]);

  const symbols = useMemo(
    () => new Set(watchlist?.stocks.map((stock) => stock.symbol) || []),
    [watchlist],
  );

  const visible = stocks.filter((stock) =>
    `${stock.symbol} ${stock.name || ""}`.toLowerCase().includes(query.toLowerCase()),
  );

  async function toggle(symbol) {
    if (!watchlist) return;
    setBusy(symbol);
    try {
      if (symbols.has(symbol)) {
        await removeFromWatchlist(watchlist.id, symbol);
      } else {
        await addToWatchlist(watchlist.id, symbol);
      }
      setWatchlist(await getDefaultWatchlist());
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  return (
    <main className="max-w-3xl mx-auto px-4">
      <section className="py-6 border-b border-line">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm text-muted">Your default watchlist</p>
            <h1 className="mt-1 text-xl font-semibold text-ink">Explore stocks</h1>
            <p className="mt-2 text-sm text-muted">
              {watchlist ? `${watchlist.stocks.length} stocks tracked` : ""}
              {refreshingQuotes ? " · Updating market prices…" : " · Latest available market data"}
            </p>
          </div>
          <button
            disabled={loading || refreshingQuotes}
            onClick={() => load(true)}
            className="border border-line px-3 py-1.5 rounded text-sm disabled:opacity-50"
          >
            {refreshingQuotes ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </section>

      {error && <ErrorMessage error={error} retry={() => load(false)} />}

      {loading ? (
        <Loading>Loading your market catalogue…</Loading>
      ) : (
        <>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by symbol or company…"
            className="mt-5 w-full border border-line rounded px-3 py-2 text-sm bg-transparent"
          />

          {visible.length ? (
            <div className="mt-3 divide-y divide-line">
              {visible.map((stock) => (
                <StockRow
                  key={stock.symbol}
                  stock={stock}
                  quote={quotes[stock.symbol]}
                  quoteError={quoteErrors[stock.symbol]}
                  busy={busy === stock.symbol}
                  inWatchlist={symbols.has(stock.symbol)}
                  onToggleWatchlist={toggle}
                />
              ))}
            </div>
          ) : (
            <Empty>
              {stocks.length
                ? `No stocks match “${query}”.`
                : "No stocks yet. Create a stock and fetch its market quote first."}
            </Empty>
          )}
        </>
      )}
    </main>
  );
}
