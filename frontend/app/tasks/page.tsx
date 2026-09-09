"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";

export default function Planner() {
  const [deadlines, setDeadlines] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [reminders, setReminders] = useState<any[]>([]);
  const [exams, setExams] = useState<any[]>([]);
  const [taskTitle, setTaskTitle] = useState("");
  const [remText, setRemText] = useState("");
  const [remAt, setRemAt] = useState("");

  async function refresh() {
    const [d, t, r, e] = await Promise.all([
      api<any[]>("/api/planner/deadlines"),
      api<any[]>("/api/planner/tasks"),
      api<any[]>("/api/planner/reminders"),
      api<any[]>("/api/planner/exams"),
    ]);
    setDeadlines(d);
    setTasks(t);
    setReminders(r);
    setExams(e);
  }
  useEffect(() => {
    refresh().catch(() => {});
  }, []);

  return (
    <Shell>
      <h1 className="text-2xl font-bold mb-4">Planner</h1>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="card">
          <div className="font-semibold mb-2">Deadlines</div>
          {deadlines.filter((d) => d.status === "open").map((d) => (
            <div key={d.id} className="text-sm py-1 flex justify-between">
              <span>{d.title} <span className="text-xs text-slate-500">({d.due_at || "no date"} · {d.source})</span></span>
              <button
                className="text-indigo-600 text-xs"
                onClick={async () => {
                  await api(`/api/planner/deadlines/${d.id}/done`, { method: "POST" });
                  refresh();
                }}
              >
                done
              </button>
            </div>
          ))}
        </div>
        <div className="card">
          <div className="font-semibold mb-2">Exams</div>
          {exams.map((e) => (
            <div key={e.id} className="text-sm py-1">
              {e.subject} — {e.title} <span className="text-xs text-slate-500">({e.exam_at || "TBA"} {e.room})</span>
            </div>
          ))}
          {exams.length === 0 && <div className="text-sm text-slate-500">None scheduled.</div>}
        </div>
        <div className="card">
          <div className="font-semibold mb-2">Tasks</div>
          <form
            className="flex gap-2 mb-2"
            onSubmit={async (e) => {
              e.preventDefault();
              if (!taskTitle.trim()) return;
              await api("/api/planner/tasks", { method: "POST", body: JSON.stringify({ title: taskTitle }) });
              setTaskTitle("");
              refresh();
            }}
          >
            <input className="input" value={taskTitle} onChange={(e) => setTaskTitle(e.target.value)} placeholder="New task…" />
            <button className="btn">Add</button>
          </form>
          {tasks.filter((t) => t.status === "open").map((t) => (
            <div key={t.id} className="text-sm py-1 flex justify-between">
              <span>{t.title}</span>
              <button
                className="text-indigo-600 text-xs"
                onClick={async () => {
                  await api(`/api/planner/tasks/${t.id}/done`, { method: "POST" });
                  refresh();
                }}
              >
                done
              </button>
            </div>
          ))}
        </div>
        <div className="card">
          <div className="font-semibold mb-2">Reminders</div>
          <form
            className="flex gap-2 mb-2"
            onSubmit={async (e) => {
              e.preventDefault();
              await api("/api/planner/reminders", {
                method: "POST",
                body: JSON.stringify({ text: remText, remind_at: new Date(remAt).toISOString() }),
              });
              setRemText("");
              setRemAt("");
              refresh();
            }}
          >
            <input className="input" value={remText} onChange={(e) => setRemText(e.target.value)} placeholder="Remind me…" required />
            <input className="input" type="datetime-local" value={remAt} onChange={(e) => setRemAt(e.target.value)} required />
            <button className="btn">Add</button>
          </form>
          {reminders.map((r) => (
            <div key={r.id} className="text-sm py-1">
              {r.text} <span className="text-xs text-slate-500">({r.remind_at} · {r.status})</span>
            </div>
          ))}
        </div>
      </div>
    </Shell>
  );
}
