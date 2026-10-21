# Design System: Vercel (Normal Blue Accent, RTL Persian)

## 1. Visual Theme & Atmosphere

Vercel's website is the visual thesis of developer infrastructure made invisible — a design system so restrained it borders on philosophical. The page is overwhelmingly white (`#ffffff`) with black (`#000000`) text, creating a gallery-like emptiness where every element earns its pixel. This isn't minimalism as decoration; it's minimalism as engineering principle. The Geist design system treats the interface like a compiler treats code — every unnecessary token is stripped away until only structure remains.

**This project's variant is Persian and fully RTL.** All text is black; the blue scale is reserved for accents (primary CTA, links, focus rings, badges, workflow markers) and never for body or heading copy.

The custom Geist font family is the crown jewel. Geist Sans uses aggressive negative letter-spacing (-2.4px to -2.88px at display sizes), creating headlines that feel compressed, urgent, and engineered — like code that's been minified for production. At body sizes, the tracking relaxes but the geometric precision persists. Geist Mono completes the system as the monospace companion for code, terminal output, and technical labels. Both fonts enable OpenType `"liga"` (ligatures) globally, adding a layer of typographic sophistication that rewards close reading.

What distinguishes Vercel from other monochrome design systems is its shadow-as-border philosophy. Instead of traditional CSS borders, Vercel uses `box-shadow: 0px 0px 0px 1px rgba(37,99,235,0.08)` — a zero-offset, zero-blur, 1px-spread shadow that creates a border-like line without the box model implications. This technique allows borders to exist in the shadow layer, enabling smoother transitions, rounded corners without clipping, and a subtler visual weight than traditional borders. The entire depth system is built on layered, multi-value shadow stacks where each layer serves a specific purpose: one for the border, one for soft elevation, one for ambient depth.

**Key Characteristics:**
- Geist Sans with extreme negative letter-spacing (-2.4px to -2.88px at display) — text as compressed infrastructure
- Geist Mono for code and technical labels with OpenType `"liga"` globally
- Shadow-as-border technique: `box-shadow 0px 0px 0px 1px` replaces traditional borders throughout
- Multi-layer shadow stacks for nuanced depth (border + elevation + ambient in single declarations)
- Pure white canvas with `#000000` text — black, maximally readable
- Workflow-specific blue accents: Ship Blue (`#1d4ed8`), Preview Blue (`#3b82f6`), Develop Blue (`#60a5fa`)
- Fully RTL layout with Persian (Farsi) copy; logical CSS properties throughout
- Focus ring system using `hsla(217, 91%, 60%, 1)` — a standard saturated blue for accessibility
- Pill badges (9999px) with tinted blue backgrounds for status indicators

## 2. Color Palette & Roles

### Primary
- **Vercel Blue** (`#1d4ed8`): Accent only — primary CTA background, links, active states, dark surface backgrounds. NEVER used for body or heading text.
- **Pure White** (`#ffffff`): Page background, card surfaces, button text on dark.
- **Deep Blue** (`#1e3a8a`): Secondary use, `--geist-console-text-color-default`, used in specific console/code contexts.
- **Ink Black** (`#000000`): ALL text — headings, body, labels, navigation. The default text color.

### Workflow Accent Colors
- **Ship Blue** (`#1d4ed8`): `--ship-text`, the "ship to production" workflow step — deep, urgent blue.
- **Preview Blue** (`#3b82f6`): `--preview-text`, the preview deployment workflow — medium vibrant blue.
- **Develop Blue** (`#60a5fa`): `--develop-text`, the development workflow — light, approachable blue.

### Console / Code Colors
- **Console Blue** (`#2563eb`): `--geist-console-text-color-blue`, syntax highlighting blue.
- **Console Indigo** (`#4f46e5`): `--geist-console-text-color-indigo`, syntax highlighting indigo-blue.
- **Console Sky** (`#0ea5e9`): `--geist-console-text-color-sky`, syntax highlighting sky blue.

### Interactive
- **Link Blue** (`#2563eb`): Primary link color with underline decoration.
- **Focus Blue** (`hsla(217, 91%, 60%, 1)`): `--ds-focus-color`, focus ring on interactive elements.
- **Ring Blue** (`rgba(96, 165, 250, 0.5)`): `--tw-ring-color`, Tailwind ring utility.

