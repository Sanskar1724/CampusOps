"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";

const PROMPTS = [
  "What is my next class?",
  "What should I focus on today?",
  "What's important from my college emails?",
  "What assignments are coming up?",
];

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [me, chat, deadlines, tasks, important] = await Promise.all([
          api<any>("/api/auth/me"),
          api<{ reply: string }>("/api/chat/", {
            method: "POST",
            body: JSON.stringify({ text: "What should I focus on today?" }),
          }),
          api<any[]>("/api/planner/deadlines"),
          api<any[]>("/api/planner/tasks"),
          api<any[]>("/api/email/important"),
        ]);
        setData({ me, brief: chat.reply });
        setStats({
          deadlines: deadlines.filter((d) => d.status === "open").length,
          tasks: tasks.filter((t) => t.status === "open").length,
          urgent: important.filter((x) => x.priority === "high").length,
        });
      } catch (err: any) {
        setError(err.message);
      }
    })();
  }, []);

  return (
    <Shell>
      <div className="rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white p-6 mb-4">
        <h1 className="text-2xl font-bold">
          {data ? `${greeting()}, ${data.me.full_name?.split(" ")[0] || "there"} 👋` : "Dashboard"}
        </h1>
        <p className="text-indigo-100 text-sm mt-1">
          Your agent already checked today's classes, deadlines, and inbox.
        </p>
      </div>
      {error && <div className="card text-sm text-red-600">{error}</div>}
      {!data && !error && (
        <div className="grid gap-4 md:grid-cols-3 animate-pulse">
          {[0, 1, 2].map((i) => (
            <div key={i} className="card h-20 bg-slate-100" />
          ))}
        </div>
      )}
      {data && (
        <div className="space-y-4">
          <div className="grid gap-4 grid-cols-3">
            {[
              [`${stats?.deadlines ?? "–"}`, "Open deadlines", "/tasks"],
              [`${stats?.tasks ?? "–"}`, "Open tasks", "/tasks"],
              [`${stats?.urgent ?? "–"}`, "Urgent updates", "/email"],
            ].map(([n, label, href]) => (
              <Link key={label} href={href} className="card text-center hover:shadow-md transition">
                <div className="text-2xl font-bold text-indigo-700">{n}</div>
                <div className="text-xs text-slate-500">{label}</div>
              </Link>
            ))}
          </div>
          <div className="card">
            <div className="font-semibold mb-2">📌 Your brief</div>
            <div className="text-sm whitespace-pre-wrap">{data.brief}</div>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="card">
              <div className="font-semibold mb-2">⚡ Quick actions</div>
              <div className="flex flex-wrap gap-2">
                <Link href="/chat" className="btn">Ask the agent</Link>
                <Link href="/timetable" className="btn-ghost">Timetable</Link>
                <Link href="/documents" className="btn-ghost">Upload PDF</Link>
              </div>
            </div>
            <div className="card">
              <div className="font-semibold mb-2">💡 Try asking</div>
              <ul className="text-sm space-y-1 text-slate-600">
                {PROMPTS.map((p) => (
                  <li key={p}>
                    <Link href={`/chat?q=${encodeURIComponent(p)}`} className="text-indigo-600 hover:underline">
                      {p}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </Shell>
  );
}
