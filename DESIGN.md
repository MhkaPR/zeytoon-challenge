# Design System: Vercel (Olive Primary Accent, RTL Persian)

## 1. Visual Theme & Atmosphere

Vercel's website is the visual thesis of developer infrastructure made invisible — a design system so restrained it borders on philosophical. The page is overwhelmingly white (`#ffffff`) with black (`#000000`) text, creating a gallery-like emptiness where every element earns its pixel. This isn't minimalism as decoration; it's minimalism as engineering principle. The Geist design system treats the interface like a compiler treats code — every unnecessary token is stripped away until only structure remains.

**This project's variant is Persian and fully RTL, and its accent is Olive Green (`#60782e`).** All text is black; the olive scale carries the primary accent (primary CTA, links, focus rings, badges, workflow markers) and is never used for body or heading copy. Because one hue everywhere would flatten the system, a small set of **harmonious supporting colors** (§2.2) is bound to specific functional roles — warning, error, success, info, highlight — never to decorative chrome.

The custom Geist font family is the crown jewel. Geist Sans uses aggressive negative letter-spacing (-2.4px to -2.88px at display sizes), creating headlines that feel compressed, urgent, and engineered — like code that's been minified for production. At body sizes, the tracking relaxes but the geometric precision persists. Geist Mono completes the system as the monospace companion for code, terminal output, and technical labels. Both fonts enable OpenType `"liga"` (ligatures) globally, adding a layer of typographic sophistication that rewards close reading.

What distinguishes Vercel from other monochrome design systems is its shadow-as-border philosophy. Instead of traditional CSS borders, Vercel uses `box-shadow: 0px 0px 0px 1px rgba(96,120,46,0.10)` — a zero-offset, zero-blur, 1px-spread shadow that creates a border-like line without the box model implications. This technique allows borders to exist in the shadow layer, enabling smoother transitions, rounded corners without clipping, and a subtler visual weight than traditional borders. The entire depth system is built on layered, multi-value shadow stacks where each layer serves a specific purpose: one for the border, one for soft elevation, one for ambient depth, and an inner olive-tinted ring for the signature "glow from within."

**Key Characteristics:**
- Geist Sans with extreme negative letter-spacing (-2.4px to -2.88px at display) — text as compressed infrastructure
- Geist Mono for code and technical labels with OpenType `"liga"` globally
- Shadow-as-border technique: `box-shadow 0px 0px 0px 1px` replaces traditional borders throughout
- Multi-layer shadow stacks for nuanced depth (border + elevation + ambient + inner glow in single declarations)
- Pure white canvas with `#000000` text — black, maximally readable
- Olive primary accent `#60782e` marks every action; a disciplined set of supporting hues (§2.2) serves status/syntax/data roles only
- Fully RTL layout with Persian (Farsi) copy; logical CSS properties throughout
- Focus ring system using a saturated olive `hsla(79, 48%, 36%, 1)` for accessibility
- Pill badges (9999px) with tinted olive backgrounds for status indicators

## 2. Color Palette & Roles

### 2.1 Primary — Olive

The olive scale is derived from the anchor `#60782e` (hue ≈ 79.5°, saturation ≈ 45%). It is the **only** color that carries brand identity, and the only one used broadly across the UI. Text stays black; olive is an accent.

| Token | Hex | Role |
|-------|-----|------|
| **Olive 950** | `#1d250e` | Deepest accent — pressed states, dark accent surfaces |
| **Olive 900** | `#2f3b17` | Hover state for primary buttons, dark accent surfaces. Not for body text |
| **Olive 800** | `#445521` | Dark accent borders/underlines, deepest workflow step |
| **Olive 700** | `#60782e` | **The anchor.** Primary CTA, links, active markers. NEVER body or heading text |
| **Olive 600** | `#79973a` | Mid accent — chart series, icon strokes, secondary accents |
| **Olive 500** | `#91b545` | Light accent — highlights, hover tints on light surfaces |
| **Olive 400** | `#a7c568` | De-emphasized accent — disabled accent states |
| **Olive 300** | `#c1d694` | Accent-tinted fills for data marks |
| **Olive 200** | `#dae7c0` | Tinted accent surfaces, chart backgrounds, light ring-border |
| **Olive 100** | `#ecf2de` | Borders, card outlines, dividers, badge backgrounds |
| **Olive 50** | `#f6f9f0` | Subtle surface tint, inner glow ring, ghost-button hover |

