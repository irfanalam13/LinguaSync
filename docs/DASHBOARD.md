# DASHBOARD (Phase 5 — Step 12)

`web/src/app/dashboard/page.tsx` — authenticated workspace.

## Features
- **Auth gate** — redirects to `/login` if no token (Zustand `isAuthenticated`).
- **Usage stats** — 4 stat cards (videos, jobs, completed, running) from `/users/me/usage`.
- **New localization** — upload dropzone → configure target language + mode
  (translate / preserve / clone / localize) → "Start localization" (creates a job).
- **Your jobs** — grid of `JobCard`s; auto-refetches every 1.5 s while any job is
  queued/running (TanStack Query `refetchInterval`).
- **Sign out** — clears tokens.

## Data flow
`useQuery(['jobs'])` + `useQuery(['usage'])`; `useMutation` to create jobs and invalidate
caches. All calls go through `shared/lib/api` with the Bearer token.

## Processing history
The jobs grid is the history (newest first); completed jobs expose preview + download
(see RESULTS_PAGE.md). A dedicated `/history` route with filters/pagination is a small extension.
