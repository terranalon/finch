import { Link } from "react-router-dom";

function CheckIcon() {
  return (
    <svg
      className="w-4 h-4 flex-shrink-0 text-[#059669] mt-px"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M3 8.5l3.5 3.5 6.5-8" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg
      className="w-4 h-4 flex-shrink-0 text-[var(--text-tertiary)] opacity-50 mt-px"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M4 4l8 8M12 4l-8 8" />
    </svg>
  );
}

const PLANS = [
  {
    name: "Free",
    desc: "For getting started with portfolio tracking.",
    price: "0",
    period: "Free forever",
    featured: false,
    cta: "Get Started",
    ctaVariant: "secondary",
    features: [
      { included: true, text: "1 broker connection" },
      { included: true, text: "Manual CSV import" },
      { included: true, text: "Basic portfolio dashboard" },
      { included: true, text: "Holdings overview" },
      { included: false, text: "Automatic sync" },
      { included: false, text: "Performance analytics" },
    ],
  },
  {
    name: "Standard",
    desc: "For active investors tracking multiple brokers.",
    price: "9",
    period: "per month",
    featured: true,
    badge: "Most Popular",
    cta: "Start Free Trial",
    ctaVariant: "primary",
    features: [
      { included: true, text: "Up to 5 broker connections" },
      { included: true, text: "Automatic daily sync" },
      { included: true, text: "Full portfolio dashboard" },
      { included: true, text: "Performance analytics" },
      { included: true, text: "S&P 500 benchmarking" },
      { included: true, text: "Asset-level insights" },
    ],
  },
  {
    name: "Premium",
    desc: "For power users who want the full picture.",
    price: "19",
    period: "per month",
    featured: false,
    cta: "Start Free Trial",
    ctaVariant: "secondary",
    features: [
      { included: true, text: "Unlimited broker connections" },
      { included: true, text: "Real-time sync (hourly)" },
      { included: true, text: "Everything in Standard" },
      { included: true, text: "Income & dividend tracking" },
      { included: true, text: "Multi-currency support" },
      { included: true, text: "Priority support" },
    ],
  },
];

export default function PricingSection() {
  return (
    <section
      id="pricing"
      className="lp-fade-up scroll-mt-20 py-24 px-8 max-w-[1200px] mx-auto"
    >
      <div className="text-center mb-14">
        <div className="text-[13px] font-semibold text-[var(--accent-primary)] uppercase tracking-[1.5px] mb-3">
          Pricing
        </div>
        <h2 className="text-[36px] font-bold text-[var(--text-primary)] tracking-[-0.02em] mb-4">
          Simple, transparent pricing
        </h2>
        <p className="text-[16px] text-[var(--text-secondary)] max-w-[560px] mx-auto leading-relaxed">
          Start free. Upgrade when you need more power.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-[400px] md:max-w-none mx-auto">
        {PLANS.map((plan) => (
          <div
            key={plan.name}
            className={`bg-[var(--bg-secondary)] border rounded-lg p-8 flex flex-col hover:-translate-y-0.5 hover:shadow-lg transition-all relative ${
              plan.featured
                ? "border-[var(--accent-primary)] lp-pricing-featured"
                : "border-[var(--border-primary)]"
            }`}
          >
            {plan.badge && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[var(--accent-primary)] text-white text-[11px] font-semibold px-3.5 py-1 rounded-full whitespace-nowrap">
                {plan.badge}
              </span>
            )}

            <div className="text-[15px] font-semibold text-[var(--text-primary)] mb-1">
              {plan.name}
            </div>
            <div className="text-[13px] text-[var(--text-tertiary)] mb-5 leading-[1.4]">
              {plan.desc}
            </div>

            <div className="flex items-baseline gap-1 mb-1">
              <span className="text-[14px] font-semibold text-[var(--text-secondary)] self-start mt-1.5">$</span>
              <span className="font-numeric text-[40px] font-bold text-[var(--text-primary)] tracking-[-0.02em] leading-none">
                {plan.price}
              </span>
            </div>
            <div className="text-[13px] text-[var(--text-tertiary)] mb-6">{plan.period}</div>

            <div className="h-px bg-[var(--border-primary)] mb-5" />

            <ul className="flex flex-col gap-2.5 mb-7 flex-1">
              {plan.features.map((feat) => (
                <li
                  key={feat.text}
                  className="text-[13px] text-[var(--text-secondary)] flex items-start gap-2 leading-[1.4]"
                >
                  {feat.included ? <CheckIcon /> : <XIcon />}
                  <span className={feat.included ? "" : "text-[var(--text-tertiary)]"}>
                    {feat.text}
                  </span>
                </li>
              ))}
            </ul>

            <Link
              to="/register"
              className={`block w-full py-2.5 text-[14px] font-semibold rounded-md text-center no-underline transition-colors ${
                plan.ctaVariant === "primary"
                  ? "bg-[var(--accent-primary)] text-white hover:opacity-90"
                  : "bg-transparent text-[var(--text-primary)] border border-[var(--border-primary)] hover:bg-[var(--bg-tertiary)]"
              }`}
            >
              {plan.cta}
            </Link>
          </div>
        ))}
      </div>
    </section>
  );
}
