"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";

export default function Onboarding() {
  const router = useRouter();
  const [log, setLog] = useState<string[]>([
    "Welcome to CampusOps! Answer step by step — starting with your full name.",
  ]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  const [done, setDone] = useState(false);
  const step = Math.min(Math.floor(log.length / 2) + 1, 8);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    const outgoing = text;
    setText("");
    setLog((l) => [...l, `You: ${outgoing}`]);
    setBusy(true);
    try {
      const data = await api<{ reply: string; done: boolean }>("/api/student/onboarding", {
        method: "POST",
        body: JSON.stringify({ text: outgoing }),
      });
      setLog((l) => [...l, `CampusOps: ${data.reply}`]);
      if (data.done) {
        setDone(true);
        setTimeout(() => router.push("/dashboard"), 1500);
      }
    } catch (err: any) {
      setLog((l) => [...l, `Error: ${err.message}`]);
    }
    setBusy(false);
  }

  return (
    <Shell>
      <h1 className="text-2xl font-bold mb-1">👋 Welcome aboard!</h1>
      <p className="text-sm text-slate-500 mb-3">
        {done ? "🎉 Profile complete — taking you to your dashboard…" : `Step ${step} of 8 · about a minute`}
      </p>
      <div className="h-2 bg-slate-100 rounded-full mb-4 overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all"
          style={{ width: `${(done ? 8 : step - 1) * 12.5}%` }}
        />
      </div>
      <div className="card space-y-2 min-h-64">
        {log.map((line, i) => (
          <div key={i} className={`text-sm rounded-lg px-3 py-2 ${line.startsWith("You:") ? "bg-indigo-50 ml-8" : "bg-slate-50 mr-8"}`}>{line}</div>
        ))}
        {busy && <div className="text-sm text-slate-500 animate-pulse">CampusOps is typing…</div>}
      </div>
      <form onSubmit={send} className="flex gap-2 mt-3">
        <input className="input" value={text} onChange={(e) => setText(e.target.value)} placeholder="Type your answer…" />
        <button className="btn" disabled={busy}>Send</button>
      </form>
    </Shell>
  );
}
