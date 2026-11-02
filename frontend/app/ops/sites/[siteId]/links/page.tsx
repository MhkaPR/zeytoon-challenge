import OpsSiteLinksPageClient from "./OpsSiteLinksPageClient";

export const instant = false;

export default function OpsSiteLinksPage({
  params,
}: {
  params: Promise<{ siteId: string }>;
}) {
  return <OpsSiteLinksPageClient params={params} />;
}
