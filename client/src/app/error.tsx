"use client";

import { AlertTriangle, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/Button";

export default function AppError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <section className="panel mx-auto max-w-2xl p-8 text-center" role="alert">
      <span className="mx-auto flex size-12 items-center justify-center rounded-2xl bg-danger/10 text-danger">
        <AlertTriangle aria-hidden="true" className="size-6" />
      </span>
      <p className="eyebrow mt-5">Unexpected error</p>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight">This view could not be rendered</h1>
      <p className="mt-3 text-sm text-muted-foreground">{error.message}</p>
      <Button className="mt-6" onClick={reset}>
        <RotateCcw aria-hidden="true" className="size-4" />
        Try again
      </Button>
    </section>
  );
}
