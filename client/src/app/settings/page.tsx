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

type ConnectionState = { kind: "idle" | "testing" | "success" | "error"; message?: string };

export default function SettingsPage() {
  const settings = useSettings();
  const settingsKey = `${settings.apiBaseUrl}:${settings.apiKey}:${settings.theme}`;
  return <SettingsForm initialSettings={settings} key={settingsKey} />;
}

function SettingsForm({ initialSettings }: { initialSettings: AppSettings }) {
  const [form, setForm] = useState<AppSettings>(initialSettings);
  const [showKey, setShowKey] = useState(false);
  const [saved, setSaved] = useState(false);
  const [connection, setConnection] = useState<ConnectionState>({ kind: "idle" });
  const queryClient = useQueryClient();

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
      setConnection({ kind: "success", message: `Connected to OpenGrader ${health.version}` });
    } catch (connectionError) {
      setConnection({ kind: "error", message: connectionError instanceof Error ? connectionError.message : "Connection failed" });
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-7">
      <div>
        <p className="eyebrow">Browser-local configuration</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">Connection settings</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">Connect this dashboard to one OpenGrader API. Settings never leave this browser except when proxying authenticated requests to your selected host.</p>
      </div>

      <Card className="overflow-hidden">
        <div className="flex items-center gap-3 border-b bg-muted/30 p-5 sm:px-7">
          <span className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary"><Server aria-hidden="true" className="size-5" /></span>
          <div><h2 className="font-semibold">OpenGrader API</h2><p className="mt-1 text-xs text-muted-foreground">Used for health, jobs, results, and audit events.</p></div>
        </div>
        <form className="space-y-6 p-5 sm:p-7" onSubmit={persist}>
          <Field
            hint="The default local API listens on port 8000. The dashboard deployment must allow this hostname."
            label="API base URL"
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
              hint="Sent as a bearer credential to protected /v1 endpoints."
              label="API key"
              name="apiKey"
              onChange={(event) => setForm((current) => ({ ...current, apiKey: event.target.value }))}
              placeholder="Paste your OpenGrader API key"
              spellCheck={false}
              type={showKey ? "text" : "password"}
              value={form.apiKey}
            />
            <Button aria-label={showKey ? "Hide API key" : "Show API key"} className="absolute right-1 top-7" onClick={() => setShowKey((visible) => !visible)} size="icon" variant="ghost">
              {showKey ? <EyeOff aria-hidden="true" className="size-4" /> : <Eye aria-hidden="true" className="size-4" />}
            </Button>
          </div>
          <label className="block space-y-2">
            <span className="text-sm font-medium">Appearance</span>
            <select className="h-11 w-full rounded-xl border bg-background px-3 text-sm" onChange={(event) => setForm((current) => ({ ...current, theme: event.target.value as AppSettings["theme"] }))} value={form.theme}>
              <option value="system">Follow system</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
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
              {connection.kind === "testing" ? "Testing health and authentication…" : connection.message}
            </div>
          ) : null}

          <div className="flex flex-col-reverse gap-3 border-t pt-6 sm:flex-row sm:justify-end">
            <Button disabled={connection.kind === "testing"} onClick={checkConnection} variant="secondary">
              {connection.kind === "testing" ? <Loader2 aria-hidden="true" className="size-4 animate-spin" /> : <ShieldCheck aria-hidden="true" className="size-4" />}
              Test connection
            </Button>
            <Button type="submit">
              {saved ? <CheckCircle2 aria-hidden="true" className="size-4" /> : <Save aria-hidden="true" className="size-4" />}
              {saved ? "Saved" : "Save settings"}
            </Button>
          </div>
        </form>
      </Card>

      <Card className="flex gap-4 border-warning/20 bg-warning/5 p-5 sm:p-6">
        <KeyRound aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-warning" />
        <div><h2 className="text-sm font-semibold">Credential handling</h2><p className="mt-1 text-xs leading-5 text-muted-foreground">The key is stored in localStorage, so use this dashboard only on a trusted device and origin. The proxy does not log or persist it. For a shared deployment, use a dedicated reverse proxy and scoped credentials when the backend supports them.</p></div>
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