- **Pure White** (`#ffffff`): Page background, card surfaces, button text on dark.
- **Ink Black** (`#000000`): ALL text — headings, body, labels, navigation. The default text color.
- **Text Muted** (`#4b5563`): Secondary/muted copy where a softer tone is needed.

### 2.2 Supporting Colors — Harmonious, Role-Bound

These hues are chosen to sit beside olive without fighting it: they are analogous or complementary neighbors at the same muted, earthy saturation level — never neon. They exist only to disambiguate meaning that a single hue cannot express on its own. Using them decoratively is a violation (§7).

| Role | Name | Hex | Tinted Surface | Where it is allowed |
|------|------|-----|----------------|---------------------|
| **Warning / Pending** | Amber | `#c18825` | `#f8eedd` | Warning banners, pending status, rate-limit notices |
| **Danger / Error** | Clay | `#ae5b37` | `#f5e6e0` | Destructive actions, error text, invalid inputs |
| **Success / Healthy** | Teal | `#3c9287` | `#e2f3f1` | Success confirmations, "synced"/"healthy" status |
| **Info / Neutral** | Slate | `#437ba3` | `#e2ecf3` | Informational notices, secondary "learn more" links |
| **Highlight / New** | Plum | `#955087` | `#f1e4ee` | New/experimental labels, one-off highlight chips |

Rules that keep them harmonious with olive:
- Use each supporting hue at **exactly its role** — never as a second brand color.
- Prefer the **text + tinted-surface pattern** (colored text on its ~92%-lightness tint) over large solid fills.
- Never place two supporting hues adjacent unless they encode opposed states (e.g. success vs. danger).
- Olive remains the default for every generic action; a supporting hue must be *more specific*, not merely different.

### 2.3 Workflow Accent Colors

The deployment pipeline is expressed as a single-hue **tonal ramp** of olive, so it reads as one progression rather than three unrelated colors.
- **Ship** (`#445521`, Olive 800): "ship to production" — the deepest, most committed step.
- **Preview** (`#60782e`, Olive 700): the preview deployment — the anchor olive.
- **Develop** (`#91b545`, Olive 500): the development step — light and approachable.

### 2.4 Console / Code Colors

Syntax highlighting uses the supporting palette, kept in the same muted register as olive.
- **Console Olive** (`#60782e`): `--geist-console-text-color-green`, keywords, strings that represent success.
- **Console Slate** (`#437ba3`): `--geist-console-text-color-blue`, identifiers, standard strings.
- **Console Plum** (`#955087`): `--geist-console-text-color-purple`, functions, decorators.
- **Console Amber** (`#c18825`): `--geist-console-text-color-amber`, numbers, warnings.
- **Console Teal** (`#3c9287`): `--geist-console-text-color-teal`, comments, types.

### 2.5 Interactive

- **Link** (`#60782e`, Olive 700): Primary link color with underline decoration.
- **Link Hover** (`#445521`, Olive 800): Link hover/active.
- **Focus** (`hsla(79, 48%, 36%, 1)`): `--ds-focus-color`, focus ring on interactive elements.
- **Ring** (`rgba(145, 181, 69, 0.5)`): `--tw-ring-color`, Tailwind ring utility — olive at 50%.

### 2.6 Surface & Overlay

- **Overlay Backdrop** (`hsla(79, 60%, 98%, 1)`): `--ds-overlay-backdrop-color`, modal/dialog backdrop.
- **Selection Text** (`hsla(79, 60%, 94%, 1)`): `--geist-selection-text-color`, text selection highlight.
- **Badge Bg** (`#ecf2de`, Olive 100): Pill badge background, tinted olive surface.
- **Badge Text** (`#4d6224`): Pill badge text — a darkened olive that clears 4.5:1 on the badge background.

### 2.7 Neutral Scale (functional aliases)

