import { Header } from "@/src/features/site/Header";
import { MainBody } from "@/src/features/home/MainBody";

/**
 * The ``main`` page (PAGES.yaml): sticky header (logo, menu, login) over the homepage body
 * (``MainBody``), which owns its own content container and the site footer.
 */
export default function MainPage() {
  return (
    <>
      <Header />
      <main className="flex flex-1 flex-col">
        <MainBody />
      </main>
    </>
  );
}
