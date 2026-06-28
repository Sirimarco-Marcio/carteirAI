import { getTransacoes, type Transacao } from "@/lib/fake-data";
import { Card, Money, CategoryChip, EmptyState } from "@/components/ui";
import Link from "next/link";

export default async function TransacoesPage() {
  const tx = await getTransacoes();

  const pendentes = tx.filter((t) => t.possivelDuplicata);
  const confirmadas = tx.filter((t) => !t.possivelDuplicata);

  return (
    <div className="mx-auto max-w-6xl">
      {/* Cabeçalho */}
      <header className="pr-28 lg:pr-0">
        <h1 className="font-display text-3xl font-bold text-ink">Extrato</h1>
        <p className="mt-1 text-muted">Histórico e revisão das transações da família</p>
      </header>

      {/* Barra de filtros */}
      <div className="mt-6">
        <Card className="p-4">
          <div className="flex flex-wrap gap-3">
            {/* Busca */}
            <div className="relative flex-1 min-w-[200px]">
              <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-muted">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8" />
                  <path d="m21 21-4.35-4.35" strokeLinecap="round" />
                </svg>
              </span>
              <input
                type="search"
                placeholder="Buscar estabelecimento..."
                className="w-full rounded-md border border-line bg-surface py-2 pl-9 pr-4 text-sm text-ink outline-none transition focus:border-brand focus:ring-[3px] focus:ring-brand-soft"
                disabled
              />
            </div>

            {/* Filtro período */}
            <select
              className="rounded-md border border-line bg-surface px-3 py-2 text-sm text-ink outline-none transition focus:border-brand focus:ring-[3px] focus:ring-brand-soft disabled:text-muted"
              disabled
            >
              <option>Junho 2026</option>
            </select>

            {/* Filtro categoria */}
            <select
              className="rounded-md border border-line bg-surface px-3 py-2 text-sm text-ink outline-none transition focus:border-brand focus:ring-[3px] focus:ring-brand-soft disabled:text-muted"
              disabled
            >
              <option>Todas as categorias</option>
            </select>

            {/* Filtro status */}
            <select
              className="rounded-md border border-line bg-surface px-3 py-2 text-sm text-ink outline-none transition focus:border-brand focus:ring-[3px] focus:ring-brand-soft disabled:text-muted"
              disabled
            >
              <option>Pendentes &amp; Confirmadas</option>
              <option>Somente pendentes</option>
              <option>Somente confirmadas</option>
            </select>
          </div>
        </Card>
      </div>

      {tx.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            titulo="Ainda sem transações"
            descricao="Assim que o app capturar a primeira, ela aparece aqui."
            acao={
              <Link
                href="/transacoes/nova"
                className="inline-flex items-center gap-2 rounded-md bg-brand-dark px-5 py-2.5 text-sm font-semibold text-brand-fg transition-colors hover:bg-brand"
              >
                Adicionar manualmente
              </Link>
            }
          />
        </div>
      ) : (
        <div className="mt-6 space-y-6">
          {/* Seção: Aguardando aprovação */}
          {pendentes.length > 0 && (
            <section>
              <div className="mb-3 flex items-center gap-3">
                <h2 className="font-display text-xl font-semibold text-ink">Aguardando Aprovação</h2>
                <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-alerta/15 text-xs font-bold text-alerta">
                  {pendentes.length}
                </span>
              </div>

              {/* Desktop: tabela */}
              <Card className="hidden overflow-hidden lg:block">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-line bg-surface-2 text-left">
                      <th className="px-5 py-3 font-semibold text-muted">Data</th>
                      <th className="px-5 py-3 font-semibold text-muted">Estabelecimento</th>
                      <th className="px-5 py-3 font-semibold text-muted">Categoria</th>
                      <th className="px-5 py-3 font-semibold text-muted">Conta</th>
                      <th className="px-5 py-3 font-semibold text-muted">Forma</th>
                      <th className="px-5 py-3 text-right font-semibold text-muted">Valor</th>
                      <th className="px-5 py-3 font-semibold text-muted">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {pendentes.map((t) => (
                      <LinhaTabela key={t.id} t={t} pendente />
                    ))}
                  </tbody>
                </table>
              </Card>

              {/* Mobile: lista */}
              <div className="space-y-3 lg:hidden">
                {pendentes.map((t) => (
                  <CartaoMobile key={t.id} t={t} pendente />
                ))}
              </div>
            </section>
          )}

          {/* Seção: Confirmadas */}
          <section>
            <h2 className="mb-3 font-display text-xl font-semibold text-ink">Confirmadas</h2>

            {confirmadas.length === 0 ? (
              <p className="text-sm text-muted">Nenhuma transação confirmada neste período.</p>
            ) : (
              <>
                {/* Desktop: tabela */}
                <Card className="hidden overflow-hidden lg:block">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-line bg-surface-2 text-left">
                        <th className="px-5 py-3 font-semibold text-muted">Data</th>
                        <th className="px-5 py-3 font-semibold text-muted">Estabelecimento</th>
                        <th className="px-5 py-3 font-semibold text-muted">Categoria</th>
                        <th className="px-5 py-3 font-semibold text-muted">Conta</th>
                        <th className="px-5 py-3 font-semibold text-muted">Forma</th>
                        <th className="px-5 py-3 text-right font-semibold text-muted">Valor</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line">
                      {confirmadas.map((t) => (
                        <LinhaTabela key={t.id} t={t} />
                      ))}
                    </tbody>
                  </table>
                </Card>

                {/* Mobile: lista */}
                <div className="space-y-3 lg:hidden">
                  {confirmadas.map((t) => (
                    <CartaoMobile key={t.id} t={t} />
                  ))}
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

/** Formata data ISO como "27 Jun" */
function formatarData(iso: string): string {
  const d = new Date(iso);
  const meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
  return `${d.getDate()} ${meses[d.getMonth()]}`;
}

/** Rótulo da forma de pagamento */
function rotulForma(forma: Transacao["forma"]): string {
  const map: Record<Transacao["forma"], string> = {
    debito: "Débito",
    credito: "Crédito",
    pix: "Pix",
    dinheiro: "Dinheiro",
  };
  return map[forma];
}

/** Linha da tabela desktop */
function LinhaTabela({ t, pendente = false }: { t: Transacao; pendente?: boolean }) {
  return (
    <tr className="transition-colors hover:bg-surface-2">
      <td className="whitespace-nowrap px-5 py-4 text-muted">{formatarData(t.data)}</td>
      <td className="px-5 py-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-ink">{t.estabelecimento}</span>
          {t.possivelDuplicata && <SeloDuplicata />}
        </div>
        <span className="text-xs text-muted">{t.pessoa}</span>
      </td>
      <td className="px-5 py-4">
        <CategoryChip categoria={t.categoria} />
      </td>
      <td className="px-5 py-4 text-muted">{t.conta}</td>
      <td className="px-5 py-4 text-muted">{rotulForma(t.forma)}</td>
      <td className="px-5 py-4 text-right">
        <Money valor={t.valor} tipo={t.tipo} />
      </td>
      {pendente && (
        <td className="px-5 py-4">
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="rounded-md bg-brand-dark px-3 py-1.5 text-xs font-semibold text-brand-fg transition-colors hover:bg-brand"
            >
              Confirmar
            </button>
            <button
              type="button"
              className="rounded-md border border-line bg-surface px-3 py-1.5 text-xs font-semibold text-muted transition-colors hover:bg-surface-2"
            >
              Ignorar
            </button>
          </div>
        </td>
      )}
    </tr>
  );
}

/** Card de transação para mobile */
function CartaoMobile({ t, pendente = false }: { t: Transacao; pendente?: boolean }) {
  return (
    <Card className={`p-4 ${pendente ? "border-l-4 border-l-alerta" : ""}`}>
      <div className="flex items-start gap-3">
        {/* Ícone / inicial */}
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-surface-2 text-sm font-semibold text-muted">
          {t.tipo === "entrada" ? "↓" : t.categoria.slice(0, 1)}
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate font-medium text-ink">{t.estabelecimento}</p>
              <p className="text-xs text-muted">
                {t.categoria} · {t.pessoa}
              </p>
              <p className="mt-0.5 text-xs text-muted">
                {formatarData(t.data)} · {t.conta} · {rotulForma(t.forma)}
              </p>
            </div>
            <Money valor={t.valor} tipo={t.tipo} className="shrink-0 text-sm" />
          </div>

          {/* Selo duplicata + ações */}
          {t.possivelDuplicata && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <SeloDuplicata />
              {pendente && (
                <>
                  <button
                    type="button"
                    className="rounded-md bg-brand-dark px-3 py-1.5 text-xs font-semibold text-brand-fg transition-colors hover:bg-brand"
                  >
                    Confirmar
                  </button>
                  <button
                    type="button"
                    className="rounded-md border border-line bg-surface px-3 py-1.5 text-xs font-semibold text-muted transition-colors hover:bg-surface-2"
                  >
                    Ignorar
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

/** Selo "Parece repetida" em cor alerta */
function SeloDuplicata() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-alerta/15 px-2 py-0.5 text-xs font-semibold text-alerta">
      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <path d="M12 8v5M12 16.5v.5" strokeLinecap="round" />
        <circle cx="12" cy="12" r="9" />
      </svg>
      Parece repetida
    </span>
  );
}
