"use client";

import { ArrowRight, ChevronLeft, ChevronRight, Search } from "lucide-react";
import Link from "next/link";
import { useDeferredValue, useMemo, useState } from "react";

import { JobStatusBadge } from "@/components/jobs/JobStatusBadge";
import { Button, buttonStyles } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { useI18n } from "@/lib/i18n";
import { formatDate, formatDuration, jobDuration, shortId } from "@/lib/utils";
import type { Job, JobStatus } from "@/types/grader";

const PAGE_SIZE = 10;

export function JobTable({ jobs }: { jobs: Job[] }) {
  const { t } = useI18n();
  const [status, setStatus] = useState<JobStatus | "all">("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const deferredSearch = useDeferredValue(search.trim().toLowerCase());

  const filtered = useMemo(
    () => jobs.filter((job) => {
      const matchesStatus = status === "all" || job.status === status;
      const matchesSearch = !deferredSearch || job.id.toLowerCase().includes(deferredSearch)
        || job.request.assignment_file.toLowerCase().includes(deferredSearch);
      return matchesStatus && matchesSearch;
    }),
    [deferredSearch, jobs, status]
  );
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const rows = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  return (
    <div className="panel overflow-hidden">
      <div className="flex flex-col gap-3 border-b p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-semibold">{t("jobs.recent")}</h2>
          <p className="mt-1 text-xs text-muted-foreground">{t("jobs.recentDetail")}</p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <label className="relative">
            <span className="sr-only">{t("jobs.search")}</span>
            <Search aria-hidden="true" className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <input
              className="h-10 w-full rounded-xl border bg-background pl-9 pr-3 text-sm sm:w-56"
              onChange={(event) => { setSearch(event.target.value); setPage(1); }}
              placeholder={t("jobs.searchPlaceholder")}
              value={search}
            />
          </label>
          <label>
            <span className="sr-only">{t("jobs.filter")}</span>
            <select
              className="h-10 w-full rounded-xl border bg-background px-3 text-sm sm:w-36"
              onChange={(event) => { setStatus(event.target.value as JobStatus | "all"); setPage(1); }}
              value={status}
            >
              <option value="all">{t("jobs.allStatuses")}</option>
              <option value="queued">{t("jobs.queued")}</option>
              <option value="running">{t("jobs.running")}</option>
              <option value="succeeded">{t("jobs.succeeded")}</option>
              <option value="failed">{t("jobs.failed")}</option>
            </select>
          </label>
        </div>
      </div>

      {rows.length === 0 ? (
        <EmptyState icon={<Search className="size-5" />} title={t("jobs.noMatch")} description={t("jobs.noMatchBody")} />
      ) : (
        <div className="overflow-x-auto">
          <table className="data-table min-w-[860px]">
            <thead>
              <tr>
                <th scope="col">{t("jobs.id")}</th>
                <th scope="col">{t("jobs.status")}</th>
                <th scope="col">{t("jobs.definition")}</th>
                <th scope="col">{t("jobs.created")}</th>
                <th scope="col">{t("jobs.duration")}</th>
                <th className="text-right" scope="col">{t("jobs.action")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((job) => (
                <tr key={job.id}>
                  <td><span className="font-mono text-xs font-semibold" title={job.id}>{shortId(job.id)}</span></td>
                  <td><JobStatusBadge status={job.status} /></td>
                  <td><span className="block max-w-72 truncate font-mono text-xs" title={job.request.assignment_file}>{job.request.assignment_file}</span></td>
                  <td className="whitespace-nowrap text-muted-foreground">{formatDate(job.created_at)}</td>
                  <td className="font-mono text-xs tabular-nums text-muted-foreground">{formatDuration(jobDuration(job))}</td>
                  <td className="text-right">
                    <Link aria-label={t("jobs.view", { id: shortId(job.id) })} className={buttonStyles({ variant: "ghost", size: "icon" })} href={`/jobs/${job.id}`}>
                      <ArrowRight aria-hidden="true" className="size-4" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex items-center justify-between border-t px-4 py-3 text-xs text-muted-foreground">
        <span>{t(filtered.length === 1 ? "jobs.countOne" : "jobs.count", { count: filtered.length })}</span>
        <div className="flex items-center gap-2">
          <span className="font-mono">{safePage} / {pageCount}</span>
          <Button aria-label={t("jobs.previous")} disabled={safePage <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))} size="icon" variant="ghost">
            <ChevronLeft aria-hidden="true" className="size-4" />
          </Button>
          <Button aria-label={t("jobs.next")} disabled={safePage >= pageCount} onClick={() => setPage((current) => Math.min(pageCount, current + 1))} size="icon" variant="ghost">
            <ChevronRight aria-hidden="true" className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
