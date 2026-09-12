"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, upload } from "@/lib/api";

function PastedText({ onDone, onError }: { onDone: (name: string) => void; onError: (m: string) => void }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <>
      <textarea
        className="input min-h-24"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={"Paste the GPT-extracted text here…"}
      />
      <button
        className="btn"
        disabled={busy || !text.trim()}
        onClick={async () => {
          setBusy(true);
          try {
            const file = new File([text], `pasted-${new Date().toISOString().slice(0, 10)}.txt`, { type: "text/plain" });
            await upload("/api/documents/upload", file);
            setText("");
            onDone(file.name);
          } catch (err: any) {
            try {
              const d = JSON.parse(err.message);
              onError(typeof d.detail === "string" ? d.detail : err.message);
            } catch {
              onError(err.message || "Upload failed.");
            }
          }
          setBusy(false);
        }}
      >
        {busy ? "Processing…" : "Process pasted text"}
      </button>
    </>
  );
}

function Facts({ facts }: { facts: any }) {  if (!facts || Object.keys(facts).length === 0)
    return <span className="text-xs text-slate-400">no structured facts yet</span>;
  return (
    <span className="flex flex-wrap gap-1">
      {Object.entries(facts).slice(0, 6).map(([k, v]) => (
        <span key={k} className="text-[11px] bg-indigo-50 text-indigo-700 rounded px-2 py-0.5">
          {k}: {Array.isArray(v) ? v.join(", ") : String(v).slice(0, 40)}
        </span>
      ))}
    </span>
  );
}

export default function Documents() {
  const [docs, setDocs] = useState<any[]>([]);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const [searched, setSearched] = useState(false);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setDocs(await api<any[]>("/api/documents/"));
  }
  useEffect(() => {
    refresh().catch((e) => setMsg(e.message));
  }, []);

  async function search(e: React.FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    setBusy(true);
    setSearched(true);
    try {
      const r = await api<any[]>(`/api/documents/search?q=${encodeURIComponent(q)}`);
      setHits(r);
      setMsg(r.length === 0 ? "No matches — try “DBMS”, “exam”, or “assignment”. Your docs may be scanned images; re-upload as text PDF for best recall." : "");
    } catch (err: any) {
      setMsg(err.message);
    }
    setBusy(false);
  }

  return (
    <Shell>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <h1 className="text-2xl font-bold">📄 Documents + Extraction</h1>
        <span className="badge badge-live">● auto-extracts dates, rooms, deadlines</span>
      </div>
      {msg && <div className="card text-sm mb-4">{msg}</div>}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-4">
          <div className="card space-y-2">
            <div className="font-semibold">Upload document (max 10–15 MB)</div>
            <input
              type="file"
              accept="application/pdf,.txt,.csv,.xlsx,.docx,image/png,image/jpeg"
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                setMsg("Processing… extracting text + facts…");
                try {
                  const r = await upload("/api/documents/upload", f);
                  setMsg(`✅ ${r.filename || f.name} processed — facts: ${JSON.stringify(r.facts || {}).slice(0, 160)}`);
                  refresh();
                } catch (err: any) {
                  try {
                    const d = JSON.parse(err.message);
                    setMsg(typeof d.detail === "string" ? d.detail : err.message);
                  } catch {
                    setMsg(err.message || "Upload failed.");
                  }
                }
              }}
            />
            <div className="text-xs text-slate-500">
              PDF, TXT, CSV, XLSX, DOCX, or photos. Scanned PDFs are re-read
              with vision OCR automatically. Facts appear below after upload.
            </div>
          </div>
          <div className="card space-y-2">
            <div className="font-semibold">✏️ Paste converted text <span className="badge badge-ok ml-1">always works</span></div>
            <div className="text-xs text-slate-500">
              Not happy with a scan? Open the PDF in ChatGPT (or any GPT tool) and ask
              <span className="font-mono"> “extract all text exactly, keep tables line by line”</span>,
              then paste the result here — no OCR needed.
            </div>
            <PastedText onDone={(name) => { setMsg(`✅ ${name} processed.`); refresh(); }} onError={setMsg} />
          </div>
          <div className="card">
            <div className="font-semibold mb-2">📂 Your documents + extracted info</div>
            {docs.map((d) => (
              <div key={d.id} className="py-2.5 border-t border-slate-100 first:border-0 text-sm space-y-1.5">
                <div className="flex justify-between items-center gap-2">
                  <span className="font-medium">{d.filename} <span className="text-xs text-slate-500 font-normal">({d.size} bytes)</span></span>
                  <button
                    className="text-red-600 text-xs hover:underline"
                    onClick={async () => {
                      await api(`/api/documents/${d.id}`, { method: "DELETE" });
                      refresh();
                    }}
                  >
                    delete
                  </button>
                </div>
                <div><Facts facts={d.facts} /></div>
                {d.warning && (
                  <div className="text-xs bg-amber-50 border border-amber-200 text-amber-800 rounded-lg p-2">
                    ⚠️ {d.warning}
                    <label className="block mt-1.5 text-indigo-700 cursor-pointer hover:underline">
                      🔁 Re-scan with OCR (re-upload the file)
                      <input
                        type="file" className="hidden"
                        accept="application/pdf,image/png,image/jpeg"
                        onChange={async (e) => {
                          const f = e.target.files?.[0];
                          if (!f) return;
                          setMsg("Re-scanning with vision OCR…");
                          try {
                            const r = await upload(`/api/documents/${d.id}/rescan`, f);
                            setMsg(`✅ Re-scan done via ${r.extraction}.`);
                            refresh();
                          } catch (err: any) {
                            setMsg(err.message || "Re-scan failed.");
                          }
                        }}
                      />
                    </label>
                  </div>
                )}
              </div>
            ))}
            {docs.length === 0 && <div className="text-sm text-slate-500">No documents yet — upload your academic calendar to enable search.</div>}
          </div>
        </div>
        <div className="card h-fit">
          <div className="font-semibold mb-1">🔍 Information extraction — semantic search</div>
          <div className="text-xs text-slate-500 mb-2">Ask in plain English: “when is the DBMS exam?”, “room change?”, “assignment due?”</div>
          <form className="flex gap-2" onSubmit={search}>
            <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. when is the DBMS exam?" />
            <button className="btn" disabled={busy}>{busy ? "…" : "Extract"}</button>
          </form>
          <div className="mt-3 space-y-2">
            {hits.map((h) => (
              <div key={h.chunk_id} className="text-sm bg-slate-50 border rounded-lg p-2.5">
                <div className="text-xs text-slate-500 mb-1">📄 {h.filename} · relevance {h.score}</div>
                {h.text.slice(0, 400)}
              </div>
            ))}
            {searched && hits.length === 0 && !busy && (
              <div className="text-sm text-slate-500 bg-amber-50 border border-amber-200 rounded-lg p-3">
                No chunks matched. Tip: upload a text PDF (not a phone photo of a screen) — Sharon&apos;s demo calendar answers “DBMS”, “exam”, “assignment”.
              </div>
            )}
            {!searched && (
              <div className="flex flex-wrap gap-1.5">
                {["when is the DBMS exam?", "room change?", "assignment due?"].map((s) => (
                  <button key={s} className="btn-ghost text-xs" onClick={() => { setQ(s); }}>| {s}</button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </Shell>
  );
}
