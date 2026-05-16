# Restyle Stitch + features UI visibles — Design

Date : 2026-05-16
Branche : `feat/ui-restyle-stitch`
Statut : approuvé (design)

## Contexte

L'application YT Synthèse (React 19 + Vite front, FastAPI back) doit être
revue pour s'aligner sur les maquettes Stitch (`stitch/*.png`) et le PRD
« YT Synthèse — Plateforme de Résumés IA ».

Le design system existe déjà dans `frontend/src/index.css` : tokens deep-dark,
accent lime `#c9ff47`, utilitaires `u-glow-surface`, `u-lime-title`,
`u-pill-btn`. La branche a déjà restylé partiellement les 5 écrans
(commits `b3e43e0` → `c05dbde`).

## Périmètre

Décision de cadrage (validée) : **restyle de cohérence globale + les
features UI réellement visibles dans les maquettes**.

Dans le périmètre :

1. Passe de cohérence visuelle sur les 5 écrans existants.
2. Bandeau Quick Stats sur la Bibliothèque.
3. Vue de lecture en split-screen (vidéo embed | document).
4. Feedback like/dislike sur une synthèse.
5. Filtre Thèmes en pills.

Hors périmètre (PRD futur, specs séparées) : crédits/quotas, export
PDF/Markdown/Notion, mail hebdomadaire, fallback Whisper, chunking des
vidéos 3h+, chiffrement RGPD, synchronisation vidéo↔timestamps.

## Décisions de conception

- **Vue de lecture** : split-screen **sans** synchronisation vidéo. Le
  sommaire scrolle vers la section, il ne déplace pas la vidéo. Aucune
  modification du summarizer ni du schéma `sections`.
- **Quick Stats** : 3 KPI calculés sur les données existantes — nombre de
  synthèses, somme des `duration_read` (proxy « temps de lecture
  économisé »), nombre de tags distincts. Aucun champ « durée vidéo »
  ajouté.
- **Feedback** : persisté en base (colonne + endpoint), pas seulement en
  état local.
- **Stratégie d'exécution** : passe pilotée par composants partagés puis
  écran par écran, en capitalisant sur le restyle déjà commité (pas de
  reconstruction du shell).

## Design system — additions partagées

Ajouts dans `frontend/src/index.css`, dans la lignée des utilitaires
existants, sans nouvelle couleur hors palette PRD :

- `.u-stat-card` : carte glass (`--bg2`, bordure `--border`,
  `--radius-lg`), icône lime, grand chiffre en `--font-display`, label en
  `--text2`. Utilisée par les Quick Stats.
- `.u-pill-filter` : chip de filtre. État inactif = fond `--bg3`, texte
  `--text2`. État actif (`.is-active`) = fond `--accent`, texte `#000`.
  Utilisée par le filtre Thèmes.
- `.u-split` : coque desktop deux colonnes en CSS Grid
  (`grid-template-columns: 1fr 1.2fr`, `gap: 28px`). Sous 1024px : une
  seule colonne. La colonne gauche héberge un enfant `position: sticky`.

Les modules CSS par écran continuent d'utiliser ces utilitaires + les
tokens ; aucun hex en dur hors `--tag-*` déjà définis.

## Backend

### `GET /stats/`

`backend/routers/stats.py` renvoie aujourd'hui `total_summaries`,
`total_cost_usd`, `total_input_tokens`, `total_output_tokens`. Ajout de :

- `total_read_minutes: int` — `SELECT COALESCE(SUM(duration_read), 0)`.
- `total_tags: int` — nombre de tags distincts agrégés depuis la colonne
  JSON `Summary.tags` (agrégation en Python sur les lignes, pas de SQL
  spécifique JSON pour rester portable SQLite).

Le champ TS `Stats` (`frontend/src/api/stats.ts`) gagne les deux champs.

### Feedback synthèse

- `models.py` : `Summary.feedback = Column(Integer, nullable=True)`.
  Valeurs : `1` (like), `-1` (dislike), `NULL` (neutre).
- Migration Alembic autogénérée (`add summary feedback column`) +
  `alembic upgrade head`.
