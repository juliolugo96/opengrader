"use client";

import { BookOpenCheck, FileText, Loader2, Plus, Trash2 } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import type { AcademicAssignment, AcademicAssignmentInput, AssignmentCheck } from "@/types/grader";

type TemplateId = "python" | "javascript" | "c" | "custom";

const templates: Record<TemplateId, { image: string; setup: string; command: string }> = {
  python: { image: "python:3.12-slim", setup: "", command: "python -m pytest -q" },
  javascript: { image: "node:22-slim", setup: "npm install", command: "npm test" },
  c: { image: "gcc:14", setup: "make", command: "make test" },
  custom: { image: "ubuntu:24.04", setup: "", command: "./run-tests.sh" }
};

interface BuilderState extends AcademicAssignmentInput {
  template: TemplateId;
}

function initialState(initial?: AcademicAssignment): BuilderState {
  return {
    name: initial?.name ?? "",
    kind: initial?.kind ?? "automated",
    context: initial?.context ?? { institution: "", course_code: "", course_name: "", period: "", section: "" },
    automated: initial?.automated ?? {
      image: templates.python.image,
      setup: null,
      timeout_seconds: 10,
      memory_mb: 256,
      cpus: 1,
      pids_limit: 128,
      tests: [{ name: "Runs successfully", command: templates.python.command, points: 10, partial_credit: {} }]
    },
    template: "python"
  };
}

