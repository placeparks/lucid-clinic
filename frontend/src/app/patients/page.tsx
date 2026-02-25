"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { getPatients } from "@/lib/api";
import type { PatientSummary, PatientList } from "@/lib/api";
import TierBadge from "@/components/TierBadge";
import ScoreBadge from "@/components/ScoreBadge";
import FilterBar from "@/components/FilterBar";
import Pagination from "@/components/Pagination";

export default function PatientsPage() {
  const params = useSearchParams();
  const [data, setData] = useState<PatientList | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const filters: Record<string, string> = {};
    params.forEach((v, k) => { filters[k] = v; });
    if (!filters.page) filters.page = "1";

    getPatients(filters)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [params]);

  return (
    <div className="max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Patients</h1>
        {data && (
          <span className="text-sm text-gray-500">{data.total.toLocaleString()} total</span>
        )}
      </div>

      <div className="mb-4">
        <FilterBar />
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
                  <th className="px-4 py-3 font-medium">Phone</th>
                  <th className="px-4 py-3 font-medium">Email</th>
                  <th className="px-4 py-3 font-medium">City</th>
                  <th className="px-4 py-3 font-medium">Last Visit</th>
                  <th className="px-4 py-3 font-medium">Visits</th>
                  <th className="px-4 py-3 font-medium">Score</th>
                  <th className="px-4 py-3 font-medium">Tier</th>
                </tr>
              </thead>
              <tbody>
                {data.patients.map((p) => (
                  <tr key={p.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <Link
                        href={`/patients/${p.id}`}
                        className="font-medium text-indigo-600 hover:text-indigo-800"
                      >
                        {p.first_name} {p.last_name}
                      </Link>
                      {p.is_dnc && (
                        <span className="ml-2 text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded">
                          DNC
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{p.cell_phone || "—"}</td>
                    <td className="px-4 py-3 text-gray-600 truncate max-w-[200px]">{p.email || "—"}</td>
                    <td className="px-4 py-3 text-gray-600">{p.city || "—"}</td>
                    <td className="px-4 py-3 text-gray-600">{p.last_appt || "—"}</td>
                    <td className="px-4 py-3 tabular-nums">{p.total_visits}</td>
                    <td className="px-4 py-3"><ScoreBadge score={p.reengagement_score} /></td>
                    <td className="px-4 py-3"><TierBadge tier={p.tier} /></td>
                  </tr>
                ))}
                {data.patients.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
                      No patients found
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
