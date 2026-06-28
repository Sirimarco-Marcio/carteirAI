import { Skeleton } from "@/components/ui";

/** Tela de carregamento da página Cartões (Suspense de rota). */
export default function Loading() {
  return (
    <div className="mx-auto max-w-6xl">
      {/* Cabeçalho */}
      <Skeleton className="h-9 w-40" />
      <Skeleton className="mt-2 h-5 w-72" />

      {/* Grid de cartões skeleton */}
      <div className="mt-6 flex gap-4 overflow-x-auto pb-1 lg:grid lg:grid-cols-3 lg:overflow-visible">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="min-w-[260px] flex-shrink-0 lg:min-w-0">
            <Skeleton className="h-52 w-full rounded-lg" />
          </div>
        ))}
      </div>

      {/* Seção inferior: fatura + histórico */}
      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_300px]">
        <Skeleton className="h-80 w-full rounded-lg" />
        <Skeleton className="h-56 w-full rounded-lg" />
      </div>
    </div>
  );
}
