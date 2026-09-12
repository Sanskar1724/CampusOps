"use client";
import { useEffect, useState } from "react";

type Exchange = { q: string; a: string[] };

const SCENES: Exchange[] = [
  {
    q: "What is my next class?",
    a: ["Next: DBMS at 09:00 (Room 301).", "Say the word and I'll set a reminder 🔔"],
  },
  {
    q: "/focus",
    a: ["🎯 Do now: CN assignment 4 (due tomorrow 5pm).", "Then revise OS 09:00 — Room 302."],
  },
  {
    q: "Did my timetable change?",
    a: ["Yes ⚠️ DBMS moved Room 301 → 405.", "Source: dept email, 8:12 AM. Timetable updated."],
  },
];

const BUTTONS = ["📅 Today", "➡️ Next", "⏰ Deadlines", "🎯 Focus"];

export default function TelegramDemo() {
  const [scene, setScene] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setScene((s) => (s + 1) % SCENES.length), 4200);
    return () => clearInterval(id);
  }, []);
  const current = SCENES[scene];

  return (
    <div className="mx-auto w-[300px] animate-[floaty_5s_ease-in-out_infinite]">
      <div className="rounded-[2rem] border-[10px] border-slate-900 bg-[#0e1621] shadow-2xl overflow-hidden">
        <div className="bg-[#17212b] px-4 py-3 flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center text-white font-bold">
            C
          </div>
          <div>
            <div className="text-white text-sm font-semibold">CampusOps</div>
            <div className="text-emerald-400 text-[11px]">@Sankiyy_bot · online</div>
          </div>
        </div>
        <div className="p-3 space-y-2 min-h-[300px]" key={scene}>
          <div className="flex justify-end">
            <span className="bg-[#2b5278] text-white text-[13px] rounded-xl rounded-br-sm px-3 py-1.5 max-w-[85%]">
              {current.q}
            </span>
          </div>
          {current.a.map((line, i) => (
            <div key={i} className="flex justify-start">
              <span className="bg-[#182533] text-slate-100 text-[13px] rounded-xl rounded-bl-sm px-3 py-1.5 max-w-[90%]">
                {line}
              </span>
            </div>
          ))}
          <div className="flex flex-wrap gap-1.5 pt-1">
            {BUTTONS.map((b) => (
              <span key={b} className="text-[11px] bg-[#2b5278]/60 text-sky-200 rounded-full px-2.5 py-1">
                {b}
              </span>
            ))}
          </div>
          <div className="text-[11px] text-slate-500 pt-1">
            Type <span className="font-mono text-sky-300">/</span> for all 10 commands
          </div>
        </div>
        <div className="px-3 pb-3">
          <div className="bg-[#17212b] rounded-full px-4 py-2 text-[13px] text-slate-500">
            Message…
          </div>
        </div>
      </div>
      <style>{`@keyframes floaty { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-10px) } }`}</style>
    </div>
  );
}
