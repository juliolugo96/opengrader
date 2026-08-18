"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useLayoutEffect, useState, type ReactNode } from "react";

import { getSettings, subscribeToSettings } from "@/lib/storage";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: (attempt, error) => {
              const status = typeof error === "object" && error && "status" in error
                ? Number(error.status)
                : 0;
              return status >= 400 && status < 500 ? false : attempt < 2;
            },
            staleTime: 2_000,
            refetchOnWindowFocus: true
          },
          mutations: { retry: false }
        }
      })
  );

  useLayoutEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const applyTheme = () => {
      const theme = getSettings().theme;
      document.documentElement.classList.toggle(
        "dark",
        theme === "dark" || (theme === "system" && media.matches)
      );
    };
    applyTheme();
    const unsubscribe = subscribeToSettings(applyTheme);
    media.addEventListener("change", applyTheme);
    return () => {
      unsubscribe();
      media.removeEventListener("change", applyTheme);
    };
  }, []);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
