import { MainBody } from "@/src/features/home/MainBody";
import { getPublishedPlans, getRecentCompanies } from "@/src/lib/api/publicCatalog";

/**
 * The ``main`` page (PAGES.yaml): the shared header lives in the root layout, and the
 * homepage body (``MainBody``) owns its own content container and the site footer.
 */
export default async function MainPage() {
  const [plans, recentCompanies] = await Promise.all([getPublishedPlans(), getRecentCompanies()]);
  return (
    <main className="flex flex-1 flex-col">
      <MainBody plans={plans} recentCompanies={recentCompanies} />
    </main>
  );
}
