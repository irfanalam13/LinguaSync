# FRONTEND ARCHITECTURE (Phase 5 — Step 10)

> Next.js 15 (App Router, React 19) + TypeScript + Tailwind + TanStack Query + Zustand +
> React Hook Form + Zod + Framer Motion. **Status: runnable scaffold** wiring the design
> system, auth, API client, and the core flows (landing → auth → dashboard → upload → jobs →
> results). `npm install` then `npm run dev`; deeper polish + full E2E coverage is iterative.

## Feature-Sliced Design layout
```
web/src/
├── app/            # Next App Router: layout, providers, pages (landing, login, dashboard)
├── features/       # upload (dropzone), jobs (job-card, progress)
├── widgets/        # composite UI blocks (compose features) — extend here
├── entities/       # domain models/UI (user, video, job) — extend here
└── shared/         # lib (api client, cn), store (auth — Zustand+persist), ui (Button, Card)
```

## State & data
- **TanStack Query** for server state (`useQuery`/`useMutation`); job list auto-refetches
  (1.5 s) while any job is queued/running.
- **Zustand** (`shared/store/auth`) holds JWT access/refresh (persisted to localStorage).
- **API client** (`shared/lib/api.ts`) attaches the Bearer token; `next.config` rewrites
  proxy `/api/*` to the backend in dev.

## Design system
Tokens live in `globals.css` (CSS vars) + `tailwind.config.ts`. Fonts via `next/font`:
**Plus Jakarta Sans** (brand/headings), **Inter** (body/buttons/forms), **JetBrains Mono**
(code). Font scale (hero 64 → caption 12) and palette (primary `#4F46E5`, secondary
`#7C3AED`, accent `#06B6D4`, success/danger) map the spec exactly.

> **Design note (flagged, honest):** the spec's `background #00d4ff`, `surface #3cacc3`,
> `card #945aa5`, `border #c40ff0` are highly saturated and clash with the stated premium
> dark inspiration (ElevenLabs/Linear/Vercel). The scaffold keeps these as literal tokens
> (`--bg-spec`, plus `background`/`surface`/`card`/`border` in Tailwind) but renders the app
> on a **dark** practical surface (`--bg #0b0b14`, etc.) for legibility. Swap to the literal
> tokens if the bright palette is intended — recommend a design review.

## Animation (Framer Motion)
Page/section fade-ups, upload state animation, animated progress bars, hover/scale. Kept
light (viewport-once reveals) for performance.

## Dark mode
`<html class="dark">` + dark token defaults; a theme toggle is a small add (tokens already
structured for it).

## Testing
- **Vitest** + Testing Library (`button.test.tsx`) for components.
- **Playwright** (`e2e/smoke.spec.ts`): landing render, auth-gate redirect, login fields.
- Run: `npm test` / `npm run e2e`. (Execution requires `npm install`; see status above.)
