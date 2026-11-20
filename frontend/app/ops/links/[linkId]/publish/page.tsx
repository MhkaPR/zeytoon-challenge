import OpsPublishPage from "./OpsPublishPage";

export const instant = false;

export default function Page({ params }: { params: Promise<{ linkId: string }> }) {
  return <OpsPublishPage params={params} />;
}
