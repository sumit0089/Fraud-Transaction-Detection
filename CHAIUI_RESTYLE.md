# ChaiUI restyle

Implemented locally on 2026-10-29. No changes have been pushed or deployed as part of this restyle.

## What changed

- Installed the official ChaiUI theme and registry components using shadcn, configured for JavaScript and the existing Vite app.
- Added the Tailwind Vite integration and the `@/` source alias required by registry components.
- Allowed `frontend/src/lib/` in `.gitignore`, because the inherited Python `lib/` rule otherwise hid ChaiUI's required `cn()` helper from future commits.
- Reused ChaiUI Button, Card, Input, Select, Table, Highlight, Backdrop, ThemeProvider, ThemeSwitcher, Dialog and ConfirmDialog.
- Restyled the existing dashboard with neutral near-black surfaces, warm hairlines, cream highlights, Manrope/Montserrat/Onest typography and asymmetric primary/outline buttons.
- Kept risk semantics in readable text and thin outlines. Cards and charts use neutral surfaces and bars, without decorative shadows or orange fills.
- Added a persistent dark/light preference. A small same-origin external script restores the theme before React mounts, compatible with the existing production CSP.
- Added a clear-history confirmation with initial focus on "Keep history". No server storage or retention behavior was introduced.
- Preserved all seven app sections, input validation, actual prediction and batch requests, session history filters/details/pagination, real metrics, loading/errors and uncertainty notices.
- Adjusted registry ThemeProvider initialization for this client-rendered Vite app; other registry APIs remain intact.

The application sidebar remains an application sidebar rather than being replaced by a marketing-site navigation block. The registry primitives provide its controls and theme; the existing navigation state and dashboard layout remain in place.

## Important files

| Path | Purpose |
| --- | --- |
| `frontend/components.json` | Official ChaiUI registry and JavaScript output configuration |
| `frontend/jsconfig.json`, `vite.config.js` | Source alias and Tailwind compilation |
| `frontend/src/chaiui.css` | Registry theme tokens, locally bundled fonts and utilities |
| `frontend/src/styles.css` | SafePay dashboard layout, semantic colors, responsive and reduced-motion rules |
| `frontend/src/components/` | Installed ChaiUI components |
| `frontend/src/App.jsx` | Existing functionality wired to the registry components, theme and confirmation |
| `frontend/src/RiskDistribution.jsx` | Theme-aware neutral chart styling |
| `frontend/public/theme-init.js` | CSP-compatible saved-theme initialization |
| `frontend/public/chaiui/background.svg` | Official ChaiUI warm hexagon background |
| `frontend/src/App.test.jsx` | Existing integration cases plus theme and confirmation tests |

## Verification actually performed

- `npm test`: 15 passed, 0 failed. Existing prediction/error/edit-lock tests remain intact. New tests cover dark/light switching, saved-theme restoration and safe history confirmation/cancellation.
- `npm run build`: passed with a separate lazy-loaded chart chunk. Fonts are bundled locally; the restyle adds UI/CSS/font assets and does not claim a page-load improvement.
- `npm audit --json`: no known vulnerabilities reported for the installed dependency graph.
- Real browser submission against the unchanged localhost FastAPI service returned the actual default score 0.1614408350121734, displayed as 16.1%.
- Real two-row synthetic CSV upload returned two assessments and one review alert. Session totals reflect these actual local responses.
- Real confirmation dialog focused "Keep history" first; cancelling retained the records.
- Dark and light inspected visually. Desktop tested at 1440 x 1000, mobile at 375 x 812. Document width equaled scroll width in both cases (1425 and 360 CSS pixels respectively, excluding scrollbars).
- Static ChaiUI review found no em dashes, orange fill utilities, decorative shadows or gradient text in frontend source. Uppercase table data labels are the documented exception. Each paragraph has at most one highlight; only the overview uses the solid asymmetric action.
- Base text/muted/quiet palette contrast against the page background measured at least 5.83:1 in the checked dark/light pairs. This is a palette check, not a complete accessibility certification.
- `git diff -- backend` is empty. API URL configuration, CORS, model artifacts and inference code are unchanged.

Screenshots: `reports/safepay-chaiui-dark.png` and `reports/safepay-chaiui-light.png`. They show actual synthetic-model session results, not real financial transactions.

The first sandboxed test attempt could not remove an existing Vitest cache directory (EPERM). The test suite was then run successfully with approved filesystem access. No cache directory was manually deleted.

## Animation follow-up

Added brief page entrances using the existing Motion dependency, staggered summary-card entrances, result reveals, risk-meter fill and subtle pointer hover/press feedback. Reduced-motion preferences disable the entrances and interaction motion. No API work waits for an animation.

Verification: `npm test` passed all 16 tests, including a regression check that animated navigation preserves typed inputs and does not issue extra health requests. `npm run build` passed. A real localhost browser submission displayed the synthetic-model result (16.1% for the default sample); the browser reported no warnings or errors. Screenshot: `reports/safepay-animations.png`. Backend code is unchanged and backend tests were not rerun for this visual change.

## Local preview and release

Visible-motion update: page translation increased to 20px over 400ms; summary cards
enter over 500ms with 90ms stagger spacing. Panels/headlines reveal, result cards
scale in, and the risk meter fills over 800ms. Chat opens from its bottom-right
origin, new exchanges reveal, and thinking dots move only while a request is pending.
The closed launcher emits three one-second outline pulses, then stops. All motion
continues to respect reduced-motion preferences. Hover feedback remains 200ms.
No new dependencies or backend/API changes were introduced.

Verification: 19 frontend tests and production build passed. Browser computed
styles confirmed the 400ms chat and 500ms panel animations; desktop and 375px
phone layouts were checked, including light theme (phone scroll/client widths
both 360px excluding scrollbar). Screenshot: `reports/safepay-visible-motion.png`.

Use the existing README commands to start the API and run `npm run dev -- --port 5173 --strictPort` from `frontend`. On a fresh checkout, `npm ci` installs the locked registry/Tailwind/font dependencies.

These are local edits. Publishing them requires a separate Git commit/push and the normal Vercel deployment. Render configuration is independent; the previously diagnosed production CORS setting is not changed by this UI work.
