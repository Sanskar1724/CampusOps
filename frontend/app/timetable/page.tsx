"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, upload } from "@/lib/api";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function Timetable() {
  const [rows, setRows] = useState<any[]>([]);
  const [form, setForm] = useState({ day: 0, subject: "", start_time: "09:00", end_time: "10:00", room: "", faculty: "" });
  const [msg, setMsg] = useState("");

  async function refresh() {
    setRows(await api<any[]>("/api/timetable/"));
  }
  useEffect(() => {
    refresh().catch((e) => setMsg(e.message));
  }, []);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    await api("/api/timetable/", { method: "POST", body: JSON.stringify(form) });
    setForm({ ...form, subject: "", room: "" });
    refresh();
  }

  return (
    <Shell>
      <h1 className="text-2xl font-bold mb-4">Timetable</h1>
      {msg && <div className="card text-sm text-red-600 mb-4">{msg}</div>}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="card">
          <div className="font-semibold mb-2">Weekly view</div>
          {DAYS.map((day, d) => (
            <div key={day} className="py-2 border-t border-slate-100 first:border-0">
              <div className="text-xs font-semibold text-slate-500">{day}</div>
              {rows.filter((r) => r.day === d).map((r) => (
                <div key={r.id} className="text-sm flex justify-between">
                  <span>{r.start_time}–{r.end_time} · {r.subject} {r.room && `(Room ${r.room})`}</span>
                  <button
                    className="text-red-600 text-xs"
                    onClick={async () => {
                      await api(`/api/timetable/${r.id}`, { method: "DELETE" });
                      refresh();
                    }}
                  >
                    delete
                  </button>
                </div>
              ))}
              {!rows.some((r) => r.day === d) && <div className="text-xs text-slate-400">—</div>}
            </div>
          ))}
        </div>
        <div className="space-y-4">
          <form onSubmit={add} className="card space-y-2">
            <div className="font-semibold">Add class</div>
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
            <div className="font-semibold">Upload CSV / JSON</div>
            <input
              type="file"
              accept=".csv,.json"
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                await upload("/api/timetable/upload", f);
                refresh();
              }}
            />
            <div className="text-xs text-slate-500">Columns: day, subject, start_time, end_time, room, faculty</div>
          </div>
        </div>
      </div>
    </Shell>
  );
}
