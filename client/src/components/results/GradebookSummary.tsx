import { Clock3, Gauge, GraduationCap, Users } from "lucide-react";

import { Card } from "@/components/ui/Card";
import { formatDuration, gradebookMetrics, jobDuration } from "@/lib/utils";
import type { GradingResult, Job, ResultStatistics } from "@/types/grader";

export function GradebookSummary({ job, result, statistics }: { job: Job; result: GradingResult; statistics: ResultStatistics }) {
  const metrics = gradebookMetrics(result);
  const items = [
    { label: "Pass rate", value: `${metrics.passRate}%`, detail: undefined, icon: GraduationCap },
    {
      label: "Average score",
      value: `${metrics.averagePercentage}%`,
      detail: `${statistics.total_score} / ${statistics.maximum_points} cohort points`,
      icon: Gauge
    },
    { label: "Students graded", value: String(statistics.student_count), detail: undefined, icon: Users },
    { label: "Execution time", value: formatDuration(jobDuration(job)), detail: undefined, icon: Clock3 }
  ];

  return (
    <div className="grid gap-px overflow-hidden rounded-2xl border bg-border sm:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <Card className="rounded-none border-0 p-5 shadow-none" key={item.label}>
            <div className="flex items-center gap-3">
              <span className="flex size-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Icon aria-hidden="true" className="size-4" />
              </span>
              <div>
                <p className="text-xs text-muted-foreground">{item.label}</p>
                <p className="mt-0.5 text-xl font-semibold tracking-tight tabular-nums">{item.value}</p>
                {item.detail ? <p className="mt-1 text-[0.68rem] text-muted-foreground">{item.detail}</p> : null}
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