### Neutral Scale
- **Blue 900** (`#1e3a8a`): Accent — hover states, dark accent surfaces. Not for text.
- **Blue 700** (`#1d4ed8`): Accent — primary CTA, links, active markers. Not for body text.
- **Blue 500** (`#3b82f6`): Tertiary text, muted links.
- **Blue 400** (`#60a5fa`): Placeholder text, disabled states (the only text-ish blue, for placeholders only).
- **Blue 100** (`#dbeafe`): Borders, card outlines, dividers.
- **Blue 50** (`#eff6ff`): Subtle surface tint, inner shadow highlight.
- **Text Black** (`#000000`): Headings, body copy, labels, navigation, captions.
- **Text Muted** (`#4b5563`): Secondary/muted copy where a softer tone is needed.

### Surface & Overlay
- **Overlay Backdrop** (`hsla(214, 100%, 98%, 1)`): `--ds-overlay-backdrop-color`, modal/dialog backdrop.
- **Selection Text** (`hsla(214, 100%, 96%, 1)`): `--geist-selection-text-color`, text selection highlight.
- **Badge Blue Bg** (`#dbeafe`): Pill badge background, tinted blue surface.
- **Badge Blue Text** (`#1d4ed8`): Pill badge text, darker blue for readability.

### Shadows & Depth
- **Border Shadow** (`rgba(37, 99, 235, 0.08) 0px 0px 0px 1px`): The signature — replaces traditional borders.
- **Subtle Elevation** (`rgba(37, 99, 235, 0.04) 0px 2px 2px`): Minimal lift for cards.
- **Card Stack** (`rgba(37,99,235,0.08) 0px 0px 0px 1px, rgba(37,99,235,0.04) 0px 2px 2px, rgba(37,99,235,0.04) 0px 8px 8px -8px, #eff6ff 0px 0px 0px 1px`): Full multi-layer card shadow.
- **Ring Border** (`rgb(191, 219, 254) 0px 0px 0px 1px`): Light blue ring-border for tabs and images.

## 3. Typography Rules

### Font Family
- **Primary**: `Geist`, with fallbacks: `Arial, Apple Color Emoji, Segoe UI Emoji, Segoe UI Symbol`
- **Monospace**: `Geist Mono`, with fallbacks: `ui-monospace, SFMono-Regular, Roboto Mono, Menlo, Monaco, Liberation Mono, DejaVu Sans Mono, Courier New`
- **OpenType Features**: `"liga"` enabled globally on all Geist text; `"tnum"` for tabular numbers on specific captions.

### Hierarchy

| Role | Font | Size | Weight | Line Height | Letter Spacing | Notes |
|------|------|------|--------|-------------|----------------|-------|
| Display Hero | Geist | 48px (3.00rem) | 600 | 1.00–1.17 (tight) | -2.4px to -2.88px | Maximum compression, billboard impact |
| Section Heading | Geist | 40px (2.50rem) | 600 | 1.20 (tight) | -2.4px | Feature section titles |
| Sub-heading Large | Geist | 32px (2.00rem) | 600 | 1.25 (tight) | -1.28px | Card headings, sub-sections |
| Sub-heading | Geist | 32px (2.00rem) | 400 | 1.50 | -1.28px | Lighter sub-headings |
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

**Primary White (Shadow-bordered)**
- Background: `#ffffff`
- Text: `#000000`
- Padding: 0px 6px (minimal — content-driven width)
- Radius: 6px (subtly rounded)
- Shadow: `rgb(191, 219, 254) 0px 0px 0px 1px` (ring-border)
- Hover: background shifts to `var(--ds-blue-900)` (dark)
- Focus: `2px solid var(--ds-focus-color)` outline + `var(--ds-focus-ring)` shadow
- Use: Standard secondary button

**Primary Blue (Inferred from Geist system)**
- Background: `#1d4ed8`
- Text: `#ffffff`
- Padding: 8px 16px
- Radius: 6px
- Use: Primary CTA ("Start Deploying", "Get Started")

