"use client";

import { Check, Clock3 } from "lucide-react";
import type { Route } from "next";
import Link from "next/link";

import { buttonStyles } from "@/components/ui/Button";
import { useI18n } from "@/lib/i18n";

const communityFeatures = [
  "plans.f.cli", "plans.f.docker", "plans.f.parallel", "plans.f.partial",
  "plans.f.reports", "plans.f.api", "plans.f.dashboard", "plans.f.pdf",
  "plans.f.docs", "plans.f.formats", "plans.f.selfManaged"
] as const;

const hostedFeatures = [
  "plans.f.subscription", "plans.f.operations", "plans.f.stripe",
  "plans.f.metering", "plans.f.delivery", "plans.f.exports", "plans.f.portability"
] as const;

const hostedPlanned = [
  "plans.f.autoscaling", "plans.f.backups", "plans.f.analytics", "plans.f.support"
] as const;

const institutionAvailable = ["plans.f.canvasImport", "plans.f.canvas"] as const;
const institutionPlanned = [
  "plans.f.rbac", "plans.f.sso", "plans.f.auditRetention", "plans.f.lms",
  "plans.f.additionalLms", "plans.f.retention", "plans.f.policyWorkers",
  "plans.f.sla", "plans.f.enterpriseDeploy", "plans.f.prioritySupport"
] as const;

export function PlanCatalog() {
  const { t } = useI18n();
  return (
    <div className="grid gap-5 xl:grid-cols-3">
      <PlanCard
        audience={t("plans.communityAudience")}
        cta={t("plans.communityCta")}
        features={communityFeatures.map((key) => t(key))}
        href="/assignments"
        name={t("plans.community")}
        price={t("plans.communityPrice")}
        sectionTitle={t("plans.included")}
      />
      <PlanCard
        audience={t("plans.hostedAudience")}
        badge={t("plans.hostedBadge")}
        cta={t("plans.hostedCta")}
        features={hostedFeatures.map((key) => t(key))}
        href="/billing"
        name={t("plans.hosted")}
        planned={hostedPlanned.map((key) => t(key))}
        plannedTitle={t("plans.enhancements")}
        price={t("plans.hostedPrice")}
        sectionTitle={t("plans.included")}
      />
      <PlanCard
        audience={t("plans.institutionAudience")}
        availableLabel={t("plans.availableNow")}
        cta={t("plans.institutionCta")}
        features={institutionAvailable.map((key) => t(key))}
        href="/integrations"
        name={t("plans.institution")}
        planned={institutionPlanned.map((key) => t(key))}
        plannedTitle={t("plans.designPartner")}
        price={t("plans.institutionPrice")}
        sectionTitle={t("plans.included")}
      />
    </div>
  );
}

function PlanCard({
  name, price, audience, badge, features, planned = [], sectionTitle,
  plannedTitle, availableLabel, href, cta
}: {
  name: string;
  price: string;
  audience: string;
  badge?: string;
  features: string[];
  planned?: string[];
  sectionTitle: string;
  plannedTitle?: string;
  availableLabel?: string;
  href: Route;
  cta: string;
}) {
  const { t } = useI18n();
  return (
    <article className="panel flex flex-col overflow-hidden p-5 sm:p-6">
      <div className="min-h-48 border-b pb-5">
        <div className="flex items-start justify-between gap-3"><h2 className="text-2xl font-semibold">{name}</h2>{badge ? <span className="rounded-full border border-primary/25 bg-primary/10 px-2.5 py-1 font-mono text-[0.64rem] font-semibold uppercase tracking-wider text-primary">{badge}</span> : null}</div>
        <p className="mt-4 text-3xl font-semibold tracking-tight">{price}</p>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">{audience}</p>
      </div>
      <div className="flex-1 py-5">
        <p className="eyebrow">{sectionTitle}</p>
        <ul className="mt-4 space-y-3">{features.map((feature) => <li className="flex items-start gap-2.5 text-sm" key={feature}><Check aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-success" /><span>{feature}{availableLabel ? <span className="mt-1 block font-mono text-[0.62rem] uppercase tracking-wide text-primary">{availableLabel}</span> : null}</span></li>)}</ul>
        {planned.length ? <div className="mt-7 border-t pt-5"><p className="eyebrow">{plannedTitle}</p><ul className="mt-4 space-y-3">{planned.map((feature) => <li className="flex items-start gap-2.5 text-sm text-muted-foreground" key={feature}><Clock3 aria-hidden="true" className="mt-0.5 size-4 shrink-0" /><span>{feature}<span className="mt-1 block font-mono text-[0.62rem] uppercase tracking-wide">{t("plans.planned")}</span></span></li>)}</ul></div> : null}
      </div>
      <Link className={buttonStyles({ className: "mt-5 w-full", variant: name === t("plans.hosted") ? "primary" : "secondary" })} href={href}>{cta}</Link>
    </article>
  );
}
