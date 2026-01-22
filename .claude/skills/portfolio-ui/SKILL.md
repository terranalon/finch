---
name: portfolio-ui
description: Opinionated constraints for building financial portfolio interfaces. Optimizes for data clarity, trust, and daily-use utility.
---

# Portfolio UI Skill

Constraints for building financial data interfaces that prioritize clarity, performance, and trust.

## How to use

- `/portfolio-ui`
  Apply these constraints to any UI work in this conversation.

- `/portfolio-ui <file>`
  Review the file against all constraints and output:
  - violations (quote the exact line/snippet)
  - why it matters (1 short sentence)
  - a concrete fix (code-level suggestion)

---

## Stack

- MUST use Tailwind CSS defaults unless custom values already exist in the project
- MUST use `motion/react` only when animation is explicitly requested
- MUST use `cn` utility (`clsx` + `tailwind-merge`) for class logic
- SHOULD use `tw-animate-css` for subtle entrance animations if needed
- MUST use existing project components before creating new ones

---

## Components

- MUST use accessible primitives for interactive elements (`Base UI`, `React Aria`, or `Radix`)
- MUST add `aria-label` to icon-only buttons
- MUST use semantic HTML (`<table>` for tabular data, `<button>` for actions)
- NEVER rebuild keyboard, focus, or tooltip behavior by hand
- NEVER mix component primitive libraries within the same view

---

## Typography

- MUST use `tabular-nums` for all numeric data (prices, percentages, quantities)
- MUST use `text-right` alignment for numeric columns
- MUST use `text-balance` for headings
- MUST use `text-pretty` for descriptions and body text
- SHOULD use monospace or semi-monospace for prices: `IBM Plex Mono`, `JetBrains Mono`, `Fira Code`
- SHOULD use clean sans-serif for labels: `IBM Plex Sans`, `DM Sans`, `Inter`
- SHOULD use `truncate` for asset names with `title` attribute for full name
- SHOULD use `line-clamp-2` for news/notes content
- NEVER use decorative, display, or script fonts
- NEVER modify `letter-spacing` unless explicitly requested

---

## Color

- MUST use semantic colors for financial data:
  - Green for gains/positive: `emerald-500` / `emerald-600`
  - Red for losses/negative: `red-500` / `red-600`
  - Neutral for unchanged: `slate-500`
- MUST use neutral base palette: `slate` or `zinc` (not warm or cool tints)
- MUST ensure 4.5:1 minimum contrast ratio for all data
- MUST limit accent color to one per view (for CTAs, active states, selections)
- SHOULD use muted backgrounds: `slate-50` light / `slate-900` dark
- SHOULD use subtle borders: `slate-200` light / `slate-700` dark
- NEVER use gradients on data-bearing elements
- NEVER use gradients for backgrounds unless explicitly requested
- NEVER use purple, rainbow, or multicolor schemes
- NEVER use color as the only indicator (add icons or text for accessibility)

---

## Charts

- MUST use line charts for time-series data (portfolio value, asset price history)
- MUST use bar charts for categorical comparisons (holdings by value, sector allocation)
- MUST use treemaps or horizontal bars for allocation/composition views
- MUST include visible axis labels with units
- MUST include legends when multiple series are present
- SHOULD use area charts (with low opacity fill) for cumulative values
- SHOULD use sparklines for inline trend indication in tables
- SHOULD use consistent colors across related charts
- NEVER use pie charts for more than 5 segments
- NEVER use 3D charts, exploded segments, or decorative chart styles
- NEVER use donut charts when exact values matter more than proportions

---

## Data Display

- MUST show key metrics above the fold: total value, day change (absolute + %), total gain/loss
- MUST align decimal points in numeric columns
- MUST use consistent decimal precision (2 for currency, 2-4 for percentages)
- MUST format large numbers with appropriate separators (1,234,567.89)
- MUST show currency symbols consistently (prefix for USD/EUR, suffix where conventional)
- SHOULD use abbreviations for large numbers in tight spaces (1.2M, 45.3K) with full value on hover
- SHOULD show percentage change with directional indicator (▲ ▼ or +/-)
- SHOULD show timestamps in relative format ("2h ago") with absolute on hover
- SHOULD group holdings by category/sector with collapsible sections
- NEVER hide critical data behind interactions (hover, click) on primary views

---

## Layout

- MUST use `h-dvh` not `h-screen` for full-height layouts
- MUST respect `safe-area-inset` for fixed elements on mobile
- MUST use fixed `z-index` scale: `z-10` (dropdown), `z-20` (modal), `z-30` (toast)
- MUST ensure content is not obscured by fixed headers/footers
- SHOULD use `size-*` for square elements (icons, avatars) instead of `w-* h-*`
- SHOULD use sticky table headers for scrollable data tables
- SHOULD use responsive breakpoints: single column mobile, table view desktop
- SHOULD maintain consistent max-width for content: `max-w-6xl` or `max-w-7xl`
- NEVER use horizontal scroll for primary data tables on desktop

