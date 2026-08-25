"use client";

import { BookOpen, Cable, ClipboardList, CreditCard, FileCheck2, History, Layers3, ScanSearch, Settings2 } from "lucide-react";
import type { Route } from "next";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { BrandWordmark } from "@/components/layout/BrandLogo";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

const navigation = [
  { href: "/assignments", key: "nav.assignments", icon: BookOpen },
  { href: "/jobs", key: "nav.jobs", icon: ClipboardList },
  { href: "/pdf", key: "nav.pdf", icon: FileCheck2 },
  { href: "/similarity" as Route, key: "nav.similarity", icon: ScanSearch },
  { href: "/integrations", key: "nav.integrations", icon: Cable },
  { href: "/audit", key: "nav.audit", icon: History },
  { href: "/billing", key: "nav.billing", icon: CreditCard },
  { href: "/plans", key: "nav.plans", icon: Layers3 },
  { href: "/settings", key: "nav.settings", icon: Settings2 }
] as const satisfies ReadonlyArray<{ href: Route; key: string; icon: typeof BookOpen }>;

export function AppSidebar() {
  const pathname = usePathname();
  const { t } = useI18n();

  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r bg-card/90 p-5 backdrop-blur-xl md:flex md:flex-col">
        <Link aria-label="OpenGrader" className="block rounded-xl" href="/assignments">
          <span className="block rounded-xl border border-slate-200/80 bg-white px-3 py-2 shadow-sm">
            <BrandWordmark />
          </span>
          <span className="mt-2 block px-1 font-mono text-[0.62rem] uppercase tracking-[0.18em] text-muted-foreground">
            {t("nav.console")}
          </span>
        </Link>

        <nav aria-label="Primary navigation" className="mt-10 space-y-1.5">
          {navigation.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;
            return (
              <Link
                aria-current={active ? "page" : undefined}
                className={cn(
                  "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition",
                  active
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
                href={item.href}
                key={item.href}
              >
                <Icon aria-hidden="true" className="size-[1.1rem]" strokeWidth={1.8} />
                {t(item.key)}
                {active ? <span className="ml-auto size-1.5 rounded-full bg-primary" /> : null}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto rounded-2xl border bg-muted/45 p-4">
          <p className="eyebrow">{t("nav.localFirst")}</p>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">
            {t("nav.localFirstBody")}
          </p>
        </div>
      </aside>

      <nav
        aria-label="Mobile navigation"
        className="fixed inset-x-3 bottom-3 z-40 flex overflow-x-auto rounded-2xl border bg-card/95 p-1.5 shadow-panel backdrop-blur-xl md:hidden"
      >
        {navigation.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex min-w-[4.75rem] flex-1 flex-col items-center gap-1 rounded-xl py-2 text-[0.68rem] font-medium",
                active ? "bg-primary/10 text-primary" : "text-muted-foreground"
              )}
              href={item.href}
              key={item.href}
            >
              <Icon aria-hidden="true" className="size-4" />
              <span className="max-w-full truncate px-0.5">{t(item.key)}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
