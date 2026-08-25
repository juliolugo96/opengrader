"use client";

import { PlanCatalog } from "@/components/plans/PlanCatalog";
import { useI18n } from "@/lib/i18n";

export default function PlansPage() {
  const { t } = useI18n();
  return (
    <div className="space-y-7">
      <div><p className="eyebrow">{t("plans.eyebrow")}</p><h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">{t("plans.title")}</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{t("plans.subtitle")}</p></div>
      <PlanCatalog />
    </div>
  );
}
