"use client";

import { useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Eye, EyeOff, KeyRound, Loader2, Save, Server, ShieldCheck, Unplug } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { testConnection } from "@/lib/api-client";
import { saveSettings, type AppSettings } from "@/lib/storage";
import { useSettings } from "@/lib/use-settings";
import { cn } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";

type ConnectionState = { kind: "idle" | "testing" | "success" | "error"; message?: string };

export default function SettingsPage() {
  const settings = useSettings();
  const settingsKey = `${settings.apiBaseUrl}:${settings.apiKey}:${settings.theme}:${settings.locale}`;
  return <SettingsForm initialSettings={settings} key={settingsKey} />;
}

function SettingsForm({ initialSettings }: { initialSettings: AppSettings }) {
  const [form, setForm] = useState<AppSettings>(initialSettings);
  const [showKey, setShowKey] = useState(false);
  const [saved, setSaved] = useState(false);
  const [connection, setConnection] = useState<ConnectionState>({ kind: "idle" });
  const queryClient = useQueryClient();
  const { t } = useI18n();

  const persist = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const error = validateSettings(form);
    if (error) {
      setConnection({ kind: "error", message: error });
      return;
    }
    const normalized = saveSettings(form);
    setForm(normalized);
    setSaved(true);
    setConnection({ kind: "idle" });
    await queryClient.invalidateQueries();
    window.setTimeout(() => setSaved(false), 1_800);
  };

  const checkConnection = async () => {
    const error = validateSettings(form);
    if (error) {
      setConnection({ kind: "error", message: error });
      return;
    }
    setConnection({ kind: "testing" });
    try {
      const health = await testConnection(form);
      setConnection({ kind: "success", message: t("settings.connected", { version: health.version }) });
    } catch (connectionError) {
      setConnection({ kind: "error", message: connectionError instanceof Error ? connectionError.message : t("settings.connectionFailed") });
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-7">
      <div>
        <p className="eyebrow">{t("settings.eyebrow")}</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">{t("settings.title")}</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{t("settings.subtitle")}</p>
      </div>

      <Card className="overflow-hidden">
        <div className="flex items-center gap-3 border-b bg-muted/30 p-5 sm:px-7">
          <span className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary"><Server aria-hidden="true" className="size-5" /></span>
          <div><h2 className="font-semibold">OpenGrader API</h2><p className="mt-1 text-xs text-muted-foreground">{t("settings.apiBody")}</p></div>
        </div>
        <form className="space-y-6 p-5 sm:p-7" onSubmit={persist}>
          <Field
            hint={t("settings.urlHint")}
            label={t("settings.url")}
            name="apiBaseUrl"
            onChange={(event) => setForm((current) => ({ ...current, apiBaseUrl: event.target.value }))}
            placeholder="http://localhost:8000"
            spellCheck={false}
            type="url"
            value={form.apiBaseUrl}
          />
          <div className="relative">
            <Field
              autoComplete="off"
              hint={t("settings.keyHint")}
              label={t("settings.key")}
              name="apiKey"
              onChange={(event) => setForm((current) => ({ ...current, apiKey: event.target.value }))}
              placeholder={t("settings.keyPlaceholder")}
              spellCheck={false}
              type={showKey ? "text" : "password"}
              value={form.apiKey}
            />
            <Button aria-label={showKey ? "Hide API key" : "Show API key"} className="absolute right-1 top-7" onClick={() => setShowKey((visible) => !visible)} size="icon" variant="ghost">
              {showKey ? <EyeOff aria-hidden="true" className="size-4" /> : <Eye aria-hidden="true" className="size-4" />}
            </Button>
          </div>
          <label className="block space-y-2">
            <span className="text-sm font-medium">{t("settings.appearance")}</span>
            <select className="h-11 w-full rounded-xl border bg-background px-3 text-sm" onChange={(event) => setForm((current) => ({ ...current, theme: event.target.value as AppSettings["theme"] }))} value={form.theme}>
              <option value="system">{t("settings.system")}</option>
              <option value="light">{t("settings.light")}</option>
              <option value="dark">{t("settings.dark")}</option>
            </select>
          </label>
          <label className="block space-y-2">
            <span className="text-sm font-medium">{t("settings.language")}</span>
            <select className="h-11 w-full rounded-xl border bg-background px-3 text-sm" onChange={(event) => setForm((current) => ({ ...current, locale: event.target.value as AppSettings["locale"] }))} value={form.locale}>
              <option value="en">{t("settings.english")}</option>
              <option value="es">{t("settings.spanish")}</option>
              <option value="zh-CN">{t("settings.chinese")}</option>
            </select>
          </label>

          {connection.kind !== "idle" ? (
            <div className={cn(
              "flex items-center gap-3 rounded-xl border p-3 text-sm",
              connection.kind === "success" && "border-success/25 bg-success/10 text-success",
              connection.kind === "error" && "border-danger/25 bg-danger/10 text-danger",
              connection.kind === "testing" && "bg-muted text-muted-foreground"
            )} role="status">
              {connection.kind === "testing" ? <Loader2 aria-hidden="true" className="size-4 animate-spin" />
                : connection.kind === "success" ? <CheckCircle2 aria-hidden="true" className="size-4" />
                  : <Unplug aria-hidden="true" className="size-4" />}
              {connection.kind === "testing" ? t("settings.testing") : connection.message}
            </div>
          ) : null}

          <div className="flex flex-col-reverse gap-3 border-t pt-6 sm:flex-row sm:justify-end">
            <Button disabled={connection.kind === "testing"} onClick={checkConnection} variant="secondary">
              {connection.kind === "testing" ? <Loader2 aria-hidden="true" className="size-4 animate-spin" /> : <ShieldCheck aria-hidden="true" className="size-4" />}
              {t("settings.test")}
            </Button>
            <Button type="submit">
              {saved ? <CheckCircle2 aria-hidden="true" className="size-4" /> : <Save aria-hidden="true" className="size-4" />}
              {saved ? t("settings.saved") : t("settings.save")}
            </Button>
          </div>
        </form>
      </Card>

      <Card className="flex gap-4 border-warning/20 bg-warning/5 p-5 sm:p-6">
        <KeyRound aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-warning" />
        <div><h2 className="text-sm font-semibold">{t("settings.credentialTitle")}</h2><p className="mt-1 text-xs leading-5 text-muted-foreground">{t("settings.credentialBody")}</p></div>
      </Card>
    </div>
  );
}

function validateSettings(settings: AppSettings): string | null {
  if (!settings.apiKey.trim()) return "Enter an API key.";
  try {
    const url = new URL(settings.apiBaseUrl);
    if (url.protocol !== "http:" && url.protocol !== "https:") return "API URL must use HTTP or HTTPS.";
  } catch {
    return "Enter a valid API base URL.";
  }
  return null;
}
