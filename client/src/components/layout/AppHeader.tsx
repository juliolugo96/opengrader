"use client";

import { useQuery } from "@tanstack/react-query";
import { Moon, Sun } from "lucide-react";
import { usePathname } from "next/navigation";

import { BrandMark } from "@/components/layout/BrandLogo";
import { Button } from "@/components/ui/Button";
import { testConnection } from "@/lib/api-client";
import { getSettings, saveSettings } from "@/lib/storage";
import { useSettings } from "@/lib/use-settings";
import { useI18n } from "@/lib/i18n";

export function AppHeader() {
  const pathname = usePathname();
  const settings = useSettings();
  const { t } = useI18n();
  const section = pathname.split("/").filter(Boolean)[0] ?? "assignments";
  const pageNames = { assignments: t("nav.assignments"), jobs: t("nav.jobs"), pdf: t("nav.pdf"), audit: t("nav.audit"), billing: t("nav.billing"), settings: t("nav.settings") } as Record<string, string>;
  const connection = useQuery({
    queryKey: ["connection", settings.apiBaseUrl, Boolean(settings.apiKey)],
    queryFn: () => testConnection(),
    enabled: Boolean(settings.apiKey),
    retry: false,
    refetchInterval: 30_000
  });
  const toggleTheme = () => {
    const currentIsDark = document.documentElement.classList.contains("dark");
    saveSettings({ ...getSettings(), theme: currentIsDark ? "light" : "dark" });
  };

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b bg-background/80 px-4 backdrop-blur-xl sm:px-6 lg:px-10">
      <div className="flex items-center gap-3">
        <span className="size-10 rounded-xl border border-slate-200/80 bg-white p-1.5 shadow-sm md:hidden">
          <BrandMark />
        </span>
        <div>
          <p className="eyebrow hidden sm:block">{t("nav.workspace")}</p>
          <p className="text-sm font-semibold">{pageNames[section] ?? t("nav.detail")}</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <div className="hidden items-center gap-2 rounded-full border bg-card px-3 py-2 sm:flex">
          <span
            className={`size-2 rounded-full ${connection.isSuccess ? "bg-success" : connection.isError ? "bg-danger" : "bg-muted-foreground/50"}`}
          />
          <span className="font-mono text-[0.65rem] uppercase tracking-[0.1em] text-muted-foreground">
            {!settings.apiKey ? t("nav.notConfigured") : connection.isSuccess ? t("nav.online") : connection.isPending ? t("nav.checking") : t("nav.unavailable")}
          </span>
        </div>
        <Button aria-label={t("nav.toggleTheme")} onClick={toggleTheme} size="icon" variant="ghost">
          <Moon aria-hidden="true" className="size-4 dark:hidden" />
          <Sun aria-hidden="true" className="hidden size-4 dark:block" />
        </Button>
      </div>
    </header>
  );
}
