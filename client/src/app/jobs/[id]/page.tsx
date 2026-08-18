"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, Download, FileJson, Loader2, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { JobStatusBadge } from "@/components/jobs/JobStatusBadge";
import { GradebookSummary } from "@/components/results/GradebookSummary";
import { GradebookTable } from "@/components/results/GradebookTable";
import { Button, buttonStyles } from "@/components/ui/Button";
import { QueryError } from "@/components/ui/QueryError";
import { Skeleton } from "@/components/ui/Skeleton";
import { getJob, getJobResult } from "@/lib/api-client";
import { buildResultsCsv, downloadText, formatDate, shortId } from "@/lib/utils";

export default function JobDetailPage() {
  const params = useParams<{ id: string }>();
  const jobId = params.id;
  const job = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "queued" || status === "running" ? 3_000 : false;
    }
  });
  const result = useQuery({
    queryKey: ["job-result", jobId],
    queryFn: () => getJobResult(jobId),
    enabled: job.data?.status === "succeeded"
  });

  if (job.isPending) return <DetailSkeleton />;
  if (job.isError) return <div className="panel"><QueryError error={job.error} retry={() => job.refetch()} /></div>;

  return (
    <div className="space-y-7">
      <div>
        <Link className={buttonStyles({ variant: "ghost", size: "sm", className: "-ml-3 mb-4" })} href="/jobs">
          <ArrowLeft aria-hidden="true" className="size-4" /> Back to jobs
        </Link>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <p className="eyebrow">Job {shortId(job.data.id)}</p>
              <JobStatusBadge status={job.data.status} />
            </div>
            <h1 className="mt-3 break-all font-mono text-2xl font-semibold tracking-tight sm:text-3xl">{job.data.request.assignment_file}</h1>
            <p className="mt-2 text-sm text-muted-foreground">Created {formatDate(job.data.created_at)} · {job.data.request.workers} workers · {job.data.request.retries} retries</p>
          </div>
          <Button aria-label="Refresh job" disabled={job.isFetching} onClick={() => job.refetch()} size="icon" variant="secondary">
            <RefreshCw aria-hidden="true" className={`size-4 ${job.isFetching ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {job.data.status === "queued" || job.data.status === "running" ? <ActiveBanner status={job.data.status} /> : null}
      {job.data.status === "failed" ? <FailurePanel error={job.data.error} /> : null}
      {job.data.status === "succeeded" && result.isPending ? <DetailSkeleton compact /> : null}
      {job.data.status === "succeeded" && result.isError ? <div className="panel"><QueryError error={result.error} retry={() => result.refetch()} /></div> : null}
      {job.data.status === "succeeded" && result.data ? (
        <>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="eyebrow">Completed gradebook</p>
              <p className="mt-1 text-sm text-muted-foreground">Runner: {result.data.result.runner} · generated {formatDate(result.data.result.generated_at)}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => downloadText(`${job.data.id}-results.json`, `${JSON.stringify(result.data, null, 2)}\n`, "application/json")} size="sm" variant="secondary">
                <FileJson aria-hidden="true" className="size-4" /> JSON
              </Button>
              <Button onClick={() => downloadText(`${job.data.id}-results.csv`, buildResultsCsv(result.data.result), "text/csv;charset=utf-8")} size="sm" variant="secondary">
                <Download aria-hidden="true" className="size-4" /> CSV
              </Button>
            </div>
          </div>
          <GradebookSummary job={job.data} result={result.data.result} statistics={result.data.statistics} />
          <GradebookTable students={result.data.result.submissions} />
        </>
      ) : null}
    </div>
  );
}

function ActiveBanner({ status }: { status: "queued" | "running" }) {
  return (
    <div className="panel flex items-center gap-4 border-sky-500/20 bg-sky-500/5 p-5" role="status">
      <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-sky-500/10 text-sky-600 dark:text-sky-400">
        <Loader2 aria-hidden="true" className="size-5 animate-spin" />
      </span>
      <div>
        <h2 className="font-semibold capitalize">Job {status}</h2>
        <p className="mt-1 text-sm text-muted-foreground">This page refreshes every three seconds. You can safely navigate away while the durable worker continues.</p>
      </div>
    </div>
  );
}

function FailurePanel({ error }: { error: string | null }) {
  return (
    <section className="panel overflow-hidden border-danger/25" role="alert">
      <div className="flex items-center gap-3 border-b border-danger/20 bg-danger/10 p-4 text-danger">
        <AlertTriangle aria-hidden="true" className="size-5" />
        <h2 className="font-semibold">Grading failed</h2>
      </div>
      <pre className="terminal-scrollbar max-h-96 overflow-auto whitespace-pre-wrap break-words bg-[#090d13] p-5 font-mono text-xs leading-6 text-red-300">{error ?? "The worker did not provide an error trace."}</pre>
    </section>
  );
}

function DetailSkeleton({ compact = false }: { compact?: boolean }) {
  return (
    <div aria-label="Loading job details" className="space-y-5">
      {!compact ? <><Skeleton className="h-5 w-24" /><Skeleton className="h-12 w-3/5" /></> : null}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }, (_, index) => <Skeleton className="h-24" key={index} />)}</div>
      <Skeleton className="h-96" />
    </div>
  );
}
