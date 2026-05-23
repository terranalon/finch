# Settings Page Redesign (Issue #128)

**Date:** 2026-04-07
**Branch:** `feat/settings-page`
**Mock:** `mocks/settings-playground.html`

## Goal

Redesign the Settings page from a vertical stacked-sections layout to a **tabbed interface** matching the approved mock. Three tabs: Profile, Security, Notifications.

## Current State

`frontend/src/pages/Settings.jsx` uses vertical `SettingsSection` cards (Profile, Security, Appearance, Preferences, Notifications). All functionality is already wired: MFA (TOTP/email OTP), theme selection, currency preference, password change, combined-view toggle.

## Design Changes

### Layout
- Centered wrapper: `max-w-[780px] mx-auto`
- Page title + subtitle at top (using `PageHeader` or inline)
- Segmented tab bar with 3 tabs (Profile, Security, Notifications)

### Tab 1: Profile
Single card containing:
1. **Personal info** - Username (editable) + Email (disabled, hint: "Contact support to change")
2. **Save Changes** button
3. Divider + **Appearance** subsection - Theme selector (Light/Dark/System)
4. Divider + **Preferences** subsection - Currency dropdown + "Show All Portfolios" toggle

### Tab 2: Security
Single card containing:
1. Description text
2. Password row (label + "Change Password" button)
3. MFA section title + Authenticator App card + Email OTP card (with toggles)
4. Default method dropdown (when both MFA methods enabled)
5. Recovery codes button

### Tab 3: Notifications
Single card with toggle rows for each notification type.

## Token Mapping (Mock -> App)

| Mock Token | App Token |
|-----------|-----------|
| `--bg-base` | `--bg-primary` |
| `--bg-card` | `--bg-secondary` |
| `--bg-elevated` | `--bg-tertiary` |
| `--border` | `--border-primary` |
| `--border-subtle` | `--border-subtle` |
| `--text-primary` | `--text-primary` |
| `--text-secondary` | `--text-secondary` |
| `--text-muted` | `--text-tertiary` |
| `--text-faint` | `--text-faint` |
| `--accent` | `--accent-primary` / Tailwind `accent` |
| `--accent-muted` | `accent/10` or `accent/15` |

## Reused Components
- `PageContainer` from `components/layout`
- `Skeleton` from `components/ui`
- `ChangePassword`, `TotpSetup`, `EmailOtpSetup`, `DisableMfaMethod`, `RegenerateRecoveryCodes` from `components/MfaSetup`

## Files Modified
- `frontend/src/pages/Settings.jsx` - Full rewrite

## Tasks
1. Rewrite Settings.jsx with tabbed layout
2. Test in browser on port 5177
3. Run /simplify-branch
4. Create PR targeting main (Closes #128)
