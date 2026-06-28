import { getNotificacoes, getTransacoes } from "@/lib/fake-data";
import { Card, Money, CategoryChip } from "@/components/ui";

/**
 * Notificações — versão CRUA (sem design do Stitch ainda).
 * É onde se revisa/aprova as transações capturadas + avisos.
 * Quando a tela do Stitch chegar, troco o visual mantendo a estrutura.
 */
export default async function NotificacoesPage() {
  const [avisos, tx] = await Promise.all([getNotificacoes(), getTransacoes()]);
  const pendentes = tx.filter((t) => t.tipo === "saida").slice(0, 3);

  return (
    <div className="mx-auto max-w-3xl">
      <header className="pr-28 lg:pr-0">
        <h1 className="font-display text-3xl font-bold text-ink">Notificações</h1>
        <p className="mt-1 text-muted">Revise o que foi capturado e veja os avisos.</p>
      </header>

      {/* Pendentes de aprovação */}
      <h2 className="mt-6 font-display text-xl font-semibold text-ink">Pendentes de aprovação</h2>
      <div className="mt-3 space-y-3">
        {pendentes.map((t) => (
          <Card key={t.id} className="p-4">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate font-medium text-ink">{t.estabelecimento}</p>
                <div className="mt-1 flex items-center gap-2">
                  <CategoryChip categoria={t.categoria} />
                  <span className="text-xs text-muted">{t.pessoa} · {t.conta}</span>
                </div>
                {t.possivelDuplicata && (
                  <p className="mt-2 inline-block rounded-full bg-alerta/10 px-2 py-0.5 text-xs font-semibold text-alerta">
                    ⚠️ Parece repetida
                  </p>
                )}
              </div>
              <Money valor={t.valor} tipo={t.tipo} />
            </div>
            <div className="mt-3 flex gap-2">
              <button className="flex-1 rounded-md bg-brand-dark py-2 text-sm font-semibold text-brand-fg hover:bg-brand">
                Confirmar
              </button>
              <button className="flex-1 rounded-md bg-surface-2 py-2 text-sm font-medium text-ink hover:bg-line">
                Ignorar
              </button>
            </div>
          </Card>
        ))}
      </div>

      {/* Avisos */}
      <h2 className="mt-8 font-display text-xl font-semibold text-ink">Avisos</h2>
      <Card className="mt-3 divide-y divide-line">
        {avisos.map((n) => (
          <div key={n.id} className="flex items-start gap-3 p-4">
            <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.lida ? "bg-line" : "bg-brand"}`} />
            <div className="min-w-0 flex-1">
              <p className={`font-medium ${n.lida ? "text-muted" : "text-ink"}`}>{n.titulo}</p>
              <p className="text-sm text-muted">{n.detalhe}</p>
            </div>
            <span className="shrink-0 text-xs text-muted">{n.quando}</span>
          </div>
        ))}
      </Card>
    </div>
  );
}
