"use client";

import { useEffect, useState } from "react";

import {
  defaultSettings,
  getSettings,
  subscribeToSettings,
  type AppSettings
} from "@/lib/storage";

export function useSettings(): AppSettings {
  const [settings, setSettings] = useState<AppSettings>(defaultSettings);

  useEffect(() => {
    const refresh = () => setSettings(getSettings());
    refresh();
    return subscribeToSettings(refresh);
  }, []);

  return settings;
}
