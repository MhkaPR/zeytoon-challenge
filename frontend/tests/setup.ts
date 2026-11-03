import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

vi.mock("next-intl", async () => {
  const fa = (await import("@/src/lib/i18n/messages/fa.json")).default as Record<string, unknown>;
  const makeTranslator = (messages: Record<string, unknown>) => {
    const t = ((key: string) => {
      const value = messages[key];
      return typeof value === "string" ? value : key;
    }) as ((key: string) => string) & {
      raw: (key: string) => unknown;
      rich: unknown;
      markup: unknown;
    };
    t.raw = (key: string) => messages[key];
    t.rich = t;
    t.markup = t;
    return t;
  };
  return {
    useTranslations: () => makeTranslator(fa),
    useLocale: () => "fa",
    NextIntlClientProvider: ({ children }: { children: unknown }) => children,
  };
});

vi.mock("next-intl/server", async () => {
  const fa = (await import("@/src/lib/i18n/messages/fa.json")).default as Record<string, unknown>;
  return {
    getTranslations: async () => {
      const t = ((key: string) => {
        const value = fa[key];
        return typeof value === "string" ? value : key;
      }) as ((key: string) => string) & { raw: (key: string) => unknown };
      t.raw = (key: string) => fa[key];
      return t;
    },
  };
});

globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
};
