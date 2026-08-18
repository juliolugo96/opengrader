"use client";

import { FileText } from "lucide-react";
import { useEffect, useState } from "react";

export function PdfPreview({ blob, title }: { blob?: Blob; title: string }) {
  if (!blob) {
    return (
      <div aria-label="Loading PDF preview" className="flex min-h-[38rem] items-center justify-center rounded-2xl border bg-muted/30 text-muted-foreground">
        <FileText aria-hidden="true" className="size-8 animate-pulse" />
      </div>
    );
  }
  return <LoadedPdf blob={blob} title={title} />;
}

function LoadedPdf({ blob, title }: { blob: Blob; title: string }) {
  const [url] = useState(() => URL.createObjectURL(blob));
  useEffect(() => () => URL.revokeObjectURL(url), [url]);
  return <object aria-label={`${title} PDF preview`} className="min-h-[48rem] w-full rounded-2xl border bg-white" data={url} type="application/pdf" />;
}
