import { getRenda, type FonteRenda, type DiaTrabalho } from "@/lib/fake-data";
import { brl, MESES_PT } from "@/lib/format";
import { Card, Money } from "@/components/ui";

// Cores fixas por status de dia (usadas via style inline — Tailwind JIT não gera dinâmico)
const COR_STATUS: Record<DiaTrabalho["status"], string> = {
  presencial: "#2f6f5e",
  remoto: "#c8852e",
  falta: "#c0493d",
};

const LABEL_STATUS: Record<DiaTrabalho["status"], string> = {
  presencial: "Presencial",
  remoto: "Remoto",
  falta: "Falta",
};

const LABEL_TIPO: Record<FonteRenda["tipo"], string> = {
  fixo_mensal: "Fixo mensal",
  por_dia: "Por dia",
};

// ────────────────────────────────────────────────────────
// Página principal (server component assíncrono)
// ────────────────────────────────────────────────────────
export default async function RendaPage() {
  const r = await getRenda();

  return (
    <div className="mx-auto max-w-6xl">
      {/* Cabeçalho */}
      <header className="pr-28 lg:pr-0">
        <h1 className="font-display text-3xl font-bold text-ink">Renda</h1>
        <p className="mt-1 text-muted">{r.competencia}</p>
      </header>

      {/* (a) Fontes de renda */}
      <Card className="mt-6 p-6">
        <h2 className="font-display text-xl font-semibold text-ink">Fontes de renda</h2>
        <div className="mt-4 divide-y divide-line">
          {r.fontes.map((f) => (
            <LinhaFonte key={f.id} fonte={f} />
          ))}
        </div>

        {/* Totais */}
        <div className="mt-4 flex flex-col gap-1 border-t border-line pt-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 text-sm text-muted">
            <span>Previsto total</span>
            <Money valor={r.previstoTotal} className="text-sm" />
          </div>
          {r.realizadoTotal !== undefined && (
            <div className="flex items-center gap-2 text-sm font-semibold text-ink">
              <span>Realizado total</span>
              <Money valor={r.realizadoTotal} className="text-sm" />
            </div>
          )}
        </div>
      </Card>

      {/* (b) Calendário do mês */}
      <Card className="mt-4 p-6">
        <h2 className="font-display text-xl font-semibold text-ink">
          Calendário — {r.competencia}
        </h2>
        <div className="mt-4">
          <Calendario dias={r.dias} competencia={r.competencia} />
        </div>

        {/* Legenda */}
        <div className="mt-4 flex flex-wrap gap-4">
          {(["presencial", "remoto", "falta"] as DiaTrabalho["status"][]).map((s) => (
            <span key={s} className="inline-flex items-center gap-2 text-sm text-ink">
              <span
                className="inline-block h-3 w-3 rounded-sm"
                style={{ backgroundColor: COR_STATUS[s] }}
                aria-hidden
              />
              {LABEL_STATUS[s]}
            </span>
          ))}
          <span className="inline-flex items-center gap-2 text-sm text-muted">
            <span className="inline-block h-3 w-3 rounded-sm border border-line bg-surface-2" aria-hidden />
            Fim de semana / s/ registro
          </span>
        </div>
      </Card>

      {/* (c) Painel Fechar mês */}
      <Card className="mt-4 p-6">
        <h2 className="font-display text-xl font-semibold text-ink">Fechar mês</h2>
        <p className="mt-1 text-sm text-muted">
          Comparativo previsto × realizado por fonte
        </p>

        {/* Tabela comparativa */}
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line text-left">
                <th className="pb-2 font-medium text-muted">Fonte</th>
                <th className="pb-2 text-right font-medium text-muted">Previsto</th>
                <th className="pb-2 text-right font-medium text-muted">Realizado</th>
                <th className="pb-2 text-right font-medium text-muted">Diferença</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {r.fontes.map((f) => {
                const diff =
                  f.realizado !== undefined ? f.realizado - f.previsto : undefined;
                return (
                  <tr key={f.id}>
                    <td className="py-3 font-medium text-ink">{f.nome}</td>
                    <td className="py-3 text-right">
                      <Money valor={f.previsto} className="text-sm" />
                    </td>
                    <td className="py-3 text-right">
                      {f.realizado !== undefined ? (
                        <Money valor={f.realizado} className="text-sm" />
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="py-3 text-right">
                      {diff !== undefined ? (
                        <span
                          className="money text-sm"
                          style={{ color: diff >= 0 ? "#2f6f5e" : "#c0493d" }}
                        >
                          {diff >= 0 ? "+" : ""}
                          {brl(diff)}
                        </span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}

              {/* Total */}
              <tr className="border-t-2 border-line font-semibold text-ink">
                <td className="pt-3">Total</td>
                <td className="pt-3 text-right">
                  <Money valor={r.previstoTotal} className="text-sm" />
                </td>
                <td className="pt-3 text-right">
                  {r.realizadoTotal !== undefined ? (
                    <Money valor={r.realizadoTotal} className="text-sm" />
                  ) : (
                    <span className="text-muted">—</span>
                  )}
                </td>
                <td className="pt-3 text-right">
                  {r.realizadoTotal !== undefined ? (
                    <span
                      className="money text-sm"
                      style={{
                        color:
                          r.realizadoTotal - r.previstoTotal >= 0 ? "#2f6f5e" : "#c0493d",
                      }}
                    >
                      {r.realizadoTotal - r.previstoTotal >= 0 ? "+" : ""}
                      {brl(r.realizadoTotal - r.previstoTotal)}
                    </span>
                  ) : (
                    <span className="text-muted">—</span>
                  )}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Linha da sobra */}
        {r.sobra !== undefined && (
          <div className="mt-4 flex flex-col gap-3 rounded-md bg-surface-2 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="label-caps">Total gasto no mês</p>
              <Money valor={r.totalGasto} className="text-base" />
            </div>
            <div className="text-right">
              <p className="label-caps">Sobra do mês</p>
              <span
                className="money text-2xl font-bold"
                style={{ color: r.sobra >= 0 ? "#2f6f5e" : "#c0493d" }}
              >
                {brl(r.sobra)}
              </span>
            </div>
          </div>
        )}

        {/* Botão Fechar competência */}
        <div className="mt-6 flex justify-end">
          <button
            type="button"
            className="rounded-md bg-brand-dark px-6 py-3 font-body font-semibold text-brand-fg transition-colors hover:bg-brand focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-soft"
          >
            Fechar competência
          </button>
        </div>
      </Card>
    </div>
  );
}

// ────────────────────────────────────────────────────────
// Subcomponentes
// ────────────────────────────────────────────────────────

function LinhaFonte({ fonte }: { fonte: FonteRenda }) {
  return (
    <div className="flex flex-col gap-1 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <p className="font-medium text-ink">{fonte.nome}</p>
        <p className="text-xs text-muted">{LABEL_TIPO[fonte.tipo]}</p>
      </div>
      <div className="flex items-center gap-6 sm:shrink-0">
        <div className="text-right">
          <p className="label-caps">Previsto</p>
          <Money valor={fonte.previsto} className="text-sm" />
        </div>
        {fonte.realizado !== undefined && (
          <div className="text-right">
            <p className="label-caps">Realizado</p>
            <Money valor={fonte.realizado} className="text-sm" />
          </div>
        )}
      </div>
    </div>
  );
}

// Gera o grid do mês: inclui célula vazia para alinhar no dia-da-semana correto.
function Calendario({
  dias,
  competencia,
}: {
  dias: DiaTrabalho[];
  competencia: string;
}) {
  // Descobrir ano e mês a partir da primeira data presente ou da competência
  let ano: number;
  let mes: number; // 0-indexed

  if (dias.length > 0) {
    const [y, m] = dias[0].data.split("-").map(Number);
    ano = y;
    mes = m - 1;
  } else {
    // fallback: parsear "Junho 2026"
    const partes = competencia.split(" ");
    mes = MESES_PT.findIndex(
      (n) => n.toLowerCase() === partes[0].toLowerCase()
    );
    ano = parseInt(partes[1], 10);
  }

  const totalDias = new Date(ano, mes + 1, 0).getDate();
  const primeiroDow = new Date(ano, mes, 1).getDay(); // 0=Dom

  // Índice rápido: "2026-06-01" → status
  const statusMap: Record<string, DiaTrabalho["status"]> = {};
  for (const d of dias) {
    statusMap[d.data] = d.status;
  }

  const cabecalhos = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

  // Células do grid (null = espaço vazio)
  const celulas: (number | null)[] = [
    ...Array.from({ length: primeiroDow }, () => null),
    ...Array.from({ length: totalDias }, (_, i) => i + 1),
  ];

  return (
    <div>
      {/* Cabeçalho dos dias da semana */}
      <div className="grid grid-cols-7 gap-1 text-center text-xs font-medium text-muted">
        {cabecalhos.map((c) => (
          <div key={c} className="py-1">
            {c}
          </div>
        ))}
      </div>

      {/* Grid de dias */}
      <div className="mt-1 grid grid-cols-7 gap-1">
        {celulas.map((dia, idx) => {
          if (dia === null) {
            return <div key={`vazio-${idx}`} />;
          }

          const iso = `${ano}-${String(mes + 1).padStart(2, "0")}-${String(dia).padStart(2, "0")}`;
          const status = statusMap[iso];
          const cor = status ? COR_STATUS[status] : null;
          const dow = new Date(ano, mes, dia).getDay();
          const fimSemana = dow === 0 || dow === 6;

          return (
            <div
              key={iso}
              title={status ? LABEL_STATUS[status] : fimSemana ? "Fim de semana" : undefined}
              className="flex aspect-square items-center justify-center rounded-md text-xs font-medium"
              style={
                cor
                  ? { backgroundColor: `${cor}22`, color: cor, border: `1px solid ${cor}55` }
                  : {
                      backgroundColor: "var(--surface-2, #f0f0f0)",
                      color: "var(--muted, #888)",
                      border: "1px solid transparent",
                    }
              }
            >
              {dia}
            </div>
          );
        })}
      </div>
    </div>
  );
}
