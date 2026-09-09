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
      if (data.done) setTimeout(() => router.push("/dashboard"), 1200);
    } catch (err: any) {
      setLog((l) => [...l, `Error: ${err.message}`]);
    }
    setBusy(false);
  }

  return (
    <Shell>
      <h1 className="text-2xl font-bold mb-4">Onboarding</h1>
      <div className="card space-y-2 min-h-64">
        {log.map((line, i) => (
          <div key={i} className="text-sm">{line}</div>
        ))}
        {busy && <div className="text-sm text-slate-500">CampusOps is typing…</div>}
      </div>
      <form onSubmit={send} className="flex gap-2 mt-3">
        <input className="input" value={text} onChange={(e) => setText(e.target.value)} placeholder="Type your answer…" />
        <button className="btn" disabled={busy}>Send</button>
      </form>
    </Shell>
  );
}
