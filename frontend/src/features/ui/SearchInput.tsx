"use client";

import { Button, Label, SearchField } from "@heroui/react";
import { Search } from "lucide-react";
import { useTranslations } from "next-intl";
import type { FormEvent } from "react";

/**
 * Shared search control: a search field paired with a circular submit button. Every search
 * surface (home hero, search page, company directory, catalog filters) renders through this
 * component so the control looks and behaves consistently.
 */
export function SearchInput({
  value,
  onChange,
  ariaLabel,
  placeholder,
  name,
  variant,
  className,
  inputClassName,
  submitLabel,
  onSubmit,
}: {
  value: string;
  onChange: (value: string) => void;
  ariaLabel: string;
  placeholder: string;
  name?: string;
  variant?: "primary" | "secondary";
  className?: string;
  inputClassName?: string;
  submitLabel?: string;
  onSubmit?: (value: string) => void;
}) {
  const ot = useTranslations();

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit?.(value);
  }

  return (
    <form
      className={className ?? "flex w-full items-center gap-[8px]"}
      role="search"
      onSubmit={handleSubmit}
    >
      <div className="min-w-0 flex-1">
        <SearchField
          aria-label={ariaLabel}
          name={name}
          value={value}
          variant={variant}
          onChange={onChange}
        >
          <Label className="sr-only">{ariaLabel}</Label>
          <SearchField.Group>
            <SearchField.SearchIcon />
            <SearchField.Input className={inputClassName} placeholder={placeholder} />
            <SearchField.ClearButton />
          </SearchField.Group>
        </SearchField>
      </div>
      <Button
        aria-label={submitLabel ?? ot("searchSubmit")}
        className="shrink-0 rounded-full"
        isIconOnly
        type="submit"
        variant="primary"
      >
        <Search aria-hidden="true" className="size-[18px]" />
      </Button>
    </form>
  );
}
