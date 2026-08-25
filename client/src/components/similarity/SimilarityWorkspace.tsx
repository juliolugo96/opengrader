"use client";

import { AlertTriangle, FileSearch, Play, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useI18n } from "@/lib/i18n";
import type { AcademicAssignment, SimilarityJob, SimilarityReport } from "@/types/grader";

interface SimilarityWorkspaceProps {
  assignments: AcademicAssignment[];
  assignmentId: string;
  submissionCounts: Record<string, number>;
  jobs: SimilarityJob[];
  report?: SimilarityReport;
  pending: boolean;
  onAssignmentChange: (assignmentId: string) => void;
  onStart: () => void;
}

const selectClass = "h-11 w-full rounded-xl border bg-background/70 px-3 text-sm shadow-sm transition hover:border-muted-foreground/40 focus:border-primary";

const statusKeys = {
  queued: "similarity.status.queued",
  running: "similarity.status.running",
  succeeded: "similarity.status.succeeded",
  failed: "similarity.status.failed"
} as const;

export function SimilarityWorkspace({ assignments, assignmentId, submissionCounts, jobs, report, pending, onAssignmentChange, onStart }: SimilarityWorkspaceProps) {
  const { t } = useI18n();
  const selectedCount = assignmentId ? submissionCounts[assignmentId] ?? 0 : 0;
  const active = jobs.some((job) => job.status === "queued" || job.status === "running");

  return (
    <div className="space-y-6">
      <section className="panel p-5 sm:p-6">
        <div className="flex items-start gap-4">
          <span className="rounded-xl bg-primary/10 p-3 text-primary"><ShieldCheck aria-hidden="true" className="size-5" /></span>
          <div>
            <h2 className="text-lg font-semibold">{t("similarity.humanTitle")}</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{t("similarity.humanBody")}</p>
          </div>
        </div>
      </section>

      <section className="panel p-5 sm:p-6">
        <p className="eyebrow">{t("similarity.scope")}</p>
        <h2 className="mt-2 text-xl font-semibold">{t("similarity.startTitle")}</h2>
        <div className="mt-5 grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
          <label className="space-y-2">
            <span className="text-sm font-medium">{t("similarity.assignment")}</span>
            <select aria-label={t("similarity.assignment")} className={selectClass} onChange={(event) => onAssignmentChange(event.target.value)} value={assignmentId}>
              <option value="">{t("similarity.choose")}</option>
              {assignments.map((assignment) => <option key={assignment.id} value={assignment.id}>{assignment.context.course_code} · {assignment.name} · {t("similarity.submissionCount", { count: submissionCounts[assignment.id] ?? 0 })}</option>)}
            </select>
          </label>
          <Button disabled={!assignmentId || selectedCount < 2 || pending || active} onClick={onStart}><Play aria-hidden="true" className="size-4" />{active ? t("similarity.active") : t("similarity.start")}</Button>
        </div>
        {assignmentId && selectedCount < 2 ? <p className="mt-3 text-sm text-warning" role="status">{t("similarity.needTwo")}</p> : null}
      </section>

      {jobs.length ? <section className="panel p-5 sm:p-6" aria-live="polite">
        <p className="eyebrow">{t("similarity.history")}</p>
        <div className="mt-4 space-y-3">{jobs.map((job) => <article className="flex flex-col gap-3 rounded-xl border bg-background/45 p-4 sm:flex-row sm:items-center sm:justify-between" key={job.id}><div><p className="font-mono text-xs">{job.id}</p><p className="mt-1 text-xs text-muted-foreground">{t("similarity.submissionCount", { count: job.submission_count })} · {new Date(job.created_at).toLocaleString()}</p>{job.error ? <p className="mt-2 text-xs text-danger">{job.error}</p> : null}</div><Badge className={job.status === "succeeded" ? "border-success/30 text-success" : job.status === "failed" ? "border-danger/30 text-danger" : "border-warning/30 text-warning"}>{t(statusKeys[job.status])}</Badge></article>)}</div>
      </section> : null}

      {report ? <section className="panel p-5 sm:p-6">
        <div className="flex items-start gap-4"><span className="rounded-xl bg-warning/10 p-3 text-warning"><FileSearch aria-hidden="true" className="size-5" /></span><div><p className="eyebrow">{t("similarity.report")}</p><h2 className="mt-2 text-xl font-semibold">{t("similarity.findings", { count: report.matches.length })}</h2><p className="mt-2 text-sm text-muted-foreground">{t("similarity.reportMeta", { documents: report.corpus_size, pairs: report.candidate_pairs_evaluated })}</p></div></div>
        <div className="mt-5 space-y-4">{report.matches.length ? report.matches.map((match) => <article className="rounded-2xl border bg-background/45 p-5" key={`${match.left_submission_id}-${match.right_submission_id}`}>
          <div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-semibold">{match.left_student_id} ↔ {match.right_student_id}</h3><p className="mt-1 text-xs text-muted-foreground">{t("similarity.score", { score: Math.round(match.score * 100) })} · {t("similarity.shared", { count: match.shared_fingerprints })}</p></div><Badge className={match.band === "high_signal" ? "border-warning/30 text-warning" : "border-primary/30 text-primary"}>{t(match.band === "high_signal" ? "similarity.band.high_signal" : "similarity.band.review")}</Badge></div>
          <div className="mt-4 space-y-3">{match.evidence.map((evidence) => <div className="grid gap-2 rounded-xl border p-3 text-xs leading-5 text-muted-foreground md:grid-cols-2" key={evidence.fingerprint}><p><span className="mb-1 block font-semibold text-foreground">{match.left_student_id}</span>{evidence.left_excerpt}</p><p><span className="mb-1 block font-semibold text-foreground">{match.right_student_id}</span>{evidence.right_excerpt}</p></div>)}</div>
        </article>) : <p className="rounded-xl border border-dashed p-5 text-sm text-muted-foreground">{t("similarity.none")}</p>}</div>
        {report.warnings.map((warning) => <p className="mt-4 flex items-start gap-2 text-xs text-warning" key={warning}><AlertTriangle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />{warning}</p>)}
        <p className="mt-5 rounded-xl bg-muted/60 p-4 text-xs leading-5 text-muted-foreground">{report.disclaimer}</p>
      </section> : null}
    </div>
  );
}
