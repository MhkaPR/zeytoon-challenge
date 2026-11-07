import { headers } from "next/headers";

/** The visitor id injected by middleware for the current request. */
export async function visitorId(): Promise<string> {
  return (await headers()).get("x-visitor-id") ?? "";
}
