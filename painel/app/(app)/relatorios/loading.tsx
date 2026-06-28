import { Skeleton } from "@/components/ui";

/** Skeleton de carregamento da página de relatório mensal. */
export default function RelatoriosLoading() {
  return (
    <div className="mx-auto max-w-6xl">
      {/* Cabeçalho */}
      <Skeleton className="h-4 w-20" />
      <Skeleton className="mt-2 h-9 w-60" />
      <Skeleton className="mt-3 h-9 w-48 rounded-lg" />

      {/* Renda por fonte */}
      <div className="mt-8">
        <Skeleton className="h-4 w-28 border-b border-line pb-2" />
        <Skeleton className="mt-3 h-40 w-full rounded-lg" />
      </div>

      {/* Frequência — 3 stat cards */}
      <div className="mt-8">
        <Skeleton className="h-4 w-24" />
        <div className="mt-3 grid grid-cols-3 gap-4">
          <Skeleton className="h-24 w-full rounded-lg" />
          <Skeleton className="h-24 w-full rounded-lg" />
          <Skeleton className="h-24 w-full rounded-lg" />
        </div>
      </div>

      {/* Gastos por categoria */}
      <div className="mt-8">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="mt-3 h-56 w-full rounded-lg" />
      </div>

      {/* Evolução do saldo */}
      <div className="mt-8">
        <Skeleton className="h-4 w-36" />
        <Skeleton className="mt-3 h-36 w-full rounded-lg" />
      </div>

      {/* Resumo */}
      <div className="mt-8 mb-12">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="mt-3 h-40 w-full rounded-lg" />
      </div>
    </div>
  );
}
