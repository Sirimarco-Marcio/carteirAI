import { Skeleton } from "@/components/ui";

/** Tela de carregamento do extrato de transações (Suspense de rota). */
export default function LoadingTransacoes() {
  return (
    <div className="mx-auto max-w-6xl">
      {/* Cabeçalho */}
      <Skeleton className="h-9 w-36" />
      <Skeleton className="mt-2 h-5 w-72" />

      {/* Barra de filtros */}
      <Skeleton className="mt-6 h-16 w-full rounded-lg" />

      {/* Seção pendentes */}
      <div className="mt-6">
        <Skeleton className="h-7 w-56" />
        <Skeleton className="mt-3 h-36 w-full rounded-lg" />
      </div>

      {/* Seção confirmadas */}
      <div className="mt-6">
        <Skeleton className="h-7 w-40" />
        <div className="mt-3 space-y-px overflow-hidden rounded-lg border border-line">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full rounded-none" />
          ))}
        </div>
      </div>
    </div>
  );
}
