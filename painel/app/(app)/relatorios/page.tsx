import { getRelatorio } from "@/lib/fake-data";
import { brl, corCategoria } from "@/lib/format";
import { Card, Money, StatCard } from "@/components/ui";
import { Sparkline } from "@/components/sparkline";

export default async function RelatoriosPage() {
  const r = await getRelatorio();

  const rendaTotal = r.rendaPorFonte.reduce((acc, f) => acc + f.valor, 0);

  return (
    <div className="mx-auto max-w-6xl">
      {/* Cabeçalho: título + seletor de mês (visual) */}
      <header className="pr-28 lg:pr-0">
        <p className="label-caps">Relatório</p>
        <div className="mt-1 flex items-center gap-3">
          <h1 className="font-display text-3xl font-bold text-ink" style={{ textWrap: "balance" }}>
            Relatório mensal
          </h1>
        </div>
        {/* Seletor de mês — visual, sem interação real */}
        <div className="mt-3 inline-flex items-center gap-1 rounded-lg border border-line bg-surface px-3 py-1.5">
          <button
            aria-label="Mês anterior"
            className="flex h-6 w-6 items-center justify-center rounded text-muted transition-colors hover:bg-surface-2 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
          >
            <ChevronLeft />
          </button>
          <span className="min-w-[110px] text-center text-sm font-semibold text-ink">
            {r.competencia}
          </span>
          <button
            aria-label="Próximo mês"
            className="flex h-6 w-6 items-center justify-center rounded text-muted transition-colors hover:bg-surface-2 hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
          >
            <ChevronRight />
          </button>
        </div>
      </header>

      {/* ── Seção 1: Renda por fonte ─────────────────────────────────── */}
      <section className="mt-8">
        <SectionLabel>Renda por fonte</SectionLabel>
        <Card className="mt-3 divide-y divide-line">
          {r.rendaPorFonte.map((fonte) => {
            const pct = rendaTotal > 0 ? (fonte.valor / rendaTotal) * 100 : 0;
            return (
              <div key={fonte.nome} className="flex items-center gap-4 px-6 py-4">
                {/* Barra de proporção */}
                <div className="flex-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-ink">{fonte.nome}</span>
                    <Money valor={fonte.valor} className="text-sm" />
                  </div>
                  <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
                    <div
                      className="h-1.5 rounded-full bg-brand transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
                {/* Percentual */}
                <span className="w-12 text-right text-xs font-semibold text-muted">
                  {pct.toFixed(0)}%
                </span>
              </div>
            );
          })}
          {/* Rodapé da seção: total */}
          <div className="flex items-center justify-between bg-surface-2 px-6 py-3">
            <span className="label-caps">Total realizado</span>
            <Money valor={r.rendaRealizada} className="font-semibold" />
          </div>
        </Card>
      </section>

      {/* ── Seção 2: Dias trabalhados ────────────────────────────────── */}
      <section className="mt-8">
        <SectionLabel>Frequência</SectionLabel>
        <div className="mt-3 flex gap-4 overflow-x-auto pb-1 lg:grid lg:grid-cols-3 lg:overflow-visible">
          <div className="min-w-[160px] flex-1">
            <StatCard titulo="Dias trabalhados">
              <DiasStat valor={r.diasTrabalhados} cor="text-entrada" />
            </StatCard>
          </div>
          <div className="min-w-[160px] flex-1">
            <StatCard titulo="Dias remotos">
              <DiasStat valor={r.diasRemotos} cor="text-alerta" />
            </StatCard>
          </div>
          <div className="min-w-[160px] flex-1">
            <StatCard titulo="Faltas">
              <DiasStat valor={r.diasFaltados} cor="text-saida" />
            </StatCard>
          </div>
        </div>
      </section>

      {/* ── Seção 3: Gastos por categoria ───────────────────────────── */}
      <section className="mt-8">
        <SectionLabel>Gastos por categoria</SectionLabel>
        <Card className="mt-3 p-6">
          <div className="space-y-5">
            {r.gastosPorCategoria.map((g) => (
              <BarraCategoria
                key={g.categoria}
                categoria={g.categoria}
                valor={g.valor}
                pct={g.percentual}
              />
            ))}
          </div>
          {/* Subtotal */}
          <div className="mt-6 flex items-center justify-between border-t border-line pt-4">
            <span className="label-caps">Total gasto</span>
            <Money valor={r.totalGasto} className="font-semibold" />
          </div>
        </Card>
      </section>

      {/* ── Seção 4: Evolução do saldo ──────────────────────────────── */}
      <section className="mt-8">
        <SectionLabel>Evolução do saldo</SectionLabel>
        <Card className="mt-3 overflow-hidden">
          <div className="flex items-center justify-between px-6 pt-5">
            <div>
              <p className="label-caps">Saldo no mês</p>
              <p className="money mt-1 text-2xl text-ink">
                {brl(r.evolucaoSaldo[r.evolucaoSaldo.length - 1] * 1000)}
              </p>
            </div>
            <span className="inline-flex items-center gap-1 rounded-full bg-brand-soft px-2.5 py-1 text-xs font-semibold text-brand-dark">
              {(() => {
                const first = r.evolucaoSaldo[0];
                const last = r.evolucaoSaldo[r.evolucaoSaldo.length - 1];
                const delta = ((last - first) / (first || 1)) * 100;
                return `↗ +${delta.toFixed(1).replace(".", ",")}%`;
              })()}
            </span>
          </div>
          <div className="-mx-0 mt-4">
            <Sparkline dados={r.evolucaoSaldo} altura={96} />
          </div>
        </Card>
      </section>

      {/* ── Seção 5: Resumo final ────────────────────────────────────── */}
      <section className="mt-8 mb-12">
        <SectionLabel>Resumo do mês</SectionLabel>
        <Card className="mt-3 divide-y divide-line">
          <LinhaResumo
            rotulo="Renda realizada"
            valor={r.rendaRealizada}
            destaque="entrada"
          />
          <LinhaResumo
            rotulo="Total gasto"
            valor={r.totalGasto}
            destaque="saida"
          />
          <div className="flex items-center justify-between bg-surface-2 px-6 py-4">
            <span className="font-display text-base font-semibold text-ink">Sobra do mês</span>
            <span
              className="money text-xl font-semibold"
              style={{ color: r.sobra >= 0 ? "#1f7a5c" : "#c0493d" }}
            >
              {r.sobra >= 0 ? "+" : ""}
              {brl(r.sobra)}
            </span>
          </div>
        </Card>
      </section>
    </div>
  );
}