- **Line** (`#ecf2de`, Olive 100): Borders, card outlines, dividers.
- **Surface Tint** (`#f6f9f0`, Olive 50): Subtle surface tint, inner shadow highlight.
- **Text Muted** (`#4b5563`): Secondary/muted copy.
- **Text Black** (`#000000`): Headings, body copy, labels, navigation, captions.

### Shadows & Depth

Shadow rings are tinted with the primary olive, so even the "border" participates in the brand without adding color noise.

- **Border Shadow** (`rgba(96, 120, 46, 0.10) 0px 0px 0px 1px`): The signature — replaces traditional borders.
- **Subtle Elevation** (`rgba(96, 120, 46, 0.05) 0px 2px 2px`): Minimal lift for cards.
- **Card Stack** (`rgba(96,120,46,0.10) 0px 0px 0px 1px, rgba(96,120,46,0.05) 0px 2px 2px, rgba(96,120,46,0.05) 0px 8px 8px -8px, #f6f9f0 0px 0px 0px 1px`): Full multi-layer card shadow.
- **Ring Border** (`rgb(218, 231, 192) 0px 0px 0px 1px`): Light olive ring-border (Olive 200) for tabs and images.

## 3. Typography Rules

### Font Family
- **Primary**: `Geist`, with fallbacks: `Arial, Apple Color Emoji, Segoe UI Emoji, Segoe UI Symbol`
- **Monospace**: `Geist Mono`, with fallbacks: `ui-monospace, SFMono-Regular, Roboto Mono, Menlo, Monaco, Liberation Mono, DejaVu Sans Mono, Courier New`
- **OpenType Features**: `"liga"` enabled globally on all Geist text; `"tnum"` for tabular numbers on specific captions.

### Hierarchy

| Role | Font | Size | Weight | Line Height | Letter Spacing | Notes |
|------|------|------|--------|-------------|----------------|-------|
| Display Hero | Geist | 48px (3.00rem) | 600 | 1.00–1.17 (tight) | -2.4px to -2.88px | Maximum compression, billboard impact |
| Section Heading | Geist | 32px (2.00rem) | 600 | 1.20 | -1.28px | Lighter sub-headings |
| Card Title | Geist | 24px (1.50rem) | 600 | 1.33 | -0.96px | Feature cards |
| Card Title Light | Geist | 24px (1.50rem) | 500 | 1.33 | -0.96px | Secondary card headings |
| Body Large | Geist | 20px (1.25rem) | 400 | 1.80 (relaxed) | normal | Introductions, feature descriptions |
| Body | Geist | 18px (1.13rem) | 400 | 1.56 | normal | Standard reading text |
| Body Small | Geist | 16px (1.00rem) | 400 | 1.50 | normal | Standard UI text |
| Body Medium | Geist | 16px (1.00rem) | 500 | 1.50 | normal | Navigation, emphasized text |
| Body Semibold | Geist | 16px (1.00rem) | 600 | 1.50 | -0.32px | Strong labels, active states |
| Button / Link | Geist | 14px (0.88rem) | 500 | 1.43 | normal | Buttons, links, captions |
| Button Small | Geist | 14px (0.88rem) | 400 | 1.00 (tight) | normal | Compact buttons |
| Caption | Geist | 12px (0.75rem) | 400–500 | 1.33 | normal | Metadata, tags |
| Mono Body | Geist Mono | 16px (1.00rem) | 400 | 1.50 | normal | Code blocks |
| Mono Caption | Geist Mono | 13px (0.81rem) | 500 | 1.54 | normal | Code labels |
| Mono Small | Geist Mono | 12px (0.75rem) | 500 | 1.00 (tight) | normal | `text-transform: uppercase`, technical labels |
| Micro Badge | Geist | 7px (0.44rem) | 700 | 1.00 (tight) | normal | `text-transform: uppercase`, tiny badges |

