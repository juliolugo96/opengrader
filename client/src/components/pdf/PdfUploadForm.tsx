"use client";

import { FileUp, Loader2 } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { useI18n } from "@/lib/i18n";
import type { AcademicAssignment, PdfUploadInput } from "@/types/grader";

const noAssignments: AcademicAssignment[] = [];

export function PdfUploadForm({
  onSubmit,
  pending,
  serverError,
  assignments = noAssignments,
  initialAssignmentId = ""
}: {
  onSubmit: (input: PdfUploadInput) => void;
  pending: boolean;
  serverError?: string;
  assignments?: AcademicAssignment[];
  initialAssignmentId?: string;
}) {
  const { t } = useI18n();
  const [studentId, setStudentId] = useState("");
  const [assignmentId, setAssignmentId] = useState(initialAssignmentId);
  const [title, setTitle] = useState(() => assignments.find((assignment) => assignment.id === initialAssignmentId)?.name ?? "");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string>();

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!studentId.trim() || !title.trim()) {
      setError(t("pdf.required"));
      return;
    }
    if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
      setError(t("pdf.choose"));
      return;
    }
    setError(undefined);
    onSubmit({ file, studentId: studentId.trim(), title: title.trim(), ...(assignmentId ? { assignmentId } : {}) });
  }

  return (
    <Card className="p-5 sm:p-6">
      <div className="flex items-start gap-4">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <FileUp aria-hidden="true" className="size-5" />
        </span>
        <div>
          <p className="eyebrow">{t("pdf.secure")}</p>
          <h2 className="mt-1 text-lg font-semibold">{t("pdf.uploadTitle")}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{t("pdf.uploadBody")}</p>
        </div>
      </div>
      <form className="mt-6 grid gap-4 lg:grid-cols-[1fr_1.3fr_1.2fr_auto] lg:items-end" onSubmit={submit}>
        {assignments.length ? (
          <label className="block space-y-2 lg:col-span-4">
            <span className="text-sm font-medium">{t("pdf.assignment")}</span>
            <select aria-label={t("pdf.assignment")} className="h-11 w-full rounded-xl border bg-background px-3 text-sm" onChange={(event) => {
              const nextId = event.target.value;
              setAssignmentId(nextId);
              const selected = assignments.find((assignment) => assignment.id === nextId);
              if (selected) setTitle(selected.name);
            }} value={assignmentId}>
              <option value="">{t("pdf.noAssignment")}</option>
              {assignments.map((assignment) => <option key={assignment.id} value={assignment.id}>{assignment.context.course_code} · {assignment.context.section} · {assignment.name}</option>)}
            </select>
          </label>
        ) : null}
        <Field label={t("pdf.student")} name="student-id" onChange={(event) => setStudentId(event.target.value)} value={studentId} />
        <Field label={t("pdf.assignmentTitle")} name="assignment-title" onChange={(event) => setTitle(event.target.value)} value={title} />
        <Field
          accept="application/pdf,.pdf"
          label={t("pdf.file")}
          name="pdf-submission"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          type="file"
        />
        <Button className="w-full lg:w-auto" disabled={pending} type="submit">
          {pending ? <Loader2 aria-hidden="true" className="size-4 animate-spin" /> : <FileUp aria-hidden="true" className="size-4" />}
          {t("pdf.upload")}
        </Button>
      </form>
      {error || serverError ? <p className="mt-4 text-sm text-danger" role="alert">{error ?? serverError}</p> : null}
    </Card>
  );
}
