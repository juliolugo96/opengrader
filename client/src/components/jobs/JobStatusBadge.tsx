import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";
import type { JobStatus } from "@/types/grader";

const styles: Record<JobStatus, string> = {
  queued: "border-warning/25 bg-warning/10 text-warning",
  running: "border-sky-500/25 bg-sky-500/10 text-sky-600 dark:text-sky-400",
  succeeded: "border-success/25 bg-success/10 text-success",
  failed: "border-danger/25 bg-danger/10 text-danger"
};

export function JobStatusBadge({ status, className }: { status: JobStatus; className?: string }) {
  const active = status === "queued" || status === "running";
  return (
    <Badge className={cn("relative", styles[status], className)}>
      <span className="relative flex size-1.5">
        {active ? <span className="absolute inset-0 animate-pulse-ring rounded-full bg-current" /> : null}
        <span className="relative size-1.5 rounded-full bg-current" />
      </span>
      {status}
    </Badge>
  );
}
