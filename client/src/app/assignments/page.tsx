"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Plus, RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";

import { AssignmentBuilder } from "@/components/assignments/AssignmentBuilder";
import { AssignmentCatalog } from "@/components/assignments/AssignmentCatalog";
import { AssignmentRunModal } from "@/components/assignments/AssignmentRunModal";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { QueryError } from "@/components/ui/QueryError";
import { Skeleton } from "@/components/ui/Skeleton";
import { createAssignment, deleteAssignment, launchAssignment, listAssignments, updateAssignment } from "@/lib/api-client";
import { useI18n } from "@/lib/i18n";
import { useSettings } from "@/lib/use-settings";
import type { AcademicAssignment, AcademicAssignmentInput, AssignmentLaunchInput } from "@/types/grader";

export default function AssignmentsPage() {
  const { t } = useI18n();
  const settings = useSettings();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [builderOpen, setBuilderOpen] = useState(false);
  const [editing, setEditing] = useState<AcademicAssignment>();
  const [running, setRunning] = useState<AcademicAssignment | null>(null);
  const assignments = useQuery({ queryKey: ["assignments", settings.apiBaseUrl, Boolean(settings.apiKey)], queryFn: () => listAssignments(), enabled: Boolean(settings.apiKey) });
  const closeBuilder = useCallback(() => { setBuilderOpen(false); setEditing(undefined); }, []);
  const save = useMutation({
    mutationFn: (input: AcademicAssignmentInput) => editing ? updateAssignment(editing.id, input) : createAssignment(input),
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["assignments"] }); closeBuilder(); }
  });
  const remove = useMutation({ mutationFn: deleteAssignment, onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["assignments"] }) });
  const launch = useMutation({
    mutationFn: (input: AssignmentLaunchInput) => launchAssignment(running!.id, input),
    onSuccess: async (job) => { await queryClient.invalidateQueries({ queryKey: ["jobs"] }); setRunning(null); router.push(`/jobs/${job.id}`); }
  });

  function confirmDelete(assignment: AcademicAssignment) {
    if (window.confirm(t("assignments.deleteConfirm", { name: assignment.name }))) remove.mutate(assignment.id);
  }

  return (
    <div className="space-y-7">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div><p className="eyebrow">{t("assignments.eyebrow")}</p><h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">{t("assignments.title")}</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{t("assignments.subtitle")}</p></div>
        <div className="flex gap-2"><Button aria-label={t("common.refresh")} disabled={!settings.apiKey || assignments.isFetching} onClick={() => assignments.refetch()} size="icon" variant="secondary"><RefreshCw aria-hidden="true" className={`size-4 ${assignments.isFetching ? "animate-spin" : ""}`} /></Button><Button disabled={!settings.apiKey} onClick={() => { setEditing(undefined); setBuilderOpen(true); }}><Plus aria-hidden="true" className="size-4" />{t("assignments.new")}</Button></div>
      </div>
      {!settings.apiKey ? <div className="panel"><EmptyState icon={<BookOpen className="size-5" />} title={t("assignments.connectTitle")} description={t("assignments.connectBody")} /></div>
        : builderOpen ? <AssignmentBuilder initial={editing} onCancel={closeBuilder} onSubmit={(input) => save.mutate(input)} pending={save.isPending} serverError={save.error?.message} />
          : assignments.isPending ? <div className="space-y-4"><Skeleton className="h-28" /><Skeleton className="h-80" /></div>
            : assignments.isError ? <div className="panel"><QueryError error={assignments.error} retry={() => assignments.refetch()} /></div>
              : <AssignmentCatalog assignments={assignments.data} onCreate={() => setBuilderOpen(true)} onDelete={confirmDelete} onEdit={(assignment) => { setEditing(assignment); setBuilderOpen(true); }} onRun={setRunning} />}
      <AssignmentRunModal assignment={running} onClose={() => { setRunning(null); launch.reset(); }} onSubmit={(input) => launch.mutate(input)} pending={launch.isPending} serverError={launch.error?.message} />
    </div>
  );
}
