# UI Restyle (Stitch Mockups) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle all 5 frontend pages to match the Stitch mockups' visual language (ambient lime glow, lime card titles, multi-color tag pills, unified pill buttons/surfaces) without changing page structure or logic.

**Architecture:** Token-driven (Approach A). Add tokens + keyframes + 3 shared utility classes to `index.css`, one global glow layer in `Layout`, then targeted `.module.css` tweaks per page. Markup changes limited to: nav CTA, tag-pill color modifier, applying utility classnames.

**Tech Stack:** React 19, Vite, CSS Modules, plain CSS custom properties. No deps added. No test framework in repo — verification is `npm run build` (must stay green) + visual check against `stitch/*/screen.png`.

**Spec:** `docs/superpowers/specs/2026-05-16-ui-restyle-stitch-design.md`

**Working dir for all commands:** `/home/fbonhomme/Projets/youtube-transcript-resume`. Branch `feat/ui-restyle-stitch` (already created). Build baseline confirmed green.

---

### Task 1: Design tokens + keyframes

**Files:**
- Modify: `frontend/src/index.css:5-31` (`:root`), and append keyframes near `:60-72`

- [ ] **Step 1: Add tokens to `:root`**

Insert after the line `--success:      #44f0a0;`:

```css
  --glow:        rgba(201,255,71,.10);
  --glow-strong: rgba(201,255,71,.20);
  --elev:        0 10px 30px rgba(0,0,0,.45);
  --elev-hover:  0 16px 48px rgba(0,0,0,.55);
  --tag-1: #c9ff47;
  --tag-2: #ffb84d;
  --tag-3: #b07cff;
  --tag-4: #4dd6ff;
```

- [ ] **Step 2: Add glow-drift keyframes**

Append to `index.css` after the `@keyframes shimmer { ... }` block:

```css
@keyframes glowDrift {
  0%   { transform: translate(-2%, -2%) scale(1);    opacity: .9; }
  50%  { transform: translate(2%, 1%)  scale(1.06);  opacity: 1; }
  100% { transform: translate(-2%, -2%) scale(1);    opacity: .9; }
}
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds (exit 0), no CSS errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat(ui): add glow/elevation/tag design tokens"
```

---

### Task 2: Shared utility classes

**Files:**
- Modify: `frontend/src/index.css` (append global utilities at end of file)

- [ ] **Step 1: Append utilities**

Add at the end of `index.css`:

```css
.u-glow-surface {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--elev);
}

.u-lime-title {
  font-family: var(--font-display);
  color: var(--accent);
  text-shadow: 0 0 18px var(--glow-strong);
  letter-spacing: -0.01em;
}

.u-pill-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--accent);
  color: #000;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.9rem;
  border: none;
  border-radius: 999px;
  padding: 10px 22px;
  transition: filter .15s, transform .15s, box-shadow .15s;
  box-shadow: 0 0 0 rgba(201,255,71,0);
}
.u-pill-btn:hover { filter: brightness(1.06); box-shadow: 0 6px 24px var(--glow-strong); }
.u-pill-btn:active { transform: translateY(1px); }
.u-pill-btn:disabled { opacity: .55; cursor: not-allowed; box-shadow: none; }
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat(ui): add shared glow-surface/lime-title/pill-btn utilities"
```

---

### Task 3: Global ambient glow layer + nav CTA

**Files:**
- Modify: `frontend/src/components/Layout.tsx`
- Modify: `frontend/src/components/Layout.module.css`

- [ ] **Step 1: Add glow element + CTA in `Layout.tsx`**

In `Layout.tsx`, change the returned tree. Replace the `<div className={styles.root}>` opening so a glow div is the first child, and replace the `navRight` block to add a CTA before `<CostBadge />`:

