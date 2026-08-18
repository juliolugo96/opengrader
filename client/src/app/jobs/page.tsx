"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ClipboardList, Plus, RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";

import { JobStatsCards } from "@/components/jobs/JobStatsCards";
import { JobTable } from "@/components/jobs/JobTable";
import { NewJobModal } from "@/components/jobs/NewJobModal";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { QueryError } from "@/components/ui/QueryError";
import { Skeleton } from "@/components/ui/Skeleton";
import { createJob, listJobs } from "@/lib/api-client";
import { useSettings } from "@/lib/use-settings";

export default function JobsPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const settings = useSettings();
  const router = useRouter();
  const queryClient = useQueryClient();
  const jobs = useQuery({
    queryKey: ["jobs", settings.apiBaseUrl, Boolean(settings.apiKey)],
    queryFn: () => listJobs({ limit: 100 }),
    enabled: Boolean(settings.apiKey),
    refetchInterval: (query) => query.state.data?.some((job) => job.status === "queued" || job.status === "running") ? 3_000 : false
  });
  const newJob = useMutation({
    mutationFn: createJob,
    onSuccess: async (job) => {
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
      setModalOpen(false);
      router.push(`/jobs/${job.id}`);
    }
  });
  const closeModal = useCallback(() => {
    setModalOpen(false);
    newJob.reset();
  }, [newJob]);

  return (
    <div className="space-y-7">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="eyebrow">MVP 4 · Operations</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">Grading jobs</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">Enqueue assignments, watch workers, and move from test output to actionable grades.</p>
        </div>
        <div className="flex gap-2">
          <Button aria-label="Refresh jobs" disabled={!settings.apiKey || jobs.isFetching} onClick={() => jobs.refetch()} size="icon" variant="secondary">
            <RefreshCw aria-hidden="true" className={`size-4 ${jobs.isFetching ? "animate-spin" : ""}`} />
          </Button>
          <Button disabled={!settings.apiKey} onClick={() => setModalOpen(true)}>
            <Plus aria-hidden="true" className="size-4" />
            New job
          </Button>
        </div>
      </div>

      {!settings.apiKey ? (
        <div className="panel">
          <EmptyState icon={<ClipboardList className="size-5" />} title="Connect OpenGrader to begin" description="Configure your API URL and bearer key. Job history will appear here once the connection is ready." />
        </div>
      ) : jobs.isPending ? (
        <JobsSkeleton />
      ) : jobs.isError ? (
        <div className="panel"><QueryError error={jobs.error} retry={() => jobs.refetch()} /></div>
      ) : (
        <>
          <JobStatsCards jobs={jobs.data} />
          <JobTable jobs={jobs.data} />
        </>
      )}

      <NewJobModal
        onClose={closeModal}
        onSubmit={(input) => newJob.mutate(input)}
        open={modalOpen}
        pending={newJob.isPending}
        serverError={newJob.error?.message}
      />
    </div>
  );
}

function JobsSkeleton() {
  return (
    <div aria-label="Loading jobs" className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => <Skeleton className="h-32" key={index} />)}
      </div>
      <Skeleton className="h-[32rem]" />
    </div>
  );
}
