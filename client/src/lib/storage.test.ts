import { describe, expect, it, vi } from "vitest";

import { defaultSettings, getSettings, normalizeBaseUrl, saveSettings, SETTINGS_CHANGED_EVENT } from "@/lib/storage";

describe("settings storage", () => {
  it("uses safe defaults for missing or malformed values", () => {
    expect(getSettings()).toEqual(defaultSettings);
    window.localStorage.setItem("opengrader.settings.v1", "not-json");
    expect(getSettings()).toEqual(defaultSettings);
  });

  it("normalizes and announces saved settings", () => {
    const listener = vi.fn();
    window.addEventListener(SETTINGS_CHANGED_EVENT, listener);

    const saved = saveSettings({
      apiBaseUrl: " http://localhost:8000/// ",
      apiKey: " test-key ",
      theme: "dark",
      locale: "es"
    });

    expect(saved).toEqual({ apiBaseUrl: "http://localhost:8000", apiKey: "test-key", theme: "dark", locale: "es" });
    expect(getSettings()).toEqual(saved);
    expect(listener).toHaveBeenCalledOnce();
    window.removeEventListener(SETTINGS_CHANGED_EVENT, listener);
  });

  it("normalizes empty and trailing-slash URLs", () => {
    expect(normalizeBaseUrl("https://grader.example///")).toBe("https://grader.example");
    expect(normalizeBaseUrl(" ")).toBe(defaultSettings.apiBaseUrl);
  });
});
