import Link from "next/link";
import TelegramDemo from "@/components/TelegramDemo";

const REPO = "https://github.com/Sanskar1724/CampusOps";
const DOC = (p: string) => `${REPO}/blob/master/docs/${p}`;

function GitHubMark({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" className={className} aria-hidden="true">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z" />
    </svg>
  );
}

function TelegramMark({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden="true">
      <path d="M21.9 4.6 2.7 12.1c-.65.25-.66 1.16-.02 1.42l4.7 1.82 1.8 5.64c.25.77 1.23.86 1.62.16l2.63-3.35 4.95 3.63c.5.37 1.23.06 1.35-.55l2.5-14.6c.12-.71-.6-1.29-1.3-1.07ZM8.6 13.6l9.2-6.9c.14-.1.31.08.2.21l-7.6 8.1-.3 3.1-1.5-4.5Z" />
    </svg>
  );
}

export default function Landing() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-indigo-50 via-white to-slate-50">
      <header className="max-w-6xl mx-auto flex items-center justify-between p-6">
        <div className="text-xl font-bold text-indigo-700 flex items-center gap-2">
          <img src="/logo.svg" alt="CampusOps logo" className="w-8 h-8" />
          CampusOps
        </div>
        <div className="flex items-center gap-3">
          <span
            title="Current release"
            className="hidden sm:inline-flex items-center gap-1.5 text-xs font-bold text-white rounded-full px-3 py-1.5 bg-gradient-to-r from-indigo-600 via-violet-600 to-fuchsia-500 shadow-md shadow-indigo-200"
          >
            ✨ v1.0
          </span>
          <a
            href={REPO}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-ghost !py-2 flex items-center gap-2"
            title="View on GitHub"
          >
            <GitHubMark />
            <span className="hidden sm:inline">GitHub</span>
          </a>
          <Link href="/login" className="btn-ghost">Sign in</Link>
          <Link href="/register" className="btn">Get started</Link>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-6 pb-20">
        <div className="text-center py-10">
          <div className="inline-block text-xs font-semibold bg-indigo-100 text-indigo-700 rounded-full px-4 py-1.5 mb-5">
            ✨ One agent for your entire academic life — web, Telegram & email
          </div>          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight leading-tight">
            Never miss a class,<br />
            <span className="text-indigo-600">deadline, or any notice</span> again
          </h1>
          <p className="mt-6 text-lg text-slate-600 max-w-2xl mx-auto">
            <strong>CampusOps (Campus Operating System)</strong> reads your college
            email, timetable, and notices — then pings you with a morning brief,
            urgent alerts, and answers. One brain, everywhere you are.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link href="/login" className="btn text-base px-6 py-3">Get started — free</Link>
            <Link href="/register" className="btn-ghost text-base px-6 py-3">Create account</Link>
          </div>
          <p className="mt-3 text-xs text-slate-500">
            Exploring? Sign in with the sample account <span className="font-mono font-semibold">demo.student@example.com / demo1234</span>
          </p>
        </div>

        <div className="overflow-hidden mb-12 [mask-image:linear-gradient(to_right,transparent,black_10%,black_90%,transparent)]">
          <div className="flex gap-2.5 w-max animate-[ticker_28s_linear_infinite]">
            {[0, 1].map((copy) => (
              <div key={copy} className="flex gap-2.5" aria-hidden={copy === 1}>
                {["/today — today's classes", "🔔 class-start pings", "🚨 room-change radar", "⏰ deadline alerts", "🎯 focus engine", "/brief — morning brief", "📄 PDFs that answer back", "🙈 hide anything", "/deadlines", "🌅 exams + reminders"].map((t) => (
                  <span key={`${copy}-${t}`} className="whitespace-nowrap text-xs font-medium bg-white border border-slate-200 rounded-full px-3.5 py-1.5 shadow-sm text-slate-600">
                    {t}
                  </span>
                ))}
              </div>
            ))}
          </div>
          <style>{`@keyframes ticker { from { transform: translateX(0) } to { transform: translateX(-50%) } }`}</style>
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

        <div className="card text-left flex items-start gap-3 mb-12">
          <span className="text-2xl">🤖</span>
          <div className="text-sm text-slate-600">
            <span className="font-semibold text-slate-900">Try it live right now: </span>
            message <span className="font-mono font-semibold">@Sankiyy_bot</span> on Telegram with{" "}
            <span className="font-mono">Hello CampusOps</span>, or press <span className="font-semibold">Get started</span> above.
            <span className="block mt-1 text-xs text-slate-500">FastAPI + Next.js · SQLite → Postgres+pgvector · offline-safe LLM fallback</span>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-8 items-center mb-12">
          <div className="text-left">
            <div className="text-xs font-semibold text-indigo-600 mb-2">✈️ TELEGRAM SPOTLIGHT</div>
            <h2 className="text-3xl font-extrabold tracking-tight mb-4">
              Your campus life,<br />in your pocket
            </h2>
            <ul className="space-y-3 text-sm text-slate-600">
              <li className="flex gap-2"><span>⌨️</span><span><strong>CLI-style commands</strong> — type <span className="font-mono">/</span> for today, next, deadlines, exams, brief, focus & more.</span></li>
              <li className="flex gap-2"><span>👆</span><span><strong>4 tap buttons</strong> under every reply — Today, Next class, Deadlines, Focus.</span></li>
              <li className="flex gap-2"><span>🔔</span><span><strong>Proactive pings</strong> — class-start alerts, deadline & exam warnings, room changes.</span></li>
              <li className="flex gap-2"><span>💬</span><span><strong>Real conversation</strong> — short personal answers plus full onboarding in chat.</span></li>
            </ul>
            <a
              href="https://t.me/Sankiyy_bot"
              target="_blank"
              rel="noopener noreferrer"
              className="btn mt-5 inline-flex items-center gap-2"
            >
              <TelegramMark className="w-4 h-4" />
              Open @Sankiyy_bot
            </a>
          </div>
          <TelegramDemo />
        </div>
      </main>
      <footer className="border-t border-slate-200 mt-4">
        <div className="max-w-6xl mx-auto px-6 py-10 grid gap-8 md:grid-cols-4 text-sm">
          <div>
            <div className="flex items-center gap-2 font-bold text-indigo-700 mb-2">
              <img src="/logo.svg" alt="CampusOps logo" className="w-6 h-6" />
              CampusOps
            </div>
            <p className="text-slate-500 text-[13px] leading-relaxed">
              Personal academic agent for students — timetable, email, documents
              and deadlines, answered by one AI brain on web, Telegram and email.
            </p>
          </div>
          <div>
            <div className="font-semibold mb-2">Team</div>
            <ul className="space-y-1.5 text-slate-600">
              <li><a className="text-indigo-600 font-medium hover:underline" href="https://github.com/Sanskar1724" target="_blank" rel="noopener noreferrer">Sanskar1724</a></li>
              <li><a className="text-indigo-600 font-medium hover:underline" href="https://github.com/Pratiksha2968" target="_blank" rel="noopener noreferrer">Pratiksha2968</a></li>
              <li><a className="text-indigo-600 hover:underline" href={`${REPO}/blob/master/CONTRIBUTORS.md`} target="_blank" rel="noopener noreferrer">All contributors →</a></li>
            </ul>
          </div>
          <div>
            <div className="font-semibold mb-2">Docs</div>
            <ul className="space-y-1.5 text-slate-600">
              <li><a className="text-indigo-600 hover:underline" href={DOC("USER_GUIDE.md")} target="_blank" rel="noopener noreferrer">📖 User guide</a></li>
              <li><a className="text-indigo-600 hover:underline" href={DOC("AGENT.md")} target="_blank" rel="noopener noreferrer">🧠 Agent design</a></li>
              <li><a className="text-indigo-600 hover:underline" href={DOC("API.md")} target="_blank" rel="noopener noreferrer">🔌 API reference</a></li>
              <li><a className="text-indigo-600 hover:underline" href={DOC("DEPLOYMENT.md")} target="_blank" rel="noopener noreferrer">🚀 Deployment</a></li>
              <li><a className="text-indigo-600 hover:underline" href={DOC("ERROR_HANDLING.md")} target="_blank" rel="noopener noreferrer">🧰 Error handling</a></li>
            </ul>
          </div>
          <div>
            <div className="font-semibold mb-2">Project</div>
            <ul className="space-y-1.5 text-slate-600">
              <li><a className="text-indigo-600 hover:underline font-medium" href={REPO} target="_blank" rel="noopener noreferrer"><span className="inline-flex items-center gap-1.5"><GitHubMark className="w-3.5 h-3.5" /> GitHub repository</span></a></li>
              <li><a className="text-indigo-600 hover:underline" href={`${REPO}/issues`} target="_blank" rel="noopener noreferrer">🐞 Report an issue</a></li>
              <li><a className="text-indigo-600 hover:underline" href="https://t.me/Sankiyy_bot" target="_blank" rel="noopener noreferrer"><span className="inline-flex items-center gap-1.5"><TelegramMark className="w-3.5 h-3.5" /> Telegram bot</span></a></li>
              <li><Link className="text-indigo-600 hover:underline" href="/help">❓ In-app help</Link></li>
            </ul>
          </div>
        </div>
        <div className="border-t border-slate-100 py-4 text-center text-xs text-slate-400">
          CampusOps — your personal academic agent · built for students
        </div>
      </footer>
    </div>
  );
}
