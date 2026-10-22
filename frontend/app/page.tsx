import { Header } from "@/src/features/site/Header";
import { MainBody } from "@/src/features/home/MainBody";

/**
 * The ``main`` page (PAGES.yaml): sticky header (logo, menu, login) over a vertical body
 * of brand logo, search box, service-type chips, and the immediate filter box.
 */
export default function MainPage() {
  return (
    <>
      <Header />
      <main className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-[80px] px-[32px] py-[80px]">
        <MainBody />
      </main>
    </>
  );
}
