"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cable } from "lucide-react";
import { useState } from "react";

import { LmsWorkspace } from "@/components/lms/LmsWorkspace";
import { EmptyState } from "@/components/ui/EmptyState";
import { QueryError } from "@/components/ui/QueryError";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  importLmsAssignment,
  linkLmsAssignment,
  listAssignments,
  listLmsAssignments,
  listLmsCourses,
  listLmsLinks,
  listLmsProviders,
  syncLmsGrades
} from "@/lib/api-client";
import { useI18n } from "@/lib/i18n";
import { useSettings } from "@/lib/use-settings";
import type { AcademicAssignment, GradeSyncInput, GradeSyncReport, LmsAssignmentLink, LmsCourse, LmsRemoteAssignment } from "@/types/grader";

const emptyStatus = {
  provider: "canvas" as const,
  configured: false,
  account_name: null,
  base_url: null
};
const emptyCourses: LmsCourse[] = [];
const emptyRemoteAssignments: LmsRemoteAssignment[] = [];
const emptyLocalAssignments: AcademicAssignment[] = [];
const emptyLinks: LmsAssignmentLink[] = [];

export default function IntegrationsPage() {
  const { t } = useI18n();
  const settings = useSettings();
  const queryClient = useQueryClient();
  const [courseId, setCourseId] = useState("");
  const [report, setReport] = useState<GradeSyncReport>();
  const enabled = Boolean(settings.apiKey);
  const providers = useQuery({ queryKey: ["lms-providers", settings.apiBaseUrl, enabled], queryFn: listLmsProviders, enabled });
  const status = providers.data?.find((item) => item.provider === "canvas") ?? emptyStatus;
  const courses = useQuery({ queryKey: ["lms-courses", settings.apiBaseUrl], queryFn: listLmsCourses, enabled: enabled && status.configured });
  const remoteAssignments = useQuery({ queryKey: ["lms-assignments", courseId], queryFn: () => listLmsAssignments(courseId), enabled: enabled && status.configured && Boolean(courseId) });
  const localAssignments = useQuery({ queryKey: ["assignments", settings.apiBaseUrl, enabled], queryFn: () => listAssignments(), enabled });
  const links = useQuery({ queryKey: ["lms-links", settings.apiBaseUrl, enabled], queryFn: listLmsLinks, enabled });
  const importAssignment = useMutation({ mutationFn: importLmsAssignment, onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ["assignments"] }), queryClient.invalidateQueries({ queryKey: ["lms-links"] })]); } });
  const linkAssignment = useMutation({ mutationFn: linkLmsAssignment, onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["lms-links"] }) });
  const sync = useMutation({ mutationFn: ({ localAssignmentId, input }: { localAssignmentId: string; input: GradeSyncInput }) => syncLmsGrades(localAssignmentId, input), onSuccess: setReport });
  const error = providers.error ?? courses.error ?? remoteAssignments.error ?? localAssignments.error ?? links.error ?? importAssignment.error ?? linkAssignment.error ?? sync.error;
  const pending = importAssignment.isPending || linkAssignment.isPending || sync.isPending;

  async function refresh() {
    await Promise.all([providers.refetch(), courses.refetch(), localAssignments.refetch(), links.refetch(), courseId ? remoteAssignments.refetch() : Promise.resolve()]);
  }

  return (
    <div className="space-y-7">
      <div><p className="eyebrow">{t("lms.eyebrow")}</p><h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">{t("lms.title")}</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{t("lms.subtitle")}</p></div>
      {!enabled ? <div className="panel"><EmptyState icon={<Cable className="size-5" />} title={t("lms.connectTitle")} description={t("lms.connectBody")} /></div> : null}
      {enabled && providers.isPending ? <Skeleton className="h-64" /> : null}
      {enabled && error ? <div className="panel"><QueryError error={error} retry={refresh} /></div> : null}
      {enabled && providers.data && !error ? (
        <LmsWorkspace
          assignments={remoteAssignments.data ?? emptyRemoteAssignments}
          courses={courses.data ?? emptyCourses}
          links={links.data ?? emptyLinks}
          localAssignments={localAssignments.data ?? emptyLocalAssignments}
          onImport={(input) => importAssignment.mutate(input)}
          onLink={(input) => linkAssignment.mutate(input)}
          onRefresh={refresh}
          onSelectCourse={setCourseId}
          onSync={(localAssignmentId, input) => sync.mutate({ localAssignmentId, input })}
          pending={pending}
          report={report}
          status={status}
        />
      ) : null}
    </div>
  );
}
