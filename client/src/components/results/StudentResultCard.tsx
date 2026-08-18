import { AlarmClock, CheckCircle2, CircleSlash2, RotateCcw, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { TerminalLogViewer } from "@/components/results/TerminalLogViewer";
import { cn, formatDuration, formatScore } from "@/lib/utils";
import type { StudentResult, TestExecution } from "@/types/grader";

export function StudentResultCard({ student }: { student: StudentResult }) {
  return (
    <div className="space-y-3 bg-muted/20 p-4 sm:p-5">
      {student.tests.map((test, index) => (
        <TestCard key={`${test.name}-${index}`} test={test} />
      ))}
    </div>
  );
}

function TestCard({ test }: { test: TestExecution }) {
  const Icon = test.timed_out ? AlarmClock : test.passed ? CheckCircle2 : test.points_earned > 0 ? CircleSlash2 : XCircle;
  return (
    <details className="group rounded-xl border bg-card open:shadow-sm">
      <summary className="flex cursor-pointer list-none flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <Icon
            aria-hidden="true"
            className={cn("size-5 shrink-0", test.passed ? "text-success" : test.points_earned > 0 ? "text-warning" : "text-danger")}
          />
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{test.name}</p>
            <p className="mt-1 truncate font-mono text-[0.68rem] text-muted-foreground">{test.command}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 pl-8 sm:pl-0">
          {test.attempts > 1 ? (
            <Badge className="border-border bg-muted text-muted-foreground">
              <RotateCcw aria-hidden="true" className="size-3" /> {test.attempts} attempts
            </Badge>
          ) : null}
          <span className="font-mono text-xs tabular-nums">{formatScore(test.points_earned, test.points_possible)}</span>
        </div>
      </summary>
      <div className="grid gap-4 border-t p-4">
        <dl className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
          <Meta label="Duration" value={formatDuration(test.duration_seconds)} />
          <Meta label="Exit code" value={test.exit_code === null ? "—" : String(test.exit_code)} />
          <Meta label="Timed out" value={test.timed_out ? "Yes" : "No"} />
          <Meta label="Status" value={test.status} />
        </dl>
        <div className="grid gap-3 xl:grid-cols-2">
          <TerminalLogViewer label="stdout" output={test.stdout} />
          <TerminalLogViewer label="stderr" output={test.stderr} />
        </div>
      </div>
    </details>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-muted/60 p-3">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="mt-1 font-mono font-medium capitalize">{value}</dd>
    </div>
  );
}