/* ── Componentes locais ──────────────────────────────────────────────── */

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="label-caps border-b border-line pb-2">{children}</p>
  );
}

function DiasStat({ valor, cor }: { valor: number; cor: string }) {
  return (
    <span className={`font-display text-2xl font-bold ${cor}`}>
      {valor}
      <span className="ml-1 text-base font-normal text-muted">dias</span>
    </span>
  );
}

function BarraCategoria({
  categoria,
  valor,
  pct,
}: {
  categoria: string;
  valor: number;
  pct: number;
}) {
  const cor = corCategoria(categoria);
  return (
    <div>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* Marcador de cor da categoria */}
          <span
            className="inline-block h-2.5 w-2.5 flex-shrink-0 rounded-sm"
            style={{ backgroundColor: cor }}
            aria-hidden
          />
          <span className="text-sm font-medium text-ink">{categoria}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden text-xs text-muted sm:inline">{pct}%</span>
          <Money valor={valor} className="text-sm" />
        </div>
      </div>
      {/* Barra horizontal */}
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-surface-2">
        <div
          className="h-2 rounded-full transition-all"
          style={{ width: `${pct}%`, backgroundColor: cor }}
        />
      </div>
    </div>
  );
}

function LinhaResumo({
  rotulo,
  valor,
  destaque,
}: {
  rotulo: string;
  valor: number;
  destaque: "entrada" | "saida";
}) {
  return (
    <div className="flex items-center justify-between px-6 py-4">
      <span className="text-sm font-medium text-muted">{rotulo}</span>
      <Money valor={valor} tipo={destaque} className="text-base" />
    </div>
  );
}

/* ── Ícones inline (SVG mínimo, sem deps) ───────────────────────────── */

function ChevronLeft() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

function ChevronRight() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M9 18l6-6-6-6" />
    </svg>
  );
}