**Pill Button / Badge**
- Background: `#dbeafe` (tinted blue)
- Text: `#1d4ed8`
- Padding: 0px 10px
- Radius: 9999px (full pill)
- Font: 12px weight 500
- Use: Status badges, tags, feature labels

**Large Pill (Navigation)**
- Background: transparent or `#1d4ed8`
- Radius: 64px–100px
- Use: Tab navigation, section selectors

### Cards & Containers
- Background: `#ffffff`
- Border: via shadow — `rgba(37, 99, 235, 0.08) 0px 0px 0px 1px`
- Radius: 8px (standard), 12px (featured/image cards)
- Shadow stack: `rgba(37,99,235,0.08) 0px 0px 0px 1px, rgba(37,99,235,0.04) 0px 2px 2px, #eff6ff 0px 0px 0px 1px`
- Image cards: `1px solid #dbeafe` with 12px top radius
- Hover: subtle shadow intensification

### Inputs & Forms
- Radio: standard styling with focus `var(--ds-blue-200)` background
- Focus shadow: `1px 0 0 0 var(--ds-blue-alpha-600)`
- Focus outline: `2px solid var(--ds-focus-color)` — consistent blue focus ring
- Border: via shadow technique, not traditional border

### Navigation
- Clean horizontal nav on white, sticky
- Vercel logotype left-aligned, 262x52px
- Links: Geist 14px weight 500, `#000000` text (accent blue on hover/active)
- Active: weight 600 or underline
- CTA: dark blue pill buttons ("Start Deploying", "Contact Sales")
- Mobile: hamburger menu collapse
- Product dropdowns with multi-level menus

### Image Treatment
- Product screenshots with `1px solid #dbeafe` border
- Top-rounded images: `12px 12px 0px 0px` radius
- Dashboard/code preview screenshots dominate feature sections
- Soft blue gradient backgrounds behind hero images (pastel blue washes)

### Distinctive Components

**Workflow Pipeline**
- Three-step horizontal pipeline: Develop → Preview → Ship
- Each step has its own blue accent: Develop Blue → Preview Blue → Ship Blue
- Connected with lines/arrows
- The visual metaphor for Vercel's core value proposition

**Trust Bar / Logo Grid**
- Company logos (Perplexity, ChatGPT, Cursor, etc.) in blue-tinted monochrome
- Horizontal scroll or grid layout
- Subtle `#dbeafe` border separation

**Metric Cards**
- Large number display (e.g., "10x faster")
- Geist 48px weight 600 for the metric
- Description below in blue body text
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
- Full-width dividers using `border-bottom: 1px solid #1d4ed8`
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
| Ring (Level 1) | `rgba(37,99,235,0.08) 0px 0px 0px 1px` | Shadow-as-border for most elements |
| Light Ring (Level 1b) | `rgb(191,219,254) 0px 0px 0px 1px` | Lighter ring for tabs, images |
| Subtle Card (Level 2) | Ring + `rgba(37,99,235,0.04) 0px 2px 2px` | Standard cards with minimal lift |
| Full Card (Level 3) | Ring + Subtle + `rgba(37,99,235,0.04) 0px 8px 8px -8px` + inner `#eff6ff` ring | Featured cards, highlighted panels |
| Focus (Accessibility) | `2px solid hsla(217, 91%, 60%, 1)` outline | Keyboard focus on all interactive elements |

**Shadow Philosophy**: Vercel has arguably the most sophisticated shadow system in modern web design. Rather than using shadows for elevation in the traditional Material Design sense, Vercel uses multi-value shadow stacks where each layer has a distinct architectural purpose: one creates the "border" (0px spread, 1px), another adds ambient softness (2px blur), another handles depth at distance (8px blur with negative spread), and an inner ring (`#eff6ff`) creates the subtle highlight that makes the card "glow" from within. This layered approach means cards feel built, not floating.

### Decorative Depth
- Hero gradient: soft, pastel blue gradient wash behind hero content (barely visible, atmospheric)
- Section borders: `1px solid #1d4ed8` (full blue line) between major sections
- No background color variation — depth comes entirely from shadow layering and border contrast

## 7. Do's and Don'ts

