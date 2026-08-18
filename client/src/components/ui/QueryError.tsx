import { AlertCircle, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/Button";

export function QueryError({ error, retry }: { error: Error; retry: () => void }) {
  return (
    <div className="flex min-h-64 flex-col items-center justify-center px-6 py-12 text-center" role="alert">
      <span className="flex size-11 items-center justify-center rounded-2xl bg-danger/10 text-danger">
        <AlertCircle aria-hidden="true" className="size-5" />
      </span>
      <h3 className="mt-4 font-semibold">Could not load this data</h3>
      <p className="mt-2 max-w-lg text-sm text-muted-foreground">{error.message}</p>
      <Button className="mt-5" onClick={retry} size="sm" variant="secondary">
        <RefreshCw aria-hidden="true" className="size-4" />
        Try again
      </Button>
    </div>
  );
}
