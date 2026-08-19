"use client";

import { CheckCircle2, CircleDashed, ClipboardList, XCircle } from "lucide-react";

import { Card } from "@/components/ui/Card";
import { useI18n } from "@/lib/i18n";
import type { Job } from "@/types/grader";

export function JobStatsCards({ jobs }: { jobs: Job[] }) {
  const { t } = useI18n();
  const counts = jobs.reduce(
    (totals, job) => {
      totals.total += 1;
      if (job.status === "queued" || job.status === "running") totals.active += 1;
      if (job.status === "succeeded") totals.succeeded += 1;
      if (job.status === "failed") totals.failed += 1;
      return totals;
    },
    { total: 0, active: 0, succeeded: 0, failed: 0 }
  );
  const items = [
    { label: t("jobs.total"), value: counts.total, icon: ClipboardList, color: "text-foreground", detail: t("jobs.totalDetail") },
    { label: t("jobs.progress"), value: counts.active, icon: CircleDashed, color: "text-sky-600 dark:text-sky-400", detail: t("jobs.progressDetail") },
    { label: t("jobs.succeeded"), value: counts.succeeded, icon: CheckCircle2, color: "text-success", detail: t("jobs.succeededDetail") },
    { label: t("jobs.failed"), value: counts.failed, icon: XCircle, color: "text-danger", detail: t("jobs.failedDetail") }
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <Card className="relative overflow-hidden p-5" key={item.label}>
            <div className="flex items-start justify-between">
              <div>
                <p className="eyebrow">{item.label}</p>
                <p className="mt-3 text-3xl font-semibold tracking-[-0.04em] tabular-nums">{item.value}</p>
                <p className="mt-1 text-xs text-muted-foreground">{item.detail}</p>
              </div>
              <span className={`flex size-10 items-center justify-center rounded-xl bg-muted ${item.color}`}>
                <Icon aria-hidden="true" className="size-[1.15rem]" strokeWidth={1.8} />
              </span>
            </div>
            <span className={`absolute inset-x-0 bottom-0 h-0.5 bg-current opacity-60 ${item.color}`} />
          </Card>
        );
      })}
    </div>
  );
}
