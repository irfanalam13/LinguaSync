# LANDING PAGE (Phase 5 — Step 11)

`web/src/app/page.tsx` — production-style marketing page, Framer-Motion animated.

## Sections
1. **Hero** — badge, gradient headline ("Localize any video, in your own voice"), subcopy,
   primary CTA (→ dashboard) + secondary (→ sign in).
2. **Features** — 4 cards: Translation (NLLB-200), Voice Cloning, Lip Sync (Wav2Lip),
   Similarity Scoring (Resemblyzer/ECAPA).
3. **How it works** — 4 numbered steps (upload → transcribe & translate → clone & lip-sync →
   download).
4. **Demo** — placeholder slot (embed a sample localized clip; wire to a public asset).
5. **Pricing (placeholder)** — intentionally omitted per "no monetization"; a neutral
   placeholder section can be added without payment logic.
6. **FAQ** — languages, on-prem/no-cloud, models.
7. **Footer** — brand + copyright.

## Design
Uses the design tokens, `gradient-text`, `glass` cards, Plus Jakarta Sans headings, Inter
body. Reveal-on-scroll via `whileInView` (once) for performance.

> Honest note: copy/demo are scaffold-level; replace the demo slot with a real sample video
> and finalize marketing copy before launch.