```tsx
  return (
    <div className={styles.root}>
      <div className={styles.glow} aria-hidden="true" />
      <nav className={styles.nav}>
        <div className={styles.brand}>
          <span className={styles.brandIcon}>▶</span>
          <span>YT Synthèses</span>
        </div>

        <div className={styles.links}>
          <NavLink to="/library" className={({ isActive }) => isActive ? styles.active : ""}>
            Bibliothèque
          </NavLink>
          <NavLink to="/new" className={({ isActive }) => isActive ? styles.active : ""}>
            + Nouvelle
          </NavLink>
          <NavLink to="/themes" className={({ isActive }) => isActive ? styles.active : ""}>
            Thèmes
          </NavLink>
          <NavLink to="/prompts" className={({ isActive }) => isActive ? styles.active : ""}>
            Prompts
          </NavLink>
        </div>

        <div className={styles.navRight}>
          <CostBadge />
          <NavLink to="/new" className={styles.cta}>+ Nouvelle synthèse</NavLink>
        </div>
      </nav>

      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
```

- [ ] **Step 2: Add `.glow` and `.cta` styles, raise nav/main z-index**

In `Layout.module.css`, add `position: relative; z-index: 1;` to `.nav` (after its `border-bottom` line) and to `.main` (after `flex: 1;`). Then append:

```css
.glow {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(60% 45% at 50% 0%, var(--glow-strong) 0%, transparent 60%),
    radial-gradient(45% 40% at 90% 100%, var(--glow) 0%, transparent 65%);
}
@media (prefers-reduced-motion: no-preference) {
  .glow { animation: glowDrift 18s ease-in-out infinite; }
}

.cta {
  display: inline-flex;
  align-items: center;
  background: var(--accent);
  color: #000;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.82rem;
  border-radius: 999px;
  padding: 7px 16px;
  white-space: nowrap;
  transition: filter .15s, box-shadow .15s;
}
.cta:hover { filter: brightness(1.06); box-shadow: 0 4px 18px var(--glow-strong); }
```

Also change `.navRight` to add `gap: 10px;`.

- [ ] **Step 3: Hide CTA label on small screens**

In the `@media (max-width: 720px)` block of `Layout.module.css`, the existing rule `.navRight { display: none; }` already hides the right slot on mobile — leave it. No change needed (cost badge + CTA hidden together as today).

- [ ] **Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Layout.tsx frontend/src/components/Layout.module.css
git commit -m "feat(ui): app-wide ambient glow layer + nav CTA pill"
```

---

### Task 4: SummaryCard — lime title + multi-color tag pills

**Files:**
- Modify: `frontend/src/components/SummaryCard.tsx:43-48`
- Modify: `frontend/src/components/SummaryCard.module.css`

- [ ] **Step 1: Tag color modifier in `SummaryCard.tsx`**

Replace the tags map (lines ~45-47) with index-derived color class:

```tsx
          {summary.tags.slice(0, 2).map((t, ti) => (
            <span key={t} className={`${styles.tag} ${styles[`tag${ti % 4}`]}`}>{t}</span>
          ))}
```

- [ ] **Step 2: Restyle title, card, tags in `SummaryCard.module.css`**

Replace the `.title` rule's `color: var(--text);` with:

```css
  color: var(--accent);
  text-shadow: 0 0 14px var(--glow);
```

Replace the `.card:hover` rule body with:

```css
  border-color: var(--accent);
  transform: translateY(-3px);
  box-shadow: var(--elev-hover), 0 0 0 1px var(--glow-strong);
