import { Skeleton } from "@/components/ui";

/** Skeleton de carregamento da página de Renda. */
export default function Loading() {
  return (
    <div className="mx-auto max-w-6xl">
      {/* Cabeçalho */}
      <Skeleton className="h-9 w-32" />
      <Skeleton className="mt-2 h-5 w-24" />

      {/* Card: fontes de renda */}
      <div className="mt-6 rounded-lg border border-line bg-surface p-6">
        <Skeleton className="h-6 w-44" />
        <div className="mt-4 divide-y divide-line">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center justify-between py-4">
              <div className="space-y-2">
                <Skeleton className="h-4 w-28" />
                <Skeleton className="h-3 w-20" />
              </div>
              <div className="flex gap-6">
                <div className="space-y-1 text-right">
                  <Skeleton className="ml-auto h-3 w-14" />
                  <Skeleton className="ml-auto h-4 w-20" />
                </div>
                <div className="space-y-1 text-right">
                  <Skeleton className="ml-auto h-3 w-14" />
                  <Skeleton className="ml-auto h-4 w-20" />
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 flex justify-between border-t border-line pt-4">
          <Skeleton className="h-4 w-36" />
          <Skeleton className="h-4 w-28" />
        </div>
      </div>

      {/* Card: calendário */}
      <div className="mt-4 rounded-lg border border-line bg-surface p-6">
        <Skeleton className="h-6 w-56" />
        <div className="mt-4 grid grid-cols-7 gap-1">
          {Array.from({ length: 7 }).map((_, i) => (
            <Skeleton key={`cab-${i}`} className="h-5 w-full" />
          ))}
          {Array.from({ length: 35 }).map((_, i) => (
            <Skeleton key={`dia-${i}`} className="aspect-square w-full rounded-md" />
          ))}
        </div>
        <div className="mt-4 flex gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-4 w-24" />
          ))}
        </div>
      </div>

      {/* Card: fechar mês */}
      <div className="mt-4 rounded-lg border border-line bg-surface p-6">
        <Skeleton className="h-6 w-36" />
        <Skeleton className="mt-1 h-4 w-64" />
        <div className="mt-4 space-y-3">
          <Skeleton className="h-8 w-full" />
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
          <Skeleton className="h-10 w-full" />
        </div>
        <Skeleton className="mt-4 h-20 w-full rounded-md" />
        <div className="mt-6 flex justify-end">
          <Skeleton className="h-11 w-44 rounded-md" />
        </div>
      </div>
    </div>
  );
}
