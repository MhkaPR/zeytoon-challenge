import { MainBody } from "@/src/features/home/MainBody";

/**
 * The ``main`` page (PAGES.yaml): the shared header lives in the root layout, and the
 * homepage body (``MainBody``) owns its own content container and the site footer.
 */
export default function MainPage() {
  return (
    <main className="flex flex-1 flex-col">
      <MainBody />
    </main>
  );
}
