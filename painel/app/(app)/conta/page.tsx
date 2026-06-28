import { getConfig, USUARIO_ATUAL } from "@/lib/fake-data";
import { brl } from "@/lib/format";
import { Avatar, Card, CategoryChip, Money } from "@/components/ui";

// ─── helpers locais ────────────────────────────────────────────────────────────

function LabelTipo({ tipo }: { tipo: "conta" | "cartao" | "ambos" }) {
  const mapa = {
    conta: { label: "Conta", bg: "bg-brand-soft text-brand-dark" },
    cartao: { label: "Cartão", bg: "bg-surface-2 text-muted" },
    ambos: { label: "Conta + Cartão", bg: "bg-brand-soft text-brand-dark" },
  };
  const { label, bg } = mapa[tipo];
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${bg}`}>
      {label}
    </span>
  );
}

function PapelBadge({ papel }: { papel: "admin" | "membro" }) {
  return (
    <span
      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
        papel === "admin"
          ? "bg-brand-soft text-brand-dark"
          : "bg-surface-2 text-muted"
      }`}
    >
      {papel === "admin" ? "Administrador" : "Membro"}
    </span>
  );
}

// ─── página ────────────────────────────────────────────────────────────────────

export default async function ContaPage() {
  const c = await getConfig();

  return (
    <div className="mx-auto max-w-2xl">
      {/* Cabeçalho */}
      <header className="pr-28 lg:pr-0">
        <h1 className="font-display text-3xl font-bold text-ink">Conta</h1>
      </header>

      {/* Perfil do usuário atual */}
      <Card className="mt-6 flex items-center gap-4 p-5">
        <Avatar emoji={USUARIO_ATUAL.emoji} size={56} />
        <div className="min-w-0 flex-1">
          <p className="font-display text-xl font-semibold text-ink">
            {USUARIO_ATUAL.nome}
          </p>
          <PapelBadge papel={USUARIO_ATUAL.papel} />
        </div>
      </Card>

      {/* (a) Contas & cartões */}
      <Card className="mt-4 p-6">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold text-ink">
            Contas &amp; cartões
          </h2>
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-md border border-line bg-surface px-3 py-1.5 text-sm font-medium text-ink transition-colors hover:bg-surface-2"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              aria-hidden
            >
              <path d="M5 12h14M12 5v14" strokeLinecap="round" />
            </svg>
            Adicionar conta
          </button>
        </div>

        <ul className="mt-4 divide-y divide-line">
          {c.contas.map((conta) => (
            <li key={conta.id} className="flex items-start gap-4 py-4 first:pt-0 last:pb-0">
              {/* Ícone banco */}
              <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-soft font-display text-lg font-bold text-brand-dark">
                {conta.banco.slice(0, 1)}
              </span>

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-ink">{conta.banco}</span>
                  <LabelTipo tipo={conta.tipo} />
                </div>
                <p className="mt-0.5 font-mono text-[11px] text-muted">
                  {conta.packageName}
                </p>
              </div>

              {/* Valores */}
              <div className="shrink-0 text-right">
                {conta.saldo !== undefined && (
                  <div>
                    <p className="label-caps text-[10px]">Saldo</p>
                    <Money valor={conta.saldo} className="text-sm" />
                  </div>
                )}
                {conta.limite !== undefined && (
                  <div className="mt-1">
                    <p className="label-caps text-[10px]">Limite</p>
                    <span className="money text-sm text-muted">
                      {brl(conta.limite)}
                    </span>
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      </Card>

      {/* (b) Categorias */}
      <Card className="mt-4 p-6">
        <h2 className="font-display text-lg font-semibold text-ink">
          Categorias
        </h2>
        <div className="mt-4 flex flex-wrap gap-2">
          {c.categorias.map((cat) => (
            <CategoryChip key={cat} categoria={cat} />
          ))}
        </div>
      </Card>

      {/* (c) Família */}
      <Card className="mt-4 p-6">
        <h2 className="font-display text-lg font-semibold text-ink">
          Família
        </h2>
        <ul className="mt-4 divide-y divide-line">
          {c.membros.map((m) => (
            <li key={m.id} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
              <Avatar emoji={m.emoji} size={40} />
              <div className="min-w-0 flex-1">
                <p className="font-medium text-ink">{m.nome}</p>
              </div>
              <PapelBadge papel={m.papel} />
            </li>
          ))}
        </ul>
      </Card>

      {/* (d) Navegação: Dispositivos + Sair */}
      <Card className="mt-4 divide-y divide-line overflow-hidden p-0">
        {/* Link Dispositivos */}
        <a
          href="/conta/dispositivos"
          className="flex items-center justify-between px-6 py-4 transition-colors hover:bg-surface-2"
        >
          <div className="flex items-center gap-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-soft text-brand-dark">
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden
              >
                <rect x="5" y="2" width="14" height="20" rx="2" />
                <path d="M12 18h.01" strokeLinecap="round" />
              </svg>
            </span>
            <span className="font-medium text-ink">Dispositivos conectados</span>
          </div>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="text-muted"
            aria-hidden
          >
            <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </a>

        {/* Botão Sair */}
        <a
          href="/login"
          className="flex items-center gap-3 px-6 py-4 transition-colors hover:bg-surface-2"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-saida/10 text-saida">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden
            >
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
          <span className="font-medium text-saida">Sair</span>
        </a>
      </Card>

      {/* Espaço no final para tab bar mobile */}
      <div className="h-8" />
    </div>
  );
}
