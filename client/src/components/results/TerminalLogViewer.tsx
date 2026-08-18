"use client";

import { Check, Copy, Terminal } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/Button";

export function TerminalLogViewer({ label, output }: { label: "stdout" | "stderr"; output: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(output);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1_500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <section className="overflow-hidden rounded-xl border border-slate-700/80 bg-[#090d13] text-slate-200">
      <div className="flex items-center justify-between border-b border-slate-800 px-3 py-2">
        <span className="flex items-center gap-2 font-mono text-[0.68rem] uppercase tracking-[0.12em] text-slate-400">
          <Terminal aria-hidden="true" className="size-3.5" />
          {label}
        </span>
        <Button
          aria-label={`Copy ${label}`}
          className="size-8 text-slate-400 hover:bg-slate-800 hover:text-slate-100"
          disabled={!output}
          onClick={copy}
          size="icon"
          variant="ghost"
        >
          {copied ? <Check aria-hidden="true" className="size-3.5 text-emerald-400" /> : <Copy aria-hidden="true" className="size-3.5" />}
        </Button>
      </div>
      <pre className="terminal-scrollbar max-h-56 min-h-20 overflow-auto whitespace-pre-wrap break-words p-4 font-mono text-xs leading-5">
        {output || <span className="text-slate-600">No output captured.</span>}
      </pre>
    </section>
  );
}
