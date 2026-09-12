import Link from "next/link";

export default function Landing() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-indigo-50 via-white to-slate-50">
      <header className="max-w-6xl mx-auto flex items-center justify-between p-6">
        <div className="text-xl font-bold text-indigo-700">🎓 CampusOps</div>
        <div className="flex items-center gap-3">
          <Link href="/login" className="btn-ghost">Sign in</Link>
          <Link href="/register" className="btn">Get started</Link>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-6 pb-20">
        <div className="text-center py-10">
          <div className="inline-block text-xs font-semibold bg-indigo-100 text-indigo-700 rounded-full px-4 py-1.5 mb-5">
            ✨ One agent for your entire academic life — web, Telegram & email
          </div>
          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight leading-tight">
            Never miss a class,<br />
            <span className="text-indigo-600">deadline, or room change</span> again
          </h1>
          <p className="mt-6 text-lg text-slate-600 max-w-2xl mx-auto">
            CampusOps reads your college email, timetable, and notices — then pings you
            with a morning brief, urgent alerts, and answers. One brain, everywhere you are.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link href="/login" className="btn text-base px-6 py-3">Get started — free</Link>
            <Link href="/chat" className="btn-ghost text-base px-6 py-3">💬 Talk to the agent</Link>
          </div>
          <p className="mt-3 text-xs text-slate-500">
            Exploring? Sign in with the sample account <span className="font-mono font-semibold">demo.student@example.com / demo1234</span>
          </p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 max-w-4xl mx-auto mb-12">
          {[
            ["1", "agent brain"],
            ["3", "channels (web, Telegram, email)"],
            ["10+", "agent tools"],
            ["24h", "deadline radar"],
          ].map(([n, label]) => (
            <div key={label} className="card text-center py-4">
              <div className="text-2xl font-extrabold text-indigo-700">{n}</div>
              <div className="text-xs text-slate-500 mt-1">{label}</div>
            </div>
          ))}
        </div>

        <div className="grid md:grid-cols-3 gap-4 text-left mb-12">
          {[
            ["🌅 Morning brief, zero effort", "Classes today, deadlines due, exams ahead, and top-3 priorities — composed every morning from YOUR data, never hallucinated."],
            ["🚨 Room-change radar", "Dept mail says “DBMS moved 301 → 405”? CampusOps detects the conflict, links the source, and alerts you before you walk to the wrong room."],
            ["🎯 “What do I do NOW?”", "New Focus engine ranks next class + overdue + due-tomorrow + urgent notices into one actionable answer. Ask it in chat."],
            ["📧 Inbox → action", "Gmail sync classifies every mail: assignment, deadline, exam, notice, spam. Important ones surface; noise stays buried."],
            ["📄 PDFs that answer back", "Upload academic calendars & notices. Semantic search + citations means you can ask “when is the DBMS exam?” and get the line."],
            ["💬 One agent, everywhere", "Web chat, Telegram @Sankiyy_bot, and email share the same Core Agent, memory, and tools — not three bots."],
          ].map(([t, d]) => (
            <div key={t} className="card hover:shadow-lg hover:-translate-y-0.5 transition">
              <div className="font-semibold">{t}</div>
              <div className="text-sm text-slate-600 mt-1.5 leading-relaxed">{d}</div>
            </div>
          ))}
        </div>

        <div className="card mb-6 border-indigo-200 bg-gradient-to-r from-indigo-50 to-violet-50">
          <div className="font-semibold mb-3">⚡ See it in action in 60 seconds</div>
          <div className="grid md:grid-cols-3 gap-3 text-sm">
            <div className="bg-white rounded-lg p-3 border"><span className="font-bold">1.</span> Sign in with the sample account → dashboard shows <em>Do-NOW + brief + urgency badges</em>.</div>
            <div className="bg-white rounded-lg p-3 border"><span className="font-bold">2.</span> Chat: <span className="font-mono text-indigo-700">“Did my timetable change?”</span> → room 301→405 with email source.</div>
            <div className="bg-white rounded-lg p-3 border"><span className="font-bold">3.</span> Chat: <span className="font-mono text-indigo-700">“What should I focus on today?”</span> → ranked plan + deadlines.</div>
          </div>
        </div>

        <div className="card text-left flex items-start gap-3">
          <span className="text-2xl">🤖</span>
          <div className="text-sm text-slate-600">
            <span className="font-semibold text-slate-900">Try it live right now: </span>
            message <span className="font-mono font-semibold">@Sankiyy_bot</span> on Telegram with{" "}
            <span className="font-mono">Hello CampusOps</span>, or press <span className="font-semibold">Get started</span> above.
            <span className="block mt-1 text-xs text-slate-500">FastAPI + Next.js · SQLite → Postgres+pgvector · offline-safe LLM fallback</span>
          </div>
        </div>
      </main>
      <footer className="border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        CampusOps — your personal academic agent · built for students
      </footer>
    </div>
  );
}
