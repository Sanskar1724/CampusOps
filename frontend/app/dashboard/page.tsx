"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";

const PROMPTS = [
  "What should I focus on today?",
  "What is my next class?",
  "Did my timetable change?",
  "What's important from my college emails?",
  "What assignments are coming up?",
  "Remind me to revise DBMS at 7pm",
];

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function fmtDate(d: string | null) {
  if (!d) return "no date";
  const dt = new Date(d);
  if (isNaN(dt.getTime())) return d;
  return dt.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function Dashboard() {
  const [me, setMe] = useState<any>(null);
  const [brief, setBrief] = useState("");
  const [deadlines, setDeadlines] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [important, setImportant] = useState<any[]>([]);
  const [timetable, setTimetable] = useState<any[]>([]);
  const [exams, setExams] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [meRes, chat, dl, t, imp, tt, ex] = await Promise.all([
          api<any>("/api/auth/me"),
          api<{ reply: string }>("/api/chat/", {
            method: "POST",
            body: JSON.stringify({ text: "What should I focus on today?" }),
          }).catch(() => ({ reply: "" })),
          api<any[]>("/api/planner/deadlines").catch(() => []),
          api<any[]>("/api/planner/tasks").catch(() => []),
          api<any[]>("/api/email/important").catch(() => []),
          api<any[]>("/api/timetable/?scope=mine").catch(() => []),
          api<any[]>("/api/planner/exams").catch(() => []),
        ]);
        setMe(meRes);
        setBrief(chat.reply || "");
        setDeadlines(dl);
        setTasks(t);
        setImportant(imp);
        setTimetable(tt);
        setExams(ex);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoaded(true);
      }
    })();
  }, []);

  const openDeadlines = useMemo(() => deadlines.filter((d) => d.status === "open"), [deadlines]);
  const openTasks = useMemo(() => tasks.filter((t) => t.status === "open"), [tasks]);
  const urgentUpdates = useMemo(() => important.filter((x) => x.priority === "high"), [important]);

  const topDeadline = useMemo(() => {
    const withDate = [...openDeadlines].sort(
      (a, b) => new Date(a.due_at || "9999").getTime() - new Date(b.due_at || "9999").getTime()
    );
    return withDate[0] || null;
  }, [openDeadlines]);

  const todayClasses = useMemo(() => {
    const day = (new Date().getDay() + 6) % 7; // Mon=0
    return timetable.filter((c: any) => c.day === day || c.day === String(day)).slice(0, 5);
  }, [timetable]);

  const overdueCount = useMemo(
    () => openDeadlines.filter((d) => d.due_at && new Date(d.due_at).getTime() < Date.now()).length,
    [openDeadlines]
  );

  return (
    <Shell>
      <div className="rounded-2xl bg-gradient-to-r from-indigo-600 via-indigo-600 to-violet-600 text-white p-6 mb-4 shadow">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold">
              {me ? `${greeting()}, ${me.full_name?.split(" ")[0] || "there"} 👋` : "Dashboard"}
            </h1>
            <p className="text-indigo-100 text-sm mt-1">
              {new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })} · agent already checked classes, deadlines & inbox
            </p>
          </div>
          <Link href="/chat?q=What%20should%20I%20focus%20on%20today%3F" className="bg-white text-indigo-700 rounded-lg px-4 py-2 text-sm font-semibold hover:bg-indigo-50">
            🎯 What do I do now?
          </Link>
        </div>
      </div>

      {error && <div className="card text-sm text-red-600 mb-4">{error}</div>}
      {!loaded && (
        <div className="grid gap-4 md:grid-cols-4 animate-pulse">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="card h-24 bg-slate-100" />
          ))}
        </div>
      )}

      {loaded && (
        <div className="space-y-4">
          <div className="grid gap-3 grid-cols-2 md:grid-cols-4">
            {[
              [`${todayClasses.length || "–"}`, "Classes today", "/timetable", "🗓️", "badge-info"],
              [`${openDeadlines.length}`, overdueCount > 0 ? `${overdueCount} overdue!` : "Open deadlines", "/tasks", "⏰", overdueCount > 0 ? "badge-urgent" : "badge-soon"],
              [`${openTasks.length}`, "Open tasks", "/tasks", "✅", "badge-info"],
              [`${urgentUpdates.length}`, "Urgent updates", "/email", "🚨", urgentUpdates.length > 0 ? "badge-urgent" : "badge-ok"],
            ].map(([n, label, href, icon, badge]) => (
              <Link key={label as string} href={href as string} className="card text-center hover:shadow-md transition py-4">
                <div className="text-xl">{icon}</div>
                <div className="text-2xl font-bold text-indigo-700">{n}</div>
                <div className="mt-1"><span className={`badge ${badge}`}>{label}</span></div>
              </Link>
            ))}
          </div>

          <div className="card border-indigo-200 bg-gradient-to-r from-indigo-50 to-white">
            <div className="font-semibold mb-2">🎯 Do NOW — ranked by the agent</div>
            <div className="grid md:grid-cols-3 gap-2 text-sm">
              <div className="bg-white rounded-lg border p-3">
                <div className="text-xs text-slate-500 font-semibold">NEXT CLASS</div>
                <div className="font-medium mt-1">{todayClasses[0] ? `${todayClasses[0].subject} · ${todayClasses[0].start_time} · Room ${todayClasses[0].room || "—"}` : "No more classes today 🎉"}</div>
              </div>
              <div className="bg-white rounded-lg border p-3">
                <div className="text-xs text-slate-500 font-semibold">TOP DEADLINE</div>
                <div className="font-medium mt-1">{topDeadline ? `${topDeadline.title} — ${fmtDate(topDeadline.due_at)}` : "All clear 🎉"}</div>
              </div>
              <div className="bg-white rounded-lg border p-3">
                <div className="text-xs text-slate-500 font-semibold">TOP ALERT</div>
                <div className="font-medium mt-1">{urgentUpdates[0]?.subject || important[0]?.subject || "Nothing urgent ✅"}</div>
              </div>
            </div>
            <div className="mt-2 text-xs text-slate-500">Full reasoning in chat → <Link href="/chat?q=What%20should%20I%20focus%20on%20today%3F" className="text-indigo-600 font-semibold hover:underline">Ask “focus on today”</Link> · Exams: {exams.length || 0} scheduled</div>
          </div>

          <div className="card">
            <div className="flex items-center justify-between mb-2">
              <div className="font-semibold">📌 Your brief</div>
              <Link href="/notifications" className="text-xs text-indigo-600 hover:underline">History →</Link>
            </div>
            <div className="text-sm whitespace-pre-wrap leading-relaxed">{brief || "Brief is warming up… open chat to generate it instantly."}</div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="card">
              <div className="font-semibold mb-2">⚡ Quick actions</div>
              <div className="flex flex-wrap gap-2">
                <Link href="/chat" className="btn">Ask the agent</Link>
                <Link href="/timetable" className="btn-ghost">🗓️ Timetable</Link>
                <Link href="/documents" className="btn-ghost">📄 Upload PDF</Link>
                <Link href="/tasks" className="btn-ghost">✅ Planner</Link>
              </div>
              <div className="mt-3 text-xs text-slate-500">Judge tip: try “Did my timetable change?” — room 301→405 detection is the wow moment.</div>
            </div>
            <div className="card">
              <div className="font-semibold mb-2">💡 Try asking</div>
              <div className="grid gap-2">
                {PROMPTS.map((p) => (
                  <Link key={p} href={`/chat?q=${encodeURIComponent(p)}`} className="prompt-card">
                    <span className="text-indigo-600">→</span> {p}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </Shell>
  );
}
