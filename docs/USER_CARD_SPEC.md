# User-card spec — the markdown behind personal answers

Every turn rebuilds `build_user_card_md()` fresh from live data and puts it
in the **system prompt** (not the user message), so the model reasons *as*
this student's tutor. Format contract (stable — tests pin the key lines):

```md
# Student: <full name>
- Dept <d> · Div <v> · Batch <b> · Sem <s> · Roll <r>
- View scope: <Div A-B1 | whole class> (timetable below is already filtered to it)
- Today (<Day>): <Subject HH:MM-HH:MM Room R>; … | no classes
- Deadlines: <title> (due <iso>, <priority>); … | none open      (top 5, 14d)
- Exams: <subject> at <iso|TBA>; … | none scheduled              (top 3, 30d)
- Recent alerts: <title> [<priority>]; … | nothing new           (top 3)
- Remember about them: <key> = <value>; … | nothing stored yet   (top 8 memories)
- Hidden from their views: <subs>, <Days>s                       (only if any)
- Style: warm, specific, varied wording; use their first name
  occasionally; never repeat a previous reply verbatim.
```

Rules: never invent rows (empty → "none …" fallbacks); PRN/college email are
**excluded** (identity stays in the DB, not the prompt); hidden items appear
only as counts elsewhere; retrieval facts arrive separately as
RETRIEVED CONTEXT, and the last ≤6 turns as chat history.
