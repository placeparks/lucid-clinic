"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createCampaign } from "@/lib/api";

const SMS_TEMPLATES = [
  "Hi {called_name}, it's been a while since your last visit to Lucid Clinic. We'd love to help you feel your best! Reply YES to schedule an appointment.",
  "Hey {called_name}! Dr. Nick's office here. We noticed it's been some time since your last adjustment. Ready to get back on track? Reply or call us!",
  "{called_name}, your spine health matters! Book a check-up at Lucid Clinic today. Reply YES or call to schedule.",
];

const EMAIL_TEMPLATES = [
  "Hi {called_name},\n\nWe hope you're doing well! It's been a while since your last visit to Lucid Clinic, and we wanted to check in.\n\nRegular chiropractic care can help you stay feeling your best. We'd love to see you again!\n\nClick here or call our office to schedule your next appointment.\n\nBest regards,\nLucid Clinic Team",
  "Dear {called_name},\n\nWe miss seeing you at Lucid Clinic! Your health and wellness are important to us.\n\nWhether you're dealing with back pain, neck stiffness, or just want a tune-up, we're here to help.\n\nSchedule your appointment today — we look forward to seeing you!\n\nWarm regards,\nDr. Nick & the Lucid Clinic Team",
];

export default function NewCampaignPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [channel, setChannel] = useState<"sms" | "email">("sms");
  const [tierFilter, setTierFilter] = useState("");
  const [scoreMin, setScoreMin] = useState(0);
  const [messageTemplate, setMessageTemplate] = useState(SMS_TEMPLATES[0]);
  const [subject, setSubject] = useState("We miss you at Lucid Clinic!");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function handleChannelChange(newChannel: "sms" | "email") {
    setChannel(newChannel);
    if (newChannel === "sms") {
      setMessageTemplate(SMS_TEMPLATES[0]);
    } else {
      setMessageTemplate(EMAIL_TEMPLATES[0]);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError("Campaign name is required");
      return;
    }
    if (!messageTemplate.trim()) {
      setError("Message template is required");
      return;
    }
    if (channel === "email" && !subject.trim()) {
      setError("Email subject is required");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const campaign = await createCampaign({
        name: name.trim(),
        channel,
        tier_filter: tierFilter || undefined,
        score_min: scoreMin,
        message_template: messageTemplate,
        subject: channel === "email" ? subject : undefined,
      });
      router.push(`/campaigns/${campaign.id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create campaign");
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "border border-gray-300 rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-indigo-500";

  // Render preview with sample data
  const previewText = messageTemplate
    .replace(/{first_name}/g, "John")
    .replace(/{called_name}/g, "Johnny")
    .replace(/{last_name}/g, "Smith");

  return (
    <div className="max-w-3xl">
      <Link href="/campaigns" className="text-sm text-indigo-600 hover:text-indigo-800 mb-1 inline-block">
        &larr; Back to Campaigns
      </Link>
      <h1 className="text-2xl font-bold mb-6">Create Campaign</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm mb-4">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Campaign Name */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Campaign Details</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-gray-500 uppercase mb-1">Campaign Name *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. February Warm Patient Outreach"
                className={inputClass}
              />
            </div>

            {/* Channel Toggle */}
            <div>
              <label className="block text-xs text-gray-500 uppercase mb-2">Channel *</label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => handleChannelChange("sms")}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    channel === "sms"
                      ? "bg-purple-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  SMS
                </button>
                <button
                  type="button"
                  onClick={() => handleChannelChange("email")}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    channel === "email"
                      ? "bg-cyan-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  Email
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Targeting */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Targeting</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 uppercase mb-1">Patient Tier</label>
              <select
                value={tierFilter}
                onChange={(e) => setTierFilter(e.target.value)}
                className={inputClass}
              >
                <option value="">All tiers</option>
                <option value="warm">Warm (6-12 months)</option>
                <option value="cool">Cool (1-2 years)</option>
                <option value="cold">Cold (2-5 years)</option>
                <option value="dormant">Dormant (5+ years)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 uppercase mb-1">Minimum Score</label>
              <input
                type="number"
                value={scoreMin}
                onChange={(e) => setScoreMin(Number(e.target.value))}
                min={0}
                max={100}
                className={inputClass}
              />
            </div>
          </div>
        </div>

        {/* Message Template */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Message</h2>
          <div className="space-y-4">
            {channel === "email" && (
              <div>
                <label className="block text-xs text-gray-500 uppercase mb-1">Subject Line *</label>
                <input
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="e.g. We miss you at Lucid Clinic!"
                  className={inputClass}
                />
              </div>
            )}

            <div>
              <label className="block text-xs text-gray-500 uppercase mb-1">Message Template *</label>
              <textarea
                value={messageTemplate}
                onChange={(e) => setMessageTemplate(e.target.value)}
                rows={channel === "email" ? 8 : 4}
                className={inputClass}
              />
              <p className="text-xs text-gray-400 mt-1">
                Available placeholders: <code className="bg-gray-100 px-1 rounded">{"{first_name}"}</code>{" "}
                <code className="bg-gray-100 px-1 rounded">{"{called_name}"}</code>{" "}
                <code className="bg-gray-100 px-1 rounded">{"{last_name}"}</code>
              </p>
            </div>

            {/* Quick Templates */}
            <div>
              <label className="block text-xs text-gray-500 uppercase mb-2">Quick Templates</label>
              <div className="flex gap-2 flex-wrap">
                {(channel === "sms" ? SMS_TEMPLATES : EMAIL_TEMPLATES).map((t, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setMessageTemplate(t)}
                    className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                      messageTemplate === t
                        ? "bg-indigo-100 text-indigo-700 border border-indigo-300"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200 border border-transparent"
                    }`}
                  >
                    Template {i + 1}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Preview */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-3">Preview</h2>
          <div className={`rounded-lg p-4 text-sm ${channel === "sms" ? "bg-purple-50" : "bg-cyan-50"}`}>
            {channel === "email" && (
              <p className="text-xs text-gray-500 mb-2">
                <strong>Subject:</strong> {subject}
              </p>
            )}
            <p className="whitespace-pre-wrap">{previewText}</p>
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Sample rendered with: John &quot;Johnny&quot; Smith
          </p>
        </div>

        {/* Submit */}
        <div className="flex items-center gap-4">
          <button
            type="submit"
            disabled={submitting}
            className="bg-indigo-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? "Creating..." : "Create Campaign"}
          </button>
          <span className="text-xs text-gray-400">
            Campaign will be created as a draft. You can review and send from the detail page.
          </span>
        </div>
      </form>
    </div>
  );
}
