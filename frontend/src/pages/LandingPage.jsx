import { useEffect } from "react";
import { useTheme } from "../contexts";

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
  const { theme, setTheme } = useTheme();

  // Force light mode -- marketing page is light-only. Restore on unmount.
  useEffect(() => {
    const prev = theme;
    if (prev !== "light") setTheme("light");
    return () => {
      if (prev !== "light") setTheme(prev);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
