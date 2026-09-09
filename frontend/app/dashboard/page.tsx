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

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [me, chat] = await Promise.all([
          api<any>("/api/auth/me"),
          api<{ reply: string }>("/api/chat/", {
            method: "POST",
            body: JSON.stringify({ text: "What should I focus on today?" }),
          }),
        ]);
        setData({ me, brief: chat.reply });
      } catch (err: any) {
        setError(err.message);
      }
    })();
  }, []);

  return (
    <Shell>
      <h1 className="text-2xl font-bold mb-4">
        {data ? `Good day, ${data.me.full_name || "student"} 👋` : "Dashboard"}
      </h1>
      {error && <div className="card text-sm text-red-600">{error}</div>}
      {!data && !error && <div className="card text-sm text-slate-500">Loading your day…</div>}
      {data && (
        <div className="grid gap-4 md:grid-cols-2">
          <div className="card md:col-span-2">
            <div className="font-semibold mb-2">Your brief</div>
            <div className="text-sm whitespace-pre-wrap">{data.brief}</div>
          </div>
          <div className="card">
            <div className="font-semibold mb-2">Quick actions</div>
            <div className="flex flex-wrap gap-2">
              <Link href="/chat" className="btn">Ask the agent</Link>
              <Link href="/timetable" className="btn-ghost">Timetable</Link>
              <Link href="/documents" className="btn-ghost">Upload PDF</Link>
            </div>
          </div>
          <div className="card">
            <div className="font-semibold mb-2">Try asking</div>
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
      )}
    </Shell>
  );
}