### Principles
- **Compression as identity**: Geist Sans at display sizes uses -2.4px to -2.88px letter-spacing — the most aggressive negative tracking of any major design system. This creates text that feels _minified_, like code optimized for production. The tracking progressively relaxes as size decreases: -1.28px at 32px, -0.96px at 24px, -0.32px at 16px, and normal at 14px.
- **Ligatures everywhere**: Every Geist text element enables OpenType `"liga"`. Ligatures aren't decorative — they're structural, creating tighter, more efficient glyph combinations.
- **Three weights, strict roles**: 400 (body/reading), 500 (UI/interactive), 600 (headings/emphasis). No bold (700) except for tiny micro-badges. This narrow weight range creates hierarchy through size and tracking, not weight.
- **Mono for identity**: Geist Mono in uppercase with `"tnum"` or `"liga"` serves as the "developer console" voice — compact technical labels that connect the marketing site to the product.

## 4. Component Stylings

### Buttons

**Primary Olive (Anchor)**
- Background: `#60782e` (Olive 700)
- Text: `#ffffff`
- Padding: 8px 16px
- Radius: 6px
- Shadow: `rgba(96, 120, 46, 0.10) 0px 0px 0px 1px`
- Hover: background `#2f3b17` (Olive 900)
- Focus: `2px solid var(--ds-focus-color)` outline + focus-ring shadow
- Use: Primary CTA ("Get Started", "Create Account")

**Secondary White (Shadow-bordered)**
- Background: `#ffffff`
- Text: `#000000`
- Padding: 0px 6px (minimal — content-driven width)
- Radius: 6px (subtly rounded)
- Shadow: `rgb(218, 231, 192) 0px 0px 0px 1px` (light olive ring-border)
- Hover: background shifts to `#2f3b17` (Olive 900), text to white
- Use: Standard secondary button

**Ghost / Text**
- Background: transparent
- Text: `#000000`
- Hover: background `#f6f9f0` (Olive 50)
- Use: Tertiary actions, inline controls

**Pill Button / Badge**
- Background: `#ecf2de` (Olive 100)
- Text: `#4d6224`
- Padding: 0px 10px
- Radius: 9999px (full pill)
- Font: 12px weight 500
- Use: Status badges, tags, feature labels

**State Badges** (supporting hues, §2.2)
- Success: bg `#e2f3f1`, text `#29655d`
- Pending: bg `#f8eedd`, text `#785417`
- Error: bg `#f5e6e0`, text `#6d3922`
- Info: bg `#e2ecf3`, text `#294c65`

**Large Pill (Navigation)**
- Background: transparent or `#60782e`
- Radius: 64px–100px
- Use: Tab navigation, section selectors

### Cards & Containers
- Background: `#ffffff`
- Border: via shadow — `rgba(96, 120, 46, 0.10) 0px 0px 0px 1px`
- Radius: 8px (standard), 12px (featured/image cards)
- Shadow stack: `rgba(96,120,46,0.10) 0px 0px 0px 1px, rgba(96,120,46,0.05) 0px 2px 2px, #f6f9f0 0px 0px 0px 1px`
- Image cards: `1px solid #ecf2de` with 12px top radius
- Hover: subtle shadow intensification

### Inputs & Forms
- Radio: standard styling with focus `#dae7c0` (Olive 200) background
- Focus shadow: `1px 0 0 0 rgba(96, 120, 46, 0.10)`
- Focus outline: `2px solid var(--ds-focus-color)` — consistent olive focus ring
- Invalid: text + ring in Clay (`#ae5b37`)
- Border: via shadow technique, not traditional border

### Navigation
- Clean horizontal nav on white, sticky
- Vercel logotype start-aligned, 262x52px
- Links: Geist 14px weight 500, `#000000` text (olive on hover/active)
- Active: weight 600 or underline in Olive 700
- CTA: olive pill buttons ("Start Deploying", "Contact Sales")
- Mobile: hamburger menu collapse
- Product dropdowns with multi-level menus

### Image Treatment
- Product screenshots with `1px solid #ecf2de` border
- Top-rounded images: `12px 12px 0px 0px` radius
- Dashboard/code preview screenshots dominate feature sections
- Soft olive gradient washes behind hero images (pastel olive, Olive 50→100)

### Distinctive Components

