> Agent-facing rules. Load together with discovery.md.
> This file is immutable. Do NOT modify it during a project.
> Project-specific decisions belong to project-context.md, never here.

---

## 0. Purpose & Scope

This file defines the coding, design, i18n, and quality rules for all frontend projects.

Relationship to other files:

- frontend-rules.md (this file): how to write code after discovery is sealed.

Priority order:

project-context.md > discovery.md > frontend-rules.md > user's mid-chat wishes

Hard rules:

- You MUST NOT modify this file during a project.
- You MUST NOT violate the No Duplication Rule (section 2.5).

---

## 1. Universal Rules

### 1.1 Language

- TypeScript is mandatory. No plain JavaScript files.
- strict: true in tsconfig.

### 1.2 Folder Structure

Choose one of the following based on the project's scale and complexity, and announce your choice to the user before scaffolding:

- layer-based: for small projects with few features.
- feature-based: for medium and large projects with multiple independent features.

Once chosen, do NOT switch mid-project without a version bump (see discovery.md section 4.4).

### 1.3 Naming Conventions

| Thing                 | Convention       | Example           |
| --------------------- | ---------------- | ----------------- |
| Files                 | camelCase        | userProfile.ts    |
| Components            | PascalCase       | UserProfile       |
| Functions / variables | camelCase        | getUserById       |
| Constants             | UPPER_SNAKE_CASE | API_BASE_URL      |
| Types / Interfaces    | PascalCase       | UserProfileProps  |
| CSS classes (if any)  | kebab-case       | user-profile-card |

### 1.4 Exports

- Use named exports by default.
- Exception: Next.js pages and layout files use default exports as required by the framework.
- Do NOT mix default and named exports in the same file.

### 1.5 Imports

- Use absolute imports where the framework supports path aliases.
- Group imports in this order, separated by blank lines:
  1. External packages.
  2. Internal absolute imports.
  3. Relative imports.
  4. Types.
- Do NOT use wildcard imports (import * as X) unless necessary.

---

## 2. Design System & Tokens

### 2.1 Token Layers

Tokens follow a three-layer model:

    Primitives  ->  Semantics  ->  Components

- Primitives: raw values. Example: blue-500: #3B82F6
- Semantics: mapped meaning. Example: primary: blue-500
- Components: per-component overrides. Example: button-bg: primary

Source files live under src/theme/tokens/.

### 2.2 Naming Convention

Tokens are defined both as CSS variables and TypeScript objects.

CSS variables:

    --color-primary-500: #3B82F6;

TypeScript:

    export const colors = {
      primary: { 500: '#3B82F6' }
    };

The TS object is the source of truth. CSS variables are generated from it.

### 2.3 Theme Structure

    src/theme/
    ├── tokens/
    │   ├── primitives.ts
    │   ├── semantic.ts
    │   └── components.ts
    ├── themes/
    │   ├── light.ts
    │   └── dark.ts
    └── index.ts

- src/theme/index.ts is the single entry point.
- All access to theme values MUST go through this entry point.
- Do NOT hardcode token values anywhere outside src/theme/.

### 2.4 Dark Mode

- If dark mode is enabled (per project-context.md), both light.ts and dark.ts MUST be defined.
- If disabled, only light.ts exists, but the structure stays identical so dark mode can be added later without refactor.

### 2.5 No Duplication Rule

- Values that live in src/theme/ MUST NOT be duplicated in project-context.md.
- project-context.md references files by path only.
- Reason: if the user edits theme files manually, project-context.md must not become stale.

---

## 3. Framework-Specific Rules

### 3.1 Vue

- Composition API is mandatory. Options API is forbidden.
- Use <script setup> in all components.
- Use Pinia for state.
- Use vue-i18n for translations.
- Use Vue Router for routing.

### 3.2 React

- Function components only. Class components are forbidden.
- Hooks are mandatory for state and side effects.
- Use Zustand or Redux for state, chosen per project complexity.
- Use react-i18next for translations.
- Use React Router for routing.

### 3.3 Next.js

- App Router is mandatory. Pages Router is forbidden.
- Server Components are the default. Use 'use client' only when necessary.
- Use next-intl for translations.
- Use App Router conventions for layouts, loading, and error boundaries.

---

## 4. Data Fetching

- Use the approved data fetching library from project-context.md.
- Default: TanStack Query.
- Exception: GraphQL projects use urql.
- Direct use of fetch() is forbidden except inside the approved data fetching library's setup or inside server-side code in Next.js.
- All API calls MUST go through a service layer (e.g., src/services/ or per-feature services).

---

## 5. Forms & Validation