```

Replace the `.tag` rule with a pill base + 4 color modifiers:

```css
.tag {
  font-size: 0.66rem;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 999px;
  border: 1px solid transparent;
  letter-spacing: 0.02em;
}
.tag0 { background: rgba(201,255,71,.14); color: var(--tag-1); border-color: rgba(201,255,71,.3); }
.tag1 { background: rgba(255,184,77,.14); color: var(--tag-2); border-color: rgba(255,184,77,.3); }
.tag2 { background: rgba(176,124,255,.14); color: var(--tag-3); border-color: rgba(176,124,255,.3); }
.tag3 { background: rgba(77,214,255,.14); color: var(--tag-4); border-color: rgba(77,214,255,.3); }
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds. (Note: `styles[\`tag${i}\`]` is dynamic — TS/Vite CSS modules allow string index; build must stay green.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/SummaryCard.tsx frontend/src/components/SummaryCard.module.css
git commit -m "feat(ui): lime card titles + multi-color tag pills"
```

---

### Task 5: Library page + ThemeSidebar filter list

**Files:**
- Modify: `frontend/src/pages/LibraryPage.tsx:29-32` (title classname)
- Modify: `frontend/src/pages/LibraryPage.module.css` (.title)
- Modify: `frontend/src/components/ThemeSidebar.module.css` (.item.active)

- [ ] **Step 1: Apply lime-title utility to Library heading**

In `LibraryPage.tsx`, change `<h1 className={styles.title}>` to `<h1 className={`${styles.title} u-lime-title`}>`. (The `u-lime-title` global class adds the lime treatment; keep `styles.title` for layout.)

- [ ] **Step 2: Desktop active filter = lime fill in `ThemeSidebar.module.css`**

Replace the desktop `.item.active` rule (lines ~44-47) with:

```css
.item.active {
  background: var(--accent);
  color: #000;
  font-weight: 600;
}
.item.active .count { color: rgba(0,0,0,.6); }
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/LibraryPage.tsx frontend/src/pages/LibraryPage.module.css frontend/src/components/ThemeSidebar.module.css
git commit -m "feat(ui): library lime title + lime-fill sidebar filter"
```

---

### Task 6: Gestion des Thèmes restyle

**Files:**
- Modify: `frontend/src/pages/ThemeManagerPage.tsx` (title + card + button classnames)
- Modify: `frontend/src/pages/ThemeManagerPage.module.css`

- [ ] **Step 1: Apply utilities in `ThemeManagerPage.tsx`**

- Change `<h1 className={styles.title}>` → `<h1 className={`${styles.title} u-lime-title`}>`
- Change both `<section className={styles.card}>` → `<section className={`${styles.card} u-glow-surface`}>`
- Change `<button type="submit" className={styles.btnPrimary}>` → `<button type="submit" className={`${styles.btnPrimary} u-pill-btn`}>`

- [ ] **Step 2: Center title + localized glow in `ThemeManagerPage.module.css`**

Add to the `.title` rule: `text-align: center;`. Add to the `.wrap` rule (create if absent — it exists per page): `position: relative;`. Append:

```css
.wrap::before {
  content: "";
  position: absolute;
  top: -40px; left: 50%;
  width: 520px; height: 320px;
  transform: translateX(-50%);
  background: radial-gradient(circle, var(--glow-strong) 0%, transparent 70%);
  pointer-events: none;
  z-index: -1;
}
.empty { text-align: center; }
.selectedColor { outline: 2px solid var(--accent); outline-offset: 2px; }
```

(If `.selectedColor` already exists, merge the outline declaration instead of duplicating.)

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ThemeManagerPage.tsx frontend/src/pages/ThemeManagerPage.module.css
git commit -m "feat(ui): restyle Gestion des Thèmes (glow hero, pill button)"
```

---

### Task 7: Prompts page restyle

**Files:**
- Modify: `frontend/src/pages/PromptsPage.tsx` (title, card, primary button classnames)
- Modify: `frontend/src/pages/PromptsPage.module.css`

- [ ] **Step 1: Apply utilities in `PromptsPage.tsx`**

- `<h1 className={styles.title}>` → `<h1 className={`${styles.title} u-lime-title`}>`
- Each `<section className={styles.card}>` → `<section className={`${styles.card} u-glow-surface`}>`
- Each top-level `className={styles.btnPrimary}` button → add `u-pill-btn`: `className={`${styles.btnPrimary} u-pill-btn`}` (the `+ Nouveau prompt` button and the form submit button).

- [ ] **Step 2: Variable-chip flavor for inline code in `PromptsPage.module.css`**

Append:

```css
.notice code {
  background: var(--accent-dim);
  color: var(--accent);
  border: 1px solid var(--glow-strong);
  border-radius: 5px;
  padding: 1px 6px;
  font-family: var(--font-mono);
  font-size: 0.78em;
}
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/PromptsPage.tsx frontend/src/pages/PromptsPage.module.css
git commit -m "feat(ui): restyle Prompts page (surfaces, pill buttons, code chips)"
```

---

### Task 8: Nouvelle synthèse + Summary Detail style extension

**Files:**
- Modify: `frontend/src/pages/NewSummaryPage.tsx` (title + submit button classnames)
- Modify: `frontend/src/pages/NewSummaryPage.module.css`
- Modify: `frontend/src/pages/SummaryDetailPage.tsx` (title classname)
- Modify: `frontend/src/pages/SummaryDetailPage.module.css`

- [ ] **Step 1: NewSummary utilities**

In `NewSummaryPage.tsx`:
- `<h1 className={styles.title}>` → `<h1 className={`${styles.title} u-lime-title`}>`
- `<button type="submit" className={styles.submit} ...>` → add `u-pill-btn`: `className={`${styles.submit} u-pill-btn`}`
- Change `<div className={styles.optionsCard}>` → `<div className={`${styles.optionsCard} u-glow-surface`}>`

- [ ] **Step 2: SummaryDetail utilities + section accent**

In `SummaryDetailPage.tsx`: change `<h1 className={styles.title}>` → `<h1 className={`${styles.title} u-lime-title`}>`.

In `SummaryDetailPage.module.css`, append a lime accent rule for section headings and pill restyle:

```css
.section h2 {
  border-left: 3px solid var(--accent);
  padding-left: 12px;
}
.pill, .tag {
  border-radius: 999px;
}
```

(If `.section h2` already has a rule, merge the two declarations into it rather than duplicating the selector.)

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/NewSummaryPage.tsx frontend/src/pages/NewSummaryPage.module.css frontend/src/pages/SummaryDetailPage.tsx frontend/src/pages/SummaryDetailPage.module.css
git commit -m "feat(ui): extend restyle to Nouvelle synthèse + Summary Detail"
```

---

### Task 9: Final visual verification

**Files:** none (verification only)

- [ ] **Step 1: Build green**

Run: `cd frontend && npm run build`
Expected: exit 0.

- [ ] **Step 2: Start dev server**

Run: `cd frontend && npm run dev` (background). Backend optional — UI shell + empty/loading states are verifiable without data; if backend is running via `./start.sh`, populated states are verifiable too.

- [ ] **Step 3: Visual checklist against `stitch/*/screen.png`**

Open http://localhost:5173 and confirm:
- Ambient lime glow visible behind content on every route (Library, /new, /themes, /prompts, detail).
- Library: lime card titles, multi-color tag pills, lime-fill active theme filter, nav CTA pill present.
- Gestion des Thèmes: centered title, radial glow behind heading, elevated form/list cards, lime pill "Créer", selected color dot ringed, centered empty state.
- Prompts: elevated cards, lime pill primary buttons, inline `code` rendered as lime chips.
- Nouvelle synthèse + Detail: elevated option card / lime title, pill submit, section headings with lime left rule, pill-shaped tags.
- Toggle OS reduced-motion → glow stops drifting but remains visible.
- Resize to 480px → no layout breakage; nav right slot hidden as before.

- [ ] **Step 4: Stop dev server, final commit if any tweaks**

If verification surfaced fixes, apply minimally and:

```bash
git add -A
git commit -m "fix(ui): visual verification adjustments"
```

---

## Self-Review

**Spec coverage:** §1 tokens→T1; §2 glow+nav→T3; §3 SummaryCard→T4; §4 Library/sidebar→T5; §5 Thèmes→T6; §6 Prompts→T7; §7 New+Detail→T8; §8 utilities→T2; testing strategy→T9. All spec sections mapped.

**Placeholder scan:** No TBD/TODO; every code step has concrete CSS/TSX. Merge-if-exists notes are explicit instructions, not placeholders.

**Type consistency:** Utility class names (`u-glow-surface`, `u-lime-title`, `u-pill-btn`) defined in T2, used verbatim in T3/T5/T6/T7/T8. Token names (`--glow`, `--glow-strong`, `--elev`, `--elev-hover`, `--tag-1..4`) defined in T1, used consistently after. Tag modifier classes `.tag0..3` defined and consumed in T4.
