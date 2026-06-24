"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Mic, Languages, Video, Waves, ArrowRight } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: (i = 0) => ({ opacity: 1, y: 0, transition: { delay: i * 0.08, duration: 0.5 } }),
};

const FEATURES = [
  { icon: Languages, title: "Translation", body: "English ⇄ Nepali with NLLB-200, accurate and fully offline." },
  { icon: Mic, title: "Voice Cloning", body: "Preserve the original speaker's identity across languages." },
  { icon: Video, title: "Lip Sync", body: "Wav2Lip aligns mouth movement to the translated speech." },
  { icon: Waves, title: "Similarity Scoring", body: "Resemblyzer + ECAPA quantify speaker fidelity." },
];

const STEPS = ["Upload your video", "We transcribe & translate", "Clone the voice & lip-sync", "Download your localized video"];

export default function Landing() {
  return (
    <main className="min-h-screen">
      {/* Hero */}
      <section className="relative mx-auto max-w-6xl px-6 pt-28 pb-20 text-center">
        <motion.div initial="hidden" animate="show" variants={fadeUp}>
          <span className="inline-block rounded-full border border-border px-4 py-1.5 text-small text-text-secondary">
            English ⇄ Nepali · voice-preserving · lip-synced
          </span>
          <h1 className="mt-6 font-heading text-hero font-bold">
            Localize any video, <span className="gradient-text">in your own voice</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-body-lg text-text-secondary">
            Upload a clip, pick a language, and get back a fully localized video — translated,
            voice-cloned, and lip-synced. No cloud AI, no per-minute fees.
          </p>
          <div className="mt-10 flex justify-center gap-4">
            <Link href="/dashboard"><Button size="lg">Try the dashboard <ArrowRight size={18} /></Button></Link>
            <Link href="/login"><Button size="lg" variant="outline">Sign in</Button></Link>
          </div>
        </motion.div>
      </section>

      {/* Features */}
      <section id="features" className="mx-auto max-w-6xl px-6 py-16">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f, i) => (
            <motion.div key={f.title} custom={i} initial="hidden" whileInView="show" viewport={{ once: true }} variants={fadeUp}>
              <Card className="h-full">
                <f.icon className="text-accent" size={28} />
                <h3 className="mt-4 font-heading text-h3">{f.title}</h3>
                <p className="mt-2 text-body text-text-secondary">{f.body}</p>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="mx-auto max-w-6xl px-6 py-16">
        <h2 className="text-center font-heading text-h2">How it works</h2>
        <div className="mt-10 grid gap-6 md:grid-cols-4">
          {STEPS.map((s, i) => (
            <motion.div key={s} custom={i} initial="hidden" whileInView="show" viewport={{ once: true }} variants={fadeUp}>
              <Card>
                <div className="text-h3 font-bold text-primary">{String(i + 1).padStart(2, "0")}</div>
                <p className="mt-2 text-body">{s}</p>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="mx-auto max-w-3xl px-6 py-16">
        <h2 className="text-center font-heading text-h2">FAQ</h2>
        <div className="mt-8 space-y-4">
          {[
            ["Which languages are supported?", "English and Nepali, in both directions."],
            ["Is my data sent to the cloud?", "No — all inference runs on the local Voice_ML service."],
            ["What models power this?", "faster-whisper, NLLB-200, MMS/SpeechT5, OpenVoice, Wav2Lip."],
          ].map(([q, a]) => (
            <Card key={q}>
              <p className="font-medium">{q}</p>
              <p className="mt-1 text-body text-text-secondary">{a}</p>
            </Card>
          ))}
        </div>
      </section>

      <footer className="border-t border-border py-10 text-center text-small text-text-secondary">
        <p>VoiceLocalize — built on the Phase 1–4 AI engine. © 2026</p>
      </footer>
    </main>
  );
}
