import { HeroSection } from "@/components/landing/hero-section";
import { WhatItDoesSection } from "@/components/landing/what-it-does-section";
import { CatchTrackAnalyzeSection } from "@/components/landing/catch-track-analyze-section";
import { ProjectSelectSection } from "@/components/landing/project-select-section";
import { AdminModeControl } from "@/components/admin-mode-control";

export default function LandingPage() {
  return (
    <main>
      <AdminModeControl floating />
      <HeroSection />
      <WhatItDoesSection />
      <CatchTrackAnalyzeSection />
      <ProjectSelectSection />
    </main>
  );
}
