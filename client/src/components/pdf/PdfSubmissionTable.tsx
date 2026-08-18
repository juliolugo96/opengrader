import { FileText, MoveRight } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { formatDate } from "@/lib/utils";
import type { PdfSubmission } from "@/types/grader";

export function PdfSubmissionTable({ submissions }: { submissions: PdfSubmission[] }) {
  if (submissions.length === 0) {
    return (
      <Card className="flex min-h-64 flex-col items-center justify-center p-8 text-center">
        <FileText aria-hidden="true" className="size-7 text-muted-foreground" />
        <h2 className="mt-4 font-semibold">No PDF submissions yet</h2>
        <p className="mt-2 text-sm text-muted-foreground">Upload the first document to begin manual grading.</p>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-5 py-3 font-medium">Student</th>
              <th className="px-5 py-3 font-medium">Assignment</th>
              <th className="px-5 py-3 font-medium">Document</th>
              <th className="px-5 py-3 font-medium">Grade</th>
              <th className="px-5 py-3 font-medium">Updated</th>
              <th className="px-5 py-3"><span className="sr-only">Open</span></th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {submissions.map((submission) => (
              <tr className="transition hover:bg-muted/30" key={submission.id}>
                <td className="px-5 py-4 font-medium">{submission.student_id}</td>
                <td className="px-5 py-4">{submission.title}</td>
                <td className="px-5 py-4 text-muted-foreground">{submission.page_count} pages · {(submission.size_bytes / 1024).toFixed(1)} KB</td>
                <td className="px-5 py-4">
                  <Badge className={submission.status === "finalized" ? "border-success/25 bg-success/10 text-success" : "border-amber-500/25 bg-amber-500/10 text-amber-600 dark:text-amber-300"}>
                    {submission.status === "finalized" ? `${submission.total_score} / ${submission.maximum_points}` : "Draft"}
                  </Badge>
                </td>
                <td className="px-5 py-4 text-muted-foreground">{formatDate(submission.updated_at)}</td>
                <td className="px-5 py-4 text-right">
                  <Link aria-label={`Grade ${submission.student_id} PDF`} className="inline-flex rounded-lg p-2 text-primary hover:bg-primary/10" href={`/pdf/${submission.id}`}>
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
