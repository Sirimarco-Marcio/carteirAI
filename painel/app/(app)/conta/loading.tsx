import { Skeleton } from "@/components/ui";

/** Skeleton de carregamento da página Conta/Configurações. */
export default function Loading() {
  return (
    <div className="mx-auto max-w-2xl">
      {/* Título */}
      <Skeleton className="h-9 w-32" />

      {/* Perfil */}
      <div className="mt-6 flex items-center gap-4 rounded-lg border border-line bg-surface p-5">
        <Skeleton className="h-14 w-14 rounded-full" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-4 w-24" />
        </div>
      </div>

      {/* Contas & cartões */}
      <div className="mt-4 rounded-lg border border-line bg-surface p-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-8 w-32 rounded-md" />
        </div>
        <div className="mt-4 space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-start gap-4 py-1">
              <Skeleton className="h-10 w-10 rounded-full" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-28" />
                <Skeleton className="h-3 w-48" />
              </div>
              <div className="space-y-1 text-right">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-4 w-20" />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Categorias */}
      <div className="mt-4 rounded-lg border border-line bg-surface p-6">
        <Skeleton className="h-5 w-28" />
        <div className="mt-4 flex flex-wrap gap-2">
          {Array.from({ length: 12 }).map((_, i) => (
            <Skeleton key={i} className="h-7 w-20 rounded-full" />
          ))}
        </div>
      </div>

      {/* Família */}
      <div className="mt-4 rounded-lg border border-line bg-surface p-6">
        <Skeleton className="h-5 w-20" />
        <div className="mt-4 space-y-3">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 py-1">
              <Skeleton className="h-10 w-10 rounded-full" />
              <Skeleton className="h-4 w-24 flex-1" />
              <Skeleton className="h-6 w-24 rounded-full" />
            </div>
          ))}
        </div>
      </div>

      {/* Navegação */}
      <div className="mt-4 overflow-hidden rounded-lg border border-line bg-surface">
        <div className="flex items-center gap-3 border-b border-line px-6 py-4">
          <Skeleton className="h-8 w-8 rounded-full" />
          <Skeleton className="h-4 w-44" />
        </div>
        <div className="flex items-center gap-3 px-6 py-4">
          <Skeleton className="h-8 w-8 rounded-full" />
          <Skeleton className="h-4 w-16" />
        </div>
      </div>
    </div>
  );
}
