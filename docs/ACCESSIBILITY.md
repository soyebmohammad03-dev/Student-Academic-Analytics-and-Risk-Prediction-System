# Accessibility and browser support

What was checked in Phase 9, how, and what was **not** checked.

## Automated checks

**Unit tests (every run of `./scripts/check.sh` and CI).** `axe-core` runs on each page
view rendered with fixture data — Dashboard, Data Explorer, Statistics, EDA, Model
Comparison, Prediction (with results), Interpretability, Risk Analysis and Methodology —
with every collapsed `<details>` opened first. Colour contrast is excluded there because
jsdom has no layout (`frontend/src/test/axe.ts`).

**Real browser (production build, real API data).** `axe-core` 4.x, all rules including
colour contrast, on all nine routes in five configurations: 1280 px light, 1280 px dark,
768 px light, 375 px light and 320 px dark, with every "Show data" table expanded. The
same run measured whether the page itself scrolls horizontally.

Issues found and fixed in Phase 9:

| Issue | Fix |
| --- | --- |
| Tertiary and secondary text, status badges and the light accent below 4.5:1 | Darker light-theme tokens; brighter dark-theme accent; a dedicated button fill colour |
| Labels on tinted confusion-matrix and two-way-table cells below 4.5:1 | Primary text colour in tinted cells; lighter tints |
| `<dl>` lists containing `<p>`/`<span>` (metric cards, cohort cards, prediction card) | Hints moved into `<dd>`; duplicate metric-card components replaced by one |
| Scrollable tables not reachable by keyboard | Focusable, labelled `region` containers |
| Heatmap data table with an empty header cell | Header labelled "Variable" |
| Page widened by visually hidden tooltip text inside scrolling tables | Tooltip wrapper made the positioning context |
| Page widened at 320 px by grid items holding wide tables | `min-w-0` on chart frames and table cards |

Final result: **0 axe violations and no page-level horizontal overflow** on all nine
routes in all five configurations.

## Manual review

- **Keyboard.** "Skip to content" link first in the tab order; segmented controls follow
  the ARIA radio-group pattern (one tab stop, arrow keys); tooltips open on focus and close
  with Escape; the mobile navigation sheet is a modal dialog that closes with Escape and
  makes the page inert while open; the prediction form moves focus to the first invalid
  field and announces the error count in a polite live region.
- **Semantics.** One `<h1>` per page, section headings, labelled form controls with
  `aria-invalid` and `aria-describedby` errors, `aria-current` on the active navigation
  link, captions on data tables.
- **Charts.** Every chart has a title, a text description or accessible name, a legend
  where colour encodes meaning, and a "Show data" table, so no value depends on colour or
  shape alone.
- **Motion and theme.** `prefers-reduced-motion` disables transitions; light, dark and
  system themes; the explicit choice is applied before first paint.

Not performed: testing with a screen reader (VoiceOver, NVDA) and a formal WCAG audit by
an accessibility specialist.

## Browsers

| Browser / engine | Version | How | Result |
| --- | --- | --- | --- |
| Chromium (Claude desktop browser pane) | 152 | Manual review, axe-core runs above, mobile navigation, prediction flow | Pass |
| Google Chrome (headless) | installed | Screenshot capture of six pages and a phone-width view with real data | Pass |
| WebKit (Safari's engine, Playwright build) | 27.2 | All nine routes at 1280 px light and 390 px dark: content present, no console errors, no failed requests, no page overflow; prediction flow, theme switch and mobile navigation | Pass |
| Firefox (Playwright build) | 157 | Could not be launched on the test machine ("Could not find profile folder") | **Not tested** |
| Safari (desktop app) | — | Not automated (requires enabling remote automation); WebKit above covers the engine | Not tested directly |
| Edge, mobile Safari, Chrome for Android | — | Not available | **Not tested** |
