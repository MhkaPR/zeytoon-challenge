"use client";

import { useTranslations } from "next-intl";
import { Skeleton, Typography } from "@heroui/react";
import { useState } from "react";

import { LlmCeilingForm } from "@/src/features/ops/settings/LlmCeilingForm";
import { TunablesForm } from "@/src/features/ops/settings/TunablesForm";
import { opsErrorMessage, useOpsData } from "@/src/features/ops/useOpsData";
import { getLlmCeiling, getSettings, setLlmCeiling, updateSettings } from "@/src/lib/api/ops";
import { getAccessToken } from "@/src/lib/session";

export default function OpsSettingsPage() {
  const ot = useTranslations("ops");
  const settings = useOpsData(getSettings, "settings");
  const ceilingState = useOpsData(getLlmCeiling, "ceiling");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true);
    setFailure(null);
    setNotice(null);
    try {
      await action();
      setNotice(success);
      settings.reload();
      ceilingState.reload();
    } catch (err) {
      setFailure(opsErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const ceiling = ceilingState.data as
    | { ceiling?: number | null; period?: string; spend?: number; exceeded?: boolean }
    | null;

  return (
    <main className="flex flex-col gap-[20px]">
      <div className="flex flex-col gap-[4px]">
        <Typography className="text-[20px] font-semibold" type="h2">
          {ot("settingsTitle")}
        </Typography>
        <Typography className="text-[13px] text-muted">{ot("settingsIntro")}</Typography>
      </div>

      {notice && (
        <Typography className="text-[13px] text-success" role="status">
          {notice}
        </Typography>
      )}
      {failure && (
        <Typography className="text-[13px] text-danger" role="alert">
          {failure}
        </Typography>
      )}

      <div className="grid gap-[16px] lg:grid-cols-2">
        {settings.loading ? (
          <Skeleton className="h-[320px] rounded-[var(--radius)]" />
        ) : settings.error || !settings.data ? (
          <Typography role="alert">{settings.error ?? ot("genericError")}</Typography>
        ) : (
          <TunablesForm
            busy={busy}
            onSave={(values) =>
              run(
                () => updateSettings(getAccessToken(), values),
                ot("settingsSaved"),
              )
            }
            values={settings.data}
          />
        )}

        {ceilingState.loading ? (
          <Skeleton className="h-[280px] rounded-[var(--radius)]" />
        ) : (
          <LlmCeilingForm
            busy={busy}
            ceiling={ceiling?.ceiling ?? null}
            exceeded={Boolean(ceiling?.exceeded)}
            onSave={(amount, period) =>
              run(
                () => setLlmCeiling(getAccessToken(), amount, period),
                ot("settingsSaved"),
              )
            }
            period={ceiling?.period ?? "monthly"}
            spend={Number(ceiling?.spend ?? 0)}
          />
        )}
      </div>
    </main>
  );
}