**Workflow Pipeline**
- Three-step horizontal pipeline: Develop → Preview → Ship
- Each step has its own olive tone: Develop Olive 500 → Preview Olive 700 → Ship Olive 800
- Connected with lines/arrows; the ramp reads as a single progression
- The visual metaphor for Vercel's core value proposition

**Trust Bar / Logo Grid**
- Company logos (Perplexity, ChatGPT, Cursor, etc.) in olive-tinted monochrome
- Horizontal scroll or grid layout
- Subtle `#ecf2de` border separation

**Metric Cards**
- Large number display (e.g., "10x faster")
- Geist 48px weight 600 for the metric, `#000000`
- Description below in muted black copy
- Shadow-bordered card container

## 5. Layout Principles

### Spacing System
- Base unit: 8px
- Scale: 1px, 2px, 3px, 4px, 5px, 6px, 8px, 10px, 12px, 14px, 16px, 32px, 36px, 40px
- Notable gap: jumps from 16px to 32px — no 20px or 24px in primary scale

### Grid & Container
- Max content width: approximately 1200px
- Hero: centered single-column with generous top padding
- Feature sections: 2–3 column grids for cards
- Full-width dividers using `border-bottom: 1px solid #ecf2de`
- Code/dashboard screenshots as full-width or contained with border

### Whitespace Philosophy
- **Gallery emptiness**: Massive vertical padding between sections (80px–120px+). The white space IS the design — it communicates that Vercel has nothing to prove and nothing to hide.
- **Compressed text, expanded space**: The aggressive negative letter-spacing on headlines is counterbalanced by generous surrounding whitespace. The text is dense; the space around it is vast.
- **Section rhythm**: White sections alternate with white sections — there's no color variation between sections. Separation comes from borders (shadow-borders) and spacing alone.

### Border Radius Scale
- Micro (2px): Inline code snippets, small spans
- Subtle (4px): Small containers
- Standard (6px): Buttons, links, functional elements
- Comfortable (8px): Cards, list items
- Image (12px): Featured cards, image containers (top-rounded)
- Large (64px): Tab navigation pills
- XL (100px): Large navigation links
- Full Pill (9999px): Badges, status pills, tags
- Circle (50%): Menu toggle, avatar containers

## 6. Depth & Elevation

| Level | Treatment | Use |
|-------|-----------|-----|
| Flat (Level 0) | No shadow | Page background, text blocks |
| Ring (Level 1) | `rgba(96,120,46,0.10) 0px 0px 0px 1px` | Shadow-as-border for most elements |
| Light Ring (Level 1b) | `rgb(218,231,192) 0px 0px 0px 1px` | Lighter ring for tabs, images |
| Subtle Card (Level 2) | Ring + `rgba(96,120,46,0.05) 0px 2px 2px` | Standard cards with minimal lift |
| Full Card (Level 3) | Ring + Subtle + `rgba(96,120,46,0.05) 0px 8px 8px -8px` + inner `#f6f9f0` ring | Featured cards, highlighted panels |
| Focus (Accessibility) | `2px solid hsla(79, 48%, 36%, 1)` outline | Keyboard focus on all interactive elements |

**Shadow Philosophy**: Vercel has arguably the most sophisticated shadow system in modern web design. Rather than using shadows for elevation in the traditional Material Design sense, Vercel uses multi-value shadow stacks where each layer has a distinct architectural purpose: one creates the "border" (0px spread, 1px), another adds ambient softness (2px blur), another handles depth at distance (8px blur with negative spread), and an inner ring (`#f6f9f0`) creates the subtle highlight that makes the card "glow" from within. This layered approach means cards feel built, not floating. Every ring is tinted with the primary olive, so the depth system itself carries brand identity without adding decorative color.

### Decorative Depth
- Hero gradient: soft, pastel olive gradient wash behind hero content (barely visible, atmospheric)
- Section borders: `1px solid #ecf2de` (light olive line) between major sections
- No background color variation — depth comes entirely from shadow layering and border contrast

## 7. Do's and Don'ts

