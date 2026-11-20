"use client";

/**
 * Client boundary for HeroUI components rendered from Server Components.
 *
 * ``@heroui/react`` marks its barrel as client-only, so importing it directly inside a
 * Server Component (a page or layout without ``"use client"``) fails the build. Re-exporting
 * the presentational pieces from this client module lets Server Components keep using the
 * same HeroUI components as client references.
 */

export * from "@heroui/react";