- `PATCH /summaries/{id}` : le schéma de mise à jour accepte un champ
  optionnel `feedback: int | None` (validé ∈ {-1, 1, null}). Renvoyer
  `feedback` actuel pour `null` ⇒ remet à neutre.
- `feedback` exposé dans le schéma `SummaryOut` (back) et les interfaces
  `SummaryOut` / `updateSummary` (front `summaries.ts`).

## Écran : Bibliothèque (`LibraryPage`)

- Nouveau composant `QuickStats` (+ `QuickStats.module.css`) : 3
  `u-stat-card` consommant `getStats` via TanStack Query (réutilise la
  `queryKey: ["stats"]` existante) — Synthèses, Temps de lecture
  économisé (formaté `Xh Ymin` à partir de `total_read_minutes`), Tags.
  Rendu au-dessus du `header` actuel.
- `ThemeSidebar` : chips en `u-pill-filter`, item « Tous » (id `null`) +
  un chip par thème affichant emoji + nom, pastille à la couleur du
  thème ; `.is-active` sur le thème sélectionné. Comportement
  `onSelect`/`selectedId` inchangé.
- Grille de cartes : structure inchangée, polissage glass uniquement.
- `SearchBar` : finaliser et conserver les modifications non commitées
  déjà présentes dans le working tree.

## Écran : Vue de lecture (`SummaryDetailPage`)

Refonte en split-screen via `.u-split`.

- **Colonne gauche** (sticky desktop) : lecteur YouTube **embed**
  (`<iframe src="https://www.youtube.com/embed/{youtube_id}">`,
  ratio 16:9, `loading="lazy"`). Sous le lecteur : titre, thème, métas
  (durée de lecture, langue, date), lien « Voir sur YouTube ↗ ».
- **Colonne droite** (scroll) :
  - **Key Takeaways** : encadré lime (`--accent-dim` + bordure
    `--accent`) listant `key_points`. Masqué si vide.
  - **Sommaire** : liste cliquable des `sections` ; clic = scroll
    (`scrollIntoView`, `behavior: smooth`) vers l'ancre de la section
    (id `section-{i}`). Masqué si pas de sections.
  - **Résumé détaillé** : `summary_long`.
  - **Sections** : chaque section avec son ancre `id="section-{i}"`.
- **Barre d'actions** : boutons 👍 / 👎 (mutation `updateSummary({
  feedback })`, toggle : recliquer le même état renvoie `null`/neutre ;
  état actif = like en `--accent`, dislike en `--danger`), select Thème
  (existant), Transcript repliable (existant), Supprimer (existant).
- Sous 1024px : empilement vertical, vidéo non-sticky, ordre vidéo →
  document.

## Passe de cohérence — écrans restants

`NewSummaryPage`, `ThemeManagerPage`, `PromptsPage` : revue d'alignement
uniquement.

- Surfaces en `u-glow-surface`, titres en `u-lime-title`, boutons
  primaires en `u-pill-btn`.
- Espacements et échelle typo harmonisés avec Bibliothèque / Lecture.
- Aucun changement fonctionnel, aucun nouveau backend (pas de « Test
  Preview » dans les Prompts pour ce chantier).

## Tests & vérification

- **Backend** : test de `GET /stats/` (présence et type des nouveaux
  champs, valeurs cohérentes sur un jeu seedé) ; test de
  `PATCH /summaries/{id}` avec `feedback` ∈ {1, -1, null} et rejet d'une
  valeur invalide.
- **Front** : `npm run build` doit passer (types inclus) ; revue visuelle
  des 5 écrans en desktop et du repli < 1024px sur Bibliothèque et
  Lecture.

## Risques / points d'attention

- Agrégation des tags distincts en Python : acceptable au volume actuel
  (SQLite mono-utilisateur) ; à revoir si la base grossit fortement.
- L'embed YouTube peut être bloqué pour certaines vidéos (intégration
  désactivée par l'auteur) : prévoir un fallback visuel (miniature +
  lien) si l'iframe échoue.
- Migration Alembic : vérifier que l'autogenerate ne capture que la
  colonne `feedback` et rien d'autre avant `upgrade head`.
