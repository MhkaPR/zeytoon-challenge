import { CompanyPublicPageClient } from "./CompanyPublicPageClient";

type Props = { params: Promise<{ domain: string }> };

// Company domains are runtime data; allow the segment to wait for them during prerendering.
export const instant = false;

/** Route shell: decodes the domain, then hands off to the client-rendered SPA view. */
export default async function CompanyPublicPage({ params }: Props) {
  const { domain } = await params;
  return <CompanyPublicPageClient domain={decodeURIComponent(domain)} />;
}
