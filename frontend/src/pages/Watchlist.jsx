import { useEffect, useState } from "react";
import { getDefaultWatchlist, getOverview, markSeen, refreshWatchlist, removeFromWatchlist } from "../api/client";
import ChangeCard from "../components/ChangeCard";
import MissedChanges from "../components/MissedChanges";
import { Empty, ErrorMessage, Loading } from "../components/State";

export default function Watchlist() { 
  const [watchlist, setWatchlist] = useState(null); 
  const [overview, setOverview] = useState(null); 
  const [error, setError] = useState(""); 
  const [loading, setLoading] = useState(true); 
  const [busy, setBusy] = useState(false); 

  const load = async () => { 
    setLoading(true); 
    setError(""); 
    try { 
      const list = await getDefaultWatchlist(); 
      setWatchlist(list); 
      setOverview(list.stocks.length ? await getOverview(list.id) : null); 
    } catch (err) { 
      setError(err.message); 
    } finally { 
      setLoading(false); 
    } 
  }; 

  useEffect(() => { load(); }, []); 

  async function action(fn) { 
    setBusy(true); 
    setError(""); 
    try { 
      await fn(); 
      await load(); 
    } catch (err) { 
      setError(err.message); 
    } finally { 
      setBusy(false); 
    } 
  } 

  return (
    <main className="max-w-2xl mx-auto px-4">
      <div className="mt-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-ink">My watchlist</h1>
          {overview && (
            <p className="mt-1 text-sm text-muted">
              {overview.changed_count} changed · {overview.up_count} up · {overview.down_count} down · {overview.unseen_count} new
            </p>
          )}
        </div>
        <button 
          disabled={busy || !watchlist?.stocks.length} 
          onClick={() => action(() => refreshWatchlist(watchlist.id))} 
          className="border border-line px-3 py-1.5 rounded text-sm disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      {error && <ErrorMessage error={error} retry={load} />}

      {loading ? (
        <Loading>Comparing against your last visit…</Loading>
      ) : !overview ? (
        <Empty>Your watchlist is empty. Add collected stocks from Home to start tracking changes.</Empty>
      ) : (
        <div className="mt-5 pb-10">
          <MissedChanges alerts={overview.missed_alerts ?? []} />
          <div className="mt-5 space-y-3">
            {overview.items
              .slice()
              .sort((a, b) => Math.abs(b.price_change_percent || 0) - Math.abs(a.price_change_percent || 0))
              .map((item) => (
                <ChangeCard 
                  key={item.symbol} 
                  item={item} 
                  busy={busy} 
                  onMarkSeen={(symbol) => action(() => markSeen(symbol))} 
                  onRemove={(symbol) => action(() => removeFromWatchlist(watchlist.id, symbol))} 
                />
              ))}
          </div>
        </div>
      )}
    </main>
  );
}
