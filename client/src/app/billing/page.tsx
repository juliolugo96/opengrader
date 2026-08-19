"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { CreditCard } from "lucide-react";

import { BillingPanel } from "@/components/billing/BillingPanel";
import { EmptyState } from "@/components/ui/EmptyState";
import { QueryError } from "@/components/ui/QueryError";
import { Skeleton } from "@/components/ui/Skeleton";
import { createBillingCheckout, createBillingPortal, getBillingOverview } from "@/lib/api-client";
import { useSettings } from "@/lib/use-settings";
import { useI18n } from "@/lib/i18n";

export default function BillingPage() {
  const settings = useSettings();
  const { t } = useI18n();
  const overview = useQuery({
    queryKey: ["billing-overview", settings.apiBaseUrl, Boolean(settings.apiKey)],
    queryFn: getBillingOverview,
    enabled: Boolean(settings.apiKey)
  });
  const checkout = useMutation({
    mutationFn: createBillingCheckout,
    onSuccess: ({ url }) => window.location.assign(url)
  });
  const portal = useMutation({
    mutationFn: createBillingPortal,
    onSuccess: ({ url }) => window.location.assign(url)
  });
  const pending = checkout.isPending || portal.isPending;
  const mutationError = checkout.error?.message ?? portal.error?.message;

  return (
    <div className="space-y-7">
      <div>
        <p className="eyebrow">{t("billing.eyebrow")}</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">{t("billing.title")}</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{t("billing.subtitle")}</p>
      </div>

      {!settings.apiKey ? (
        <div className="panel"><EmptyState icon={<CreditCard className="size-5" />} title={t("billing.connect")} description={t("billing.connectBody")} /></div>
      ) : null}
      {settings.apiKey && overview.isPending ? <Skeleton className="h-96" /> : null}
      {settings.apiKey && overview.isError ? <div className="panel"><QueryError error={overview.error} retry={() => overview.refetch()} /></div> : null}
      {overview.data ? (
        <BillingPanel
          onCheckout={(email) => checkout.mutate(email)}
          onPortal={() => portal.mutate()}
          overview={overview.data}
          pending={pending}
          serverError={mutationError}
        />
      ) : null}
    </div>
  );
}
