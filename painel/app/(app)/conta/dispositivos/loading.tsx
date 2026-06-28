import { Skeleton } from "@/components/ui";

export default function DispositivosLoading() {
  return (
    <div className="mx-auto max-w-2xl">
      {/* Cabeçalho skeleton */}
      <header className="pr-28 lg:pr-0">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="mt-3 h-9 w-64" />
        <Skeleton className="mt-2 h-4 w-80" />
      </header>

      {/* Aviso skeleton */}
      <Skeleton className="mt-5 h-14 w-full rounded-md" />

      {/* Lista skeleton — 2 itens */}
      <ul className="mt-6 space-y-3">
        {[0, 1].map((i) => (
          <li
            key={i}
            className="flex items-center gap-4 rounded-lg border border-line bg-surface px-5 py-4"
          >
            {/* Ícone */}
            <Skeleton className="h-10 w-10 shrink-0 rounded-full" />

            {/* Nome + último envio */}
            <div className="min-w-0 flex-1 space-y-2">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3 w-28" />
            </div>

            {/* Badge + botão */}
            <div className="flex shrink-0 flex-col items-end gap-2 sm:flex-row sm:items-center sm:gap-3">
              <Skeleton className="h-6 w-14 rounded-full" />
              <Skeleton className="h-7 w-24 rounded-md" />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
