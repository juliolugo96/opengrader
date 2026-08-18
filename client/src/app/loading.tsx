import { Skeleton } from "@/components/ui/Skeleton";

export default function AppLoading() {
  return (
    <div aria-label="Loading page" className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-10 w-72 max-w-full" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton className="h-32" key={index} />
        ))}
      </div>
      <Skeleton className="h-96" />
    </div>
  );
}
