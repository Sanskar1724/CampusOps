"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";

const KINDS: [string, string][] = [
  ["notify_brief", "🌅 Morning brief"],
  ["notify_deadline", "⏰ Deadline alerts"],
  ["notify_reminder", "🔔 Reminders"],
  ["notify_change", "🚨 Room / schedule changes"],
];

const KIND_ICON: Record<string, string> = {
  brief: "🌅",
  deadline: "⏰",
  reminder: "🔔",
  change: "🚨",
};

export default function Notifications() {
  const [items, setItems] = useState<any[]>([]);
  const [prefs, setPrefs] = useState<any>({});
  const [msg, setMsg] = useState("");

  async function refresh() {
    setItems(await api<any[]>("/api/notifications/"));
    setPrefs(await api<any>("/api/student/preferences"));
  }
  useEffect(() => {
    refresh().catch((e) => setMsg(e.message));
  }, []);

  async function save(patch: any) {
    const next = { ...prefs, ...patch };
    setPrefs(next);
    await api("/api/student/preferences", { method: "PUT", body: JSON.stringify(patch) });
  }

  return (
    <Shell>
      <h1 className="text-2xl font-bold mb-4">🔔 Notifications</h1>
      {msg && <div className="card text-sm text-red-600 mb-4">{msg}</div>}
      <div className="card mb-4">
        <div className="font-semibold mb-1">⚙️ Your notification rules</div>
        <div className="text-xs text-slate-500 mb-3">
          Turn each alert on/off, set quiet hours, pick the channel. Missed quiet-hour items retry later — never spam.
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          {KINDS.map(([key, label]) => (
            <label key={key} className="flex items-center gap-2 text-sm bg-slate-50 rounded-lg px-3 py-2 cursor-pointer">
              <input
                type="checkbox"
                checked={prefs[key] !== false}
                onChange={(e) => save({ [key]: e.target.checked }).catch((err) => setMsg(err.message))}
              />
              {label}
            </label>
          ))}
        </div>
        <div className="grid gap-2 sm:grid-cols-3 mt-3">
          <div>
            <label className="label">🌙 Quiet from (hour)</label>
            <input
              className="input" type="number" min={0} max={23}
              value={prefs.quiet_start ?? ""}
              placeholder="e.g. 22"
              onChange={(e) => save({ quiet_start: e.target.value === "" ? null : Number(e.target.value) }).catch((err) => setMsg(err.message))}
            />
          </div>
          <div>
            <label className="label">🌅 Quiet until (hour)</label>
            <input
              className="input" type="number" min={0} max={23}
              value={prefs.quiet_end ?? ""}
              placeholder="e.g. 7"
              onChange={(e) => save({ quiet_end: e.target.value === "" ? null : Number(e.target.value) }).catch((err) => setMsg(err.message))}
            />
          </div>
          <div>
            <label className="label">📡 Channel</label>
            <select
              className="input" value={prefs.notify_channel || "auto"}
              onChange={(e) => save({ notify_channel: e.target.value }).catch((err) => setMsg(err.message))}
            >
              <option value="auto">Auto (best available)</option>
              <option value="gateway">Caspian gateway</option>
              <option value="telegram">Telegram bot</option>
            </select>
          </div>
        </div>
      </div>
      <div className="card">
        <div className="font-semibold mb-2">📨 Recent alerts</div>
        {items.length === 0 && <div className="text-sm text-slate-500">No notifications yet — your brief lands here every morning. 🌅</div>}
        {items.map((n) => (
          <div key={n.id} className="py-2 border-t border-slate-100 first:border-0 text-sm flex gap-2">
            <span className="text-lg">{KIND_ICON[n.kind] || "📌"}</span>
            <div>
              <div className="font-medium">
                {n.title} <span className="text-xs text-slate-500">· {n.kind} · {n.status}</span>
              </div>
              <div className="text-slate-600 whitespace-pre-wrap">{n.body}</div>
              {n.error && <div className="text-xs text-amber-700 mt-1">⚠️ delivery issue: {n.error} — will retry</div>}
            </div>
          </div>
        ))}
      </div>
    </Shell>
  );
}
