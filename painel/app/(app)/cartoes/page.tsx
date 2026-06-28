import { getCartoes, type Cartao } from "@/lib/fake-data";
import { brl } from "@/lib/format";
import { Card, Money, EmptyState } from "@/components/ui";

// Lançamentos simulados da fatura aberta (por cartão id)
const LANCAMENTOS_FATURA: Record<string, { descricao: string; data: string; categoria: string; valor: number }[]> = {
  c1: [
    { descricao: "Padaria Central", data: "27/Jun", categoria: "Alimentação", valor: 45.5 },
    { descricao: "iFood", data: "25/Jun", categoria: "Alimentação", valor: 89.9 },
    { descricao: "Uber", data: "24/Jun", categoria: "Transporte", valor: 34.0 },
    { descricao: "Netflix", data: "20/Jun", categoria: "Assinaturas", valor: 55.9 },
  ],
  c2: [
    { descricao: "Supermercado Pão de Açúcar", data: "25/Jun", categoria: "Mercado", valor: 450.2 },
    { descricao: "Posto Ipiranga", data: "26/Jun", categoria: "Transporte", valor: 188.0 },
    { descricao: "Farmácia Pacheco", data: "23/Jun", categoria: "Saúde", valor: 72.3 },
    { descricao: "CEAT Academia", data: "01/Jun", categoria: "Saúde", valor: 99.0 },
  ],
};

function diasParaVencimento(diaVencimento: number): number {
  const hoje = new Date();
  const mesAtual = hoje.getMonth();
  const anoAtual = hoje.getFullYear();
  let venc = new Date(anoAtual, mesAtual, diaVencimento);
  if (venc < hoje) {
    venc = new Date(anoAtual, mesAtual + 1, diaVencimento);
  }
  return Math.ceil((venc.getTime() - hoje.getTime()) / (1000 * 60 * 60 * 24));
}

