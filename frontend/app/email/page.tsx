"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";

export default function Email() {
  const [items, setItems] = useState<any[]>([]);
  const [important, setImportant] = useState<any[]>([]);
  const [msg, setMsg] = useState("");

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

  return (
    <Shell>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Email Intelligence</h1>
        <button
          className="btn-ghost"
          onClick={async () => {
            setMsg("");
            try {
              const r = await api<{ processed: number }>("/api/email/sync", { method: "POST" });
              setMsg(`Synced ${r.processed} emails.`);
              refresh();
            } catch (e: any) {
              setMsg(e.message);
            }
          }}
        >
          Sync Gmail
        </button>
      </div>
      {msg && <div className="card text-sm mb-4">{msg}</div>}
      <div className="card mb-4">
        <div className="font-semibold mb-2">Important & relevant</div>
        {important.length === 0 && <div className="text-sm text-slate-500">Nothing flagged yet.</div>}
        {important.map((x, i) => (
          <div key={i} className="py-2 border-t border-slate-100 first:border-0 text-sm">
            <span className="font-medium">{x.subject}</span>{" "}
            <span className="text-xs bg-indigo-50 text-indigo-700 rounded px-2 py-0.5">{x.kind} · {x.priority}</span>
            <div className="text-slate-600 text-xs mt-1">{JSON.stringify(x.facts)}</div>
          </div>
        ))}
      </div>
      <div className="card">
        <div className="font-semibold mb-2">Recent mail</div>
        {items.map((e) => (
          <div key={e.id} className="py-2 border-t border-slate-100 first:border-0 text-sm">
            <div className="font-medium">{e.subject}</div>
            <div className="text-xs text-slate-500">{e.sender}</div>
            <div className="text-slate-600 mt-1">{e.body?.slice(0, 300)}</div>
          </div>
        ))}
      </div>
    </Shell>
  );
}
