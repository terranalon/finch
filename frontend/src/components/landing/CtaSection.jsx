import { Link } from "react-router-dom";

export default function CtaSection() {
  return (
    <section
      className="lp-fade-up py-24 px-8 text-center"
      style={{ background: "linear-gradient(135deg, #1E3A5F 0%, #0F2440 100%)" }}
    >
      <div className="max-w-[600px] mx-auto">
        <h2 className="text-[36px] max-sm:text-[28px] font-bold text-white tracking-[-0.02em] mb-4">
          Start tracking your real performance.
        </h2>
        <p className="text-[16px] text-white/70 mb-8 leading-[1.5]">
          Join investors who stopped guessing and started knowing.
        </p>
        <Link
          to="/register"
          className="inline-flex items-center justify-center bg-white text-[#1E3A5F] text-[15px] font-semibold px-6 py-3 rounded-md hover:bg-[#F0F4FF] transition-colors no-underline"
        >
          Get Started Free
        </Link>
      </div>
    </section>
  );
}
