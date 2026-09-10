"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Shell from "@/components/Shell";
import { api, getToken } from "@/lib/api";

type Msg = { from: "you" | "agent"; text: string; at: string };

const SUGGESTED = [
  "🎯 What should I focus on today?",
  "🗓️ What is my next class?",
  "🚨 Did my timetable change?",
  "📧 What's important from my college emails?",
  "⏰ What assignments are coming up?",
  "📄 Search my documents for exam dates",
];

function timeNow() {
  return new Date().toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function ChatBody() {
  const params = useSearchParams();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState<number | null>(null);
  const asked = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, busy]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function ask(question: string) {
    const q = question.trim();
    if (!q || busy) return;
    if (!getToken()) {
      setError("⚠️ You're not signed in — chat needs a login. Go to /login and use demo.student@example.com / demo1234 (1 click).");
      return;
    }
    setMsgs((m) => [...m, { from: "you", text: q, at: timeNow() }]);
    setBusy(true);
    setError("");
    try {
      const data = await api<{ reply: string }>("/api/chat/", {
        method: "POST",
        body: JSON.stringify({ text: q }),
      });
      setMsgs((m) => [...m, { from: "agent", text: data.reply, at: timeNow() }]);
    } catch (err: any) {
      const raw = err.message || "";
      if (raw.includes("Session expired") || raw.includes("401")) {
        setError("⚠️ Session expired — please sign in again with demo.student@example.com / demo1234.");
      } else {
        setError(raw || "Chat failed — API at localhost:8000 may be down. Restart: python -m uvicorn backend.app.main:app --port 8000");
      }
    }
    setBusy(false);
    inputRef.current?.focus();
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
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <h1 className="text-2xl font-bold">💬 AI Chat</h1>
        <span className="badge badge-live">● same brain as Telegram + email</span>
      </div>
      <div className="card space-y-4 min-h-96">
        {msgs.length === 0 && (
          <div>
            <div className="rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white p-5 mb-3">
              <div className="font-bold text-lg">👋 Hey, I&apos;m CampusOps — your academic co-pilot</div>
              <div className="text-sm text-indigo-100 mt-1">I&apos;ve read your timetable, inbox & deadlines. Ask me what to do next — I answer from YOUR data, with sources.</div>
            </div>
            <div className="grid md:grid-cols-2 gap-2">
              {SUGGESTED.map((s) => (
                <button key={s} className="prompt-card" onClick={() => ask(s.replace(/^[🎯🗓️🚨📧⏰📄]\s/, ""))} disabled={busy}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} className={`flex gap-2 ${m.from === "you" ? "justify-end" : "justify-start"}`}>
            {m.from === "agent" && <div className="shrink-0 w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center text-sm">🎓</div>}
            <div className={`max-w-[85%]`}>
              <div
                className={`inline-block rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap leading-relaxed shadow-sm ${
                  m.from === "you" ? "bg-indigo-600 text-white rounded-br-md" : "bg-slate-100 text-slate-900 rounded-bl-md border"
                }`}
              >
                {m.text}
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[11px] text-slate-400">{m.from === "you" ? "You" : "CampusOps"} · {m.at}</span>
                {m.from === "agent" && (
                  <button
                    className="text-[11px] text-indigo-600 hover:underline"
                    onClick={() => {
                      navigator.clipboard?.writeText(m.text).catch(() => {});
                      setCopied(i);
                      setTimeout(() => setCopied(null), 1200);
                    }}
                  >
                    {copied === i ? "copied ✓" : "copy"}
                  </button>
                )}
              </div>
            </div>
            {m.from === "you" && <div className="shrink-0 w-8 h-8 rounded-full bg-slate-300 flex items-center justify-center text-sm">🧑‍🎓</div>}
          </div>
        ))}
        {busy && (
          <div className="flex gap-2 items-center">
            <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center text-sm animate-pulse">🎓</div>
            <div className="text-sm text-slate-500 animate-pulse">CampusOps is checking your timetable, inbox & deadlines…</div>
          </div>
        )}
        {error && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">{error}</div>}
        <div ref={bottomRef} />
      </div>
      <div className="flex flex-wrap gap-2 mt-3">
        {SUGGESTED.slice(0, 4).map((s) => (
          <button key={s} className="btn-ghost text-xs" onClick={() => ask(s.replace(/^[🎯🗓️🚨📧⏰📄]\s/, ""))} disabled={busy}>
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
        <input
          ref={inputRef}
          className="input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Ask anything academic… (Enter to send)"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (text.trim()) {
                ask(text);
                setText("");
              }
            }
          }}
        />
        <button className="btn px-6" disabled={busy || !text.trim()}>{busy ? "…" : "Send ➤"}</button>
      </form>
      <div className="mt-2 text-xs text-slate-500">⚡ Judge demo: “Did my timetable change?” → “What should I focus on today?” → “Remind me to revise at 7pm”</div>
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
