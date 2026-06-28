import { Skeleton } from "@/components/ui";

/** Tela de carregamento padrão do grupo (Suspense de rota). */
export default function Loading() {
  return (
    <div className="mx-auto max-w-6xl">
      <Skeleton className="h-9 w-56" />
      <Skeleton className="mt-2 h-5 w-32" />
      <Skeleton className="mt-6 h-32 w-full rounded-lg" />
      <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 w-full rounded-lg" />
        ))}
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-72 w-full rounded-lg" />
        <Skeleton className="h-72 w-full rounded-lg" />
      </div>
    </div>
  );
}
