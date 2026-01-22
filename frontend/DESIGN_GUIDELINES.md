# Finch Design Guidelines

Design system for Finch Portfolio Tracker. All new components and pages must follow these guidelines.

**Reference:** See `.claude/skills/portfolio-ui.md` for complete UI constraints.

---

## Color System

### Always Use CSS Variables

Never use hardcoded Tailwind colors. Always use CSS variables from `src/index.css`.

### Backgrounds

| Variable | Usage |
|----------|-------|
| `--bg-primary` | Page backgrounds |
| `--bg-secondary` | Cards, modals, inputs |
| `--bg-tertiary` | Hover states |

```jsx
// Good
<div className="bg-[var(--bg-primary)]">

// Bad
<div className="bg-white dark:bg-gray-900">
```

### Text

| Variable | Usage |
|----------|-------|
| `--text-primary` | Headings, primary text |
| `--text-secondary` | Descriptions |
| `--text-tertiary` | Muted text, placeholders |

### Borders

| Variable | Usage |
|----------|-------|
| `--border-primary` | Default borders |
| `--border-secondary` | Emphasized borders |

### Accent Color (Blue)

Primary accent is **blue** for buttons, links, and focus states.

| Class | Usage |
|-------|-------|
| `text-accent` | Links, accent text |
| `bg-accent` | Primary buttons |
| `hover:bg-accent-hover` | Hover states |
| `focus:ring-accent` | Focus rings |

```jsx
// Good
<button className="bg-accent hover:bg-accent-hover">

// Bad - don't use emerald for primary actions
<button className="bg-emerald-600">
```

### Financial Data Colors

For gains/losses, use semantic colors (NOT the accent blue):

| Purpose | Classes |
|---------|---------|
| Gains/Positive | `text-positive`, `bg-positive-bg` |
| Losses/Negative | `text-negative`, `bg-negative-bg` |

```jsx
// Good
<span className="text-positive">+5.2%</span>
<span className="text-negative">-3.1%</span>

// Also good - using Tailwind semantic colors
<span className="text-emerald-600">+5.2%</span>
<span className="text-red-600">-3.1%</span>
```

**IMPORTANT:** Never use color alone - always pair with icons (▲/▼) or text (+/-).

---

## Typography

### Numeric Data

| Rule | Class |
|------|-------|
| All numbers | `tabular-nums` |
| Numeric columns | `text-right` |
| Prices/currency | `font-mono tabular-nums` |

```jsx
// Good
<td className="text-right tabular-nums font-mono">$1,234.56</td>

// Bad
<td>$1,234.56</td>
```

### Text Wrapping

| Element | Class |
|---------|-------|
| Headings | `text-balance` |
| Descriptions | `text-pretty` |
| Asset names in tight spaces | `truncate` with `title` attribute |

### Font Stack

- **Numbers:** JetBrains Mono (already configured)
- **Body:** Inter (already configured)
- **NEVER:** Decorative, display, or script fonts

---

## Layout

### Full-Height Layouts

```jsx
// Good - uses dynamic viewport height
<div className="min-h-dvh">

// Bad - doesn't account for mobile browser chrome
<div className="min-h-screen">
```

### Square Elements

```jsx
// Good - single size property
<Icon className="size-6" />

// Acceptable but verbose
<Icon className="w-6 h-6" />
```

### Z-Index Scale

| Layer | Value |
|-------|-------|
| Dropdowns | `z-10` |
| Modals | `z-20` |
| Navigation | `z-30` |
| Toasts | `z-40` |

### Container Width

Always use consistent max-width: `max-w-6xl` or `max-w-7xl`

---

## Buttons

Use predefined button classes:

| Class | Usage |
|-------|-------|
| `btn-primary` | Primary actions (submit, save) |
| `btn-secondary` | Secondary actions (cancel, demo) |
| `btn-ghost` | Tertiary actions |

All clickable elements must have `cursor-pointer`.

---

## Input Fields

```jsx
<input
  className="
    mt-1 block w-full px-3 py-2
    border border-[var(--border-primary)]
    placeholder-[var(--text-tertiary)]
    text-[var(--text-primary)]
    bg-[var(--bg-secondary)]
    rounded-md
    focus:outline-none focus:ring-2 focus:ring-accent
    sm:text-sm transition-colors
  "
/>
```

---

## Charts

| Data Type | Chart Type |
|-----------|------------|
| Time-series (portfolio value, price history) | Line chart or Area chart |
| Categorical comparisons (holdings by value) | Bar chart |
| Allocation/composition | Treemap or horizontal bars |

**Rules:**
- MUST include axis labels with units
- MUST include legends for multiple series
- NEVER use pie charts for more than 5 segments
- NEVER use 3D charts or decorative styles

---

## Loading States

- MUST use skeleton screens matching data layout
- MUST show stale data with "Updating..." rather than replacing with spinner
- NEVER block entire view when partial data is available
- NEVER use spinning logos

```jsx
import { Skeleton } from '../components/ui';

// Good
<Skeleton className="h-8 w-32" />
```

---

## Empty States

- MUST provide one clear primary action ("Add your first holding")
- MUST explain what will appear when populated
- NEVER leave views completely blank
- NEVER show generic "No data"

---

## Animation

- MUST NOT add animation unless explicitly requested
- MUST respect `prefers-reduced-motion`
- MUST keep interaction feedback under 150ms
- Only animate `transform` and `opacity`
- NEVER animate layout properties (`width`, `height`, `margin`)
- NEVER animate number changes in real-time

---

## Interaction

- All clickable elements: `cursor-pointer`
- Destructive actions: Use confirmation dialog
- Errors: Show inline, next to relevant input
- Focus: Use `focus-visible` for keyboard indicators
- NEVER block paste in input fields

---

## Mobile

- Touch targets: minimum 44x44px
- Use `safe-area-inset-bottom` for fixed bottom elements
- NEVER rely on hover states for essential information

---

## Accessibility

- Minimum 4.5:1 contrast ratio for text
- Color is never the only indicator (use icons/text)
- All images have `alt` text
- Form inputs have labels
- Charts have text alternatives (summary or data table)

---

## Pre-Delivery Checklist

### Data Integrity
- [ ] All numbers use `tabular-nums`
- [ ] Decimals are aligned and consistent
- [ ] Gains are green, losses are red, with icons/text backup

### Visual Quality
- [ ] No gradients on data elements
- [ ] Skeleton loaders match content layout
- [ ] Empty states have clear actions

### Interaction
- [ ] All clickable elements have `cursor-pointer`
- [ ] Destructive actions use confirmation dialogs
- [ ] Keyboard navigation works

### Accessibility
- [ ] 4.5:1 contrast on all text
- [ ] Color is not the only indicator
- [ ] Touch targets are 44px minimum

---

## Quick Reference

**DO:**
- Use CSS variables: `var(--bg-primary)`, `var(--text-secondary)`
- Use `min-h-dvh` for full-height layouts
- Use `size-*` for square elements
- Use `tabular-nums font-mono` for financial data
- Use `text-balance` for headings, `text-pretty` for body

**DON'T:**
- Use hardcoded colors: `bg-gray-50`, `text-gray-900`
- Use `min-h-screen` (use `min-h-dvh`)
- Use color alone without icons/text
- Use decorative fonts or 3D charts
- Animate layout properties

---

## Files Reference

- **Color tokens:** `src/index.css`
- **Tailwind config:** `tailwind.config.js`
- **UI Components:** `src/components/ui/`
- **Layout Components:** `src/components/layout/`
- **Portfolio UI Skill:** `.claude/skills/portfolio-ui.md`
