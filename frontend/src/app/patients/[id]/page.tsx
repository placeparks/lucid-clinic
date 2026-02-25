"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getPatient } from "@/lib/api";
import type { Patient } from "@/lib/api";
import TierBadge from "@/components/TierBadge";
import ScoreBadge from "@/components/ScoreBadge";

function Field({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div>
      <dt className="text-xs text-gray-500 uppercase tracking-wider">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium">{value || "—"}</dd>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-lg font-semibold mb-4">{title}</h2>
      <dl className="grid grid-cols-2 md:grid-cols-3 gap-4">{children}</dl>
    </div>
  );
}

export default function PatientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (id) {
      getPatient(Number(id))
        .then(setPatient)
        .catch((e) => setError(e.message));
    }
  }, [id]);

  if (error) {
    return (
      <div className="max-w-4xl">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
          {error}
        </div>
      </div>
    );
  }

  if (!patient) {
    return (
      <div className="max-w-4xl">
        <p className="text-gray-400">Loading...</p>
      </div>
    );
  }

  const fmt = (n: number) =>
    n.toLocaleString("en-US", { style: "currency", currency: "USD" });

  return (
    <div className="max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link href="/patients" className="text-sm text-indigo-600 hover:text-indigo-800 mb-1 inline-block">
            &larr; Back to Patients
          </Link>
          <h1 className="text-2xl font-bold">
            {patient.first_name} {patient.last_name}
            {patient.suffix ? ` ${patient.suffix}` : ""}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Account #{patient.account_id}
            {patient.called_name && patient.called_name !== patient.first_name && (
              <span> &middot; Goes by &ldquo;{patient.called_name}&rdquo;</span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <ScoreBadge score={patient.reengagement_score} />
          <TierBadge tier={patient.tier} />
          {patient.is_dnc && (
            <span className="bg-red-100 text-red-700 px-2.5 py-1 rounded-full text-xs font-bold">
              DNC
            </span>
          )}
        </div>
      </div>

      {/* Contact */}
      <Section title="Contact Information">
        <Field label="Cell Phone" value={patient.cell_phone} />
        <Field label="Alt Phone" value={patient.alt_phone} />
        <Field label="Work Phone" value={patient.work_phone} />
        <Field label="Email" value={patient.email} />
        <Field label="Preferred Contact" value={patient.pref_contact} />
        <Field label="Address" value={
          [patient.address, patient.city, patient.state, patient.zip].filter(Boolean).join(", ")
        } />
      </Section>

      {/* Demographics */}
      <Section title="Demographics">
        <Field label="Sex" value={patient.sex} />
        <Field label="Date of Birth" value={patient.birthdate} />
        <Field label="Marital Status" value={patient.marital} />
        <Field label="Employment" value={patient.employment} />
        <Field label="Referred By" value={patient.ref_by} />
        <Field label="Account Created" value={patient.account_created} />
      </Section>

      {/* Visit History */}
      <Section title="Visit History">
        <Field label="Total Visits" value={patient.total_visits} />
        <Field label="Last Appointment" value={patient.last_appt} />
        <Field label="Re-engagement Score" value={patient.reengagement_score} />
      </Section>

      {/* Insurance */}
      <Section title="Insurance">
        <Field label="Carrier" value={patient.ins_carrier} />
        <Field label="Plan Type" value={patient.ins_plan_type} />
        <Field label="Group" value={patient.ins_group} />
        <Field label="Member ID" value={patient.ins_member_id} />
        <Field label="Code" value={patient.ins_code} />
        <Field label="Copay" value={patient.copay ? fmt(patient.copay) : null} />
      </Section>

      {/* Financial */}
      <Section title="Financial Summary">
        <Field label="Balance" value={fmt(patient.balance)} />
        <Field label="Patient Balance" value={fmt(patient.pat_balance)} />
        <Field label="Total Charges" value={fmt(patient.total_charges)} />
        <Field label="Total Receipts" value={fmt(patient.total_receipts)} />
      </Section>

      {/* Remarks */}
      {patient.remarks && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-2">Remarks</h2>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{patient.remarks}</p>
        </div>
      )}
    </div>
  );
}
