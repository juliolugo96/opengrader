"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Download } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { PdfGradingWorkspace } from "@/components/pdf/PdfGradingWorkspace";
import { PdfPreview } from "@/components/pdf/PdfPreview";
import { Button, buttonStyles } from "@/components/ui/Button";
import { QueryError } from "@/components/ui/QueryError";
import { Skeleton } from "@/components/ui/Skeleton";
import { getPdfDocument, getPdfFeedback, getPdfSubmission, savePdfGrade } from "@/lib/api-client";
import { formatDate } from "@/lib/utils";

export default function PdfGradingPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const submission = useQuery({ queryKey: ["pdf-submission", id], queryFn: () => getPdfSubmission(id) });
  const pdfDocument = useQuery({ queryKey: ["pdf-document", id], queryFn: () => getPdfDocument(id) });
  const save = useMutation({
    mutationFn: (grade: Parameters<typeof savePdfGrade>[1]) => savePdfGrade(id, grade),
    onSuccess: (updated) => {
      queryClient.setQueryData(["pdf-submission", id], updated);
      void queryClient.invalidateQueries({ queryKey: ["pdf-submissions"] });
    }
  });

  if (submission.isPending) return <PdfDetailSkeleton />;
  if (submission.isError) return <div className="panel"><QueryError error={submission.error} retry={() => submission.refetch()} /></div>;

  async function downloadFeedback() {
    const blob = await getPdfFeedback(id);
    downloadBlob(`${id}-feedback.pdf`, blob);
  }

  return (
    <div className="space-y-6">
      <div>
        <Link className={buttonStyles({ variant: "ghost", size: "sm", className: "-ml-3 mb-4" })} href="/pdf"><ArrowLeft aria-hidden="true" className="size-4" /> Back to PDF grading</Link>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="eyebrow">{submission.data.status === "finalized" ? "Finalized" : "Draft"} · {submission.data.page_count} pages</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">{submission.data.title}</h1>
            <p className="mt-2 text-sm text-muted-foreground">{submission.data.student_id} · {submission.data.original_filename} · uploaded {formatDate(submission.data.created_at)}</p>
          </div>
          <Button disabled={!pdfDocument.data} onClick={() => pdfDocument.data ? downloadBlob(submission.data.original_filename, pdfDocument.data) : undefined} size="sm" variant="secondary"><Download aria-hidden="true" className="size-4" /> Original PDF</Button>
        </div>
      </div>

      {pdfDocument.isError ? <div className="panel"><QueryError error={pdfDocument.error} retry={() => pdfDocument.refetch()} /></div> : null}
      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(28rem,0.95fr)]">
        <section className="panel sticky top-5 p-3" aria-labelledby="document-preview-title">
          <h2 className="sr-only" id="document-preview-title">Document preview</h2>
          <PdfPreview blob={pdfDocument.data} title={submission.data.title} />
        </section>
        <PdfGradingWorkspace
          onDownload={() => void downloadFeedback()}
          onSave={(grade) => save.mutate(grade)}
          pending={save.isPending}
          serverError={save.error?.message}
          submission={submission.data}
        />
      </div>
    </div>
  );
}

function downloadBlob(filename: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function PdfDetailSkeleton() {
  return (
    <div aria-label="Loading PDF grading workspace" className="space-y-5">
      <Skeleton className="h-10 w-2/5" />
      <div className="grid gap-6 xl:grid-cols-2"><Skeleton className="h-[48rem]" /><Skeleton className="h-[48rem]" /></div>
    </div>
  );
}
