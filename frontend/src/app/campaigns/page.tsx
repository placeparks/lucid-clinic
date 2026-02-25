"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getCampaigns, getCommsStatus } from "@/lib/api";
import type { Campaign, CampaignList, CommsStatus } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  sending: "bg-blue-100 text-blue-800 animate-pulse",
  sent: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

const CHANNEL_STYLES: Record<string, string> = {
  sms: "bg-purple-100 text-purple-800",
  email: "bg-cyan-100 text-cyan-800",
};

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<CampaignList | null>(null);
  const [commsStatus, setCommsStatus] = useState<CommsStatus | null>(null);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");

  function load() {
    const params: Record<string, string> = {};
    if (statusFilter) params.status = statusFilter;
    if (channelFilter) params.channel = channelFilter;

    Promise.all([getCampaigns(params), getCommsStatus()])
      .then(([c, s]) => {
        setCampaigns(c);
        setCommsStatus(s);
      })
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, [statusFilter, channelFilter]);

  return (
    <div className="max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Campaigns</h1>
          <p className="text-sm text-gray-500 mt-1">SMS & email re-engagement campaigns</p>
        </div>
        <Link
          href="/campaigns/new"
          className="bg-indigo-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          + New Campaign
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm mb-4">
          {error}
        </div>
      )}

      {/* Comms Status Banner */}
      {commsStatus && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
          <div className="flex items-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-gray-500">Mode:</span>
              {commsStatus.mock_mode ? (
                <span className="text-yellow-600 font-medium">Mock</span>
              ) : (
                <span className="text-green-600 font-medium">Live</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-gray-500">Twilio:</span>
              {commsStatus.twilio_configured ? (
                <span className="text-green-600 font-medium">Configured</span>
              ) : (
                <span className="text-gray-400">Not configured</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-gray-500">Resend:</span>
              {commsStatus.resend_configured ? (
                <span className="text-green-600 font-medium">Configured</span>
              ) : (
                <span className="text-gray-400">Not configured</span>
              )}
            </div>
            {commsStatus.mock_mode && (
              <span className="text-xs text-yellow-600 ml-auto">
                Mock mode — no real messages sent. Set COMMS_MOCK_MODE=false to go live.
              </span>
            )}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-500">Status:</span>
          {["", "draft", "sending", "sent", "failed"].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                statusFilter === s
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {s || "All"}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 text-sm ml-4">
          <span className="text-gray-500">Channel:</span>
          {["", "sms", "email"].map((c) => (
            <button
              key={c}
              onClick={() => setChannelFilter(c)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                channelFilter === c
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {c ? c.toUpperCase() : "All"}
            </button>
          ))}
        </div>
      </div>

      {/* Campaign Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 bg-gray-50 border-b">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Channel</th>
              <th className="px-4 py-3 font-medium">Tier</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Recipients</th>
              <th className="px-4 py-3 font-medium">Sent</th>
              <th className="px-4 py-3 font-medium">Responded</th>
              <th className="px-4 py-3 font-medium">Booked</th>
              <th className="px-4 py-3 font-medium">Created</th>
            </tr>
          </thead>
          <tbody>
            {campaigns?.campaigns.map((c) => (
              <tr key={c.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3">
                  <Link
                    href={`/campaigns/${c.id}`}
                    className="text-indigo-600 hover:text-indigo-800 font-medium"
                  >
                    {c.name}
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${CHANNEL_STYLES[c.channel] || "bg-gray-100"}`}>
                    {c.channel.toUpperCase()}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600 capitalize">
                  {c.tier_filter || "All"}
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[c.status] || "bg-gray-100"}`}>
                    {c.status}
                  </span>
                </td>
                <td className="px-4 py-3 tabular-nums">{c.total_recipients}</td>
                <td className="px-4 py-3 tabular-nums">{c.sent_count}</td>
                <td className="px-4 py-3 tabular-nums">{c.responded_count}</td>
                <td className="px-4 py-3 tabular-nums">{c.booked_count}</td>
                <td className="px-4 py-3 text-gray-600">
                  {c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}
                </td>
              </tr>
            ))}
            {(!campaigns || campaigns.campaigns.length === 0) && (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-gray-400">
                  No campaigns yet. Create your first campaign to start re-engaging patients.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
