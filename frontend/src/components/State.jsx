export function Loading({ children = "Loading…" }) { return <div className="py-10 text-center text-sm text-muted">{children}</div>; }
export function ErrorMessage({ error, retry }) { return <div className="my-5 border border-signal-red bg-signal-redBg p-4 text-sm text-ink">{error}{retry && <button onClick={retry} className="ml-3 text-pulse underline">Try again</button>}</div>; }
export function Empty({ children }) { return <div className="py-10 text-center text-sm text-muted">{children}</div>; }
