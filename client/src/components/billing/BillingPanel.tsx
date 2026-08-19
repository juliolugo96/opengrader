"use client";

import { ArrowUpRight, CircleCheck, CreditCard, Gauge, Loader2, ShieldCheck } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { useI18n } from "@/lib/i18n";
import { formatDate } from "@/lib/utils";
import type { BillingOverview } from "@/types/grader";

export function BillingPanel({
  overview,
  onCheckout,
  onPortal,
  pending,
  serverError
}: {
  overview: BillingOverview;
  onCheckout: (email: string) => void;
  onPortal: () => void;
  pending: boolean;
  serverError?: string;
}) {
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string>();

  if (overview.mode === "local") {
    return (
      <Card className="overflow-hidden p-6 sm:p-8">
        <div className="flex max-w-3xl items-start gap-4">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-success/10 text-success">
            <ShieldCheck aria-hidden="true" className="size-6" />
          </span>
          <div>
            <Badge className="border-success/25 bg-success/10 text-success">{t("billing.localBadge")}</Badge>
            <h2 className="mt-4 text-2xl font-semibold tracking-tight">{t("billing.localTitle")}</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {t("billing.localBody")}
            </p>
          </div>
        </div>
      </Card>
    );
  }

  function submitCheckout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = email;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized)) {
      setError(t("billing.emailError"));
      return;
    }
    setError(undefined);
    onCheckout(normalized);
  }

  const statusStyle = overview.entitled
    ? "border-success/25 bg-success/10 text-success"
    : "border-amber-500/25 bg-amber-500/10 text-amber-700 dark:text-amber-300";

  return (
    <div className="space-y-5">
      <Card className="overflow-hidden p-6 sm:p-8">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-4">
            <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <CreditCard aria-hidden="true" className="size-6" />
            </span>
            <div>
              <Badge className={statusStyle}>{t(`billing.status.${overview.status}`)}</Badge>
              <h2 className="mt-4 text-2xl font-semibold tracking-tight">
                {overview.entitled ? t("billing.enabled") : t("billing.activate")}
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                {t("billing.hostedBody")}
              </p>
              {overview.current_period_end ? (
                <p className="mt-3 text-sm font-medium">
                  {overview.cancel_at_period_end ? t("billing.ends") : t("billing.renews")} {formatDate(overview.current_period_end)}
                </p>
              ) : null}
            </div>
          </div>
          {overview.customer_configured ? (
            <Button disabled={pending} onClick={onPortal} variant="secondary">
              {pending ? <Loader2 aria-hidden="true" className="size-4 animate-spin" /> : <ArrowUpRight aria-hidden="true" className="size-4" />}
              {t("billing.manage")}
            </Button>
          ) : null}
        </div>
      </Card>

      <div className="grid gap-4 sm:grid-cols-3">
        <UsageCard icon={<Gauge className="size-5" />} label={t("billing.accepted")} value={overview.usage.total_units} />
        <UsageCard icon={<CircleCheck className="size-5" />} label={t("billing.reported")} value={overview.usage.reported_units} />
        <UsageCard icon={<Loader2 className="size-5" />} label={t("billing.pending")} value={overview.usage.pending_units} />
      </div>

      {!overview.entitled ? (
        <Card className="p-6 sm:p-8">
          <p className="eyebrow">{t("billing.checkout")}</p>
          <h2 className="mt-2 text-xl font-semibold">{t("billing.start")}</h2>
          <p className="mt-2 text-sm text-muted-foreground">{t("billing.checkoutBody")}</p>
          <form className="mt-5 flex max-w-xl flex-col gap-3 sm:flex-row sm:items-end" onSubmit={submitCheckout}>
            <Field className="sm:min-w-80" error={error} label={t("billing.email")} name="billing-email" onChange={(event) => setEmail(event.target.value)} type="email" value={email} />
            <Button className="shrink-0" disabled={pending} type="submit">
              {pending ? <Loader2 aria-hidden="true" className="size-4 animate-spin" /> : <CreditCard aria-hidden="true" className="size-4" />}
              {t("billing.subscribe")}
            </Button>
          </form>
          {serverError ? <p className="mt-4 text-sm text-danger" role="alert">{serverError}</p> : null}
        </Card>
      ) : null}

      <p className="px-1 text-xs leading-5 text-muted-foreground">
        {t("billing.usageNote")}
      </p>
    </div>
  );
}

function UsageCard({ icon, label, value }: { icon: ReactNode; label: string; value: number }) {
  return (
    <Card className="p-5">
      <div className="flex items-center gap-3 text-muted-foreground">{icon}<span className="text-sm">{label}</span></div>
      <p className="mt-4 text-3xl font-semibold tabular-nums">{value.toLocaleString()}</p>
    </Card>
  );
}
