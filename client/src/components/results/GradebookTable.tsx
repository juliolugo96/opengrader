"use client";

import { ChevronDown, Search, Users } from "lucide-react";
import { useDeferredValue, useState } from "react";

import { StudentResultCard } from "@/components/results/StudentResultCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { cn, formatScore, percentage } from "@/lib/utils";
import type { StudentResult } from "@/types/grader";

export function GradebookTable({ students }: { students: StudentResult[] }) {
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const deferredSearch = useDeferredValue(search.trim().toLowerCase());
  const visible = students.filter((student) => student.student_id.toLowerCase().includes(deferredSearch));

  return (
    <div className="panel overflow-hidden">
      <div className="flex flex-col gap-3 border-b p-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-semibold">Student gradebook</h2>
          <p className="mt-1 text-xs text-muted-foreground">Select a student to inspect individual test executions.</p>
        </div>
        <label className="relative">
          <span className="sr-only">Search students</span>
          <Search aria-hidden="true" className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            className="h-10 w-full rounded-xl border bg-background pl-9 pr-3 text-sm sm:w-64"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search student ID"
            value={search}
          />
        </label>
      </div>

      {visible.length === 0 ? (
        <EmptyState icon={<Users className="size-5" />} title="No students found" description="No student ID matches the current search." />
      ) : (
        <div className="overflow-x-auto">
          <table className="data-table min-w-[680px]">
            <thead>
              <tr>
                <th scope="col">Student</th>
                <th scope="col">Status</th>
                <th scope="col">Score</th>
                <th scope="col">Progress</th>
                <th className="w-16" scope="col"><span className="sr-only">Details</span></th>
              </tr>
            </thead>
            <tbody>
              {visible.map((student) => {
                const scorePercentage = percentage(student.score, student.maximum_score);
                const isExpanded = expanded === student.student_id;
                return (
                  <StudentRow
                    expanded={isExpanded}
                    key={student.student_id}
                    onToggle={() => setExpanded(isExpanded ? null : student.student_id)}
                    percentage={scorePercentage}
                    student={student}
                  />
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StudentRow({ student, percentage: scorePercentage, expanded, onToggle }: {
  student: StudentResult;
  percentage: number;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <tr>
        <td><span className="font-mono text-xs font-semibold">{student.student_id}</span></td>
        <td><span className={cn("text-sm font-medium capitalize", student.status === "pass" ? "text-success" : student.status === "partial" ? "text-warning" : "text-danger")}>{student.status}</span></td>
        <td className="font-mono text-xs tabular-nums">{formatScore(student.score, student.maximum_score)}</td>
        <td>
          <div className="flex items-center gap-3">
            <div className="h-2 w-full max-w-44 overflow-hidden rounded-full bg-muted">
              <div className={cn("h-full rounded-full", scorePercentage >= 70 ? "bg-success" : scorePercentage > 0 ? "bg-warning" : "bg-danger")} style={{ width: `${scorePercentage}%` }} />
            </div>
            <span className="w-12 font-mono text-xs tabular-nums text-muted-foreground">{scorePercentage}%</span>
          </div>
        </td>
        <td>
          <button
            aria-expanded={expanded}
            aria-label={`${expanded ? "Collapse" : "Expand"} ${student.student_id} results`}
            className="flex size-9 items-center justify-center rounded-xl text-muted-foreground transition hover:bg-muted hover:text-foreground"
            onClick={onToggle}
          >
            <ChevronDown aria-hidden="true" className={cn("size-4 transition-transform", expanded && "rotate-180")} />
          </button>
        </td>
      </tr>
      {expanded ? (
        <tr>
          <td className="!p-0" colSpan={5}><StudentResultCard student={student} /></td>
        </tr>
      ) : null}
    </>
  );
}
