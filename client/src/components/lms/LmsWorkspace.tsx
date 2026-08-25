"use client";

import { ArrowDownToLine, CheckCircle2, Link2, RefreshCw, Send, ShieldCheck } from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { useI18n } from "@/lib/i18n";
import type {
  AcademicAssignment,
  AcademicContext,
  GradeSyncInput,
  GradeSyncReport,
  LmsAssignmentImportInput,
  LmsAssignmentLink,
  LmsAssignmentLinkInput,
  LmsConnectionStatus,
  LmsCourse,
  LmsRemoteAssignment,
  StudentIdType
} from "@/types/grader";

interface LmsWorkspaceProps {
  status: LmsConnectionStatus;
  courses: LmsCourse[];
  assignments: LmsRemoteAssignment[];
  localAssignments: AcademicAssignment[];
  links: LmsAssignmentLink[];
  pending: boolean;
  report?: GradeSyncReport;
  onSelectCourse: (courseId: string) => void;
  onImport: (input: LmsAssignmentImportInput) => void;
  onLink: (input: LmsAssignmentLinkInput) => void;
  onSync: (localAssignmentId: string, input: GradeSyncInput) => void;
  onRefresh?: () => void;
}

const emptyContext: AcademicContext = {
  institution: "",
  course_code: "",
  course_name: "",
  period: "",
  section: ""
};

const selectClass = "h-11 w-full rounded-xl border bg-background/70 px-3 text-sm shadow-sm transition hover:border-muted-foreground/40 focus:border-primary";

