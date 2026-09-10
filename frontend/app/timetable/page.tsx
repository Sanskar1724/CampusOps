"use client";
import { useEffect, useMemo, useState } from "react";
import Shell from "@/components/Shell";
import { api, upload } from "@/lib/api";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/** Deterministic pastel color per subject so the week is scannable. */
const PALETTE = [
  "bg-indigo-50 border-indigo-300 text-indigo-900",
  "bg-violet-50 border-violet-300 text-violet-900",
  "bg-sky-50 border-sky-300 text-sky-900",
  "bg-emerald-50 border-emerald-300 text-emerald-900",
  "bg-amber-50 border-amber-300 text-amber-900",
  "bg-rose-50 border-rose-300 text-rose-900",
  "bg-teal-50 border-teal-300 text-teal-900",
];
function colorFor(subject: string) {
  let h = 0;
  for (const ch of subject.toLowerCase()) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return PALETTE[h % PALETTE.length];
}

/** Turn raw API errors into human sentences instead of a crash screen. */
function friendlyError(raw: string): string {
  try {
    const data = JSON.parse(raw);
    const detail = typeof data.detail === "string" ? data.detail : raw;
    if (detail.includes("Unknown day")) return `${detail} Tip: use full names (Monday) or Mon/Tue…`;
    if (detail.includes("No timetable rows")) return detail;
    if (detail.includes("scanned")) return detail;
    return detail.slice(0, 300);
  } catch {
    return raw.slice(0, 300) || "Upload failed. Please try again.";
  }
}

