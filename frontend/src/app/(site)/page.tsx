import { Hero } from "@/components/sections/hero";
import { BlindSpot } from "@/components/sections/blind-spot";
import { WalkGate } from "@/components/sections/walk-gate";
import { GateExplorerSection } from "@/components/sections/gate-explorer-section";
import { Results } from "@/components/sections/results";
import { Pipeline } from "@/components/sections/pipeline";
import { SeenFromAbove } from "@/components/sections/seen-from-above";
import { EthicsSection } from "@/components/sections/ethics-section";
import { RunIt } from "@/components/sections/run-it";
import { CtaBand } from "@/components/sections/cta-band";

export default function HomePage() {
  return (
    <main>
      <Hero />
      <BlindSpot />
      <WalkGate />
      <GateExplorerSection />
      <Results />
      <Pipeline />
      <SeenFromAbove />
      <EthicsSection />
      <RunIt />
      <CtaBand />
    </main>
  );
}
