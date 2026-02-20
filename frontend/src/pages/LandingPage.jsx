import { useEffect } from "react";

import "../components/landing/landing.css";
import LandingNavbar from "../components/landing/LandingNavbar";
import HeroSection from "../components/landing/HeroSection";
import BrokersSection from "../components/landing/BrokersSection";
import FeaturesSection from "../components/landing/FeaturesSection";
import HowItWorksSection from "../components/landing/HowItWorksSection";
import PricingSection from "../components/landing/PricingSection";
import CtaSection from "../components/landing/CtaSection";
import LandingFooter from "../components/landing/LandingFooter";

export default function LandingPage() {
  // Force light mode -- marketing page is light-only
  useEffect(() => {
    const hadDark = document.documentElement.classList.contains("dark");
    document.documentElement.classList.remove("dark");
    return () => {
      if (hadDark) document.documentElement.classList.add("dark");
    };
  }, []);

  // Fade-in animations: IntersectionObserver for scroll reveal,
  // hero elements animate in immediately without waiting for scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) =>
        entries.forEach((e) => {
          if (e.isIntersecting) e.target.classList.add("is-visible");
        }),
      { threshold: 0.1, rootMargin: "0px 0px -40px 0px" }
    );
    document.querySelectorAll(".lp-fade-up").forEach((el) => observer.observe(el));

    const heroTimer = setTimeout(() => {
      document
        .querySelectorAll(".lp-hero-glow .lp-fade-up")
        .forEach((el) => el.classList.add("is-visible"));
    }, 100);

    return () => {
      observer.disconnect();
      clearTimeout(heroTimer);
    };
  }, []);

  return (
    <div className="scroll-smooth bg-[var(--bg-primary)] text-[var(--text-primary)] overflow-x-hidden">
      <LandingNavbar />
      <HeroSection />
      <BrokersSection />
      <FeaturesSection />
      <HowItWorksSection />
      <PricingSection />
      <CtaSection />
      <LandingFooter />
    </div>
  );
}
