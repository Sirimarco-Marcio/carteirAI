import { getResumoPainel, type Transacao } from "@/lib/fake-data";
import { brl, corCategoria } from "@/lib/format";
import { Card, Money, StatCard } from "@/components/ui";
import { Sparkline } from "@/components/sparkline";

export default async function DashboardPage() {
  const d = await getResumoPainel();

  return (
    <div className="mx-auto max-w-6xl">
      {/* Cabeçalho (sino + avatar ficam no shell, fixos no topo direito) */}
      <header className="pr-28 lg:pr-0">
        <h1 className="font-display text-3xl font-bold text-ink">{d.saudacao}</h1>
        <p className="mt-1 text-muted">{d.competencia}</p>
      </header>

      {/* Herói: saldo acumulado com sparkline "respirando" */}
      <Card className="mt-6 overflow-hidden p-6">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="label-caps">Saldo acumulado</p>
            <p className="money mt-2 text-3xl text-ink lg:text-4xl">{brl(d.saldoAcumulado)}</p>
          </div>
          <span className="mb-1 inline-flex items-center gap-1 rounded-full bg-brand-soft px-2.5 py-1 text-sm font-semibold text-brand-dark">
            ↗ +{d.variacaoPct.toFixed(1).replace(".", ",")}%
          </span>
        </div>
        <div className="-mx-6 -mb-6 mt-4">
          <Sparkline dados={d.sparkline} altura={88} />
        </div>
      </Card>

      {/* Cartões-resumo (scroll horizontal no mobile) */}
      <div className="mt-4 flex gap-4 overflow-x-auto pb-1 lg:grid lg:grid-cols-4 lg:overflow-visible">
        <div className="min-w-[180px] flex-1">
          <StatCard titulo="Saldo de giro"><Money valor={d.saldoGiro} /></StatCard>
        </div>
        <div className="min-w-[180px] flex-1">
          <StatCard titulo="Total gasto"><Money valor={d.totalGasto} /></StatCard>
        </div>
        <div className="min-w-[180px] flex-1">
          <StatCard titulo="Faturas em aberto" alerta rodape={`Vence em ${d.faturaVenceEmDias} dias`}>
            <Money valor={d.faturasAberto} />
          </StatCard>
        </div>
        <div className="min-w-[180px] flex-1">
          <StatCard titulo="Pendências">
            <span className="inline-flex items-center gap-2 text-base">
              <span className="h-2 w-2 rounded-full bg-brand" />
              {d.pendencias} transações
            </span>
          </StatCard>
        </div>
      </div>

      {/* Duas colunas: gastos por categoria + últimas transações */}
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card className="p-6">
          <h2 className="font-display text-xl font-semibold text-ink">Gastos por categoria</h2>
          <div className="mt-5 space-y-4">
            {d.gastosPorCategoria.map((g) => (
              <BarraCategoria key={g.categoria} categoria={g.categoria} valor={g.valor} pct={g.percentual} />
            ))}
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-xl font-semibold text-ink">Últimas transações</h2>
            <a href="/transacoes" className="text-sm font-medium text-brand">Ver todas</a>
          </div>
          <ul className="mt-4 divide-y divide-line">
            {d.ultimasTransacoes.map((t) => (
              <LinhaTransacao key={t.id} t={t} />
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}

function BarraCategoria({ categoria, valor, pct }: { categoria: string; valor: number; pct: number }) {
  const cor = corCategoria(categoria);
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-ink">{categoria}</span>
        <Money valor={valor} className="text-sm" />
      </div>
      <div className="mt-2 h-2 w-full rounded-full bg-surface-2">
        <div className="h-2 rounded-full" style={{ width: `${pct}%`, backgroundColor: cor }} />
      </div>
    </div>
  );
}

function LinhaTransacao({ t }: { t: Transacao }) {
  return (
    <li className="flex items-center gap-3 py-3">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-2 text-xs font-semibold text-muted">
        {t.tipo === "entrada" ? "↓" : t.categoria.slice(0, 1)}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-ink">{t.estabelecimento}</p>
        <p className="truncate text-xs text-muted">{t.categoria} · {t.pessoa}</p>
      </div>
      <Money valor={t.valor} tipo={t.tipo} className="text-sm" />
    </li>
  );
}