function PorcentagemLimite({ usado, limite }: { usado: number; limite: number }) {
  const pct = Math.min((usado / limite) * 100, 100);
  const cor =
    pct >= 90
      ? "bg-saida"
      : pct >= 70
        ? "bg-alerta"
        : "bg-brand";
  return (
    <div className="mt-3">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted">Limite usado</span>
        <Money valor={usado} className="text-sm font-semibold" />
      </div>
      <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-surface-2">
        <div
          className={`h-2 rounded-full transition-all ${cor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-1 flex justify-between text-xs text-muted">
        <span>{brl(limite - usado)} disp.</span>
        <span>Total {brl(limite)}</span>
      </div>
    </div>
  );
}

function CartaoCard({ cartao, ativo }: { cartao: Cartao; ativo: boolean }) {
  const diasVenc = diasParaVencimento(cartao.diaVencimento);
  const venceBreve = diasVenc <= 5;

  return (
    <Card
      className={`cursor-pointer p-5 transition-shadow hover:shadow-float ${
        ativo ? "ring-2 ring-brand" : ""
      }`}
    >
      {/* Topo: nome + ícone */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="label-caps text-muted">{cartao.banco}</p>
          <p className="mt-0.5 font-display text-xl font-bold text-ink">{cartao.banco}</p>
        </div>
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-soft text-brand-dark">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="2" y="5" width="20" height="14" rx="2" />
            <path d="M2 10h20" strokeLinecap="round" />
          </svg>
        </span>
      </div>

      <PorcentagemLimite usado={cartao.usado} limite={cartao.limite} />

      {/* Fechamento / Vencimento */}
      <div className="mt-4 flex gap-6 border-t border-line pt-4">
        <div>
          <p className="label-caps text-muted">Fechamento</p>
          <p className="mt-0.5 text-sm font-semibold text-ink">
            Dia {cartao.diaFechamento}
          </p>
        </div>
        <div>
          <p className={`label-caps ${venceBreve ? "text-alerta" : "text-muted"}`}>
            Vencimento
          </p>
          <p
            className={`mt-0.5 text-sm font-semibold ${
              venceBreve ? "text-alerta" : "text-ink"
            }`}
          >
            Dia {cartao.diaVencimento}
            {venceBreve && (
              <span className="ml-1.5 inline-flex items-center rounded-full bg-alerta/10 px-1.5 py-0.5 text-xs font-medium text-alerta">
                {diasVenc === 0 ? "hoje" : `${diasVenc}d`}
              </span>
            )}
          </p>
        </div>
      </div>
    </Card>
  );
}

function FaturaAberta({ cartao }: { cartao: Cartao }) {
  const lancamentos = LANCAMENTOS_FATURA[cartao.id] ?? [];
  const diasVenc = diasParaVencimento(cartao.diaVencimento);
  const venceBreve = diasVenc <= 5;

  return (
    <Card className="p-6">
      {/* Cabeçalho da fatura */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-display text-xl font-semibold text-ink">Fatura Aberta</h2>
          <p className={`mt-0.5 text-sm ${venceBreve ? "text-alerta font-medium" : "text-muted"}`}>
            {cartao.banco} · Vence em {diasVenc <= 0 ? "hoje" : `${diasVenc} dia${diasVenc !== 1 ? "s" : ""}`}
          </p>
        </div>
        <Money valor={cartao.usado} className="text-2xl font-bold" />
      </div>

      {/* Botão Pagar fatura */}
      <button
        type="button"
        className="mt-5 w-full rounded-md bg-brand-dark px-5 py-3 font-body font-semibold text-brand-fg transition-colors hover:bg-brand focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-soft"
      >
        Pagar fatura
      </button>

      {/* Lançamentos recentes */}
      {lancamentos.length > 0 && (
        <div className="mt-6">
          <p className="label-caps text-muted">Lançamentos recentes</p>
          <ul className="mt-3 divide-y divide-line">
            {lancamentos.map((l, i) => (
              <li key={i} className="flex items-center gap-3 py-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-2 text-xs font-semibold text-muted">
                  {l.categoria.slice(0, 2)}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-ink">{l.descricao}</p>
                  <p className="text-xs text-muted">
                    {l.data} · {l.categoria}
                  </p>
                </div>
                <Money valor={l.valor} tipo="saida" className="text-sm" />
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

export default async function CartoesPage() {
  const cartoes = await getCartoes();

  if (cartoes.length === 0) {
    return (
      <div className="mx-auto max-w-6xl">
        <header className="pr-28 lg:pr-0">
          <h1 className="font-display text-3xl font-bold text-ink">Cartões</h1>
          <p className="mt-1 text-muted">Gerencie seus limites e acompanhe as faturas mensais.</p>
        </header>
        <div className="mt-8">
          <EmptyState
            titulo="Sem cartões"
            descricao="Nenhum cartão cadastrado. Adicione um nas configurações para acompanhar seus limites e faturas."
          />
        </div>
      </div>
    );
  }

  // Exibe o cartão com vencimento mais próximo na seção de fatura
  const cartaoDestaque = [...cartoes].sort(
    (a, b) =>
      diasParaVencimento(a.diaVencimento) - diasParaVencimento(b.diaVencimento),
  )[0];

  return (
    <div className="mx-auto max-w-6xl">
      {/* Cabeçalho */}
      <header className="pr-28 lg:pr-0">
        <h1 className="font-display text-3xl font-bold text-ink">Cartões</h1>
        <p className="mt-1 text-muted">Gerencie seus limites e acompanhe as faturas mensais.</p>
      </header>

      {/* Grid de cartões */}
      <div className="mt-6 flex gap-4 overflow-x-auto pb-1 lg:grid lg:grid-cols-3 lg:overflow-visible">
        {cartoes.map((c) => (
          <div key={c.id} className="min-w-[260px] flex-shrink-0 lg:min-w-0">
            <CartaoCard cartao={c} ativo={c.id === cartaoDestaque.id} />
          </div>
        ))}
      </div>

      {/* Seção inferior: fatura aberta + placeholder histórico */}
      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_300px]">
        <FaturaAberta cartao={cartaoDestaque} />

        {/* Histórico de faturas (placeholder) */}
        <Card className="p-5">
          <h3 className="font-display text-base font-semibold text-ink">Histórico</h3>
          <ul className="mt-4 divide-y divide-line">
            {[
              { mes: "Maio 2026", valor: 3890.45, paga: true },
              { mes: "Abril 2026", valor: 4120.0, paga: true },
              { mes: "Março 2026", valor: 2950.3, paga: true },
            ].map((h) => (
              <li key={h.mes} className="flex items-center justify-between gap-2 py-3">
                <div>
                  <p className="text-sm font-medium text-ink">{h.mes}</p>
                  <Money valor={h.valor} className="text-xs" />
                </div>
                {h.paga && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-entrada/10 px-2 py-0.5 text-xs font-semibold text-entrada">
                    Paga
                  </span>
                )}
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
