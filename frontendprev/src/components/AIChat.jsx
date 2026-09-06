import { useState } from "react";
import { askAI } from "../api/client";

const STARTERS = [
  "What changed since I last checked?",
  "Which stock needs my attention?",
  "Which stock moved the most?",
  "Why is RELIANCE green?",
];

export default function AIChat() {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(text = question) {
    const trimmed = text.trim();
    if (!trimmed || busy) return;

    setQuestion("");
    setError("");
    setMessages((current) => [...current, { role: "user", text: trimmed }]);
    setBusy(true);

    try {
      const result = await askAI(trimmed);
      setMessages((current) => [
        ...current,
        { role: "assistant", text: result.answer },
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen((value) => !value)}
        className="fixed bottom-5 right-5 z-40 bg-ink text-paper rounded-full px-4 py-3 shadow-lg text-sm font-medium"
        aria-label="Open Pulse AI assistant"
      >
        {open ? "Close AI" : "Ask Pulse AI"}
      </button>

      {open && (
        <section className="fixed bottom-20 right-5 z-40 w-[min(92vw,380px)] h-[min(70vh,560px)] bg-paper border border-line rounded-xl shadow-xl flex flex-col overflow-hidden">
          <header className="px-4 py-3 border-b border-line">
            <div className="font-semibold text-ink">Pulse AI</div>
            <div className="text-xs text-muted mt-0.5">
              Ask about changes in your watchlist.
            </div>
          </header>

          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {!messages.length && (
              <div className="space-y-2">
                <p className="text-sm text-muted">
                  I explain the market facts already calculated by Pulse.
                </p>
                {STARTERS.map((starter) => (
                  <button
                    key={starter}
                    onClick={() => submit(starter)}
                    className="w-full text-left border border-line rounded-lg px-3 py-2 text-sm text-ink hover:bg-gray-50"
                  >
                    {starter}
                  </button>
                ))}
              </div>
            )}

            {messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={message.role === "user" ? "flex justify-end" : "flex justify-start"}
              >
                <div
                  className={
                    message.role === "user"
                      ? "max-w-[85%] rounded-lg bg-ink text-paper px-3 py-2 text-sm"
                      : "max-w-[90%] rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink"
                  }
                >
                  {message.text}
                </div>
              </div>
            ))}

            {busy && (
              <div className="text-xs text-muted">Pulse is thinking…</div>
            )}

            {error && (
              <div className="rounded border border-line bg-white p-3 text-sm text-signal-red">
                {error}
              </div>
            )}
          </div>

          <form
            onSubmit={(event) => {
              event.preventDefault();
              submit();
            }}
            className="p-3 border-t border-line flex gap-2"
          >
            <input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about your watchlist…"
              disabled={busy}
              className="min-w-0 flex-1 border border-line rounded-lg px-3 py-2 text-sm bg-transparent"
            />
            <button
              type="submit"
              disabled={busy || !question.trim()}
              className="bg-ink text-paper rounded-lg px-3 py-2 text-sm disabled:opacity-40"
            >
              Send
            </button>
          </form>
        </section>
      )}
    </>
  );
}