export function LmsWorkspace({
  status,
  courses,
  assignments,
  localAssignments,
  links,
  pending,
  report,
  onSelectCourse,
  onImport,
  onLink,
  onSync,
  onRefresh
}: LmsWorkspaceProps) {
  const { t } = useI18n();
  const [courseId, setCourseId] = useState("");
  const [importing, setImporting] = useState<LmsRemoteAssignment | null>(null);
  const [context, setContext] = useState<AcademicContext>(emptyContext);
  const [importError, setImportError] = useState<string>();
  const [linkLocalId, setLinkLocalId] = useState("");
  const [linkRemoteId, setLinkRemoteId] = useState("");
  const [studentIdType, setStudentIdType] = useState<StudentIdType>("sis_user_id");
  const [dryRun, setDryRun] = useState(false);
  const [jobIds, setJobIds] = useState<Record<string, string>>({});

  const linkedLocalIds = useMemo(
    () => new Set(links.map((link) => link.local_assignment_id)),
    [links]
  );
  const availableLocalAssignments = localAssignments.filter(
    (assignment) => !linkedLocalIds.has(assignment.id)
  );
  const localById = useMemo(
    () => new Map(localAssignments.map((assignment) => [assignment.id, assignment])),
    [localAssignments]
  );

  function selectCourse(value: string) {
    setCourseId(value);
    setLinkRemoteId("");
    setImporting(null);
    if (value) onSelectCourse(value);
  }

  function beginImport(assignment: LmsRemoteAssignment) {
    const course = courses.find((item) => item.id === assignment.course_id);
    setContext({
      ...emptyContext,
      course_code: course?.course_code ?? "",
      course_name: course?.name ?? "",
      period: course?.term ?? ""
    });
    setImportError(undefined);
    setImporting(assignment);
  }

  function submitImport(event: FormEvent) {
    event.preventDefault();
    if (!importing || Object.values(context).some((value) => !value.trim())) {
      setImportError(t("lms.required"));
      return;
    }
    onImport({
      external_course_id: importing.course_id,
      external_assignment_id: importing.id,
      kind: "pdf",
      context
    });
  }

  function updateContext(field: keyof AcademicContext, value: string) {
    setContext((current) => ({ ...current, [field]: value }));
  }

  if (!status.configured) {
    return (
      <section className="panel p-6 sm:p-8">
        <div className="flex items-start gap-4">
          <span className="rounded-xl bg-warning/10 p-3 text-warning"><ShieldCheck aria-hidden="true" className="size-5" /></span>
          <div>
            <p className="eyebrow">{t("lms.canvas")}</p>
            <h2 className="mt-2 text-xl font-semibold">{t("lms.notConfigured")}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{t("lms.notConfiguredBody")}</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <div className="space-y-6">
      <section className="panel p-5 sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <span className="rounded-xl bg-success/10 p-3 text-success"><CheckCircle2 aria-hidden="true" className="size-5" /></span>
            <div>
              <p className="eyebrow">{t("lms.canvas")} · {t("lms.connected")}</p>
              <h2 className="mt-1 text-lg font-semibold">{status.account_name ?? t("lms.account")}</h2>
              <p className="mt-1 text-xs text-muted-foreground">{status.base_url}</p>
            </div>
          </div>
          {onRefresh ? <Button aria-label={t("lms.refresh")} disabled={pending} onClick={onRefresh} variant="secondary"><RefreshCw aria-hidden="true" className="size-4" />{t("common.refresh")}</Button> : null}
        </div>
      </section>

      <section className="panel p-5 sm:p-6">
        <p className="eyebrow">{t("lms.discovery")}</p>
        <h2 className="mt-2 text-xl font-semibold">{t("lms.discovery")}</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{t("lms.discoveryBody")}</p>
        <label className="mt-5 block max-w-xl space-y-2">
          <span className="text-sm font-medium">{t("lms.course")}</span>
          <select aria-label={t("lms.course")} className={selectClass} onChange={(event) => selectCourse(event.target.value)} value={courseId}>
            <option value="">{t("lms.chooseCourse")}</option>
            {courses.map((course) => <option key={course.id} value={course.id}>{course.course_code ? `${course.course_code} · ` : ""}{course.name}{course.term ? ` · ${course.term}` : ""}</option>)}
          </select>
        </label>

        {courseId ? (
          assignments.length ? (
            <div className="mt-6 grid gap-3 lg:grid-cols-2">
              {assignments.map((assignment) => (
                <article className="rounded-2xl border bg-background/45 p-4" key={assignment.id}>
                  <div className="flex items-start justify-between gap-3">
                    <div><h3 className="font-semibold">{assignment.name}</h3><p className="mt-1 text-xs text-muted-foreground">{assignment.points_possible === null ? "—" : t("lms.points", { count: assignment.points_possible })}{assignment.published ? "" : ` · ${t("lms.unpublished")}`}</p></div>
                    <span className="rounded-lg bg-primary/10 px-2 py-1 font-mono text-[0.65rem] text-primary">#{assignment.id}</span>
                  </div>
                  {assignment.description ? <p className="mt-3 line-clamp-3 text-xs leading-5 text-muted-foreground">{assignment.description}</p> : null}
                  <Button aria-label={t("lms.importAria", { name: assignment.name })} className="mt-4" onClick={() => beginImport(assignment)} size="sm" variant="secondary"><ArrowDownToLine aria-hidden="true" className="size-4" />{t("lms.import")}</Button>
                </article>
              ))}
            </div>
          ) : <p className="mt-6 rounded-xl border border-dashed p-5 text-sm text-muted-foreground">{t("lms.noAssignments")}</p>
        ) : null}

        {importing ? (
          <form className="mt-6 rounded-2xl border border-primary/25 bg-primary/5 p-5" onSubmit={submitImport}>
            <h3 className="text-lg font-semibold">{t("lms.importTitle", { name: importing.name })}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{t("lms.importBody")}</p>
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <Field label={t("assignments.institution")} name="lms-institution" onChange={(event) => updateContext("institution", event.target.value)} value={context.institution} />
              <Field label={t("assignments.courseCode")} name="lms-course-code" onChange={(event) => updateContext("course_code", event.target.value)} value={context.course_code} />
              <Field label={t("assignments.courseName")} name="lms-course-name" onChange={(event) => updateContext("course_name", event.target.value)} value={context.course_name} />
              <Field label={t("assignments.period")} name="lms-period" onChange={(event) => updateContext("period", event.target.value)} value={context.period} />
              <Field label={t("assignments.section")} name="lms-section" onChange={(event) => updateContext("section", event.target.value)} value={context.section} />
            </div>
            {importError ? <p className="mt-4 text-sm text-danger" role="alert">{importError}</p> : null}
            <div className="mt-5 flex gap-2"><Button disabled={pending} type="submit">{t("lms.importAssignment")}</Button><Button onClick={() => setImporting(null)} variant="ghost">{t("common.cancel")}</Button></div>
          </form>
        ) : null}

        {courseId && assignments.length && availableLocalAssignments.length ? (
          <form className="mt-6 grid gap-4 rounded-2xl border p-5 md:grid-cols-[1fr_1fr_auto] md:items-end" onSubmit={(event) => { event.preventDefault(); if (linkLocalId && linkRemoteId) onLink({ local_assignment_id: linkLocalId, external_course_id: courseId, external_assignment_id: linkRemoteId }); }}>
            <label className="space-y-2"><span className="text-sm font-medium">{t("lms.localAssignment")}</span><select className={selectClass} onChange={(event) => setLinkLocalId(event.target.value)} value={linkLocalId}><option value="">{t("lms.chooseAssignment")}</option>{availableLocalAssignments.map((assignment) => <option key={assignment.id} value={assignment.id}>{assignment.context.course_code} · {assignment.name}</option>)}</select></label>
            <label className="space-y-2"><span className="text-sm font-medium">{t("lms.remoteAssignment")}</span><select className={selectClass} onChange={(event) => setLinkRemoteId(event.target.value)} value={linkRemoteId}><option value="">{t("lms.chooseAssignment")}</option>{assignments.map((assignment) => <option key={assignment.id} value={assignment.id}>{assignment.name}</option>)}</select></label>
            <Button disabled={pending || !linkLocalId || !linkRemoteId} type="submit" variant="secondary"><Link2 aria-hidden="true" className="size-4" />{t("lms.link")}</Button>
          </form>
        ) : null}
      </section>

      <section className="panel p-5 sm:p-6">
        <p className="eyebrow">{t("lms.links")}</p>
        <h2 className="mt-2 text-xl font-semibold">{t("lms.links")}</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{t("lms.linksBody")}</p>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <label className="space-y-2"><span className="text-sm font-medium">{t("lms.studentIdType")}</span><select className={selectClass} onChange={(event) => setStudentIdType(event.target.value as StudentIdType)} value={studentIdType}><option value="sis_user_id">{t("lms.sisId")}</option><option value="canvas_user_id">{t("lms.canvasId")}</option><option value="login_id">{t("lms.loginId")}</option></select></label>
          <label className="flex items-center gap-3 rounded-xl border bg-background/45 px-4 py-3"><input aria-label={t("lms.dryRun")} checked={dryRun} className="size-4 accent-primary" onChange={(event) => setDryRun(event.target.checked)} type="checkbox" /><span><span className="block text-sm font-medium">{t("lms.dryRun")}</span><span className="block text-xs text-muted-foreground">{t("lms.dryRunBody")}</span></span></label>
        </div>
        {links.length ? <div className="mt-5 space-y-3">{links.map((link) => {
          const assignment = localById.get(link.local_assignment_id);
          const name = assignment?.name ?? link.local_assignment_id;
          return <article className="grid gap-4 rounded-2xl border bg-background/45 p-4 lg:grid-cols-[1fr_minmax(12rem,20rem)_auto] lg:items-end" key={link.id}>
            <div><h3 className="font-semibold">{name}</h3><p className="mt-1 text-xs text-muted-foreground">Canvas · {link.external_course_id} / {link.external_assignment_id}</p></div>
            {assignment?.kind === "automated" ? <Field label={t("lms.jobId")} name={`job-${assignment.id}`} onChange={(event) => setJobIds((current) => ({ ...current, [assignment.id]: event.target.value }))} value={jobIds[assignment.id] ?? ""} /> : <p className="text-xs text-muted-foreground">{t("assignments.pdfBadge")}</p>}
            <Button aria-label={t("lms.syncAria", { name })} disabled={pending || (assignment?.kind === "automated" && !(jobIds[assignment.id] ?? "").trim())} onClick={() => onSync(link.local_assignment_id, { dry_run: dryRun, job_id: assignment?.kind === "automated" ? (jobIds[assignment.id] ?? "").trim() || null : null, student_id_type: studentIdType })}><Send aria-hidden="true" className="size-4" />{t("lms.sync")}</Button>
          </article>;
        })}</div> : <p className="mt-5 rounded-xl border border-dashed p-5 text-sm text-muted-foreground">{t("lms.noLinks")}</p>}
      </section>

      {report ? <section className="panel p-5 sm:p-6" aria-live="polite"><p className="eyebrow">{t("lms.report")}</p><div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">{([["lms.attempted", report.attempted], ["lms.sent", report.sent], ["lms.skipped", report.skipped], ["lms.failed", report.failed]] as const).map(([key, value]) => <div className="rounded-xl border bg-background/45 p-4" key={key}><p className="text-2xl font-semibold">{value}</p><p className="mt-1 text-xs text-muted-foreground">{t(key)}</p></div>)}</div></section> : null}
    </div>
  );
}
