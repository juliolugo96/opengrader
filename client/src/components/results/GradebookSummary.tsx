import { Clock3, Gauge, GraduationCap, Users } from "lucide-react";

import { Card } from "@/components/ui/Card";
import { formatDuration, gradebookMetrics, jobDuration } from "@/lib/utils";
import type { GradingResult, Job } from "@/types/grader";

export function GradebookSummary({ job, result }: { job: Job; result: GradingResult }) {
  const metrics = gradebookMetrics(result);
  const items = [
    { label: "Pass rate", value: `${metrics.passRate}%`, icon: GraduationCap },
    { label: "Average score", value: `${metrics.averagePercentage}%`, icon: Gauge },
    { label: "Students graded", value: String(metrics.studentCount), icon: Users },
    { label: "Execution time", value: formatDuration(jobDuration(job)), icon: Clock3 }
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
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
