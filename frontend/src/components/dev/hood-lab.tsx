"use client";
import * as React from "react";
import { HoodGauge } from "@/components/ui/hood-gauge";
import { Button } from "@/components/ui/button";
import { spreadForGate } from "@/lib/brand/hood";

function Slider({ id, label, min, max, step, value, onChange, valueText }: {
  id: string; label: string; min: number; max: number; step: number; value: number; onChange: (v: number) => void; valueText: string;
}) {
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="flex items-baseline justify-between text-sm text-bone-2">
        <span>{label}</span>
        <span className="num text-bone">{valueText}</span>
      </label>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        aria-valuetext={valueText}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-2 w-full cursor-pointer accent-(--signal)"
      />
    </div>
  );
}

/** Dev-only playground for the gauge: the same component the console, explorer and favicon story use. */
export function HoodLab() {
  const [gate, setGate] = React.useState(1);
  const [score, setScore] = React.useState(100);
  const [animate, setAnimate] = React.useState(true);

  return (
    <div className="grid gap-8 md:grid-cols-[minmax(0,260px)_1fr] md:items-center">
      <div className="flex items-center justify-center rounded-card border border-line bg-ink-1 p-8 shadow-[var(--inner-highlight)]">
        <HoodGauge gate={gate} score={score} size={220} animate={animate} />
      </div>
      <div className="flex max-w-md flex-col gap-5">
        <Slider id="gate" label="Gate multiplier G(s)" min={0.3} max={1} step={0.01} value={gate} onChange={setGate}
          valueText={`${gate.toFixed(2)} (open ${spreadForGate(gate).toFixed(1)} degrees)`} />
        <Slider id="score" label="Final score T_final" min={0} max={100} step={1} value={score} onChange={setScore} valueText={String(score)} />
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" onClick={() => { setGate(1); setScore(100); }}>Passes</Button>
          <Button size="sm" variant="secondary" onClick={() => { setGate(0.65); setScore(65); }}>Tapers</Button>
          <Button size="sm" variant="secondary" onClick={() => { setGate(0.3); setScore(30); }}>Trips</Button>
          <Button size="sm" variant={animate ? "primary" : "ghost"} aria-pressed={animate} onClick={() => setAnimate((a) => !a)}>
            Animate {animate ? "on" : "off"}
          </Button>
        </div>
      </div>
    </div>
  );
}