export default function Timetable() {
  const [rows, setRows] = useState<any[]>([]);
  const [me, setMe] = useState<any>(null);
  const [mineOnly, setMineOnly] = useState(true);
  const [form, setForm] = useState({ day: 0, subject: "", start_time: "09:00", end_time: "10:00", room: "", faculty: "" });
  const [msg, setMsg] = useState("");
  const [msgOk, setMsgOk] = useState(false);
  const [lastDetected, setLastDetected] = useState<any[]>([]);
  const [paste, setPaste] = useState("");
  const [pasting, setPasting] = useState(false);

  const today = (new Date().getDay() + 6) % 7; // Mon=0

  function say(text: string, ok: boolean) {
    setMsg(text);
    setMsgOk(ok);
  }

  async function refresh(mine: boolean = mineOnly) {
    const [tt, profile] = await Promise.all([
      api<any[]>(`/api/timetable/?scope=${mine ? "mine" : "all"}`),
      me ? Promise.resolve(me) : api<any>("/api/auth/me"),
    ]);
    if (!me) setMe(profile);
    setRows([...tt].sort((a, b) => Number(a.day) - Number(b.day) || String(a.start_time).localeCompare(String(b.start_time))));
  }
  useEffect(() => {
    refresh().catch((e) => say(e.message, false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function setScope(mine: boolean) {
    setMineOnly(mine);
    try {
      await refresh(mine);
    } catch (e: any) {
      say(e.message, false);
    }
  }

  const byDay = useMemo(() => {
    const m: Record<number, any[]> = {};
    for (const r of rows) {
      const d = Number(r.day);
      (m[d] = m[d] || []).push(r);
    }
    return m;
  }, [rows]);

  const todayRows = byDay[today] || [];

  async function add(e: React.FormEvent) {
    e.preventDefault();
    await api("/api/timetable/", { method: "POST", body: JSON.stringify(form) });
    setForm({ ...form, subject: "", room: "", faculty: "" });
    refresh();
  }

  return (
    <Shell>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <h1 className="text-2xl font-bold">🗓️ Timetable</h1>
        <div className="flex items-center gap-2">
          {me && (me.division || me.batch) && (
            <span className="badge badge-info">Div {me.division || "—"} · Batch {me.batch || "—"}</span>
          )}
          <button
            className={`text-xs rounded-full border px-3 py-1.5 font-semibold ${mineOnly ? "bg-indigo-600 text-white border-indigo-600" : "bg-white text-slate-600"}`}
            onClick={() => setScope(!mineOnly)}
            title="Filter classes to your division & batch"
          >
            {mineOnly ? "✓ My classes" : "Show all divisions"}
          </button>
          <span className="badge badge-info">{rows.length} classes / week</span>
        </div>
      </div>

      {todayRows.length > 0 && (
        <div className="rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white p-4 mb-4 shadow">
          <div className="text-xs font-semibold text-indigo-200">TODAY · {DAYS[today].toUpperCase()}</div>
          <div className="flex flex-wrap gap-2 mt-2">
            {todayRows.map((r) => (
              <span key={r.id} className="bg-white/15 rounded-lg px-3 py-1.5 text-sm">
                <span className="font-bold">{r.start_time}</span> {r.subject}
                {r.room && <span className="opacity-80"> · Room {r.room}</span>}
              </span>
            ))}
          </div>
        </div>
      )}

      {msg && (
        <div className={`card text-sm mb-4 ${msgOk ? "text-emerald-700 border-emerald-200 bg-emerald-50" : "text-red-600"}`}>
          {msg}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3 space-y-3">
          {DAYS.map((day, d) => {
            const classes = byDay[d] || [];
            const isToday = d === today;
            return (
              <div key={day} className={`card !p-4 ${isToday ? "!border-indigo-400 ring-2 ring-indigo-100" : ""}`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`w-9 h-9 rounded-lg flex items-center justify-center text-xs font-bold ${isToday ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600"}`}>
                      {SHORT[d]}
                    </span>
                    <span className="font-semibold">{day}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {isToday && <span className="badge badge-info">today</span>}
                    <span className="text-xs text-slate-400">{classes.length === 0 ? "free" : `${classes.length} class${classes.length > 1 ? "es" : ""}`}</span>
                  </div>
                </div>
                {classes.length === 0 && <div className="text-sm text-slate-400 italic">No classes — free day 🎉</div>}
                <div className="space-y-2">
                  {classes.map((r) => (
                    <div key={r.id} className={`border-l-4 rounded-lg px-3 py-2 flex items-center justify-between gap-2 ${colorFor(r.subject)}`}>
                      <div>
                        <div className="font-bold text-sm">{r.subject}</div>
                        <div className="text-xs opacity-80 mt-0.5">
                          🕘 {r.start_time}–{r.end_time}
                          {r.room && <span className="ml-2">🚪 Room {r.room}</span>}
                          {r.faculty && <span className="ml-2">👤 {r.faculty}</span>}
                          {(r.division || r.batch) && (
                            <span className="ml-2 font-semibold">· Div {r.division || "–"} {r.batch || ""}</span>
                          )}
                        </div>
                      </div>
                      <button
                        title="Delete class"
                        className="shrink-0 text-xs opacity-50 hover:opacity-100 hover:text-red-600 transition"
                        onClick={async () => {
                          await api(`/api/timetable/${r.id}`, { method: "DELETE" });
                          refresh();
                        }}
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        <div className="lg:col-span-2 space-y-4">
          <form onSubmit={add} className="card space-y-2">
            <div className="font-semibold">➕ Add class</div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="label">Day</label>
                <select className="input" value={form.day} onChange={(e) => setForm({ ...form, day: Number(e.target.value) })}>
                  {DAYS.map((d, i) => (
                    <option key={d} value={i}>{d}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Subject</label>
                <input className="input" value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} required />
              </div>
              <div>
                <label className="label">Start</label>
                <input className="input" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} required />
              </div>
              <div>
                <label className="label">End</label>
                <input className="input" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} required />
              </div>
              <div>
                <label className="label">Room</label>
                <input className="input" value={form.room} onChange={(e) => setForm({ ...form, room: e.target.value })} />
              </div>
              <div>
                <label className="label">Faculty</label>
                <input className="input" value={form.faculty} onChange={(e) => setForm({ ...form, faculty: e.target.value })} />
              </div>
            </div>
            <button className="btn" type="submit">Add</button>
          </form>

          <div className="card space-y-2">
            <div className="font-semibold">📤 Upload CSV / JSON</div>
            <input
              type="file"
              accept=".csv,.json"
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                say("", true);
                try {
                  const r = await upload("/api/timetable/upload", f);
                  say(`✅ Timetable replaced — ${r.entries ?? rows.length} classes now.`, true);
                  refresh();
                } catch (err: any) {
                  say(friendlyError(err.message), false);
                }
              }}
            />
            <div className="text-xs text-slate-500">Headers are flexible: Day/Subject/Start/End, Time ranges, Teacher, Venue all work.</div>
          </div>

          <div className="card space-y-2">
            <div className="font-semibold">📄 Scan PDF / photo timetable</div>
            <input
              type="file"
              accept="application/pdf,image/png,image/jpeg"
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                say("", true);
                try {
                  const r = await upload("/api/timetable/from-document", f);
                  setLastDetected(r.rows || []);
                  say(`✅ Detected ${r.entries} classes from ${f.name}${r.method ? ` (read via ${r.method})` : ""}.`, true);
                  refresh();
                } catch (err: any) {
                  say(friendlyError(err.message) + " Tip: use “Paste timetable text” below — it never needs OCR.", false);
                }
              }}
            />
            <div className="text-xs text-slate-500">Text PDFs read instantly; scans retry with vision OCR automatically.</div>
          </div>

          <div className="card space-y-2">
            <div className="font-semibold">✏️ Paste timetable text <span className="badge badge-ok ml-1">always works</span></div>
            <textarea
              className="input min-h-24"
              value={paste}
              onChange={(e) => setPaste(e.target.value)}
              placeholder={"Monday 09:00-10:00 DBMS Room 301\nTuesday 11:00-12:00 OS Room 302"}
            />
            <button
              className="btn"
              disabled={pasting || !paste.trim()}
              onClick={async () => {
                say("", true);
                setPasting(true);
                try {
                  const r = await api<{ entries: number; rows: any[] }>("/api/timetable/from-text", {
                    method: "POST",
                    body: JSON.stringify({ text: paste }),
                  });
                  setLastDetected(r.rows || []);
                  say(`✅ Detected ${r.entries} classes from pasted text.`, true);
                  setPaste("");
                  refresh();
                } catch (err: any) {
                  say(friendlyError(err.message), false);
                }
                setPasting(false);
              }}
            >
              {pasting ? "Detecting…" : "Detect & replace timetable"}
            </button>
          </div>

          {lastDetected.length > 0 && (
            <div className="card">
              <div className="font-semibold mb-2">🔍 Last detected ({lastDetected.length})</div>
              <div className="rounded-lg overflow-hidden border border-slate-200">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-slate-50 text-xs text-slate-500 text-left">
                      <th className="px-2 py-1.5">Day</th>
                      <th className="px-2 py-1.5">Time</th>
                      <th className="px-2 py-1.5">Subject</th>
                      <th className="px-2 py-1.5">Room</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lastDetected.map((r: any, i: number) => (
                      <tr key={i} className="border-t border-slate-100">
                        <td className="px-2 py-1.5 font-medium">{String(r.day).slice(0, 3)}</td>
                        <td className="px-2 py-1.5 text-slate-600">{r.start_time}–{r.end_time}</td>
                        <td className="px-2 py-1.5">{r.subject}</td>
                        <td className="px-2 py-1.5 text-slate-600">{r.room || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </Shell>
  );
}
