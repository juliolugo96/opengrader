"use client";

import { BookOpen, FileUp, Pencil, Play, Search, Trash2 } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button, buttonStyles } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import type { AcademicAssignment } from "@/types/grader";

function unique(assignments: AcademicAssignment[], field: "institution" | "period" | "section") {
  return [...new Set(assignments.map((assignment) => assignment.context[field]))].sort();
}

export function AssignmentCatalog({ assignments, onEdit, onDelete, onRun, onCreate }: {
  assignments: AcademicAssignment[];
  onEdit: (assignment: AcademicAssignment) => void;
  onDelete: (assignment: AcademicAssignment) => void;
  onRun: (assignment: AcademicAssignment) => void;
  onCreate: () => void;
}) {
  const { t } = useI18n();
  const [institution, setInstitution] = useState("");
  const [period, setPeriod] = useState("");
  const [section, setSection] = useState("");
  const [search, setSearch] = useState("");
  const visible = useMemo(() => assignments.filter((assignment) => {
    const haystack = `${assignment.name} ${assignment.context.course_code} ${assignment.context.course_name}`.toLowerCase();
    return (!institution || assignment.context.institution === institution)
      && (!period || assignment.context.period === period)
      && (!section || assignment.context.section === section)
      && (!search || haystack.includes(search.toLowerCase()));
  }), [assignments, institution, period, search, section]);
  const groups = useMemo(() => visible.reduce((result, assignment) => {
    const key = `${assignment.context.institution}\u0000${assignment.context.course_code}\u0000${assignment.context.course_name}\u0000${assignment.context.period}\u0000${assignment.context.section}`;
    const group = result.get(key);
    if (group) group.push(assignment);
    else result.set(key, [assignment]);
    return result;
  }, new Map<string, AcademicAssignment[]>()), [visible]);

  if (assignments.length === 0) {
    return <Card><EmptyState icon={<BookOpen className="size-5" />} title={t("assignments.emptyTitle")} description={t("assignments.emptyBody")} action={<Button onClick={onCreate}>{t("assignments.new")}</Button>} /></Card>;
  }

  return (
    <div className="space-y-5">
      <Card className="p-4 sm:p-5">
        <p className="eyebrow">{t("assignments.filters")}</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="relative"><span className="sr-only">{t("assignments.filters")}</span><Search aria-hidden="true" className="absolute left-3 top-3.5 size-4 text-muted-foreground" /><input className="h-11 w-full rounded-xl border bg-background pl-9 pr-3 text-sm" onChange={(event) => setSearch(event.target.value)} placeholder={t("assignments.name")} value={search} /></label>
          <FilterSelect label={t("assignments.institution")} options={unique(assignments, "institution")} value={institution} onChange={setInstitution} all={t("common.all")} />
          <FilterSelect label={t("assignments.period")} options={unique(assignments, "period")} value={period} onChange={setPeriod} all={t("common.all")} />
          <FilterSelect label={t("assignments.section")} options={unique(assignments, "section")} value={section} onChange={setSection} all={t("common.all")} />
        </div>
      </Card>
      {[...groups.entries()].map(([key, group]) => {
        const context = group[0].context;
        return (
          <section aria-label={`${context.course_code} · ${context.course_name}`} className="space-y-3" key={key}>
            <div className="flex flex-col gap-1 px-1 sm:flex-row sm:items-end sm:justify-between">
              <div><p className="eyebrow">{context.institution} · {context.period}</p><h2 className="mt-1 text-xl font-semibold">{context.course_code} · {context.course_name}</h2></div>
              <p className="text-sm text-muted-foreground">{t("assignments.section")} {context.section}</p>
            </div>
            <div className="grid gap-3 lg:grid-cols-2">
              {group.map((assignment) => {
                const points = assignment.automated?.tests.reduce((total, check) => total + check.points, 0) ?? 0;
                return (
                  <Card className="flex flex-col p-5" key={assignment.id}>
                    <div className="flex items-start justify-between gap-3"><div><Badge className={assignment.kind === "automated" ? "border-primary/20 bg-primary/5 text-primary" : "border-warning/20 bg-warning/5 text-warning"}>{t(assignment.kind === "automated" ? "assignments.automatedBadge" : "assignments.pdfBadge")}</Badge><h3 className="mt-3 text-lg font-semibold">{assignment.name}</h3></div><div className="flex"><Button aria-label={`${t("common.edit")} ${assignment.name}`} onClick={() => onEdit(assignment)} size="icon" variant="ghost"><Pencil aria-hidden="true" className="size-4" /></Button><Button aria-label={`${t("common.delete")} ${assignment.name}`} onClick={() => onDelete(assignment)} size="icon" variant="ghost"><Trash2 aria-hidden="true" className="size-4" /></Button></div></div>
                    <p className="mt-2 text-sm text-muted-foreground">{assignment.kind === "automated" ? `${t("assignments.checkCount", { count: assignment.automated?.tests.length ?? 0 })} · ${t("assignments.points", { count: points })}` : t("assignments.pdfReady")}</p>
                    <div className="mt-5 flex border-t pt-4">{assignment.kind === "automated" ? <Button onClick={() => onRun(assignment)} size="sm"><Play aria-hidden="true" className="size-4" />{t("assignments.run")}</Button> : <Link className={cn(buttonStyles({ size: "sm" }))} href={`/pdf?assignment=${encodeURIComponent(assignment.id)}`}><FileUp aria-hidden="true" className="size-4" />{t("assignments.upload")}</Link>}</div>
                  </Card>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function FilterSelect({ label, options, value, onChange, all }: { label: string; options: string[]; value: string; onChange: (value: string) => void; all: string }) {
  return <label><span className="sr-only">{label}</span><select aria-label={label} className="h-11 w-full rounded-xl border bg-background px-3 text-sm" onChange={(event) => onChange(event.target.value)} value={value}><option value="">{all} · {label}</option>{options.map((option) => <option key={option}>{option}</option>)}</select></label>;
}
