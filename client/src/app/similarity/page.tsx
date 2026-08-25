"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ScanSearch } from "lucide-react";
import { useState } from "react";

import { SimilarityWorkspace } from "@/components/similarity/SimilarityWorkspace";
import { EmptyState } from "@/components/ui/EmptyState";
import { QueryError } from "@/components/ui/QueryError";
import { Skeleton } from "@/components/ui/Skeleton";
import { createSimilarityJob, getSimilarityReport, listAllPdfSubmissions, listAssignments, listSimilarityJobs } from "@/lib/api-client";
import { useI18n } from "@/lib/i18n";
import { useSettings } from "@/lib/use-settings";

export default function SimilarityPage() {
  const { t } = useI18n();
  const settings = useSettings();
  const queryClient = useQueryClient();
  const [assignmentId, setAssignmentId] = useState("");
  const enabled = Boolean(settings.apiKey);
  const assignments = useQuery({ queryKey: ["assignments", settings.apiBaseUrl, enabled], queryFn: () => listAssignments(), enabled, select: (items) => items.filter((item) => item.kind === "pdf") });
  const submissions = useQuery({ queryKey: ["pdf-submissions", settings.apiBaseUrl, enabled], queryFn: listAllPdfSubmissions, enabled });
  const jobs = useQuery({ queryKey: ["similarity-jobs", settings.apiBaseUrl, assignmentId], queryFn: () => listSimilarityJobs(assignmentId || undefined), enabled, refetchInterval: (query) => query.state.data?.some((job) => job.status === "queued" || job.status === "running") ? 1000 : false });
  const latestSuccessful = jobs.data?.find((job) => job.status === "succeeded");
  const report = useQuery({ queryKey: ["similarity-report", latestSuccessful?.id], queryFn: () => getSimilarityReport(latestSuccessful!.id), enabled: Boolean(latestSuccessful) });
  const start = useMutation({ mutationFn: () => createSimilarityJob(assignmentId), onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["similarity-jobs"] }) });
  const counts = (submissions.data ?? []).reduce<Record<string, number>>((result, submission) => { if (submission.assignment_id) result[submission.assignment_id] = (result[submission.assignment_id] ?? 0) + 1; return result; }, {});
  const error = assignments.error ?? submissions.error ?? jobs.error ?? report.error ?? start.error;

  return <div className="space-y-7">
    <div><p className="eyebrow">{t("similarity.eyebrow")}</p><h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">{t("similarity.title")}</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{t("similarity.subtitle")}</p></div>
    {!enabled ? <div className="panel"><EmptyState icon={<ScanSearch className="size-5" />} title={t("similarity.connectTitle")} description={t("similarity.connectBody")} /></div> : null}
    {enabled && (assignments.isPending || submissions.isPending || jobs.isPending) ? <Skeleton className="h-80" /> : null}
    {enabled && error ? <div className="panel"><QueryError error={error} retry={() => { void Promise.all([assignments.refetch(), submissions.refetch(), jobs.refetch()]); }} /></div> : null}
    {enabled && assignments.data && submissions.data && jobs.data && !error ? <SimilarityWorkspace assignmentId={assignmentId} assignments={assignments.data} jobs={jobs.data} onAssignmentChange={setAssignmentId} onStart={() => start.mutate()} pending={start.isPending} report={report.data} submissionCounts={counts} /> : null}
  </div>;
}
