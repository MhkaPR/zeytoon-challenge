# Frontend Design System

This guide documents the design system implemented by `frontend/app/globals.css` and the shared frontend components. When a detail is not defined there, treat the examples in `frontend/app` and `frontend/src/features` as the source of truth. This is a Persian-first product UI, including public marketplace pages and operational dashboards.

## 1. Design direction

The interface pairs a clean white canvas with black text and a restrained olive accent. Persian content leads, while Latin identifiers, URLs, and technical values remain easy to scan. Layouts favor clear hierarchy, compact controls, readable cards, and responsive page widths. The operational screens use practical data-dense tables and forms; public pages use larger headings and more generous spacing.

Avoid describing the product as a Vercel clone. Geist is present for Latin text and code, but Vazirmatn is the first font in the UI stack. Do not invent marketing-site patterns, component measurements, or colors that the code does not establish.

## 2. Foundations

### Color tokens

`globals.css` defines the following palette and maps its semantic colors to HeroUI v3 variables.

| Token | Value | Intended use |
|---|---|---|
| Olive 950 | `#1d250e` | Deepest olive tone |
| Olive 900 | `#2f3b17` | Dark olive tone |
| Olive 800 | `#445521` | Deep accent |
| Olive 700 | `#60782e` | Main accent and link color |
| Olive 600 | `#79973a` | Mid accent |
| Olive 500 | `#91b545` | Lighter accent |
| Olive 400 | `#a7c568` | Soft accent |
| Olive 300 | `#c1d694` | Soft accent |
| Olive 200 | `#dae7c0` | Border tone |
| Olive 100 | `#ecf2de` | Separator tone |
| Olive 50 | `#f6f9f0` | Subtle tinted surface |
| Ink | `#000000` | Primary text |
| Muted ink | `#4b5563` | Supporting text and placeholders |
| White | `#ffffff` | Surface and field background |

Semantic mappings include accent `oklch(53.7% 0.1045 124.93)`, success `oklch(60.46% 0.0842 183.83)`, warning `oklch(66.74% 0.1282 75.93)`, and danger `oklch(56.29% 0.1193 43.2)`. Use HeroUI semantic utilities such as `bg-accent`, `text-muted`, `bg-success-soft`, and `text-danger` so states follow the theme. Status colors describe status; olive is the general brand/action accent.

The code does not define the old guide's amber/clay/slate/plum hex set or special workflow ramp as application-wide tokens. Do not rely on those as canonical colors.

### Surfaces and depth

- Page background: `--background` (`oklch(0.979 0 0 / 0.92)`); root body also uses the white `--ds-white` token.
- Cards and overlays: white semantic surfaces.
- Secondary/tertiary surfaces: olive-50 tint.
- Text: black foreground; muted copy uses `#4b5563`.
- Borders and separators: olive-200 and olive-100 respectively.
- Surface shadow: olive-tinted ring with very subtle elevation.
- Overlay/card shadow: a slightly deeper multi-layer olive-tinted stack.
- Fields: white with a transparent border and a subtle shadow ring.

Use the semantic surface and shadow tokens first. Components may use ordinary border utilities where they need table rules or separators; the code does not prohibit CSS borders globally.

### Radius

The global radius is `8px`; form fields use `6px`. Components can use other radii when their local styles call for them, such as circular icon controls. Avoid prescribing a universal pill radius: it is not part of the global token system.

## 3. Typography

The font stack in `@theme inline` is:

- Sans: `var(--font-vazirmatn), var(--font-geist-sans), Arial, sans-serif`
- Mono: `var(--font-geist-mono), ui-monospace, SFMono-Regular, Menlo, monospace`

Use Vazirmatn for Persian UI and copy. Geist supports Latin text and numerals; Geist Mono is appropriate for code and technical values. `html` enables the `liga` OpenType feature globally. No global font-size or letter-spacing scale is defined in `globals.css`; components set sizes where needed. Existing screens commonly use 12–14px for dense operational copy, 15–20px for card and section headings, and 26–40px for page headings. Treat these as observed examples, not hard limits.

Do not apply aggressive Latin negative tracking to Persian text. Use semantic typography components such as HeroUI `Typography` where practical, then add local sizing and weight utilities consistent with nearby screens.

## 4. Layout and direction

