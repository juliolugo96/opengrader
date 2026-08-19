"use client";

import { Loader2, Play } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { useI18n } from "@/lib/i18n";
import type { AcademicAssignment, AssignmentLaunchInput } from "@/types/grader";

export function AssignmentRunModal({ assignment, onClose, onSubmit, pending, serverError }: {
  assignment: AcademicAssignment | null;
  onClose: () => void;
  onSubmit: (input: AssignmentLaunchInput) => void;
  pending: boolean;
  serverError?: string;
}) {
  const { t } = useI18n();
  const [submissionsDirectory, setSubmissionsDirectory] = useState("submissions");
  const [workers, setWorkers] = useState(1);
  const [retries, setRetries] = useState(0);
  const [noDocker, setNoDocker] = useState(false);
  const [error, setError] = useState<string>();

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!submissionsDirectory.trim()) {
      setError(t("assignments.required"));
      return;
    }
    setError(undefined);
    onSubmit({ submissionsDirectory: submissionsDirectory.trim(), workers, retries, submissionPatterns: [], noDocker });
  }

  return (
    <Modal description={assignment ? `${assignment.context.course_code} · ${assignment.context.section}` : undefined} onClose={onClose} open={Boolean(assignment)} title={t("assignments.runTitle", { name: assignment?.name ?? "" })}>
      <form className="space-y-5" onSubmit={submit}>
        <Field label={t("assignments.submissionsDirectory")} name="submissions-directory" onChange={(event) => setSubmissionsDirectory(event.target.value)} value={submissionsDirectory} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("assignments.workers")} max="64" min="1" name="workers" onChange={(event) => setWorkers(Number(event.target.value))} type="number" value={workers} />
          <Field label={t("assignments.retries")} max="10" min="0" name="retries" onChange={(event) => setRetries(Number(event.target.value))} type="number" value={retries} />
        </div>
        <label className="flex items-start gap-3 rounded-xl border bg-muted/20 p-3 text-sm"><input checked={noDocker} className="mt-0.5 accent-primary" onChange={(event) => setNoDocker(event.target.checked)} type="checkbox" /><span>{t("assignments.localMode")}</span></label>
        {error || serverError ? <p className="text-sm text-danger" role="alert">{error ?? serverError}</p> : null}
        <div className="flex justify-end gap-3 border-t pt-5"><Button onClick={onClose} variant="secondary">{t("common.cancel")}</Button><Button disabled={pending} type="submit">{pending ? <Loader2 aria-hidden="true" className="size-4 animate-spin" /> : <Play aria-hidden="true" className="size-4" />}{t("assignments.start")}</Button></div>
      </form>
    </Modal>
  );
}
