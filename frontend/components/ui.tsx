"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import {
  BookOpen,
  Compass,
  Feather,
  Globe2,
  HandHeart,
  Heart,
  HeartPulse,
  Leaf,
  Mountain,
  Palette,
  Rocket,
  ShieldCheck,
  Sparkles,
  Sprout,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import type { ClientStatus } from "@/lib/api";

export function Logo({ className = "h-7 w-7" }: { className?: string }) {
  // Four interlaced rings: individual, family, community, world.
  return (
    <svg viewBox="0 0 40 40" className={className} fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <circle cx="20" cy="13" r="8" />
      <circle cx="27" cy="20" r="8" />
      <circle cx="20" cy="27" r="8" />
      <circle cx="13" cy="20" r="8" />
    </svg>
  );
}

export function Brand({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="flex items-center gap-2.5 text-gold">
      <Logo />
      <span className="font-serif text-xl tracking-wide text-ink">
        Aligned <span className="text-gold">AI</span>
      </span>
    </Link>
  );
}

export function TopBar({ right }: { right?: ReactNode }) {
  return (
    <header className="no-print sticky top-0 z-30 border-b border-line/70 bg-paper/85 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-8">
        <Brand />
        <div className="flex items-center gap-3 text-sm">{right}</div>
      </div>
    </header>
  );
}

export function FadeIn({ children, delay = 0, className = "" }: { children: ReactNode; delay?: number; className?: string }) {
  // CSS rather than JS-driven so content can never get stuck invisible.
  return (
    <div className={`fade-in ${className}`} style={{ animationDelay: `${delay}s` }}>
      {children}
    </div>
  );
}

/** Renders **bold** segments from the assistant's replies. */
export function RichText({ text }: { text: string }) {
  return (
    <>
      {text.split("\n").map((line, i) => (
        <p key={i} className={line.trim() === "" ? "h-3" : ""}>
          {line.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
            part.startsWith("**") && part.endsWith("**") ? (
              <strong key={j} className="font-medium text-ink">
                {part.slice(2, -2)}
              </strong>
            ) : (
              <span key={j}>{part}</span>
            ),
          )}
        </p>
      ))}
    </>
  );
}

const VALUE_ICONS: [string[], LucideIcon][] = [
  [["family", "love", "relationship", "home"], Heart],
  [["education", "learning", "knowledge", "wisdom"], BookOpen],
  [["impact", "environment", "planet", "sustainab", "climate", "stewardship"], Leaf],
  [["service", "community", "generosity", "giving", "compassion", "contribution"], HandHeart],
  [["freedom", "independence", "autonomy"], Feather],
  [["growth", "curiosity"], Sprout],
  [["adventure", "travel", "exploration"], Compass],
  [["health", "wellbeing", "vitality"], HeartPulse],
  [["security", "stability", "protection"], ShieldCheck],
  [["entrepreneur", "business", "ambition", "innovation"], Rocket],
  [["creativity", "art", "beauty"], Palette],
  [["justice", "equity", "world"], Globe2],
  [["resilience", "courage", "integrity"], Mountain],
];

export function ValueIcon({ name, className = "h-5 w-5" }: { name: string; className?: string }) {
  const n = name.toLowerCase();
  const Icon = VALUE_ICONS.find(([keys]) => keys.some((k) => n.includes(k)))?.[1] ?? Sparkles;
  return <Icon className={className} strokeWidth={1.4} />;
}

export function ScoreRing({ value, size = 180, stroke = 6, label }: { value: number; size?: number; stroke?: number; label?: string }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="#EDE7DB" strokeWidth={stroke} fill="none" />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke="url(#gold)"
          strokeWidth={stroke}
          strokeLinecap="round"
          fill="none"
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: c * (1 - value / 100) }}
          transition={{ duration: 1.6, ease: [0.22, 1, 0.36, 1], delay: 0.2 }}
        />
        <defs>
          <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#C9A873" />
            <stop offset="100%" stopColor="#8A6A3A" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-serif text-[3.2rem] leading-none text-ink" style={{ fontSize: size / 3.6 }}>
          {value}
          <span className="text-gold" style={{ fontSize: size / 8 }}>%</span>
        </span>
        {label && <span className="eyebrow mt-2 !text-[10px]">{label}</span>}
      </div>
    </div>
  );
}

export function Bar({ value, delay = 0 }: { value: number; delay?: number }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-cream">
      <motion.div
        className="h-full rounded-full bg-gradient-to-r from-gold-light to-gold-deep"
        initial={{ width: 0 }}
        animate={{ width: `${value}%` }}
        transition={{ duration: 1.2, delay, ease: [0.22, 1, 0.36, 1] }}
      />
    </div>
  );
}

export const STATUS: Record<ClientStatus, { label: string; cls: string }> = {
  discovery: { label: "In discovery", cls: "bg-cream text-ink-muted" },
  statement: { label: "Statement ready", cls: "bg-gold-pale/60 text-gold-deep" },
  aligned: { label: "Alignment scored", cls: "bg-sage/10 text-sage" },
};

export function scoreTone(score: number) {
  if (score >= 80) return { label: "Well aligned", cls: "text-sage bg-sage/10" };
  if (score >= 60) return { label: "Largely aligned", cls: "text-gold-deep bg-gold-pale/60" };
  return { label: "Opportunity", cls: "text-amber bg-amber/10" };
}

export function Spinner({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center gap-6 py-24 text-center">
      <motion.div
        className="text-gold"
        animate={{ rotate: 360 }}
        transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
      >
        <Logo className="h-14 w-14" />
      </motion.div>
      <motion.p
        key={label}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="font-serif text-2xl italic text-ink-soft"
      >
        {label}
      </motion.p>
    </div>
  );
}
