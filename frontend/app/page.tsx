"use client";

import { useEffect, useState } from "react";

import { MainBody } from "@/src/features/home/MainBody";
import {
  getPublishedPlans,
  getRecentCompanies,
  type PublicPlan,
  type RecentPublicCompany,
} from "@/src/lib/api/publicCatalog";

/**
 * The ``main`` page. The page is a client-rendered SPA: it fetches the published catalog
 * from the API in the browser instead of on the server.
 */
export default function MainPage() {
  const [plans, setPlans] = useState<PublicPlan[]>([]);
  const [recentCompanies, setRecentCompanies] = useState<RecentPublicCompany[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.all([getPublishedPlans(), getRecentCompanies()])
      .then(([nextPlans, nextCompanies]) => {
        if (active) {
          setPlans(nextPlans);
          setRecentCompanies(nextCompanies);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="flex flex-1 flex-col">
      <MainBody loading={loading} plans={plans} recentCompanies={recentCompanies} />
    </main>
  );
}
