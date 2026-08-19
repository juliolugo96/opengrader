"use client";

import { useQuery } from "@tanstack/react-query";
import { ClipboardList, Plus, RefreshCw } from "lucide-react";
import Link from "next/link";

import { JobStatsCards } from "@/components/jobs/JobStatsCards";
import { JobTable } from "@/components/jobs/JobTable";
import { Button, buttonStyles } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { QueryError } from "@/components/ui/QueryError";
import { Skeleton } from "@/components/ui/Skeleton";
import { listAllJobs } from "@/lib/api-client";
import { useSettings } from "@/lib/use-settings";
import { useI18n } from "@/lib/i18n";

export default function JobsPage() {
  const settings = useSettings();
  const { t } = useI18n();
  const jobs = useQuery({
    queryKey: ["jobs", settings.apiBaseUrl, Boolean(settings.apiKey)],
    queryFn: listAllJobs,
    enabled: Boolean(settings.apiKey),
    refetchInterval: (query) => query.state.data?.some((job) => job.status === "queued" || job.status === "running") ? 3_000 : false
  });

  return (
    <div className="space-y-7">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="eyebrow">{t("jobs.eyebrow")}</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">{t("jobs.title")}</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{t("jobs.subtitle")}</p>
        </div>
        <div className="flex gap-2">
          <Button aria-label="Refresh jobs" disabled={!settings.apiKey || jobs.isFetching} onClick={() => jobs.refetch()} size="icon" variant="secondary">
            <RefreshCw aria-hidden="true" className={`size-4 ${jobs.isFetching ? "animate-spin" : ""}`} />
          </Button>
          <Link aria-disabled={!settings.apiKey} className={buttonStyles({ className: !settings.apiKey ? "pointer-events-none opacity-50" : "" })} href="/assignments">
            <Plus aria-hidden="true" className="size-4" />
            {t("jobs.choose")}
          </Link>
        </div>
      </div>

      {!settings.apiKey ? (
        <div className="panel">
          <EmptyState icon={<ClipboardList className="size-5" />} title={t("jobs.connectTitle")} description={t("jobs.connectBody")} />
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
