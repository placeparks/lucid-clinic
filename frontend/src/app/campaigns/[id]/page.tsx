"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getCampaign,
  sendCampaign,
  getCampaignMessages,
} from "@/lib/api";
import type { Campaign, OutreachMessage, MessageList } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  sending: "bg-blue-100 text-blue-800 animate-pulse",
  sent: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

const MSG_STATUS_STYLES: Record<string, string> = {
  pending: "bg-gray-100 text-gray-600",
  sent: "bg-blue-100 text-blue-800",
  delivered: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  bounced: "bg-orange-100 text-orange-800",
  blocked: "bg-yellow-100 text-yellow-800",
};

export default function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [messages, setMessages] = useState<MessageList | null>(null);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const [msgPage, setMsgPage] = useState(1);
  const [msgStatusFilter, setMsgStatusFilter] = useState("");

  function load() {
    if (!id) return;
    const cid = Number(id);
    const msgParams: Record<string, string | number> = { page: msgPage, per_page: 25 };
    if (msgStatusFilter) msgParams.status = msgStatusFilter;

    Promise.all([getCampaign(cid), getCampaignMessages(cid, msgParams)])
      .then(([c, m]) => {
        setCampaign(c);
        setMessages(m);
      })
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
    // Auto-refresh if campaign is sending
    const interval = setInterval(() => {
      if (campaign?.status === "sending") load();
    }, 3000);
    return () => clearInterval(interval);
  }, [id, msgPage, msgStatusFilter]);

  async function handleSend() {
    if (!campaign) return;
    setSending(true);
    setError("");
    try {
      const updated = await sendCampaign(campaign.id);
      setCampaign(updated);
      load(); // Refresh messages
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to send campaign");
    } finally {
      setSending(false);
    }
  }

  if (!campaign) {
    return (
      <div className="max-w-5xl">
        <p className="text-gray-400">Loading campaign...</p>
      </div>
    );
  }

  const deliveryRate = campaign.sent_count > 0
    ? Math.round(((campaign.sent_count - campaign.failed_count) / campaign.sent_count) * 100)
    : 0;

  const responseRate = campaign.sent_count > 0
    ? Math.round((campaign.responded_count / campaign.sent_count) * 100)
    : 0;

  return (
    <div className="max-w-5xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link href="/campaigns" className="text-sm text-indigo-600 hover:text-indigo-800 mb-1 inline-block">
            &larr; Back to Campaigns
          </Link>
          <h1 className="text-2xl font-bold">{campaign.name}</h1>
          <p className="text-sm text-gray-500 mt-1">
            {campaign.channel.toUpperCase()} &middot;{" "}
            {campaign.tier_filter ? `${campaign.tier_filter} tier` : "All tiers"} &middot;{" "}
            Score {">="} {campaign.score_min}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${STATUS_STYLES[campaign.status] || "bg-gray-100"}`}>
            {campaign.status}
          </span>
          {campaign.status === "draft" && (
            <button
              onClick={handleSend}
              disabled={sending}
              className="bg-green-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              {sending ? "Sending..." : "Send Campaign"}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        {[
          { label: "Recipients", value: campaign.total_recipients, color: "text-gray-900" },
          { label: "Sent", value: campaign.sent_count, color: "text-blue-600" },
          { label: "Failed", value: campaign.failed_count, color: "text-red-600" },
          { label: "Responded", value: campaign.responded_count, color: "text-purple-600" },
          { label: "Booked", value: campaign.booked_count, color: "text-green-600" },
          { label: "Delivery Rate", value: `${deliveryRate}%`, color: "text-gray-900" },
        ].map((stat) => (
          <div key={stat.label} className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 uppercase">{stat.label}</p>
            <p className={`text-2xl font-bold tabular-nums ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Campaign Info */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold mb-3">Message Template</h2>
        {campaign.channel === "email" && campaign.subject && (
          <p className="text-sm text-gray-500 mb-2">
            <strong>Subject:</strong> {campaign.subject}
          </p>
        )}
        <div className={`rounded-lg p-4 text-sm whitespace-pre-wrap ${
          campaign.channel === "sms" ? "bg-purple-50" : "bg-cyan-50"
        }`}>
          {campaign.message_template}
        </div>
        <div className="flex items-center gap-4 mt-3 text-xs text-gray-400">
          <span>Created: {campaign.created_at ? new Date(campaign.created_at).toLocaleString() : "—"}</span>
          {campaign.sent_at && (
            <span>Sent: {new Date(campaign.sent_at).toLocaleString()}</span>
          )}
        </div>
      </div>

      {/* Message Log */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold">
            Message Log ({messages?.total || 0})
          </h2>
          <div className="flex items-center gap-2">
            {["", "sent", "delivered", "failed", "bounced"].map((s) => (
              <button
                key={s}
                onClick={() => { setMsgStatusFilter(s); setMsgPage(1); }}
                className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                  msgStatusFilter === s
                    ? "bg-indigo-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {s || "All"}
              </button>
            ))}
          </div>
        </div>

        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 bg-gray-50 border-b">
              <th className="px-4 py-3 font-medium">ID</th>
              <th className="px-4 py-3 font-medium">Recipient</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Sent</th>
              <th className="px-4 py-3 font-medium">Delivered</th>
              <th className="px-4 py-3 font-medium">Response</th>
              <th className="px-4 py-3 font-medium">Error</th>
            </tr>
          </thead>
          <tbody>
            {messages?.messages.map((msg) => (
              <tr key={msg.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-600">#{msg.id}</td>
                <td className="px-4 py-3 font-mono text-xs">{msg.recipient || "—"}</td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${MSG_STATUS_STYLES[msg.status] || "bg-gray-100"}`}>
                    {msg.status}
                    {msg.is_opt_out && " (OPT-OUT)"}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600 text-xs">
                  {msg.sent_at ? new Date(msg.sent_at).toLocaleString() : "—"}
                </td>
                <td className="px-4 py-3 text-gray-600 text-xs">
                  {msg.delivered_at ? new Date(msg.delivered_at).toLocaleString() : "—"}
                </td>
                <td className="px-4 py-3 text-xs">
                  {msg.response_text ? (
                    <span className="text-purple-700">{msg.response_text}</span>
                  ) : (
                    <span className="text-gray-300">—</span>
                  )}
                </td>
                <td className="px-4 py-3 text-xs text-red-500 max-w-[200px] truncate">
                  {msg.error_message || "—"}
                </td>
              </tr>
            ))}
            {(!messages || messages.messages.length === 0) && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                  {campaign.status === "draft"
                    ? "No messages yet. Send the campaign to start outreach."
                    : "No messages found."}
                </td>
              </tr>
            )}
          </tbody>
        </table>

        {/* Pagination */}
        {messages && messages.total > 25 && (
          <div className="px-4 py-3 border-t border-gray-200 flex items-center justify-between">
            <span className="text-xs text-gray-500">
              Showing {((msgPage - 1) * 25) + 1}–{Math.min(msgPage * 25, messages.total)} of {messages.total}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setMsgPage(Math.max(1, msgPage - 1))}
                disabled={msgPage <= 1}
                className="px-3 py-1 text-xs rounded border disabled:opacity-50"
              >
                Prev
              </button>
              <button
                onClick={() => setMsgPage(msgPage + 1)}
                disabled={msgPage * 25 >= messages.total}
                className="px-3 py-1 text-xs rounded border disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
