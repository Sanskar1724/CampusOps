"use client";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";

export default function Help() {
  const [md, setMd] = useState("Loading guide…");
  const [copied, setCopied] = useState("");

  useEffect(() => {
    api<{ markdown: string }>("/api/system/help")
      .then((d) => setMd(d.markdown))
      .catch((e) => setMd(`Could not load the guide: ${e.message}`));
  }, []);

  const copy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(""), 1500);
  };

  return (
    <Shell>
      <h1 className="text-2xl font-bold mb-1">❓ Help & User Guide</h1>
      <p className="text-sm text-slate-500 mb-4">Everything you need — from first login to Telegram, data retention, and troubleshooting.</p>

      <div className="grid gap-4 md:grid-cols-2 mb-4">
        <div className="card border-indigo-200 bg-gradient-to-r from-indigo-50 to-white">
          <div className="font-semibold mb-2">🔗 Keep your data forever</div>
          <div className="text-sm text-slate-600 mb-2">Your data is tied to your <span className="font-mono">college email</span> — not your device. Log out or change browser? Just log in again with the same email and everything returns. Telegram too:</div>
          <ol className="text-sm text-slate-600 list-decimal list-inside space-y-1 mb-3">
            <li>Web: <span className="font-semibold">Profile → Generate Telegram link code</span> (6 digits, 10 min)</li>
            <li>Telegram: send <span className="font-mono">/link 123456</span> to @Sankiyy_bot</li>
            <li>Done — web and Telegram now share one account. No more “already registered” errors.</li>
          </ol>
          <div className="text-xs bg-amber-50 border border-amber-200 rounded p-2">💡 Same email = same data, even after months. The code is just for linking a new device/Telegram.</div>
        </div>
        <div className="card">
          <div className="font-semibold mb-2">🔄 Quick restart commands</div>
          <div className="text-xs text-slate-500 mb-2">Copy-paste in your server terminal:</div>
          <div className="space-y-2">
            {[
              ["API", "python -m uvicorn backend.app.main:app --port 8000"],
              ["Web", "cd frontend; npm run dev  # :3001"],
              ["Telegram (one only)", "TELEGRAM_SELF_HOST=1 python -m backend.app.comms.runner"],
              ["Worker", "python -m backend.app.jobs.worker"],
            ].map(([label, cmd]) => (
              <div key={label} className="flex items-center justify-between gap-2 bg-slate-50 rounded px-2 py-1.5">
                <span className="text-xs font-semibold">{label}:</span>
                <code className="text-xs font-mono flex-1 text-right truncate">{cmd}</code>
                <button className="text-xs text-indigo-600 hover:underline" onClick={() => copy(cmd, label)}>{copied === label ? "✓ Copied" : "Copy"}</button>
              </div>
            ))}
          </div>
          <div className="text-xs text-slate-500 mt-2">On Render/Vercel, use <span className="font-mono">Manual Deploy → Deploy latest commit</span> after pushing.</div>
        </div>
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-2">
          <div className="font-semibold">📖 Full guide</div>
          <span className="text-xs text-slate-500">Live from docs/USER_GUIDE.md</span>
        </div>
        <div className="text-sm whitespace-pre-wrap leading-relaxed bg-slate-50 rounded-lg p-3 border max-h-[60vh] overflow-auto">{md}</div>
      </div>

      <div className="card mt-4 bg-gradient-to-r from-sky-50 to-indigo-50 border-sky-200">
        <div className="font-semibold mb-1">Still stuck?</div>
        <div className="text-sm text-slate-600">Settings → Backend connections shows every integration 🟢/🔴 with the exact fix. For Telegram silence, ensure exactly one runner and that you’ve sent <span className="font-mono">/link CODE</span> after generating it on the web.</div>
      </div>
    </Shell>
  );
}
