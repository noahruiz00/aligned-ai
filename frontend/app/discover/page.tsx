"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, ArrowUp } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { FadeIn, Logo, RichText, Spinner, TopBar } from "@/components/ui";
import { api, type ChatMessage, type Household, type Stage } from "@/lib/api";

const STAGES: { key: Stage | "steward"; label: string }[] = [
  { key: "discover", label: "Discover" },
  { key: "harvest", label: "Harvest" },
  { key: "architect", label: "Architect" },
  { key: "steward", label: "Steward" },
];
const TOTAL_QUESTIONS = 6;
const LOADING_LINES = [
  "Listening for what matters most…",
  "Harvesting your values…",
  "Architecting your Wealth Purpose Statement…",
];

export default function Discover() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [household, setHousehold] = useState<Household>("individual");
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [userId, setUserId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [stage, setStage] = useState<Stage>("discover");
  const [answered, setAnswered] = useState(0);
  const [ready, setReady] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [loadingLine, setLoadingLine] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, thinking, ready]);

  useEffect(() => {
    if (!generating) return;
    const t = setInterval(() => setLoadingLine((l) => Math.min(l + 1, LOADING_LINES.length - 1)), 2600);
    return () => clearInterval(t);
  }, [generating]);

  async function start(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setThinking(true);
    setError(null);
    try {
      const r = await api.startChat(name.trim(), household);
      setConversationId(r.conversation_id);
      setUserId(r.user_id);
      setDemoMode(r.demo_mode);
      setMessages([{ role: "assistant", content: r.reply }]);
      setTimeout(() => inputRef.current?.focus(), 300);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reach the server");
    } finally {
      setThinking(false);
    }
  }

  async function send() {
    const text = input.trim();
    if (!text || !conversationId || thinking) return;
    setInput("");
    setError(null);
    setMessages((m) => [...m, { role: "user", content: text }]);
    setThinking(true);
    try {
      const r = await api.sendChat(conversationId, text);
      setMessages((m) => [...m, { role: "assistant", content: r.reply }]);
      setStage(r.stage);
      setAnswered(r.answered);
      setReady(r.ready);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setMessages((m) => m.slice(0, -1));
      setInput(text);
    } finally {
      setThinking(false);
      inputRef.current?.focus();
    }
  }

  async function architect() {
    if (!conversationId || !userId) return;
    setGenerating(true);
    setLoadingLine(0);
    try {
      await api.analyzeValues(conversationId);
      await api.generatePurpose(userId);
      router.push(`/client/${userId}/statement`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setGenerating(false);
    }
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  if (generating) {
    return (
      <main className="min-h-screen">
        <TopBar />
        <Spinner label={LOADING_LINES[loadingLine]} />
      </main>
    );
  }

  // --- Intake ---------------------------------------------------------------
  if (!conversationId) {
    return (
      <main className="min-h-screen">
        <TopBar />
        <div className="mx-auto max-w-xl px-5 py-20 sm:px-8">
          <FadeIn>
            <p className="eyebrow">Discover</p>
            <h1 className="mt-4 font-serif text-5xl leading-tight">
              Let&apos;s begin with <em className="text-gold-deep">you</em>, not your portfolio.
            </h1>
            <p className="mt-6 leading-relaxed text-ink-muted">
              Over the next few minutes, you&apos;ll be asked a handful of questions about purpose, meaning, and
              legacy. Answer as briefly or as fully as you like.
            </p>
          </FadeIn>
          <FadeIn delay={0.15}>
            <form onSubmit={start} className="card mt-10 space-y-8 p-8">
              <label className="block">
                <span className="eyebrow">Your name</span>
                <input
                  autoFocus
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Sarah Johnson"
                  className="mt-3 w-full border-b border-line bg-transparent pb-2 font-serif text-2xl outline-none transition placeholder:text-ink-muted/40 focus:border-gold"
                />
              </label>
              <div>
                <span className="eyebrow">I&apos;m planning as</span>
                <div className="mt-3 grid grid-cols-3 gap-2">
                  {(["individual", "couple", "family"] as Household[]).map((h) => (
                    <button
                      type="button"
                      key={h}
                      onClick={() => setHousehold(h)}
                      className={`rounded-xl border px-3 py-3 text-sm capitalize transition ${
                        household === h ? "border-gold bg-gold-pale/40 text-ink" : "border-line text-ink-muted hover:border-gold/50"
                      }`}
                    >
                      {h === "individual" ? "An individual" : h === "couple" ? "A couple" : "A family"}
                    </button>
                  ))}
                </div>
              </div>
              <button type="submit" disabled={!name.trim() || thinking} className="btn-primary w-full">
                {thinking ? "Preparing…" : "Begin the conversation"} <ArrowRight className="h-4 w-4" />
              </button>
              {error && <p className="text-sm text-amber">{error}</p>}
            </form>
          </FadeIn>
        </div>
      </main>
    );
  }

  // --- Conversation -----------------------------------------------------------
  const stageIndex = STAGES.findIndex((s) => s.key === stage);
  return (
    <main className="flex h-screen flex-col">
      <TopBar right={demoMode && <span className="rounded-full bg-cream px-3 py-1 text-xs text-ink-muted">Demo mode</span>} />

      <div className="border-b border-line/70 bg-paper">
        <div className="mx-auto flex max-w-3xl items-center gap-4 px-5 py-4 sm:px-8">
          {STAGES.map((s, i) => (
            <div key={s.key} className="flex flex-1 items-center gap-3">
              <span className={`text-xs tracking-wide transition ${i <= stageIndex ? "text-gold-deep" : "text-ink-muted/50"}`}>
                <span className="font-serif">{`0${i + 1}`}</span> <span className="hidden sm:inline">{s.label}</span>
              </span>
              {i < STAGES.length - 1 && <div className={`h-px flex-1 ${i < stageIndex ? "bg-gold/60" : "bg-line"}`} />}
            </div>
          ))}
        </div>
        <div className="h-0.5 bg-cream">
          <motion.div className="h-full bg-gold" animate={{ width: `${Math.min(answered / TOTAL_QUESTIONS, 1) * 100}%` }} transition={{ duration: 0.8 }} />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-8 px-5 py-10 sm:px-8">
          <AnimatePresence initial={false}>
            {messages.map((m, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                className={m.role === "user" ? "flex justify-end" : "flex gap-4"}
              >
                {m.role === "assistant" ? (
                  <>
                    <div className="mt-1 shrink-0 text-gold">
                      <Logo className="h-6 w-6" />
                    </div>
                    <div className="max-w-[85%] space-y-1 font-serif text-[1.35rem] leading-relaxed text-ink-soft">
                      <RichText text={m.content} />
                    </div>
                  </>
                ) : (
                  <div className="max-w-[80%] rounded-2xl rounded-br-md bg-ink px-5 py-3.5 leading-relaxed text-paper">{m.content}</div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>

          {thinking && (
            <div className="flex items-center gap-4 text-gold">
              <motion.div animate={{ rotate: 360 }} transition={{ duration: 6, repeat: Infinity, ease: "linear" }}>
                <Logo className="h-6 w-6" />
              </motion.div>
              <span className="font-serif text-lg italic text-ink-muted">Reflecting…</span>
            </div>
          )}

          {ready && !thinking && (
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="card flex flex-col items-start gap-4 border-gold/40 bg-gold-pale/20 p-6 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="eyebrow">Ready to architect</p>
                <p className="mt-1 text-sm text-ink-muted">You can keep talking, or create your Wealth Purpose Statement now.</p>
              </div>
              <button onClick={architect} className="btn-primary shrink-0">
                Create my statement <ArrowRight className="h-4 w-4" />
              </button>
            </motion.div>
          )}
          {error && <p className="text-sm text-amber">{error}</p>}
          <div ref={endRef} />
        </div>
      </div>

      <div className="border-t border-line bg-paper/90 backdrop-blur">
        <div className="mx-auto max-w-3xl px-5 py-4 sm:px-8">
          <div className="flex items-end gap-3 rounded-2xl border border-line bg-white p-2 pl-5 shadow-card focus-within:border-gold/60">
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKey}
              placeholder="Share what comes to mind…"
              className="max-h-40 flex-1 resize-none bg-transparent py-2.5 leading-relaxed outline-none placeholder:text-ink-muted/50"
            />
            <button
              onClick={send}
              disabled={!input.trim() || thinking}
              aria-label="Send"
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-ink text-paper transition hover:bg-gold-deep disabled:opacity-30"
            >
              <ArrowUp className="h-4 w-4" />
            </button>
          </div>
          <p className="mt-2 text-center text-[11px] text-ink-muted/70">
            Your answers are shared only with your advisor. This conversation is not financial advice.
          </p>
        </div>
      </div>
    </main>
  );
}
