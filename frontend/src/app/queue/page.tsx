"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { getQueue, updateQueueStatus } from "@/lib/api";
import type { QueueItem, QueueList } from "@/lib/api";
import TierBadge from "@/components/TierBadge";
import ScoreBadge from "@/components/ScoreBadge";
import Pagination from "@/components/Pagination";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-blue-100 text-blue-800",
  contacted: "bg-yellow-100 text-yellow-800",
  responded: "bg-indigo-100 text-indigo-800",
  booked: "bg-green-100 text-green-800",
  dead: "bg-gray-100 text-gray-500",
};

const STATUSES = ["pending", "contacted", "responded", "booked", "dead"];

export default function QueuePage() {
  const params = useSearchParams();
  const [data, setData] = useState<QueueList | null>(null);
  const [error, setError] = useState("");

  function load() {
    const filters: Record<string, string> = {};
    params.forEach((v, k) => { filters[k] = v; });
    if (!filters.page) filters.page = "1";

    getQueue(filters)
      .then(setData)
      .catch((e) => setError(e.message));
  }

  useEffect(load, [params]);

  async function handleStatusChange(id: number, newStatus: string) {
    try {
      await updateQueueStatus(id, newStatus);
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update status");
    }
  }

  return (
    <div className="max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Re-engagement Queue</h1>
        {data && (
          <span className="text-sm text-gray-500">{data.total.toLocaleString()} patients</span>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        {STATUSES.map((s) => {
          const active = params.get("status") === s;
          return (
            <Link
              key={s}
              href={active ? "/queue" : `/queue?status=${s}`}
              className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors capitalize ${
                active
                  ? "bg-indigo-600 text-white border-indigo-600"
                  : "bg-white text-gray-600 border-gray-300 hover:border-gray-400"
              }`}
            >
              {s}
            </Link>
          );
        })}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm mb-4">
          {error}
        </div>
      )}

      {data && (
        <>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 bg-gray-50 border-b">
                  <th className="px-4 py-3 font-medium">Name</th>
                  <th className="px-4 py-3 font-medium">Contact</th>
                  <th className="px-4 py-3 font-medium">Last Visit</th>
                  <th className="px-4 py-3 font-medium">Days Ago</th>
                  <th className="px-4 py-3 font-medium">Score</th>
                  <th className="px-4 py-3 font-medium">Tier</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((q) => (
                  <tr key={q.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3">
                      {q.patient_id ? (
                        <Link
                          href={`/patients/${q.patient_id}`}
                          className="font-medium text-indigo-600 hover:text-indigo-800"
                        >
                          {q.full_name}
                        </Link>
                      ) : (
                        <span className="font-medium">{q.full_name}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{q.cell_phone || q.email || "—"}</td>
                    <td className="px-4 py-3 text-gray-600">{q.last_appt || "—"}</td>
                    <td className="px-4 py-3 tabular-nums">{q.days_since_appt ?? "—"}</td>
                    <td className="px-4 py-3"><ScoreBadge score={q.score} /></td>
                    <td className="px-4 py-3"><TierBadge tier={q.tier} /></td>
                    <td className="px-4 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_STYLES[q.status] || ""}`}>
                        {q.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={q.status}
                        onChange={(e) => handleStatusChange(q.id, e.target.value)}
                        className="text-xs border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      >
                        {STATUSES.map((s) => (
                          <option key={s} value={s} className="capitalize">{s}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
                      No queue items found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <Pagination total={data.total} page={data.page} perPage={data.per_page} />
        </>
      )}
    </div>
  );
}
