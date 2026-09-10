"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";

function FactPills({ facts }: { facts: any }) {
  if (!facts || Object.keys(facts).length === 0)
    return <span className="text-xs text-slate-400">no facts</span>;
  const skip = new Set(["kind", "priority"]);
  const entries = Object.entries(facts).filter(([k]) => !skip.has(k)).slice(0, 5);
  if (entries.length === 0) return <span className="text-xs text-slate-400">classified, no extra fields</span>;
  return (
    <span className="flex flex-wrap gap-1 mt-1">
      {entries.map(([k, v]) => (
        <span key={k} className="text-[11px] bg-slate-100 text-slate-700 rounded px-2 py-0.5">
          {k}: {Array.isArray(v) ? v.join(" → ") : String(v)}
        </span>
      ))}
    </span>
  );
}

export default function Email() {
  const [items, setItems] = useState<any[]>([]);
  const [important, setImportant] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const [syncing, setSyncing] = useState(false);

  async function refresh() {
    const [a, b] = await Promise.all([
      api<any[]>("/api/email/"),
      api<any[]>("/api/email/important"),
    ]);
    setItems(a);
    setImportant(b);
  }
  useEffect(() => {
    refresh().catch((e) => setMsg(e.message));
  }, []);

  async function sync() {
    setMsg("");
    setSyncing(true);
    try {
      const r = await api<{ processed: number }>("/api/email/sync", { method: "POST" });
      setMsg(`✅ Synced ${r.processed} emails — classifications below.`);
      refresh();
    } catch (e: any) {
      let friendly = e.message;
      try {
        const d = JSON.parse(e.message);
        friendly = typeof d.detail === "string" ? d.detail : friendly;
      } catch {}
      if (friendly.includes("Gmail not connected")) {
        friendly = "⚠️ Gmail not connected yet — go to Settings → Connect Gmail, then press Sync again. Demo emails below already work without it.";
      }
      setMsg(friendly);
    }
    setSyncing(false);
  }

  return (
    <Shell>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <h1 className="text-2xl font-bold">📧 Email Intelligence</h1>
        <button className="btn-ghost" onClick={sync} disabled={syncing}>
          {syncing ? "Syncing…" : "🔄 Sync Gmail"}
        </button>
      </div>
      {msg && <div className="card text-sm mb-4">{msg}</div>}
      <div className="card mb-4">
        <div className="font-semibold mb-1">🚨 Important & relevant — auto-classified</div>
        <div className="text-xs text-slate-500 mb-2">Every mail → kind (assignment / exam / room-change / notice) + priority + extracted dates & rooms.</div>
        {important.length === 0 && <div className="text-sm text-slate-500">Nothing flagged yet — press Sync Gmail or connect it in Settings.</div>}
        {important.map((x, i) => (
          <div key={i} className="py-2.5 border-t border-slate-100 first:border-0 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium">{x.subject}</span>
              <span className="text-xs bg-indigo-50 text-indigo-700 rounded px-2 py-0.5">{x.kind}</span>
              <span className={`badge ${x.priority === "high" ? "badge-urgent" : "badge-ok"}`}>{x.priority}</span>
              {x.confidence != null && <span className="text-[11px] text-slate-400">{Math.round(x.confidence * 100)}% sure</span>}
            </div>
            <FactPills facts={x.facts} />
          </div>
        ))}
      </div>
      <div className="card">
        <div className="font-semibold mb-2">📥 Recent mail</div>
        {items.map((e) => (
          <div key={e.id} className="py-2 border-t border-slate-100 first:border-0 text-sm">
            <div className="font-medium">{e.subject}</div>
            <div className="text-xs text-slate-500">{e.sender}</div>
            <div className="text-slate-600 mt-1">{e.body?.slice(0, 300)}</div>
          </div>
        ))}
        {items.length === 0 && <div className="text-sm text-slate-500">No mail yet.</div>}
      </div>
    </Shell>
  );
}
