"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getAgentStatus,
  getAgentSessions,
  submitAgentTask,
} from "@/lib/api";
import type { AgentStatus, AgentSessionList } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  running: "bg-blue-100 text-blue-800 animate-pulse",
  success: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  partial: "bg-yellow-100 text-yellow-800",
  cancelled: "bg-gray-100 text-gray-500",
  awaiting_confirmation: "bg-purple-100 text-purple-800",
  pending: "bg-gray-100 text-gray-600",
};

const TASK_LABELS: Record<string, string> = {
  sync_patients: "Sync Patients",
  book_appointment: "Book Appointment",
  update_record: "Update Record",
};

function formatDuration(start: string | null, end: string | null): string {
  if (!start) return "—";
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  const sec = Math.round((e - s) / 1000);
  if (sec < 60) return `${sec}s`;
  return `${Math.floor(sec / 60)}m ${sec % 60}s`;
}

export default function AgentPage() {
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [sessions, setSessions] = useState<AgentSessionList | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [selectedTask, setSelectedTask] = useState("sync_patients");

  // Task-specific form fields
  const [accountId, setAccountId] = useState("");
  const [apptDate, setApptDate] = useState("");
  const [apptTime, setApptTime] = useState("");
  const [provider, setProvider] = useState("");
  const [updateEmail, setUpdateEmail] = useState("");
  const [updatePhone, setUpdatePhone] = useState("");
  const [updateAddress, setUpdateAddress] = useState("");

  function load() {
    Promise.all([getAgentStatus(), getAgentSessions({ per_page: 20 })])
      .then(([s, sess]) => {
        setStatus(s);
        setSessions(sess);
      })
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  function buildParams(): Record<string, unknown> {
    if (selectedTask === "sync_patients") {
      return {};
    }
    if (selectedTask === "book_appointment") {
      return {
        patient_account_id: accountId,
        date: apptDate,
        time: apptTime || undefined,
        provider: provider || undefined,
      };
    }
    if (selectedTask === "update_record") {
      const fields: Record<string, string> = {};
      if (updateEmail.trim()) fields.email = updateEmail.trim();
      if (updatePhone.trim()) fields.cell_phone = updatePhone.trim();
      if (updateAddress.trim()) fields.address = updateAddress.trim();
      return {
        patient_account_id: accountId,
        fields,
      };
    }
    return {};
  }

  async function handleSubmit() {
    setSubmitting(true);
    setError("");
    try {
      const params = buildParams();
      // sync_patients is read-only so auto-confirm; others need explicit confirmation
      const autoConfirm = selectedTask === "sync_patients";
      await submitAgentTask(selectedTask, params, autoConfirm);
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to submit task");
    } finally {
      setSubmitting(false);
    }
  }

  const inputClass =
    "border border-gray-300 rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-indigo-500";

  return (
    <div className="max-w-6xl">
      <h1 className="text-2xl font-bold mb-6">Agent Control</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm mb-4">
          {error}
        </div>
      )}

      {/* Agent Status */}
      {status && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">System Status</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-xs text-gray-500 uppercase">Mode</p>
              <p className="font-medium">
                {status.mock_mode ? (
                  <span className="text-yellow-600">Mock</span>
                ) : (
                  <span className="text-green-600">Live</span>
                )}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase">VNC</p>
              <p className="font-medium">
                {status.vnc_configured ? (
                  <span className="text-green-600">Configured</span>
                ) : (
                  <span className="text-gray-400">Not configured</span>
                )}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase">API Key</p>
              <p className="font-medium">
                {status.api_key_configured ? (
                  <span className="text-green-600">Set</span>
                ) : (
                  <span className="text-gray-400">Not set</span>
                )}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase">Running</p>
              <p className="font-medium">
                {status.running_session_id ? (
                  <Link href={`/agent/${status.running_session_id}`} className="text-blue-600">
                    Session #{status.running_session_id}
                  </Link>
                ) : (
                  <span className="text-gray-400">Idle</span>
                )}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Submit Task */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Run Agent Task</h2>

        <div className="space-y-4">
          {/* Task type selector */}
          <div>
            <label className="block text-xs text-gray-500 uppercase mb-1">Task Type</label>
            <select
              value={selectedTask}
              onChange={(e) => setSelectedTask(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {status?.available_tasks.map((t) => (
                <option key={t} value={t}>
                  {TASK_LABELS[t] || t}
                </option>
              )) || (
                <>
                  <option value="sync_patients">Sync Patients</option>
                  <option value="book_appointment">Book Appointment</option>
                  <option value="update_record">Update Record</option>
                </>
              )}
            </select>
          </div>

          {/* Book Appointment fields */}
          {selectedTask === "book_appointment" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-4 bg-gray-50 rounded-lg">
              <div>
                <label className="block text-xs text-gray-500 uppercase mb-1">Patient Account ID *</label>
                <input
                  type="text"
                  value={accountId}
                  onChange={(e) => setAccountId(e.target.value)}
                  placeholder="e.g. 6211C"
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 uppercase mb-1">Date *</label>
                <input
                  type="date"
                  value={apptDate}
                  onChange={(e) => setApptDate(e.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 uppercase mb-1">Time (optional)</label>
                <input
                  type="time"
                  value={apptTime}
                  onChange={(e) => setApptTime(e.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 uppercase mb-1">Provider (optional)</label>
                <input
                  type="text"
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  placeholder="e.g. Dr. Smith"
                  className={inputClass}
                />
              </div>
            </div>
          )}

          {/* Update Record fields */}
          {selectedTask === "update_record" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-4 bg-gray-50 rounded-lg">
              <div className="md:col-span-2">
                <label className="block text-xs text-gray-500 uppercase mb-1">Patient Account ID *</label>
                <input
                  type="text"
                  value={accountId}
                  onChange={(e) => setAccountId(e.target.value)}
                  placeholder="e.g. 6211C"
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 uppercase mb-1">New Email</label>
                <input
                  type="email"
                  value={updateEmail}
                  onChange={(e) => setUpdateEmail(e.target.value)}
                  placeholder="patient@email.com"
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 uppercase mb-1">New Phone</label>
                <input
                  type="tel"
                  value={updatePhone}
                  onChange={(e) => setUpdatePhone(e.target.value)}
                  placeholder="(555) 123-4567"
                  className={inputClass}
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-xs text-gray-500 uppercase mb-1">New Address</label>
                <input
                  type="text"
                  value={updateAddress}
                  onChange={(e) => setUpdateAddress(e.target.value)}
                  placeholder="123 Main St"
                  className={inputClass}
                />
              </div>
              <p className="md:col-span-2 text-xs text-gray-400">Fill in only the fields you want to update. Leave others blank.</p>
            </div>
          )}

          {/* Sync Patients — no extra fields */}
          {selectedTask === "sync_patients" && (
            <p className="text-sm text-gray-500 p-4 bg-gray-50 rounded-lg">
              Read-only sync from EZBIS Survey Generator. No parameters needed.
            </p>
          )}

          {/* Submit button */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleSubmit}
              disabled={submitting || !!status?.running_session_id}
              className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {submitting ? "Submitting..." : selectedTask === "sync_patients" ? "Run Sync" : "Submit Task"}
            </button>
            {status?.running_session_id && (
              <span className="text-sm text-yellow-600">A task is already running</span>
            )}
            {selectedTask !== "sync_patients" && (
              <span className="text-xs text-gray-400">Write operations require confirmation before execution</span>
            )}
          </div>
        </div>

        {status?.mock_mode && (
          <p className="text-xs text-yellow-600 mt-3">
            Running in mock mode — no real VNC connection. Set AGENT_MOCK_MODE=false to connect to EZBIS.
          </p>
        )}
      </div>

      {/* Session History */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">Session History</h2>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 bg-gray-50 border-b">
              <th className="px-4 py-3 font-medium">ID</th>
              <th className="px-4 py-3 font-medium">Task</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Started</th>
              <th className="px-4 py-3 font-medium">Duration</th>
              <th className="px-4 py-3 font-medium">Steps</th>
              <th className="px-4 py-3 font-medium">Screenshots</th>
              <th className="px-4 py-3 font-medium">Records</th>
            </tr>
          </thead>
          <tbody>
            {sessions?.sessions.map((s) => (
              <tr key={s.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3">
                  <Link href={`/agent/${s.id}`} className="text-indigo-600 hover:text-indigo-800 font-medium">
                    #{s.id}
                  </Link>
                </td>
                <td className="px-4 py-3">{TASK_LABELS[s.session_type || ""] || s.session_type}</td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[s.status || ""] || "bg-gray-100"}`}>
                    {s.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {s.started_at ? new Date(s.started_at).toLocaleString() : "—"}
                </td>
                <td className="px-4 py-3 tabular-nums">
                  {formatDuration(s.started_at, s.ended_at)}
                </td>
                <td className="px-4 py-3 tabular-nums">{s.iterations_used}</td>
                <td className="px-4 py-3 tabular-nums">{s.screenshot_count}</td>
                <td className="px-4 py-3 tabular-nums">{s.records_affected}</td>
              </tr>
            ))}
            {(!sessions || sessions.sessions.length === 0) && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
                  No agent sessions yet. Run a task above to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