The root document sets `lang="fa"` and `dir="rtl"`. Keep page structure RTL by default. Use logical Tailwind utilities (`ms-*`, `me-*`, `ps-*`, `pe-*`, `start-*`, `end-*`) when positioning relative to reading direction. Apply `dir="ltr"` locally to URLs, domains, and other values that need left-to-right reading.

Common page containers use a maximum width near `1200px` and responsive horizontal padding, often 16px on small screens, 24px at `sm`, and 32px at `md`. Some account/panel pages use a narrower 1000px container. Let the page's purpose determine width rather than forcing one layout everywhere.

Spacing is set locally with Tailwind values. Repeated examples include gaps and padding of 4, 6, 8, 10, 12, 16, 18, 20, 24, 28, 32, 40, 64, and 80px. Responsive grids commonly move from one column to two at `sm`, and to three at `lg` where the content supports it. Data tables should scroll horizontally when necessary instead of squeezing values beyond readability.

## 5. Components and interaction

### HeroUI

The frontend imports `@heroui/styles` and uses `@heroui/react` (v3). The global CSS overrides HeroUI semantic variables, so use semantic variants and color utilities rather than hard-coded palette values for routine controls. HeroUI v3's theming model supports CSS-variable overrides and semantic tokens; the app's actual token values are defined in `globals.css`.

### Buttons and links

Use HeroUI `Button` variants for shared actions. Existing code also uses compact accent buttons with olive background, white foreground, and approximately 6–13px vertical/horizontal padding depending on context. Secondary actions commonly use `bg-surface-secondary`; ghost actions remain visually quiet. Keep labels concise and preserve visible keyboard focus.

Links use the olive semantic link token. Hover/active treatments should remain legible and follow nearby component patterns.

### Cards

Use HeroUI `Card` variants (`default` or `secondary`) for grouped content. Cards in the frontend typically have 16–24px padding, 8–16px internal gaps, and the shared surface shadow/radius. Use the secondary variant for gently tinted groupings rather than inventing decorative gradients.

### Forms

Fields use the semantic field background, foreground, placeholder, border, shadow, and 6px field radius. Keep labels and validation messages explicit. Use danger tokens for invalid/error feedback and retain a clear focus indication. Prefer HeroUI form components where the surrounding feature already uses them.

### Alerts and status

`globals.css` provides `.alert--default`, `.alert--accent`, `.alert--success`, `.alert--warning`, and `.alert--danger` styles using HeroUI soft semantic colors. Status text should communicate state in addition to color. Reserve success, warning, and danger for their meanings.

### Tables and dense data

Operational tables use compact 12–13px text, muted headers, modest row padding, and olive-tinted separator lines. Keep long URLs in LTR cells and truncate or allow horizontal scrolling where appropriate. Avoid adding unnecessary card chrome around every table row.

### Navigation

The shared header is sticky, uses the background token, and adds the surface shadow after scrolling. It is responsive: mobile centers the logo and keeps menu/account controls available; desktop shows the site navigation. Use this implementation as the pattern for shared navigation rather than assuming a specific brand lockup size or pill CTA.

## 6. Accessibility and localization

- Keep Persian strings in the existing `next-intl` message catalogs.
- Maintain `lang="fa"` and root RTL direction.
- Keep URLs, domains, and technical identifiers readable with local LTR direction as needed.
- Preserve semantic headings, labels, roles, and status announcements.
- Ensure keyboard focus is visible and status/error meaning is not conveyed by color alone.
- Use responsive layouts that retain usable controls and readable content on narrow screens.

## 7. Practical guidance for new UI

1. Start with the established HeroUI component and semantic color tokens.
2. Follow the nearest existing page for local spacing, typography, and interaction patterns.
3. Use Vazirmatn-first typography and RTL flow; set local LTR direction only for values that need it.
4. Keep olive for primary actions and identity; use semantic status colors only for status.
5. Prefer white or softly tinted surfaces, shared radius and shadow tokens, and clear content grouping.
6. Check narrow-screen behavior, especially for tables, headers, forms, and action groups.

## Source references

- `frontend/app/globals.css` — palette, HeroUI variable mapping, font stack, global text and alert styles.
- `frontend/app/layout.tsx` — Persian locale, RTL document direction, shared app shell.
- `frontend/src/features/site/Header.tsx` — responsive sticky navigation pattern.
- `frontend/src/features/ops/` and `frontend/app/` — operational and public page examples.
