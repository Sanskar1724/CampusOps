# CampusOps User Guide

Welcome! CampusOps is your personal academic agent — it tracks your classes,
deadlines, emails, and documents, then helps you stay on top of everything.
You talk to the SAME agent on the website, on Telegram, and over email.

## 1. Getting started (2 minutes)

1. **Create your account** (Register page) or tap **Continue with Google**.
2. **Finish onboarding** — the agent asks 8 quick questions (name, PRN,
   department, division, batch, roll number, semester, college email).
   Your division + batch decide which classes are yours.
3. Open the **Dashboard** — your brief is already there.

## 2. Timetable — yours by default

- The **Timetable** page opens on **👤 My classes** (your division + batch only,
  e.g. B1). Tap **Show all divisions** anytime for the whole class.
- **Add a class** with the form, **upload CSV/JSON**, or **scan a PDF/photo**
  of the college timetable.
- **Paste timetable text** straight from the portal/PDF.
- **Hide things you don't want**: just tell the agent in chat —
  `hide OS`, `don't show Saturdays`, `mute Physics`. Hidden items vanish from
  chat, briefs, and My classes (rows are kept). `show everything again`
  restores all; `what did I hide` lists them.
- **Delete for real**: `delete Physics class` removes those rows permanently.

## 3. Chat — what to ask

- `What should I focus on today?` — ranked plan with 🎯 Do now
- `What is my next class?` / `What do I have tomorrow?`
- `Did my timetable change?` — room/time conflicts with email sources
- `What's important from my college emails?`
- `Remind me about OS revision tomorrow at 9am`
- `Add task: revise DBMS indexing`
- `When is the DBMS exam?` (searches your documents)

## 4. Email intelligence

- **Settings → Connect Gmail** (read-only, Google login — your password is
  never asked). Then **Email → Sync Gmail** (or `Sync?days=30&limit=50`
  for a deep catch-up).
- Every mail is classified: assignment, deadline, exam, room/timetable change,
  event, placement, notice — with dates, rooms, and subjects extracted.
- Relevant items become deadlines, exams, and announcements automatically.
  Room changes trigger a ⚠️ change alert.

## 5. Documents

- Upload **PDF, TXT, CSV, XLSX, DOCX, PNG, JPG** on the Documents page.
- Scanned/photo PDFs are re-read with vision OCR automatically (watch for the
  extraction badge). If a scan reads poorly, press **🔁 Re-scan with OCR**.
- Use **semantic search**: `exam dates`, `fee rules`, `holiday list`.

## 6. Telegram — @Sankiyy_bot

- Message the bot, answer onboarding once, then chat like on the website.
- **Commands** (type `/` to list them all): `/today` `/tomorrow` `/week`
  `/next` `/deadlines` `/exams` `/reminders` `/brief` `/focus` `/help` —
  plus 4 tappable buttons (Today, Next class, Deadlines, Focus) under
  every reply. Answers are short and formatted for chat.
- Class-start pings (🔔 ~15 min before) and exam alerts arrive automatically
  when notifications are on.
- Keep ONE bot runner at a time (two pollers steal each other's updates).

## 7. Notifications — your rules

- **Notifications page → Preferences**: toggle morning brief, deadline,
  reminder, and change alerts separately; set **quiet hours**
  (e.g. 22:00–07:00) and delivery channel (auto / gateway / Telegram).
- The worker sends the **morning brief**, **due-soon deadline** alerts,
  and due **reminders**. Missed quiet-hour items retry later — nothing spams.

## 8. Privacy in one paragraph

- Your PRN, email, and academic data are visible only to you — every screen
  and every agent answer is filtered to your account.
- Passwords are hashed; college mail uses Google OAuth (we never see your
  password). Email/PDF text is treated as untrusted data, never as
  instructions.

## 9. When something looks wrong

- **Settings → Backend connections** shows every integration 🟢/🔴 with the fix.
- Timetable looks off? Check **Show all divisions** — your Div/Batch in
  **Profile** decides your filter.
- Bot silent on Telegram? Make sure exactly one runner polls, and use
  `TELEGRAM_SELF_HOST=1` where the Caspian gateway is blocked.
