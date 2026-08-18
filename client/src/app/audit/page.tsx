"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, History, RefreshCw } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { QueryError } from "@/components/ui/QueryError";
import { Skeleton } from "@/components/ui/Skeleton";
import { listAuditEvents } from "@/lib/api-client";
import { useSettings } from "@/lib/use-settings";
import { cn, formatDate, humanizeAction, shortId } from "@/lib/utils";

export default function AuditPage() {
  const settings = useSettings();
  const events = useQuery({
    queryKey: ["audit-events", settings.apiBaseUrl, Boolean(settings.apiKey)],
    queryFn: () => listAuditEvents(500),
    enabled: Boolean(settings.apiKey),
    refetchInterval: 10_000
  });

  return (
    <div className="space-y-7">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="eyebrow">Immutable operations record</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">Audit trail</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">Trace every durable job transition to a worker or non-secret API-key fingerprint.</p>
        </div>
        <Button aria-label="Refresh audit events" disabled={!settings.apiKey || events.isFetching} onClick={() => events.refetch()} size="icon" variant="secondary">
          <RefreshCw aria-hidden="true" className={`size-4 ${events.isFetching ? "animate-spin" : ""}`} />
        </Button>
      </div>

      <section className="panel overflow-hidden">
        {!settings.apiKey ? (
          <EmptyState icon={<History className="size-5" />} title="Credentials required" description="Configure your bearer key before accessing the audit trail." />
        ) : events.isPending ? (
          <div aria-label="Loading audit trail" className="space-y-2 p-4">{Array.from({ length: 7 }, (_, index) => <Skeleton className="h-16" key={index} />)}</div>
        ) : events.isError ? (
          <QueryError error={events.error} retry={() => events.refetch()} />
        ) : events.data.length === 0 ? (
          <EmptyState icon={<Activity className="size-5" />} title="No events yet" description="Creating a grading job will start the chronological audit trail." />
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table min-w-[760px]">
              <thead>
                <tr>
                  <th scope="col">Timestamp</th>
                  <th scope="col">Event</th>
                  <th scope="col">Actor / key fingerprint</th>
                  <th scope="col">Job reference</th>
                </tr>
              </thead>
              <tbody>
                {events.data.map((event, index) => (
                  <tr key={event.id}>
                    <td className="relative whitespace-nowrap text-muted-foreground">
                      <span className="absolute left-0 top-1/2 size-2 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-card bg-primary" />
                      {formatDate(event.occurred_at)}
                    </td>
                    <td>
                      <Badge className={cn(
                        "capitalize",
                        event.action.includes("failed") ? "border-danger/25 bg-danger/10 text-danger"
                          : event.action.includes("succeeded") ? "border-success/25 bg-success/10 text-success"
                            : event.action.includes("started") ? "border-sky-500/25 bg-sky-500/10 text-sky-600 dark:text-sky-400"
                              : "bg-muted text-muted-foreground"
                      )}>
                        {humanizeAction(event.action)}
                      </Badge>
                    </td>
                    <td><code className="rounded-lg bg-muted px-2 py-1 font-mono text-xs">{event.actor}</code></td>
                    <td>
                      <Link className="font-mono text-xs font-semibold text-primary hover:underline" href={`/jobs/${event.resource_id}`} title={event.resource_id}>
                        {shortId(event.resource_id)}
                      </Link>
                      {index === events.data.length - 1 ? <span className="ml-2 text-[0.65rem] uppercase tracking-wider text-muted-foreground">latest</span> : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