### Do
- Use Geist Sans with aggressive negative letter-spacing at display sizes (-2.4px to -2.88px at 48px)
- Use shadow-as-border (`0px 0px 0px 1px rgba(96,120,46,0.10)`) instead of traditional CSS borders
- Enable `"liga"` on all Geist text — ligatures are structural, not optional
- Use the three-weight system: 400 (body), 500 (UI), 600 (headings)
- Keep `#60782e` (Olive 700) as the single primary accent across the UI
- Use the supporting palette (§2.2) strictly for its assigned role, and prefer tinted-surface + colored-text over large solid fills
- Apply the workflow olive ramp (Develop 500 → Preview 700 → Ship 800) only in workflow context
- Use multi-layer shadow stacks for cards (border + elevation + ambient + inner highlight)
- Use `#000000` for ALL text (headings, body, labels, nav); olive is an accent only
- Lay out everything RTL with Persian copy and logical CSS properties

### Don't
- Don't use positive letter-spacing on Geist Sans — it's always negative or zero
- Don't use weight 700 (bold) on body text — 600 is the maximum, used only for headings
- Don't use traditional CSS `border` on cards — use the shadow-border technique
- Don't color body or heading text olive (or any supporting hue) — text is black; color is reserved for accents
- Don't add hues beyond the olive scale and the five role-bound supporting colors — no neon, no untethered brand colors
- Don't decorate with supporting colors — each must encode a specific meaning (warning, error, success, info, highlight)
- Don't repurpose a supporting hue as a general-purpose CTA or link color — olive owns those roles
- Don't lay out LTR — the site is fully RTL (use `dir="rtl"` and logical properties like `ms-`/`me-`)
- Don't apply the workflow olive ramp decoratively — it marks pipeline stages only
- Don't use heavy shadows (> 0.12 opacity) — the shadow system is whisper-level
- Don't increase body text letter-spacing — Geist is designed to run tight
- Don't use pill radius (9999px) on primary action buttons — pills are for badges/tags only
- Don't skip the inner `#f6f9f0` ring in card shadows — it's the glow that makes the system work

## 8. RTL & Persian (Farsi) Localization

The product is Persian-first and the entire interface is **RTL**. This is not an optional
theme — it is the default layout direction.

### Direction
- The root document uses `dir="rtl"` and `lang="fa"`; set both on `<html>`.
- Use **logical CSS properties** everywhere: `margin-inline-start/end` (`ms-*`/`me-*`),
  `padding-inline` (`ps-*`/`pe-*`), `inset-inline-start/end` (`start-*`/`end-*`),
  `text-align: start/end`. Never use `left`/`right` for layout.
- Icons that imply direction (arrows, chevrons, back/forward) MUST be mirrored.
- Flex/grid order follows the RTL flow automatically with logical properties; avoid
  hard-coded `order` values that assume LTR.

### Typography for Persian
- Body copy uses a Persian-capable font stack; Geist Sans is retained for Latin text,
  numerals, and code. Font stack order: Persian UI font first, then Geist, then system
  fallbacks.
- Persian text does NOT use the aggressive Latin negative letter-spacing. Tracking rules
  (see §3) apply to **Latin** Geist text only; Persian copy uses normal tracking.
- Numerals: use Persian digits (`۰۱۲۳۴۵۶۷۸۹`) in user-facing copy where the design calls for
  it, and keep Latin digits inside code/technical labels rendered with Geist Mono.

### Copy
- All user-facing strings are in Persian. Keep a single source of strings (a dictionary or
  i18n catalog) rather than inline literals, so the language can be extended later.
- Do not machine-translate technical identifiers (JWT, OTP, API) — keep them as-is.

## 9. Responsive Behavior

### Breakpoints
| Name | Width | Key Changes |
|------|-------|-------------|
| Mobile Small | <400px | Tight single column, minimal padding |
| Mobile | 400–600px | Standard mobile, stacked layout |
| Tablet Small | 600–768px | 2-column grids begin |
| Tablet | 768–1024px | Full card grids, expanded padding |
| Desktop Small | 1024–1200px | Standard desktop layout |
| Desktop | 1200–1400px | Full layout, maximum content width |
| Large Desktop | >1400px | Centered, generous margins |

