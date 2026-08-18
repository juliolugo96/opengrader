"use client";

import { FileUp, Loader2 } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import type { PdfUploadInput } from "@/types/grader";

export function PdfUploadForm({
  onSubmit,
  pending,
  serverError
}: {
  onSubmit: (input: PdfUploadInput) => void;
  pending: boolean;
  serverError?: string;
}) {
  const [studentId, setStudentId] = useState("");
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string>();

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!studentId.trim() || !title.trim()) {
      setError("Enter a student ID and assignment title.");
      return;
    }
    if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
      setError("Choose a .pdf file.");
      return;
    }
    setError(undefined);
    onSubmit({ file, studentId: studentId.trim(), title: title.trim() });
  }

  return (
    <Card className="p-5 sm:p-6">
      <div className="flex items-start gap-4">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <FileUp aria-hidden="true" className="size-5" />
        </span>
        <div>
          <p className="eyebrow">Secure ingestion</p>
          <h2 className="mt-1 text-lg font-semibold">Upload a PDF submission</h2>
          <p className="mt-1 text-sm text-muted-foreground">Documents are validated and stored under a generated server-side ID.</p>
        </div>
      </div>
      <form className="mt-6 grid gap-4 lg:grid-cols-[1fr_1.3fr_1.2fr_auto] lg:items-end" onSubmit={submit}>
        <Field label="Student ID" name="student-id" onChange={(event) => setStudentId(event.target.value)} value={studentId} />
        <Field label="Assignment title" name="assignment-title" onChange={(event) => setTitle(event.target.value)} value={title} />
        <Field
          accept="application/pdf,.pdf"
          label="PDF submission"
          name="pdf-submission"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          type="file"
        />
        <Button className="w-full lg:w-auto" disabled={pending} type="submit">
          {pending ? <Loader2 aria-hidden="true" className="size-4 animate-spin" /> : <FileUp aria-hidden="true" className="size-4" />}
          Upload PDF
        </Button>
      </form>
      {error || serverError ? <p className="mt-4 text-sm text-danger" role="alert">{error ?? serverError}</p> : null}
    </Card>
  );
}
