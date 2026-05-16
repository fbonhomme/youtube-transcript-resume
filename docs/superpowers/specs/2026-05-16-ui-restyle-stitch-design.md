# UI Restyle — Stitch Mockups

**Date:** 2026-05-16
**Status:** Approved design, pending implementation plan

## Goal

Restyle the frontend to match the visual language of the three Stitch mockups in
`stitch/` (Library dashboard, Gestion des Thèmes, Prompts config) and extend that
same language across all five pages of the app for consistency.

This is a **visual restyle only**. Existing page structures, component logic,
data models, routing, and API calls are unchanged. No structural/master-detail
rewrites (e.g. the mockup's two-pane Prompts layout is intentionally NOT adopted).

## Decisions (from brainstorming)

- **Scope:** All pages — the 3 mockup screens plus Nouvelle synthèse and Summary
  Detail get the same visual language.
- **Fidelity:** Visual restyle only; current page structures preserved.
- **Ambiance:** App-wide ambient green radial glow, lime card titles, multi-color
  tag pills.
- **Approach A:** Token-driven refresh — update `index.css` tokens, one global
  glow layer in `Layout`, a small set of shared utility classes, then targeted
  per-page `.module.css` tweaks.

## Existing visual baseline

The app already uses a dark theme with lime accent (`--accent #c9ff47`), Syne
display font, DM Sans body, JetBrains Mono. The restyle refines this baseline —
it does not introduce a new palette. The deltas vs. the mockups are: ambient
glow, lime card titles, multi-color tag pills, a prominent nav CTA pill, and
unified card/field/button surfaces.

## Design

### 1. Design tokens — `frontend/src/index.css`

Add to `:root` (keep existing tokens):

- `--glow`: soft low-alpha lime radial color stop.
- `--glow-strong`: higher-alpha variant for localized page glows.
- `--elev`: standard card box-shadow.
- `--tag-1`, `--tag-2`, `--tag-3`, `--tag-4`: lime, amber, violet, cyan — used
  to cycle tag-pill colors by index.

Add `@keyframes glowDrift` (slow, subtle position/opacity drift). Wrap its usage
in `@media (prefers-reduced-motion: no-preference)` so reduced-motion users get a
static glow.

### 2. Global ambient glow + nav — `Layout.tsx` / `Layout.module.css`

- Add one decorative element inside `.root`, behind `<main>`:
  `position: fixed; inset: 0; pointer-events: none; z-index: 0`. It paints a
  large soft lime radial gradient anchored top-center plus a fainter one
  bottom-right. `<main>` and `<nav>` sit at `z-index: 1`.
- Nav right slot: add a prominent lime **pill CTA** "+ Nouvelle synthèse"
  (`NavLink` to `/new`). The existing `CostBadge` is kept, rendered as a smaller
  mono chip beside the CTA (not removed).
- Mobile: CTA collapses to "+" only; cost badge stays hidden at <=720px as today.

### 3. SummaryCard — `SummaryCard.module.css` (+ minimal `.tsx` className)

- `.title`: color `--accent`, Syne, faint lime text-glow.
- `.tag`: filled rounded pill. Color cycles `--tag-1..4` via
  `style={{...}}` or an index-derived modifier class on each tag (index already
  passed to the card). Footer date kept.
- `.card`: border + `--elev`; hover raises elevation and adds a lime border glow.
  Thumbnail overlay gradient slightly stronger for title contrast.

### 4. Library page — `LibraryPage.module.css`

- `.title` gets faint lime text-glow (uses shared utility).
- `ThemeSidebar` (`ThemeSidebar.module.css`): items restyled as the mockup
  filter list — selected item = lime fill + dark text; theme color shown as a
  dot. Structure unchanged.

### 5. Gestion des Thèmes — `ThemeManagerPage.module.css`

- `.wrap`: localized `--glow-strong` radial behind the heading; `.title`
  centered.
- `.card`: shared elevated/bordered surface (`.u-glow-surface`).
- Color dots enlarged; selected dot shows a check mark / ring.
- Primary buttons → lime pill; empty state centered.

### 6. Prompts page — `PromptsPage.module.css`

- Shared surface/card restyle; primary buttons → lime pill; ghost/danger buttons
  restyled to match. Structure unchanged.
- Inline `<code>` chips in the JSON-schema notice rendered as small lime chips
  (the mockup's variable-chip flavor) — CSS only, no logic change.

### 7. Nouvelle synthèse & Summary Detail — style extension

- Inputs/selects/textarea: unified dark field with lime focus ring, normalized
  via tokens (`NewSummaryPage.module.css`, `SummaryDetailPage.module.css`).
- Buttons unified to the pill (primary) / ghost / danger system.
- Detail page: hero unchanged structurally; section `h2` gets a lime accent
  rule; `.pill`/`.tag` adopt the new pill style; transcript `<pre>` restyled.
  The app-wide ambient glow shows through.

### 8. Shared utilities — `index.css`

Three small global classes, applied via `className` alongside existing module
classes (the only markup change besides the nav CTA and tag color cycling):

- `.u-glow-surface` — bordered, elevated card surface.
- `.u-lime-title` — lime color + Syne + faint text-glow.
- `.u-tagpill` — base pill chip (color set by `--tag-*` modifier).

These prevent visual drift between pages and keep tuning centralized.

## Out of scope

- No structural/layout rewrites (no two-pane Prompts, no horizontal Theme form).
- No new features, routes, components, data model or API changes.
- No prompt-template-variable feature (the mockup's `{video_title}` chips are
  decorative inspiration only).
- No dependency changes.

## Testing strategy

- Run the dev server (`./start.sh` or `npm run dev`).
- Visually verify all 5 pages against the mockups: Library (grid + empty +
  loading), Gestion des Thèmes (form + empty + populated list + edit), Prompts
  (new + list + edit), Nouvelle synthèse (idle + pending), Summary Detail
  (full + transcript toggle).
- Verify `prefers-reduced-motion` disables glow drift (static glow remains).
- Check no layout regressions at 720px and 480px breakpoints.
- Confirm focus-visible rings still meet contrast over the new surfaces.

## Risks

- Ambient glow could reduce text contrast — keep glow alpha low and verify
  against body text and focus rings.
- Shared utility classes intentionally break strict CSS-module isolation;
  acceptable trade-off for cross-page consistency, documented here.
