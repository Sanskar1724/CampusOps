# Contributing to CampusOps

## Workflow (required)

1. Clone, then branch **from `master`**: `git checkout -b yourname/feature`
2. Set your identity once (needed for contributor credit):
   `git config user.name "YourGitHubUsername"` and
   `git config user.email "YourGitHubUsername@users.noreply.github.com"`
3. Small commits, descriptive messages (one feature/fix per commit).
4. Push the branch, open a **Pull Request** against `master`.
5. Green checks required: `python -m pytest backend/tests/ -q`,
   `npx tsc --noEmit` (in `frontend/`), `npm run build`.

## Rules

- Never commit `.env`, `*.db`, `node_modules/`, `.venv/`, `.next/`,
  `__pycache__/` — all ignored. Copy `.env.example` to `.env` locally.
- Every student-scoped query filters by the JWT student. Cross-student
  access must return 404, with a test proving it.
- `backend/app/comms/` is the only place that imports `caspian`.
- No chain-of-thought leaves the server; email/PDF text is untrusted data.
- Frontend: no hardcoded API host (use `lib/api.ts`); parse `detail` errors.