export function AssignmentBuilder({
  initial,
  onCancel,
  onSubmit,
  pending,
  serverError
}: {
  initial?: AcademicAssignment;
  onCancel: () => void;
  onSubmit: (input: AcademicAssignmentInput) => void;
  pending: boolean;
  serverError?: string;
}) {
  const { t } = useI18n();
  const [form, setForm] = useState(() => initialState(initial));
  const [error, setError] = useState<string>();
  const automated = form.automated ?? initialState().automated!;

  function updateContext(field: keyof AcademicAssignmentInput["context"], value: string) {
    setForm((current) => ({ ...current, context: { ...current.context, [field]: value } }));
  }

  function setKind(kind: AcademicAssignmentInput["kind"]) {
    setForm((current) => ({ ...current, kind, automated: kind === "automated" ? current.automated ?? initialState().automated : null }));
    setError(undefined);
  }

  function selectTemplate(template: TemplateId) {
    const selected = templates[template];
    setForm((current) => ({
      ...current,
      template,
      automated: {
        ...(current.automated ?? initialState().automated!),
        image: selected.image,
        setup: selected.setup || null,
        tests: (current.automated ?? initialState().automated!).tests.map((check, index) => ({
          ...check,
          command: index === 0 ? selected.command : check.command
        }))
      }
    }));
  }

  function updateAutomated<K extends keyof NonNullable<AcademicAssignmentInput["automated"]>>(field: K, value: NonNullable<AcademicAssignmentInput["automated"]>[K]) {
    setForm((current) => ({ ...current, automated: { ...(current.automated ?? initialState().automated!), [field]: value } }));
  }

  function updateCheck(index: number, field: keyof AssignmentCheck, value: string | number) {
    updateAutomated("tests", automated.tests.map((check, checkIndex) => checkIndex === index ? { ...check, [field]: value } : check));
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const context = Object.fromEntries(Object.entries(form.context).map(([key, value]) => [key, value.trim()])) as AcademicAssignmentInput["context"];
    if (!form.name.trim() || Object.values(context).some((value) => !value)) {
      setError(t("assignments.required"));
      return;
    }
    if (form.kind === "automated") {
      const names = automated.tests.map((check) => check.name.trim());
      const invalid = automated.tests.some((check) => !check.name.trim() || !check.command.trim() || check.points <= 0);
      if (invalid || new Set(names).size !== names.length) {
        setError(t("assignments.checkRequired"));
        return;
      }
    }
    setError(undefined);
    onSubmit({
      name: form.name.trim(),
      kind: form.kind,
      context,
      automated: form.kind === "automated" ? {
        ...automated,
        image: automated.image.trim(),
        setup: automated.setup?.trim() || null,
        tests: automated.tests.map((check) => ({ ...check, name: check.name.trim(), command: check.command.trim() }))
      } : null
    });
  }

  return (
    <form className="space-y-6" onSubmit={submit}>
      <Card className="p-5 sm:p-7">
        <div className="flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary"><BookOpenCheck aria-hidden="true" className="size-5" /></span>
          <div><p className="eyebrow">1 · {t("assignments.academicDetails")}</p><h2 className="mt-1 text-lg font-semibold">{t("assignments.academicDetails")}</h2></div>
        </div>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <Field label={t("assignments.institution")} name="institution" onChange={(event) => updateContext("institution", event.target.value)} value={form.context.institution} />
          <Field label={t("assignments.period")} name="period" onChange={(event) => updateContext("period", event.target.value)} value={form.context.period} />
          <Field label={t("assignments.courseCode")} name="course-code" onChange={(event) => updateContext("course_code", event.target.value)} value={form.context.course_code} />
          <Field label={t("assignments.courseName")} name="course-name" onChange={(event) => updateContext("course_name", event.target.value)} value={form.context.course_name} />
          <Field label={t("assignments.section")} name="section" onChange={(event) => updateContext("section", event.target.value)} value={form.context.section} />
          <Field label={t("assignments.name")} name="assignment-name" onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} value={form.name} />
        </div>
      </Card>

      <Card className="p-5 sm:p-7">
        <p className="eyebrow">2 · {t("assignments.evaluation")}</p>
        <fieldset className="mt-4 grid gap-3 sm:grid-cols-2">
          <legend className="mb-3 text-lg font-semibold">{t("assignments.type")}</legend>
          {(["automated", "pdf"] as const).map((kind) => (
            <label className={cn("flex cursor-pointer gap-3 rounded-2xl border p-4 transition", form.kind === kind && "border-primary bg-primary/5")} key={kind}>
              <input aria-label={t(kind === "automated" ? "assignments.automated" : "assignments.pdf")} checked={form.kind === kind} className="mt-1 accent-primary" name="kind" onChange={() => setKind(kind)} type="radio" />
              <span><span className="block font-medium">{t(kind === "automated" ? "assignments.automated" : "assignments.pdf")}</span><span className="mt-1 block text-xs leading-5 text-muted-foreground">{t(kind === "automated" ? "assignments.automatedHelp" : "assignments.pdfHelp")}</span></span>
            </label>
          ))}
        </fieldset>

        {form.kind === "automated" ? (
          <div className="mt-7 space-y-6 border-t pt-6">
            <label className="block space-y-2">
              <span className="text-sm font-medium">{t("assignments.startingPoint")}</span>
              <select aria-label={t("assignments.startingPoint")} className="h-11 w-full rounded-xl border bg-background px-3 text-sm" onChange={(event) => selectTemplate(event.target.value as TemplateId)} value={form.template}>
                <option value="python">{t("assignments.templatePython")}</option><option value="javascript">{t("assignments.templateJavascript")}</option><option value="c">{t("assignments.templateC")}</option><option value="custom">{t("assignments.templateCustom")}</option>
              </select>
            </label>
            <div>
              <div className="flex items-center justify-between"><h3 className="font-semibold">{t("assignments.checks")}</h3><Button onClick={() => updateAutomated("tests", [...automated.tests, { name: "", command: "", points: 10, partial_credit: {} }])} size="sm" variant="secondary"><Plus aria-hidden="true" className="size-4" />{t("assignments.addCheck")}</Button></div>
              <div className="mt-3 space-y-3">
                {automated.tests.map((check, index) => (
                  <div className="grid gap-3 rounded-2xl border bg-muted/20 p-4 md:grid-cols-[1fr_1.4fr_7rem_auto] md:items-end" key={index}>
                    <Field aria-label={`${t("assignments.checkName")} ${index + 1}`} label={t("assignments.checkName")} name={`check-name-${index}`} onChange={(event) => updateCheck(index, "name", event.target.value)} value={check.name} />
                    <Field aria-label={`${t("assignments.instruction")} ${index + 1}`} label={t("assignments.instruction")} name={`check-command-${index}`} onChange={(event) => updateCheck(index, "command", event.target.value)} spellCheck={false} value={check.command} />
                    <Field aria-label={`${t("assignments.pointsLabel")} ${index + 1}`} label={t("assignments.pointsLabel")} min="0.1" name={`check-points-${index}`} onChange={(event) => updateCheck(index, "points", Number(event.target.value))} step="0.1" type="number" value={check.points} />
                    <Button aria-label={`${t("assignments.removeCheck")} ${index + 1}`} disabled={automated.tests.length === 1} onClick={() => updateAutomated("tests", automated.tests.filter((_, checkIndex) => checkIndex !== index))} size="icon" variant="ghost"><Trash2 aria-hidden="true" className="size-4" /></Button>
                  </div>
                ))}
              </div>
            </div>
            <details className="rounded-2xl border bg-muted/20 p-4">
              <summary className="cursor-pointer text-sm font-medium">{t("assignments.advanced")}</summary>
              <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <Field label={t("assignments.environment")} name="image" onChange={(event) => updateAutomated("image", event.target.value)} value={automated.image} />
                <Field label={t("assignments.preparation")} name="setup" onChange={(event) => updateAutomated("setup", event.target.value)} value={automated.setup ?? ""} />
                <Field label={t("assignments.timeout")} min="0.1" name="timeout" onChange={(event) => updateAutomated("timeout_seconds", Number(event.target.value))} step="0.1" type="number" value={automated.timeout_seconds} />
                <Field label={t("assignments.memory")} min="32" name="memory" onChange={(event) => updateAutomated("memory_mb", Number(event.target.value))} type="number" value={automated.memory_mb} />
                <Field label={t("assignments.cpus")} min="0.1" name="cpus" onChange={(event) => updateAutomated("cpus", Number(event.target.value))} step="0.1" type="number" value={automated.cpus} />
                <Field label={t("assignments.processes")} min="16" name="processes" onChange={(event) => updateAutomated("pids_limit", Number(event.target.value))} type="number" value={automated.pids_limit} />
              </div>
            </details>
          </div>
        ) : (
          <div className="mt-6 flex items-center gap-3 rounded-2xl border border-primary/20 bg-primary/5 p-4 text-sm text-muted-foreground"><FileText aria-hidden="true" className="size-5 shrink-0 text-primary" />{t("assignments.pdfReady")}</div>
        )}
      </Card>

      {error || serverError ? <p className="rounded-xl border border-danger/20 bg-danger/5 p-3 text-sm text-danger" role="alert">{error ?? serverError}</p> : null}
      <div className="flex justify-end gap-3"><Button onClick={onCancel} variant="secondary">{t("common.cancel")}</Button><Button disabled={pending} type="submit">{pending ? <Loader2 aria-hidden="true" className="size-4 animate-spin" /> : null}{pending ? t("common.saving") : t("common.save")}</Button></div>
    </form>
  );
}
