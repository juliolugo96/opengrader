export interface AppSettings {
  apiBaseUrl: string;
  apiKey: string;
  theme: "light" | "dark" | "system";
}

const STORAGE_KEY = "opengrader.settings.v1";
export const SETTINGS_CHANGED_EVENT = "opengrader:settings-changed";

export const defaultSettings: AppSettings = {
  apiBaseUrl: "http://localhost:8000",
  apiKey: "",
  theme: "system"
};

export function getSettings(): AppSettings {
  if (typeof window === "undefined") return defaultSettings;

  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) return defaultSettings;
    const parsed = JSON.parse(stored) as Partial<AppSettings>;
    return {
      apiBaseUrl: normalizeBaseUrl(parsed.apiBaseUrl ?? defaultSettings.apiBaseUrl),
      apiKey: typeof parsed.apiKey === "string" ? parsed.apiKey : "",
      theme: isTheme(parsed.theme) ? parsed.theme : "system"
    };
  } catch {
    return defaultSettings;
  }
}

export function saveSettings(settings: AppSettings): AppSettings {
  const normalized = {
    ...settings,
    apiBaseUrl: normalizeBaseUrl(settings.apiBaseUrl),
    apiKey: settings.apiKey.trim()
  };
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
  window.dispatchEvent(new CustomEvent(SETTINGS_CHANGED_EVENT));
  return normalized;
}

export function subscribeToSettings(listener: () => void): () => void {
  window.addEventListener("storage", listener);
  window.addEventListener(SETTINGS_CHANGED_EVENT, listener);
  return () => {
    window.removeEventListener("storage", listener);
    window.removeEventListener(SETTINGS_CHANGED_EVENT, listener);
  };
}

export function normalizeBaseUrl(value: string): string {
  const trimmed = value.trim().replace(/\/+$/, "");
  return trimmed || defaultSettings.apiBaseUrl;
}

function isTheme(value: unknown): value is AppSettings["theme"] {
  return value === "light" || value === "dark" || value === "system";
}