- Vue: vee-validate + Zod.
- React / Next: react-hook-form + Zod.
- Zod schemas are the single source of truth for validation.
- Forms MUST NOT contain ad-hoc validation logic outside the Zod schema.

---

## 6. Icons

### 6.1 Single Icon Pack Rule

- Only ONE icon pack per project.
- The chosen pack is recorded in project-context.md (section 6).
- Mixing icons from multiple packs is forbidden.
- If an icon is missing from the chosen pack, use the pack's own custom-icon mechanism, or ask the user before adding another pack.

### 6.2 Usage

- Import icons individually, not as a full bundle, to keep the bundle small.
- Icon size and color MUST come from design tokens, not hardcoded values.
- Decorative icons MUST have aria-hidden="true".
- Meaningful icons MUST have an accessible label (aria-label or visible text).

---

## 7. i18n Protocol

### 7.1 Hard Rules

- Every project MUST install an i18n library, even if only one language is used.
- Hardcoded user-facing strings are forbidden. Not even placeholders.
- All visible text MUST come from translation files.

### 7.2 Library Per Framework

- Vue: vue-i18n
- React: react-i18next
- Next.js: next-intl

### 7.3 File Structure

Namespace-based:

    locales/
    ├── fa/
    │   ├── common.json
    │   ├── auth.json
    │   └── <feature>.json
    └── en/
        └── ...

Each feature has its own namespace file.

### 7.4 Usage

- Key format: <namespace>.<section>.<key>
- Example: t('auth.login.title')

### 7.5 Cookie

- Selected language MUST be stored in a cookie.
- Cookie name: locale
- Cookie is set on language change and read on app bootstrap.

### 7.6 Language Switcher

- If project-context.md says multiple languages: include a switcher.
- If single language: no switcher, but cookie is still set to the default on first load.

---

## 8. RTL & Accessibility

### 8.1 RTL

- All projects are RTL-first.
- Set dir="rtl" on the html element (or the appropriate root) based on the active language.
- Use Tailwind logical properties (ms-, me-, ps-, pe-) instead of physical ones (ml-, mr-, pl-, pr-).
- Do NOT use left/right in CSS. Use inline-start/inline-end.

### 8.2 Accessibility

- All interactive elements MUST be keyboard accessible.
- All images MUST have alt attributes (empty alt for decorative images).
- All form inputs MUST have associated labels.
- Color contrast MUST meet WCAG AA.

---

## 9. Quality Gates

Before delivering any feature, verify all of the following:

- TypeScript errors: zero.
- ESLint warnings: zero.
- Prettier: applied.
- Tests: passing.
- Hardcoded strings: zero.
- Function Registry (in project-context.md): updated with any new utility, hook, or reusable component.
- project-context.md: updated if any decision or registry entry changed.

If any item is unchecked, do NOT deliver the feature.

---

## 10. Function Registry Rules

The Function Registry lives in project-context.md (section 9 of that file).

### 10.1 Registration Conditions

Register:

- Utility functions (pure, reusable).
- Custom hooks.
- Reusable components (e.g., a default dialog, a data table).

Do NOT register:

- Page-level components.
- Private local helpers inside a single file.
- Framework boilerplate.

### 10.2 Workflow

1. Before writing any new utility, hook, or reusable component, check the Function Registry.
2. If an equivalent already exists, reuse it. Do NOT duplicate.
3. After writing a new one that meets the registration conditions, add it to the registry immediately.
4. Registry entry format: Name, File, Signature, Purpose.

---

## 12. Communication Rules

- Speak in the user's language.
- Be concise. Use bullets for multi-part answers.
- Announce major decisions (folder structure, dependency additions) before executing them.
- After the seal (discovery.md section 4.3), any major change requires explicit user confirmation before execution.

---

## 13. Anti-Patterns

You MUST NOT:

- Hardcode user-facing strings.
- Use the any type.
- Use default export for components (except Next.js pages and layouts).
- Use CSS magic numbers without a token.
- Duplicate utility functions without checking the Function Registry.
- Use inline styles except for dynamic values that cannot be expressed as tokens.
- Use console.log in production code.
- Use !important in CSS.
- Ignore ESLint warnings.
- Duplicate design system values in project-context.md instead of referencing source files.
- Use fetch() directly outside the approved data fetching library's setup or Next.js server code.
- Mix icons from more than one icon pack.
- Use Options API in Vue.
- Use class components in React.
- Use Pages Router in Next.js.

---

## 14. Self-Check (before each delivery)

Before delivering, verify:

- All Quality Gates (section 9) are green.
- No Anti-Patterns (section 13) are present.
- Function Registry is up to date.
- project-context.md is up to date.
- If a sealed decision was changed, a version bump was applied.