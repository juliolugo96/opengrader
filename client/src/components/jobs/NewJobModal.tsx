"use client";

import { AlertCircle, Loader2, Play, SlidersHorizontal } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import type { CreateJobInput } from "@/types/grader";

const initialForm: CreateJobInput = {
  assignmentPath: "assignments/hw1.yaml",
  submissionsDirectory: "submissions",
  workers: 4,
  retries: 1,
  submissionFilter: "",
  noDocker: false
};

export function NewJobModal({
  open,
  onClose,
  onSubmit,
  pending,
  serverError
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (input: CreateJobInput) => void;
  pending: boolean;
  serverError?: string;
}) {
  const [form, setForm] = useState<CreateJobInput>(initialForm);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextErrors = validate(form);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length === 0) onSubmit(form);
  };

  return (
    <Modal
      description="Paths are resolved on the machine running the OpenGrader API."
      onClose={onClose}
      open={open}
      title="Start a grading job"
    >
      <form className="space-y-5" onSubmit={submit}>
        <Field
          autoFocus
          error={errors.assignmentPath}
          label="Assignment YAML path"
          name="assignmentPath"
          onChange={(event) => setForm((current) => ({ ...current, assignmentPath: event.target.value }))}
          placeholder="assignments/hw1.yaml"
          value={form.assignmentPath}
        />
        <Field
          error={errors.submissionsDirectory}
          label="Submissions directory"
          name="submissionsDirectory"
          onChange={(event) => setForm((current) => ({ ...current, submissionsDirectory: event.target.value }))}
          placeholder="submissions/"
          value={form.submissionsDirectory}
        />

        <details className="rounded-xl border bg-muted/20 p-4">
          <summary className="flex cursor-pointer list-none items-center gap-2 text-sm font-medium">
            <SlidersHorizontal aria-hidden="true" className="size-4 text-muted-foreground" />
            Advanced controls
          </summary>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <Field
              error={errors.workers}
              label="Parallel workers"
              max={64}
              min={1}
              name="workers"
              onChange={(event) => setForm((current) => ({ ...current, workers: Number(event.target.value) }))}
              type="number"
              value={form.workers}
            />
            <Field
              error={errors.retries}
              label="Retries"
              max={10}
              min={0}
              name="retries"
              onChange={(event) => setForm((current) => ({ ...current, retries: Number(event.target.value) }))}
              type="number"
              value={form.retries}
            />
            <Field
              className="sm:col-span-2"
              hint="Optional case-sensitive shell pattern, for example section-a-*"
              label="Submission filter"
              name="submissionFilter"
              onChange={(event) => setForm((current) => ({ ...current, submissionFilter: event.target.value }))}
              placeholder="section-a-*"
              value={form.submissionFilter}
            />
            <label className="flex items-start gap-3 rounded-xl border bg-background/70 p-3 sm:col-span-2">
              <input
                checked={form.noDocker}
                className="mt-0.5 size-4 accent-[hsl(var(--primary))]"
                onChange={(event) => setForm((current) => ({ ...current, noDocker: event.target.checked }))}
                type="checkbox"
              />
              <span>
                <span className="block text-sm font-medium">Run without Docker</span>
                <span className="mt-1 block text-xs leading-5 text-danger">Trusted code only. Commands run with the API host user&apos;s permissions.</span>
              </span>
            </label>
          </div>
        </details>

        {serverError ? (
          <div className="flex gap-2 rounded-xl border border-danger/25 bg-danger/10 p-3 text-sm text-danger" role="alert">
            <AlertCircle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            {serverError}
          </div>
        ) : null}

        <div className="flex flex-col-reverse gap-3 pt-1 sm:flex-row sm:justify-end">
          <Button disabled={pending} onClick={onClose} variant="ghost">Cancel</Button>
          <Button disabled={pending} type="submit">
            {pending ? <Loader2 aria-hidden="true" className="size-4 animate-spin" /> : <Play aria-hidden="true" className="size-4" />}
            {pending ? "Enqueuing…" : "Start grading"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function validate(input: CreateJobInput): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!input.assignmentPath.trim()) errors.assignmentPath = "Enter an assignment YAML path.";
  if (!input.submissionsDirectory.trim()) errors.submissionsDirectory = "Enter a submissions directory.";
  if (!Number.isInteger(input.workers) || input.workers < 1 || input.workers > 64) {
    errors.workers = "Workers must be an integer from 1 to 64.";
  }
  if (!Number.isInteger(input.retries) || input.retries < 0 || input.retries > 10) {
    errors.retries = "Retries must be an integer from 0 to 10.";
  }
  return errors;
}
