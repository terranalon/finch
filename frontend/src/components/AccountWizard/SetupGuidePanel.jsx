import { useState } from 'react';

import { getBrokerGuide } from './constants/guides/index.js';
import {
  CheckIcon,
  ChevronDownIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  LightBulbIcon,
  ShieldCheckIcon,
  WrenchIcon,
  XIcon,
} from './icons.jsx';

function SectionHeading({ icon: Icon, title, iconColor }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <div className={`p-2 rounded-lg ${iconColor}`}>
        <Icon className="size-5" />
      </div>
      <h3 className="text-lg font-bold text-[var(--text-primary)]">{title}</h3>
    </div>
  );
}

function ExpandableScreenshot({ src, alt }) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <>
      <div
        className="mt-3 rounded-lg overflow-hidden border border-[var(--border-primary)] cursor-pointer hover:border-accent transition-colors group"
        onClick={() => setIsExpanded(true)}
      >
        <img src={src} alt={alt} className="w-full" loading="lazy" />
        <div className="px-3 py-1.5 bg-[var(--bg-tertiary)] text-xs text-[var(--text-tertiary)] text-center group-hover:text-accent transition-colors">
          Click to expand
        </div>
      </div>

      {isExpanded && (
        <div
          className="fixed inset-0 z-[70] flex items-center justify-center bg-black/80 p-4 cursor-pointer"
          onClick={() => setIsExpanded(false)}
        >
          <button
            onClick={() => setIsExpanded(false)}
            className="absolute top-4 right-4 p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors cursor-pointer"
          >
            <XIcon className="size-6 text-white" />
          </button>
          <img
            src={src}
            alt={alt}
            className="max-w-full max-h-full rounded-lg shadow-2xl object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </>
  );
}

function StepCard({ step, index }) {
  return (
    <div className="flex gap-4">
      <div className="flex-shrink-0 size-8 rounded-full bg-accent text-white flex items-center justify-center font-bold text-sm">
        {index + 1}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h4 className="font-semibold text-[var(--text-primary)]">{step.title}</h4>
          {step.optional && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--bg-tertiary)] text-[var(--text-tertiary)]">
              optional
            </span>
          )}
        </div>
        <p className="text-sm text-[var(--text-secondary)] mt-1">{step.description}</p>

        {step.checklist && (
          <div className="mt-3 space-y-1.5">
            {step.checklist.map((item) => (
              <div key={item.label} className="flex items-center gap-2">
                <CheckIcon className={`size-4 ${item.required ? 'text-accent' : 'text-[var(--text-tertiary)]'}`} />
                <span className={`text-sm ${item.required ? 'font-medium text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'}`}>
                  {item.label}
                  {item.required && <span className="text-xs text-accent ml-1">(required)</span>}
                </span>
              </div>
            ))}
          </div>
        )}

        {step.tip && (
          <div className="mt-3 flex items-start gap-2 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800">
            <LightBulbIcon className="size-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-amber-800 dark:text-amber-300">{step.tip}</p>
          </div>
        )}

        {step.screenshot && (
          <ExpandableScreenshot src={step.screenshot} alt={`Step ${index + 1}: ${step.title}`} />
        )}
      </div>
    </div>
  );
}