### Do
- Use Geist Sans with aggressive negative letter-spacing at display sizes (-2.4px to -2.88px at 48px)
- Use shadow-as-border (`0px 0px 0px 1px rgba(37,99,235,0.08)`) instead of traditional CSS borders
- Enable `"liga"` on all Geist text — ligatures are structural, not optional
- Use the three-weight system: 400 (body), 500 (UI), 600 (headings)
- Apply workflow accent blues (Ship/Preview/Develop) only in their workflow context
- Use multi-layer shadow stacks for cards (border + elevation + ambient + inner highlight)
- Keep the palette white + black + blue accents — blue marks actions and emphasis, never copy
- Use `#000000` for ALL text (headings, body, labels, nav); blue is an accent only
- Lay out everything RTL with Persian copy and logical CSS properties

### Don't
- Don't use positive letter-spacing on Geist Sans — it's always negative or zero
- Don't use weight 700 (bold) on body text — 600 is the maximum, used only for headings
- Don't use traditional CSS `border` on cards — use the shadow-border technique
- Don't introduce non-blue hues (reds, oranges, yellows, greens, pinks, purples) into the UI chrome
- Don't color body or heading text blue — text is black; blue is reserved for accents
- Don't lay out LTR — the site is fully RTL (use `dir="rtl"` and logical properties like `ms-`/`me-`)
- Don't apply the workflow accent blues (Ship Blue, Preview Blue, Develop Blue) decoratively
- Don't use heavy shadows (> 0.1 opacity) — the shadow system is whisper-level
- Don't increase body text letter-spacing — Geist is designed to run tight
- Don't use pill radius (9999px) on primary action buttons — pills are for badges/tags only
- Don't skip the inner `#eff6ff` ring in card shadows — it's the glow that makes the system work

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
- Primary CTA: Vercel Blue (`#1d4ed8`)
- Background: Pure White (`#ffffff`)
- Heading text: Ink Black (`#000000`)
- Body text: Ink Black (`#000000`); muted copy `#4b5563`
- Border (shadow): `rgba(37, 99, 235, 0.08) 0px 0px 0px 1px`
- Link: Link Blue (`#2563eb`)
- Focus ring: Focus Blue (`hsla(217, 91%, 60%, 1)`)

### Example Component Prompts
- "Create an RTL hero section on white background. Headline at 48px Geist weight 600, line-height 1.00, letter-spacing -2.4px, color #000000. Subtitle at 20px Geist weight 400, line-height 1.80, color #000000. Blue CTA button (#1d4ed8, 6px radius, 8px 16px padding) and ghost button (white, shadow-border rgba(37,99,235,0.08) 0px 0px 0px 1px, 6px radius)."
- "Design a card: white background, no CSS border. Use shadow stack: rgba(37,99,235,0.08) 0px 0px 0px 1px, rgba(37,99,235,0.04) 0px 2px 2px, #eff6ff 0px 0px 0px 1px. Radius 8px. Title at 24px Geist weight 600, letter-spacing -0.96px, #000000. Body at 16px weight 400, #000000."
- "Build a pill badge: #dbeafe background, #1d4ed8 text, 9999px radius, 0px 10px padding, 12px Geist weight 500."
- "Create an RTL navigation: white sticky header, `dir=\"rtl\"`. Geist 14px weight 500 for links, #000000 text. Blue pill CTA on the left. Shadow-border on bottom: rgba(37,99,235,0.08) 0px 0px 0px 1px."
- "Design an RTL workflow section showing three steps: Develop (label color #60a5fa), Preview (#3b82f6), Ship (#1d4ed8). Each step: 14px Geist Mono uppercase label + 24px Geist weight 600 title (#000000) + 16px weight 400 description (#000000)."

### Iteration Guide
1. Always use shadow-as-border instead of CSS border — `0px 0px 0px 1px rgba(37,99,235,0.08)` is the foundation
2. Letter-spacing scales with font size: -2.4px at 48px, -1.28px at 32px, -0.96px at 24px, normal at 14px
3. Three weights only: 400 (read), 500 (interact), 600 (announce)
4. Color is functional, never decorative — workflow blues (Ship/Preview/Develop) mark pipeline stages only
5. The inner `#eff6ff` ring in card shadows is what gives Vercel cards their subtle inner glow
6. Geist Mono uppercase for technical labels, Geist Sans for everything else
