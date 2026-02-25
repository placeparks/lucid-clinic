"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getAgentSession,
  getSessionScreenshots,
  confirmAgentTask,
  cancelAgentTask,
  getScreenshotUrl,
} from "@/lib/api";
import type { AgentSession, Screenshot } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  running: "bg-blue-100 text-blue-800 animate-pulse",
  success: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  partial: "bg-yellow-100 text-yellow-800",
  cancelled: "bg-gray-100 text-gray-500",
  awaiting_confirmation: "bg-purple-100 text-purple-800",
};

export default function AgentSessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [session, setSession] = useState<AgentSession | null>(null);
  const [screenshots, setScreenshots] = useState<Screenshot[]>([]);
  const [error, setError] = useState("");
  const [acting, setActing] = useState(false);

  function load() {
    if (!id) return;
    const sid = Number(id);
    Promise.all([getAgentSession(sid), getSessionScreenshots(sid)])
      .then(([s, sc]) => {
        setSession(s);
        setScreenshots(sc);
      })
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [id]);

  async function handleConfirm() {
    if (!session) return;
    setActing(true);
    try {
      await confirmAgentTask(session.id);
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setActing(false);
    }
  }

  async function handleCancel() {
    if (!session) return;
    setActing(true);
    try {
      await cancelAgentTask(session.id);
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setActing(false);
    }
  }

  if (!session) {
    return (
      <div className="max-w-4xl">
        <p className="text-gray-400">Loading session...</p>
      </div>
    );
  }

  let params: Record<string, unknown> = {};
  try {
    params = JSON.parse(session.task_params || "{}");
  } catch { /* empty */ }

  let resultSummary: Record<string, unknown> = {};
  try {
    resultSummary = JSON.parse(session.result_summary || "{}");
  } catch { /* empty */ }

  return (
    <div className="max-w-5xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link href="/agent" className="text-sm text-indigo-600 hover:text-indigo-800 mb-1 inline-block">
            &larr; Back to Agent
          </Link>
          <h1 className="text-2xl font-bold">
            Session #{session.id}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {session.session_type} &middot;{" "}
            {session.started_at ? new Date(session.started_at).toLocaleString() : "—"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${STATUS_STYLES[session.status || ""] || "bg-gray-100"}`}>
            {session.status}
          </span>
          {session.status === "awaiting_confirmation" && (
            <button
              onClick={handleConfirm}
              disabled={acting}
              className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
            >
              Confirm & Run
            </button>
          )}
          {(session.status === "running" || session.status === "awaiting_confirmation") && (
            <button
              onClick={handleCancel}
              disabled={acting}
              className="bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50"
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Session Info */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold mb-4">Session Details</h2>
        <dl className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <dt className="text-xs text-gray-500 uppercase">Iterations</dt>
            <dd className="font-medium tabular-nums">{session.iterations_used}</dd>
          </div>
          <div>
            <dt className="text-xs text-gray-500 uppercase">Screenshots</dt>
            <dd className="font-medium tabular-nums">{session.screenshot_count}</dd>
          </div>
          <div>
            <dt className="text-xs text-gray-500 uppercase">Records Affected</dt>
            <dd className="font-medium tabular-nums">{session.records_affected}</dd>
          </div>
          <div>
            <dt className="text-xs text-gray-500 uppercase">Duration</dt>
            <dd className="font-medium tabular-nums">
              {session.started_at && session.ended_at
                ? `${Math.round((new Date(session.ended_at).getTime() - new Date(session.started_at).getTime()) / 1000)}s`
                : session.status === "running" ? "In progress..." : "—"
              }
            </dd>
          </div>
        </dl>
      </div>

      {/* Task Parameters */}
      {Object.keys(params).length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-3">Task Parameters</h2>
          <pre className="bg-gray-50 rounded-lg p-4 text-sm overflow-x-auto">
            {JSON.stringify(params, null, 2)}
          </pre>
        </div>
      )}

      {/* Result Summary */}
      {Object.keys(resultSummary).length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-3">Result</h2>
          <pre className="bg-gray-50 rounded-lg p-4 text-sm overflow-x-auto">
            {JSON.stringify(resultSummary, null, 2)}
          </pre>
        </div>
      )}

      {/* Error Log */}
      {session.error_log && (
        <div className="bg-red-50 rounded-xl border border-red-200 p-6">
          <h2 className="text-lg font-semibold mb-3 text-red-700">Error</h2>
          <pre className="text-sm text-red-600 whitespace-pre-wrap">{session.error_log}</pre>
        </div>
      )}

      {/* Screenshot Gallery */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold mb-4">
          Screenshots ({screenshots.length})
        </h2>
        {screenshots.length === 0 ? (
          <p className="text-gray-400 text-sm">No screenshots captured yet.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {screenshots.map((sc) => (
              <div key={sc.filename} className="border border-gray-200 rounded-lg overflow-hidden">
                <img
                  src={getScreenshotUrl(session.id, sc.filename)}
                  alt={`Step ${sc.step}: ${sc.action}`}
                  className="w-full"
                  loading="lazy"
                />
                <div className="px-3 py-2 bg-gray-50 flex items-center justify-between text-xs text-gray-500">
                  <span>Step {sc.step}: {sc.action}</span>
                  <span>{Math.round(sc.size_bytes / 1024)}KB</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
