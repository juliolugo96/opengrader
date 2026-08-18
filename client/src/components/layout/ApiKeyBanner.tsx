"use client";

import { KeyRound } from "lucide-react";
import Link from "next/link";

import { buttonStyles } from "@/components/ui/Button";
import { useSettings } from "@/lib/use-settings";

export function ApiKeyBanner() {
  const settings = useSettings();
  if (settings.apiKey) return null;

  return (
    <div className="border-b border-warning/25 bg-warning/10 px-4 py-3 sm:px-6 lg:px-10" role="status">
      <div className="mx-auto flex max-w-[1600px] flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3 text-sm">
          <KeyRound aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-warning" />
          <p><span className="font-semibold">API credentials required.</span> Add your local OpenGrader URL and bearer key to load grading data.</p>
        </div>
        <Link className={buttonStyles({ variant: "secondary", size: "sm", className: "shrink-0 bg-background/70" })} href="/settings">
          Configure connection
        </Link>
      </div>
    </div>
  );
}