---

## Interaction

- MUST use `cursor-pointer` on all clickable elements
- MUST show errors inline, next to the relevant input or action
- MUST use `AlertDialog` for destructive actions (delete holding, disconnect account)
- MUST provide keyboard navigation for all interactive elements
- SHOULD show hover states on table rows for clickable rows
- SHOULD use `focus-visible` for keyboard focus indicators
- NEVER block paste in input fields
- NEVER use double-click as the only way to trigger an action

---

## Loading States

- MUST use skeleton screens matching the data layout structure
- MUST show stale data with "Updating..." indicator rather than replacing with spinner
- MUST indicate loading state on refresh buttons during fetch
- SHOULD load critical data (total value) before secondary data (individual holdings)
- SHOULD use optimistic updates for user actions where safe
- NEVER block the entire view when partial data is available
- NEVER use spinning logos or branded loading animations

---

## Empty States

- MUST provide one clear primary action: "Add your first holding" / "Connect an account"
- MUST explain what will appear when the view is populated
- SHOULD use a simple illustration or icon (not decorative graphics)
- SHOULD show example data or screenshot if helpful
- NEVER leave empty views completely blank
- NEVER use generic "No data" without guidance

---

## Animation

- MUST NOT add animation unless explicitly requested
- MUST animate only compositor properties: `transform`, `opacity`
- MUST respect `prefers-reduced-motion`
- MUST keep interaction feedback under 150ms
- SHOULD use `ease-out` for entrance animations
- SHOULD pause any looping animations when off-screen
- NEVER animate layout properties: `width`, `height`, `top`, `left`, `margin`, `padding`
- NEVER animate number changes in real-time (distracting for financial data)
- NEVER use bounce, elastic, or playful easing curves
- NEVER apply `will-change` outside active animations

---

## Performance

- MUST virtualize lists with more than 50 items
- MUST debounce search/filter inputs (300ms)
- MUST lazy-load charts below the fold
- SHOULD paginate or "load more" for large datasets
- SHOULD cache API responses for offline viewing
- NEVER animate large `blur()` or `backdrop-filter` surfaces
- NEVER use `useEffect` for logic that can be expressed as render computation
- NEVER fetch all historical data on initial load (use sensible defaults: 1M, 1Y)

---

## Real-Time Data

- SHOULD poll at reasonable intervals (30s-60s for prices, not sub-second)
- SHOULD show "Last updated: X" timestamp
- SHOULD allow manual refresh with button
- SHOULD indicate stale data visually (muted color, icon)
- NEVER auto-refresh while user is actively interacting (editing, modal open)
- NEVER flash or highlight every price change (only significant moves if any)

---

## Mobile Considerations

- MUST ensure touch targets are minimum 44x44px
- MUST use `safe-area-inset-bottom` for fixed bottom navigation
- SHOULD prioritize summary view on mobile, details on tap
- SHOULD use bottom sheets instead of modals for filters/actions
- SHOULD support pull-to-refresh for data updates
- NEVER rely on hover states for essential information on touch devices

---

## Accessibility

- MUST use sufficient color contrast (4.5:1 for text, 3:1 for UI elements)
- MUST not rely on color alone (use icons: ▲/▼, +/-, or text labels)
- MUST provide text alternatives for charts (summary or data table)
- MUST ensure screen readers can navigate tabular data
- SHOULD announce live data updates to screen readers appropriately (polite, not assertive)
- SHOULD test with keyboard-only navigation

---

## Pre-Delivery Checklist

Before delivering portfolio UI code, verify:

### Data Integrity
- [ ] All numbers use `tabular-nums`
- [ ] Decimals are aligned and consistent
- [ ] Currency symbols are consistent
- [ ] Gains are green, losses are red, with icons/text backup

### Visual Quality
- [ ] No gradients on data elements
- [ ] No decorative fonts
- [ ] Skeleton loaders match content layout
- [ ] Empty states have clear actions

### Interaction
- [ ] All clickable elements have `cursor-pointer`
- [ ] Destructive actions use confirmation dialogs
- [ ] Errors appear inline near the action
- [ ] Keyboard navigation works

### Performance
- [ ] Large lists are virtualized
- [ ] Charts lazy-load below fold
- [ ] No layout-triggering animations
- [ ] Reasonable polling interval for live data

### Accessibility
- [ ] 4.5:1 contrast on all text
- [ ] Color is not the only indicator
- [ ] Touch targets are 44px minimum
- [ ] Screen reader can navigate data
