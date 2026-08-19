"use client";

import { FileText, MoveRight } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { formatDate } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import type { PdfSubmission } from "@/types/grader";

export function PdfSubmissionTable({ submissions }: { submissions: PdfSubmission[] }) {
  const { t } = useI18n();
  if (submissions.length === 0) {
    return (
      <Card className="flex min-h-64 flex-col items-center justify-center p-8 text-center">
        <FileText aria-hidden="true" className="size-7 text-muted-foreground" />
        <h2 className="mt-4 font-semibold">{t("pdf.none")}</h2>
        <p className="mt-2 text-sm text-muted-foreground">{t("pdf.noneBody")}</p>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-5 py-3 font-medium">{t("pdf.student")}</th>
              <th className="px-5 py-3 font-medium">{t("pdf.assignment")}</th>
              <th className="px-5 py-3 font-medium">{t("pdf.document")}</th>
              <th className="px-5 py-3 font-medium">{t("pdf.grade")}</th>
              <th className="px-5 py-3 font-medium">{t("pdf.updated")}</th>
              <th className="px-5 py-3"><span className="sr-only">{t("pdf.open")}</span></th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {submissions.map((submission) => (
              <tr className="transition hover:bg-muted/30" key={submission.id}>
                <td className="px-5 py-4 font-medium">{submission.student_id}</td>
                <td className="px-5 py-4">{submission.title}</td>
                <td className="px-5 py-4 text-muted-foreground">{t("pdf.pages", { count: submission.page_count })} · {(submission.size_bytes / 1024).toFixed(1)} KB</td>
                <td className="px-5 py-4">
                  <Badge className={submission.status === "finalized" ? "border-success/25 bg-success/10 text-success" : "border-amber-500/25 bg-amber-500/10 text-amber-600 dark:text-amber-300"}>
                    {submission.status === "finalized" ? `${submission.total_score} / ${submission.maximum_points}` : t("pdf.draft")}
                  </Badge>
                </td>
                <td className="px-5 py-4 text-muted-foreground">{formatDate(submission.updated_at)}</td>
                <td className="px-5 py-4 text-right">
                  <Link aria-label={t("pdf.gradeStudent", { student: submission.student_id })} className="inline-flex rounded-lg p-2 text-primary hover:bg-primary/10" href={`/pdf/${submission.id}`}>
                    <MoveRight aria-hidden="true" className="size-4" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
