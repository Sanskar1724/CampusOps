"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, upload } from "@/lib/api";

export default function Documents() {
  const [docs, setDocs] = useState<any[]>([]);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<any[]>([]);
  const [msg, setMsg] = useState("");

  async function refresh() {
    setDocs(await api<any[]>("/api/documents/"));
  }
  useEffect(() => {
    refresh().catch((e) => setMsg(e.message));
  }, []);

  return (
    <Shell>
      <h1 className="text-2xl font-bold mb-4">Documents</h1>
      {msg && <div className="card text-sm mb-4">{msg}</div>}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-4">
          <div className="card space-y-2">
            <div className="font-semibold">Upload PDF (max 10 MB)</div>
            <input
              type="file"
              accept="application/pdf"
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                setMsg("");
                try {
                  await upload("/api/documents/upload", f);
                  refresh();
                } catch (err: any) {
                  setMsg(err.message);
                }
              }}
            />
          </div>
          <div className="card">
            <div className="font-semibold mb-2">Your documents</div>
            {docs.map((d) => (
              <div key={d.id} className="py-2 border-t border-slate-100 first:border-0 text-sm flex justify-between">
                <span>{d.filename} <span className="text-xs text-slate-500">({d.size} bytes)</span></span>
                <button
                  className="text-red-600 text-xs"
                  onClick={async () => {
                    await api(`/api/documents/${d.id}`, { method: "DELETE" });
                    refresh();
                  }}
                >
                  delete
                </button>
              </div>
            ))}
            {docs.length === 0 && <div className="text-sm text-slate-500">No documents yet.</div>}
          </div>
        </div>
        <div className="card">
          <div className="font-semibold mb-2">Semantic search</div>
          <form
            className="flex gap-2"
            onSubmit={async (e) => {
              e.preventDefault();
              setHits(await api<any[]>(`/api/documents/search?q=${encodeURIComponent(q)}`));
            }}
          >
            <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. exam dates" />
            <button className="btn">Search</button>
          </form>
          <div className="mt-3 space-y-2">
            {hits.map((h) => (
              <div key={h.chunk_id} className="text-sm bg-slate-50 rounded p-2">
                <div className="text-xs text-slate-500">{h.filename} · {h.score}</div>
                {h.text.slice(0, 300)}
              </div>
            ))}
          </div>
        </div>
      </div>
    </Shell>
  );
}
