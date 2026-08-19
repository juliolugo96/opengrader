"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, RefreshCw } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { PdfSubmissionTable } from "@/components/pdf/PdfSubmissionTable";
import { PdfUploadForm } from "@/components/pdf/PdfUploadForm";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { QueryError } from "@/components/ui/QueryError";
import { Skeleton } from "@/components/ui/Skeleton";
import { listAllPdfSubmissions, listAssignments, uploadPdfSubmission } from "@/lib/api-client";
import { useSettings } from "@/lib/use-settings";
import { useI18n } from "@/lib/i18n";

export default function PdfSubmissionsPage() {
  return <Suspense fallback={<Skeleton className="h-96" />}><PdfSubmissionsContent /></Suspense>;
}

function PdfSubmissionsContent() {
  const settings = useSettings();
  const { t } = useI18n();
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const initialAssignmentId = searchParams.get("assignment") ?? "";
  const submissions = useQuery({
    queryKey: ["pdf-submissions", settings.apiBaseUrl, Boolean(settings.apiKey)],
    queryFn: listAllPdfSubmissions,
    enabled: Boolean(settings.apiKey)
  });
  const assignments = useQuery({
    queryKey: ["assignments", settings.apiBaseUrl, Boolean(settings.apiKey)],
    queryFn: () => listAssignments(),
    enabled: Boolean(settings.apiKey),
    select: (items) => items.filter((assignment) => assignment.kind === "pdf")
  });
  const upload = useMutation({
    mutationFn: uploadPdfSubmission,
    onSuccess: async (submission) => {
      await queryClient.invalidateQueries({ queryKey: ["pdf-submissions"] });
      router.push(`/pdf/${submission.id}`);
    }
  });

  return (
    <div className="space-y-7">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="eyebrow">{t("pdf.eyebrow")}</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">{t("pdf.title")}</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{t("pdf.subtitle")}</p>
        </div>
        <Button aria-label={t("pdf.refresh")} disabled={!settings.apiKey || submissions.isFetching} onClick={() => submissions.refetch()} size="icon" variant="secondary">
          <RefreshCw aria-hidden="true" className={`size-4 ${submissions.isFetching ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {!settings.apiKey ? (
        <div className="panel"><EmptyState icon={<FileText className="size-5" />} title={t("pdf.connectTitle")} description={t("pdf.connectBody")} /></div>
      ) : (
        <PdfUploadForm assignments={assignments.data ?? []} initialAssignmentId={initialAssignmentId} onSubmit={(input) => upload.mutate(input)} pending={upload.isPending} serverError={upload.error?.message} />
      )}

      {settings.apiKey && submissions.isPending ? <Skeleton className="h-80" /> : null}
      {settings.apiKey && submissions.isError ? <div className="panel"><QueryError error={submissions.error} retry={() => submissions.refetch()} /></div> : null}
      {settings.apiKey && submissions.data ? <PdfSubmissionTable submissions={submissions.data} /> : null}
    </div>
  );
}
