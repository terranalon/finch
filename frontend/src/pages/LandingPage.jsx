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
      if (hadDark) {
        document.documentElement.classList.add("dark");
      }
    };
  }, []);

  // Scroll-triggered fade-in for all .lp-fade-up elements
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) =>
        entries.forEach((e) => {
          if (e.isIntersecting) e.target.classList.add("is-visible");
        }),
      { threshold: 0.1, rootMargin: "0px 0px -40px 0px" }
    );
    const elements = document.querySelectorAll(".lp-fade-up");
    elements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  // Hero elements animate in immediately without waiting for scroll
  useEffect(() => {
    const timer = setTimeout(() => {
      document
        .querySelectorAll(".lp-hero-glow .lp-fade-up")
        .forEach((el) => el.classList.add("is-visible"));
    }, 100);
    return () => clearTimeout(timer);
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
