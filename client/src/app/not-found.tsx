import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { buttonStyles } from "@/components/ui/Button";

export default function NotFound() {
  return (
    <section className="panel mx-auto max-w-xl p-10 text-center">
      <p className="eyebrow">404 · Not found</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight">That gradebook is off the roster</h1>
      <p className="mt-3 text-muted-foreground">The requested page or job does not exist.</p>
      <Link className={buttonStyles({ className: "mt-7" })} href="/jobs">
        <ArrowLeft aria-hidden="true" className="size-4" />
        Back to jobs
      </Link>
    </section>
  );
}
