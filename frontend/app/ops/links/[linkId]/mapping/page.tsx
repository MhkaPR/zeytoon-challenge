"use client";

import { Skeleton, Typography } from "@heroui/react";
import { use, useState } from "react";

import { MappingWorkspace } from "@/src/features/ops/mapping/MappingWorkspace";
import { LinkStageNav } from "@/src/features/ops/pipeline/LinkStageNav";
import { opsErrorMessage, useOpsData } from "@/src/features/ops/useOpsData";
import { AuthApiError } from "@/src/lib/api/auth";
import { getPlanSchema, getRecipe, saveRecipe, type RecipeBinding } from "@/src/lib/api/ops";
import { opsStrings } from "@/src/lib/i18n/strings";
import { getAccessToken } from "@/src/lib/session";

export default function OpsMappingPage({
  params,
}: {
  params: Promise<{ linkId: string }>;
}) {
  const { linkId } = use(params);
  const id = Number(linkId);
  const recipeState = useOpsData((token) => getRecipe(token, id), String(id));
  const schemaState = useOpsData(getPlanSchema, "plan-schema");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  async function save(planType: string, bindings: RecipeBinding[]) {
    setBusy(true);
    setFailure(null);
    setNotice(null);
    try {
      await saveRecipe(getAccessToken(), id, planType, bindings);
      setNotice(opsStrings.recipeSaved);
      recipeState.reload();
    } catch (err) {
      if (err instanceof AuthApiError && err.code === "recipe_incomplete") {
        setFailure(opsStrings.recipeIncomplete);
      } else {
        setFailure(opsErrorMessage(err));
      }
    } finally {
      setBusy(false);
    }
  }

  const loading = recipeState.loading || schemaState.loading;

  return (
    <main className="flex flex-col gap-[20px]">
      <div className="flex flex-col gap-[4px]">
        <Typography className="text-[20px] font-semibold" type="h2">
          {opsStrings.mappingTitle}
        </Typography>
        <Typography className="text-[13px] text-muted">{opsStrings.mappingIntro}</Typography>
        <LinkStageNav active="mapping" linkId={id} siteId={recipeState.data?.recipe?.site_id} />
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

      {loading ? (
        <Skeleton className="h-[320px] rounded-[var(--radius)]" />
      ) : recipeState.error || schemaState.error || !recipeState.data || !schemaState.data ? (
        <Typography role="alert">
          {recipeState.error ?? schemaState.error ?? opsStrings.genericError}
        </Typography>
      ) : (
        <MappingWorkspace
          busy={busy}
          errorText={recipeState.data.recipe ? null : null}
          initialRecipe={recipeState.data.recipe}
          onSave={save}
          planTypes={schemaState.data.plan_types}
          tables={recipeState.data.tables}
        />
      )}
    </main>
  );
}
