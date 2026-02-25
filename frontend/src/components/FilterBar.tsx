"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

const TIERS = ["", "active", "warm", "cool", "cold", "dormant"];

export default function FilterBar() {
  const router = useRouter();
  const params = useSearchParams();

  const push = useCallback(
    (key: string, value: string) => {
      const sp = new URLSearchParams(params.toString());
      if (value) sp.set(key, value);
      else sp.delete(key);
      sp.set("page", "1");
      router.push(`?${sp.toString()}`);
    },
    [params, router]
  );

  return (
    <div className="flex flex-wrap items-center gap-3">
      <input
        type="text"
        placeholder="Search name, email, phone..."
        defaultValue={params.get("search") || ""}
        onKeyDown={(e) => {
          if (e.key === "Enter") push("search", e.currentTarget.value);
        }}
        className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-indigo-500"
      />
      <select
        defaultValue={params.get("tier") || ""}
        onChange={(e) => push("tier", e.target.value)}
        className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
      >
        <option value="">All Tiers</option>
        {TIERS.filter(Boolean).map((t) => (
          <option key={t} value={t} className="capitalize">{t}</option>
        ))}
      </select>
      <label className="flex items-center gap-2 text-sm text-gray-600">
        <input
          type="checkbox"
          defaultChecked={params.get("has_insurance") === "true"}
          onChange={(e) => push("has_insurance", e.target.checked ? "true" : "")}
          className="rounded"
        />
        Has Insurance
      </label>
    </div>
  );
}