function DataScopeTable({ dataScope }) {
  return (
    <div className="overflow-hidden rounded-xl border border-[var(--border-primary)]">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-[var(--bg-tertiary)]">
            <th className="text-left px-4 py-2.5 font-semibold text-[var(--text-secondary)]">Data Type</th>
            <th className="text-center px-4 py-2.5 font-semibold text-[var(--text-secondary)] w-20">Status</th>
            <th className="text-left px-4 py-2.5 font-semibold text-[var(--text-secondary)]">Notes</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border-primary)]">
          {dataScope.map((row) => (
            <tr key={row.type}>
              <td className="px-4 py-2.5 font-medium text-[var(--text-primary)]">{row.type}</td>
              <td className="px-4 py-2.5 text-center">
                {row.included ? (
                  <CheckIcon className="size-5 text-positive mx-auto" />
                ) : (
                  <XIcon className="size-5 text-[var(--text-tertiary)] mx-auto" />
                )}
              </td>
              <td className="px-4 py-2.5 text-[var(--text-secondary)]">{row.note}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TroubleshootingItem({ item }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="border border-[var(--border-primary)] rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-[var(--bg-secondary)] transition-colors cursor-pointer"
      >
        <ExclamationTriangleIcon className="size-5 text-amber-500 flex-shrink-0" />
        <span className="flex-1 text-sm font-medium text-[var(--text-primary)]">{item.problem}</span>
        <ChevronDownIcon className={`size-5 text-[var(--text-tertiary)] transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      {isOpen && (
        <div className="px-4 pb-3 pl-12">
          <p className="text-sm text-[var(--text-secondary)]">{item.solution}</p>
        </div>
      )}
    </div>
  );
}

function SecurityList({ icon: Icon, label, items, colorClass }) {
  return (
    <div>
      <p className={`text-xs font-semibold ${colorClass} uppercase tracking-wide mb-2`}>{label}</p>
      <ul className="space-y-1.5">
        {items.map((item) => (
          <li key={item} className="flex items-start gap-2 text-sm text-[var(--text-primary)]">
            <Icon className={`size-4 ${colorClass} flex-shrink-0 mt-0.5`} />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function GuideOverview({ overview, estimatedTime }) {
  return (
    <div className="p-5 rounded-xl bg-accent-50 dark:bg-accent-900/20 border border-accent-200 dark:border-accent-800">
      <p className="text-sm text-accent-800 dark:text-accent-300">{overview}</p>
      {estimatedTime && (
        <div className="flex items-center gap-2 mt-3 text-xs text-accent-600 dark:text-accent-400">
          <ClockIcon className="size-4" />
          <span>Estimated time: {estimatedTime}</span>
        </div>
      )}
    </div>
  );
}

function GuidePrerequisites({ prerequisites }) {
  if (!prerequisites?.length) return null;
  return (
    <div>
      <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wide mb-3">
        Before you start
      </h3>
      <ul className="space-y-2">
        {prerequisites.map((prereq) => (
          <li key={prereq} className="flex items-start gap-2 text-sm text-[var(--text-primary)]">
            <CheckIcon className="size-4 text-accent flex-shrink-0 mt-0.5" />
            {prereq}
          </li>
        ))}
      </ul>
    </div>
  );
}

function GuideSecuritySection({ security }) {
  if (!security) return null;
  return (
    <div>
      <SectionHeading
        icon={ShieldCheckIcon}
        title="Security Best Practices"
        iconColor="bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400"
      />
      <div className="space-y-4">
        <SecurityList icon={CheckIcon} label="Recommended" items={security.recommended} colorClass="text-positive" />
        <SecurityList icon={XIcon} label="Avoid" items={security.avoid} colorClass="text-negative" />
        {security.note && (
          <p className="text-xs text-[var(--text-tertiary)] italic">{security.note}</p>
        )}
      </div>
    </div>
  );
}

function GuideLimitations({ limitations }) {
  if (!limitations?.length) return null;
  return (
    <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800">
      <h4 className="text-sm font-semibold text-amber-800 dark:text-amber-300 mb-2">Limitations</h4>
      <ul className="space-y-1.5">
        {limitations.map((limit) => (
          <li key={limit} className="flex items-start gap-2 text-sm text-amber-700 dark:text-amber-400">
            <span className="text-amber-500 mt-1">-</span>
            {limit}
          </li>
        ))}
      </ul>
    </div>
  );
}

function RichGuideContent({ guide }) {
  return (
    <div className="space-y-8">
      <GuideOverview overview={guide.overview} estimatedTime={guide.estimatedTime} />
      <GuidePrerequisites prerequisites={guide.prerequisites} />

      <div>
        <h3 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wide mb-4">
          Steps
        </h3>
        <div className="space-y-6">
          {guide.steps.map((step, idx) => (
            <StepCard key={idx} step={step} index={idx} />
          ))}
        </div>
      </div>

      <GuideSecuritySection security={guide.security} />

      {guide.dataScope?.length > 0 && (
        <div>
          <SectionHeading
            icon={CheckIcon}
            title="What Gets Imported"
            iconColor="bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
          />
          <DataScopeTable dataScope={guide.dataScope} />
        </div>
      )}

      <GuideLimitations limitations={guide.limitations} />

      {guide.troubleshooting?.length > 0 && (
        <div>
          <SectionHeading
            icon={WrenchIcon}
            title="Troubleshooting"
            iconColor="bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400"
          />
          <div className="space-y-2">
            {guide.troubleshooting.map((item) => (
              <TroubleshootingItem key={item.problem} item={item} />
            ))}
          </div>
        </div>
      )}

      {guide.afterSetup && (
        <div className="p-5 rounded-xl bg-positive-light dark:bg-positive-bg-dark/20 border border-positive-light dark:border-positive-dark/30">
          <h4 className="font-semibold text-positive dark:text-positive-dark mb-2">After setup</h4>
          <p className="text-sm text-positive dark:text-positive-dark/80">{guide.afterSetup}</p>
        </div>
      )}
    </div>
  );
}

function SimpleGuideContent({ instructions }) {
  return (
    <div className="space-y-8">
      <div className="space-y-6">
        {instructions.steps.map((step, idx) => (
          <div key={idx} className="flex gap-4">
            <div className="flex-shrink-0 size-8 rounded-full bg-accent text-white flex items-center justify-center font-bold">
              {idx + 1}
            </div>
            <div className="flex-1">
              <p className="text-[var(--text-primary)]">{step}</p>
            </div>
          </div>
        ))}
      </div>

      {instructions.note && (
        <div className="p-5 rounded-xl bg-accent-50 dark:bg-accent-900/20 border border-accent-200 dark:border-accent-800">
          <h4 className="font-semibold text-accent-900 dark:text-accent-300 mb-2">Note</h4>
          <p className="text-sm text-accent-700 dark:text-accent-400">{instructions.note}</p>
        </div>
      )}
    </div>
  );
}

export function SetupGuidePanel({ broker, guideType, onClose }) {
  const instructions = broker?.instructions?.[guideType];
  const richGuide = getBrokerGuide(broker?.type, guideType);

  if (!instructions && !richGuide) {
    return null;
  }

  const title = richGuide?.title ?? instructions?.title ?? 'Setup Guide';

  return (
    <div className="fixed inset-0 z-[60] flex justify-end">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      <div className="relative w-full max-w-2xl bg-[var(--bg-primary)] shadow-2xl overflow-y-auto">
        <div className="sticky top-0 bg-[var(--bg-primary)] border-b border-[var(--border-primary)] px-6 py-4 flex items-center justify-between z-10">
          <div>
            <h2 className="text-xl font-bold text-[var(--text-primary)]">{title}</h2>
            <p className="text-sm text-[var(--text-tertiary)]">Step-by-step guide</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
          >
            <XIcon className="size-6 text-[var(--text-tertiary)]" />
          </button>
        </div>

        <div className="p-6">
          {richGuide ? (
            <RichGuideContent guide={richGuide} />
          ) : (
            <SimpleGuideContent instructions={instructions} />
          )}

          <div className="mt-8 p-5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-primary)]">
            <h4 className="font-semibold text-[var(--text-primary)] mb-2">Need help?</h4>
            <p className="text-sm text-[var(--text-secondary)]">
              If you&apos;re having trouble, check out our FAQ or contact support.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
