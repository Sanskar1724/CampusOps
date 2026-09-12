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

function TelegramLogo({ className = "w-5 h-5" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center justify-center rounded-full bg-[#229ED9] ${className}`}>
      <svg viewBox="0 0 24 24" fill="white" className="w-3/5 h-3/5" aria-hidden="true">
        <path d="M21.9 4.6 2.7 12.1c-.65.25-.66 1.16-.02 1.42l4.7 1.82 1.8 5.64c.25.77 1.23.86 1.62.16l2.63-3.35 4.95 3.63c.5.37 1.23.06 1.35-.55l2.5-14.6c.12-.71-.6-1.29-1.3-1.07ZM8.6 13.6l9.2-6.9c.14-.1.31.08.2.21l-7.6 8.1-.3 3.1-1.5-4.5Z" />
      </svg>
    </span>
  );
}

export default function TelegramDemo() {
  const [scene, setScene] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setScene((s) => (s + 1) % SCENES.length), 4200);
    return () => clearInterval(id);
  }, []);
  const current = SCENES[scene];

  return (
    <div className="mx-auto w-[300px] animate-[floaty_5s_ease-in-out_infinite]">
      {/* iPhone frame: side buttons + rounded titanium edge */}
      <div className="relative rounded-[3rem] bg-slate-900 p-[10px] shadow-2xl">
        <div className="absolute -left-[2px] top-20 w-[3px] h-8 bg-slate-700 rounded-l-md" />
        <div className="absolute -left-[2px] top-32 w-[3px] h-12 bg-slate-700 rounded-l-md" />
        <div className="absolute -right-[2px] top-24 w-[3px] h-14 bg-slate-700 rounded-r-md" />
        <div className="rounded-[2.4rem] overflow-hidden bg-[#0e1621]">
          {/* iOS status bar */}
          <div className="bg-[#0e1621] px-6 pt-3 pb-1 flex items-center justify-between text-white text-xs font-semibold">
            <span>9:41</span>
            <div className="flex items-center gap-1.5">
              <svg viewBox="0 0 16 12" className="w-4 h-3" fill="white" aria-hidden="true">
                <rect x="0" y="7" width="3" height="5" rx="0.5" />
                <rect x="4.5" y="5" width="3" height="7" rx="0.5" />
                <rect x="9" y="2.5" width="3" height="9.5" rx="0.5" />
                <rect x="13" y="0" width="3" height="12" rx="0.5" opacity="0.4" />
              </svg>
              <svg viewBox="0 0 24 24" className="w-4 h-4" fill="white" aria-hidden="true">
                <path d="M12 18.5a1.75 1.75 0 1 0 0 .01M12 14c-2 0-3.8.78-5.14 2.05l1.7 1.7A4.98 4.98 0 0 1 12 16.5c1.38 0 2.63.56 3.54 1.46l1.7-1.7A7.22 7.22 0 0 0 12 14m0-4c-3.1 0-5.9 1.2-7.93 3.2l1.7 1.7A8.97 8.97 0 0 1 12 12c2.48 0 4.72 1 6.34 2.62l1.7-1.7A11.2 11.2 0 0 0 12 10m0-4c-4.2 0-8 1.68-10.77 4.4l1.7 1.7A13.46 13.46 0 0 1 12 8c3.73 0 7.1 1.51 9.55 3.94l1.7-1.7A15.68 15.68 0 0 0 12 6" />
              </svg>
              <svg viewBox="0 0 25 12" className="w-6 h-3" aria-hidden="true">
                <rect x="0" y="0" width="21" height="12" rx="3" fill="none" stroke="white" opacity="0.5" />
                <rect x="2" y="2" width="15" height="8" rx="1.5" fill="white" />
                <rect x="22.5" y="3.5" width="2.5" height="5" rx="1" fill="white" opacity="0.5" />
              </svg>
            </div>
          </div>
          {/* Dynamic Island */}
          <div className="bg-[#0e1621] flex justify-center pb-1">
            <div className="w-24 h-6 bg-black rounded-full border border-slate-800" />
          </div>
          {/* Telegram chat header with official-style logo */}
          <div className="bg-[#17212b] px-4 py-2.5 flex items-center gap-3">
            <TelegramLogo className="w-9 h-9" />
            <div>
              <div className="text-white text-sm font-semibold">CampusOps</div>
              <div className="text-emerald-400 text-[11px]">@Sankiyy_bot · online</div>
            </div>
          </div>
          <div className="p-3 space-y-2 min-h-[290px]" key={scene}>
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
          <div className="px-3 pb-4">
            <div className="bg-[#17212b] rounded-full px-4 py-2 text-[13px] text-slate-500">
              Message…
            </div>
          </div>
          {/* iOS home indicator */}
          <div className="bg-[#0e1621] flex justify-center pb-2">
            <div className="w-28 h-1 bg-slate-600 rounded-full" />
          </div>
        </div>
      </div>
      <style>{`@keyframes floaty { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-10px) } }`}</style>
    </div>
  );
}
