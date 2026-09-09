import Link from "next/link";

export default function Landing() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-indigo-50 via-white to-white">
      <header className="max-w-5xl mx-auto flex items-center justify-between p-6">
        <div className="text-xl font-bold text-indigo-700">🎓 CampusOps</div>
        <div className="space-x-3">
          <Link href="/login" className="btn-ghost">Sign in</Link>
          <Link href="/register" className="btn">Get started</Link>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-6 py-16 text-center">
        <div className="inline-block text-xs font-semibold bg-indigo-100 text-indigo-700 rounded-full px-3 py-1 mb-4">
          Your personal academic agent
        </div>
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
          An AI agent that knows your <span className="text-indigo-600">academic life</span>
        </h1>
        <p className="mt-6 text-lg text-slate-600 max-w-2xl mx-auto">
          CampusOps reads your college email, timetable, and notices — then tells you
          what matters: room changes, deadlines, exams, and what to focus on today.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Link href="/register" className="btn">Create your profile</Link>
          <Link href="/chat" className="btn-ghost">Talk to the agent</Link>
        </div>
        <div className="mt-14 grid md:grid-cols-3 gap-4 text-left">
          {[
            ["🌅 Morning brief", "Classes, deadlines, and priorities — every day."],
            ["🔔 Change detection", "Room moved? Exam rescheduled? You'll know first."],
            ["💬 One agent, everywhere", "Web chat, Telegram, and email share the same brain."],
          ].map(([t, d]) => (
            <div key={t} className="card hover:shadow-md transition">
              <div className="font-semibold">{t}</div>
              <div className="text-sm text-slate-600 mt-1">{d}</div>
            </div>
          ))}
        </div>
        <div className="mt-10 card text-left flex items-start gap-3">
          <span className="text-2xl">🤖</span>
          <div className="text-sm text-slate-600">
            <span className="font-semibold text-slate-900">Try it live: </span>
            message <span className="font-mono">@Sankiyy_bot</span> on Telegram, or sign in
            with the demo account <span className="font-mono">demo.student@example.com</span>.
          </div>
        </div>
      </main>
    </div>
  );
}