### Touch Targets
- Buttons use comfortable padding (8px–16px vertical)
- Navigation links at 14px with adequate spacing
- Pill badges have 10px horizontal padding for tap targets
- Mobile menu toggle uses 50% radius circular button

### Collapsing Strategy
- Hero: display 48px → scales down, maintains negative tracking proportionally
- Navigation: horizontal links + CTAs → hamburger menu
- Feature cards: 3-column → 2-column → single column stacked
- Code screenshots: maintain aspect ratio, may horizontally scroll
- Trust bar logos: grid → horizontal scroll
- Footer: multi-column → stacked single column
- Section spacing: 80px+ → 48px on mobile

### Image Behavior
- Dashboard screenshots maintain border treatment at all sizes
- Hero gradient softens/simplifies on mobile
- Product screenshots use responsive images with consistent border radius
- Full-width sections maintain edge-to-edge treatment

## 10. Agent Prompt Guide

### Quick Color Reference
- Primary CTA: Olive (`#60782e`)
- Primary CTA hover: Olive 900 (`#2f3b17`)
- Background: Pure White (`#ffffff`)
- Heading text: Ink Black (`#000000`)
- Body text: Ink Black (`#000000`); muted copy `#4b5563`
- Border (shadow): `rgba(96, 120, 46, 0.10) 0px 0px 0px 1px`
- Link: Olive (`#60782e`); link hover `#445521`
- Focus ring: `hsla(79, 48%, 36%, 1)`
- Badge: bg `#ecf2de`, text `#4d6224`
- Warning `#c18825` · Error `#ae5b37` · Success `#3c9287` · Info `#437ba3` · Highlight `#955087` (role-bound only)

### Example Component Prompts
- "Create an RTL hero section on white background. Headline at 48px Geist weight 600, line-height 1.00, letter-spacing -2.4px, color #000000. Subtitle at 20px Geist weight 400, line-height 1.80, color #000000. Olive CTA button (#60782e, white text, 6px radius, 8px 16px padding, hover #2f3b17) and ghost button (white, shadow-border rgba(96,120,46,0.10) 0px 0px 0px 1px, 6px radius)."
- "Design a card: white background, no CSS border. Use shadow stack: rgba(96,120,46,0.10) 0px 0px 0px 1px, rgba(96,120,46,0.05) 0px 2px 2px, #f6f9f0 0px 0px 0px 1px. Radius 8px. Title at 24px Geist weight 600, letter-spacing -0.96px, #000000. Body at 16px weight 400, #000000."
- "Build a pill badge: #ecf2de background, #4d6224 text, 9999px radius, 0px 10px padding, 12px Geist weight 500."
- "Create an RTL navigation: white sticky header, `dir=\"rtl\"`. Geist 14px weight 500 links, #000000 text, olive on hover. Olive pill CTA at the inline-end. Shadow-border on the bottom edge: rgba(96,120,46,0.10) 0px 0px 0px 1px."
- "Design an RTL workflow section showing three steps as an olive tonal ramp: Develop (#91b545), Preview (#60782e), Ship (#445521). Each step: 14px Geist Mono uppercase label + 24px Geist weight 600 title (#000000) + 16px weight 400 description (#000000)."
- "Add a status row using the supporting palette: success chip (#e2f3f1 bg / #29655d text), pending chip (#f8eedd bg / #785417 text), error chip (#f5e6e0 bg / #6d3922 text). Olive stays reserved for actions — do not tint these chips olive."

### Iteration Guide
1. Always use shadow-as-border instead of CSS border — `0px 0px 0px 1px rgba(96,120,46,0.10)` is the foundation
2. Letter-spacing scales with font size: -2.4px at 48px, -1.28px at 32px, -0.96px at 24px, normal at 14px
3. Three weights only: 400 (read), 500 (interact), 600 (announce)
4. Color is functional, never decorative — olive marks actions and identity; the five supporting hues mark status/syntax only
5. The inner `#f6f9f0` ring in card shadows is what gives cards their subtle inner glow
6. Geist Mono uppercase for technical labels, Geist Sans for everything else
7. When in doubt, use olive — a supporting hue must earn its place by encoding meaning olive cannot
