"use client";

import { useEffect, useState } from "react";
import { getAnalyticsOverview, getContactCoverage, getQueue } from "@/lib/api";
import type { AnalyticsOverview, ContactCoverage, QueueItem } from "@/lib/api";
import StatsCard from "@/components/StatsCard";
import TierBadge from "@/components/TierBadge";
import ScoreBadge from "@/components/ScoreBadge";

export default function Dashboard() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [coverage, setCoverage] = useState<ContactCoverage | null>(null);
  const [topQueue, setTopQueue] = useState<QueueItem[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      getAnalyticsOverview(),
      getContactCoverage(),
      getQueue({ per_page: 10, sort_by: "score", sort_dir: "desc" }),
    ])
      .then(([o, c, q]) => {
        setOverview(o);
        setCoverage(c);
        setTopQueue(q.items);
      })
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="max-w-4xl">
        <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
          Failed to load data. Make sure the backend is running at{" "}
          <code className="bg-red-100 px-1 rounded">http://localhost:8000</code>.
          <br />
          <span className="text-xs mt-1 block">{error}</span>
        </div>
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="max-w-4xl">
        <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
        <p className="text-gray-400">Loading...</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl">
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {/* Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatsCard label="Total Patients" value={overview.total_patients} />
        <StatsCard label="Queue Size" value={overview.queue_size} sub="Ready for outreach" />
        <StatsCard label="Has Email" value={overview.has_email} />
        <StatsCard label="DNC Flagged" value={overview.dnc_count} sub="Do not contact" />
      </div>

      {/* Tier Breakdown */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <h2 className="text-lg font-semibold mb-4">Patient Tiers</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-4">
          {overview.tiers.map((t) => (
            <div key={t.tier} className="text-center">
              <p className="text-2xl font-bold tabular-nums">{t.count.toLocaleString()}</p>
              <TierBadge tier={t.tier} />
            </div>
          ))}
        </div>
      </div>

      {/* Contact Coverage */}
      {coverage && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
          <h2 className="text-lg font-semibold mb-4">Contact Coverage</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatsCard label="Email + Phone" value={coverage.has_both} />
            <StatsCard label="Email Only" value={coverage.email_only} />
            <StatsCard label="Phone Only" value={coverage.phone_only} />
            <StatsCard label="No Contact" value={coverage.no_contact} />
          </div>
        </div>
      )}

      {/* Top Queue Items */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold mb-4">Top Re-engagement Candidates</h2>
        <div className="overflow-x-auto -mx-6 px-6 sm:mx-0 sm:px-0">
          <table className="w-full text-sm min-w-[600px]">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="pb-2 font-medium">Name</th>
                <th className="pb-2 font-medium">Contact</th>
                <th className="pb-2 font-medium">Last Visit</th>
                <th className="pb-2 font-medium">Days</th>
                <th className="pb-2 font-medium">Score</th>
                <th className="pb-2 font-medium">Tier</th>
              </tr>
            </thead>
            <tbody>
              {topQueue.map((q) => (
                <tr key={q.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-2.5 font-medium">{q.full_name}</td>
                  <td className="py-2.5 text-gray-600">{q.cell_phone || q.email || "—"}</td>
                  <td className="py-2.5 text-gray-600">{q.last_appt || "—"}</td>
                  <td className="py-2.5 tabular-nums">{q.days_since_appt ?? "—"}</td>
                  <td className="py-2.5"><ScoreBadge score={q.score} /></td>
                  <td className="py-2.5"><TierBadge tier={q.tier} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
