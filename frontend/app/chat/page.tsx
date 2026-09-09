"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";

type Msg = { from: "you" | "agent"; text: string };

const SUGGESTED = [
  "What is my next class?",
  "What do I have tomorrow?",
  "What's important from my college emails?",
  "Did my timetable change?",
];

function ChatBody() {
  const params = useSearchParams();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const asked = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, busy]);

  async function ask(question: string) {
    setMsgs((m) => [...m, { from: "you", text: question }]);
    setBusy(true);
    setError("");
    try {
      const data = await api<{ reply: string }>("/api/chat/", {
        method: "POST",
        body: JSON.stringify({ text: question }),
      });
      setMsgs((m) => [...m, { from: "agent", text: data.reply }]);
    } catch (err: any) {
      setError(err.message);
    }
    setBusy(false);
  }

  useEffect(() => {
    const q = params.get("q");
    if (q && !asked.current) {
      asked.current = true;
      ask(q);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  return (
    <>
      <h1 className="text-2xl font-bold mb-4">AI Chat</h1>
      <div className="card space-y-3 min-h-96">
        {msgs.length === 0 && (
          <div className="text-sm text-slate-500">
            Ask about classes, deadlines, emails, or documents. Same agent as messaging.
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} className={m.from === "you" ? "text-right" : "text-left"}>
            <span
              className={`inline-block rounded-lg px-3 py-2 text-sm max-w-full whitespace-pre-wrap ${
                m.from === "you" ? "bg-indigo-600 text-white" : "bg-slate-100"
              }`}
            >
              {m.text}
            </span>
          </div>
        ))}
        {busy && <div className="text-sm text-slate-500 animate-pulse">CampusOps is thinking…</div>}
        {error && <div className="text-sm text-red-600">{error}</div>}
        <div ref={bottomRef} />
      </div>
      <div className="flex flex-wrap gap-2 mt-3">
        {SUGGESTED.map((s) => (
          <button key={s} className="btn-ghost text-xs" onClick={() => ask(s)} disabled={busy}>
            {s}
          </button>
        ))}
      </div>
      <form
        className="flex gap-2 mt-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (text.trim()) {
            ask(text);
            setText("");
          }
        }}
      >
        <input className="input" value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask anything academic…" />
        <button className="btn" disabled={busy}>Send</button>
      </form>
    </>
  );
}

export default function Chat() {
  return (
    <Shell>
      <Suspense>
        <ChatBody />
      </Suspense>
    </Shell>
  );
}
