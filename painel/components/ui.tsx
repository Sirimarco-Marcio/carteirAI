import { brl, brlSinal, corCategoria } from "@/lib/format";
import type { Tipo } from "@/lib/fake-data";

/** Card branco com hairline (Level 1). */
export function Card({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-lg border border-line bg-surface ${className}`}>{children}</div>
  );
}

/** Valor monetário em mono tabular, alinhado à direita, colorido por tipo. */
export function Money({
  valor,
  tipo,
  className = "",
}: {
  valor: number;
  tipo?: Tipo;
  className?: string;
}) {
  const cor = tipo === "entrada" ? "text-entrada" : tipo === "saida" ? "text-saida" : "text-ink";
  const texto = tipo ? brlSinal(valor, tipo) : brl(valor);
  return <span className={`money ${cor} ${className}`}>{texto}</span>;
}

/** Chip de categoria: bolinha + nome (cor por categoria via style inline). */
export function CategoryChip({ categoria }: { categoria: string }) {
  const cor = corCategoria(categoria);
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
      style={{ backgroundColor: `${cor}1a` }}
    >
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: cor }} aria-hidden />
      <span className="text-ink">{categoria}</span>
    </span>
  );
}

/** Cartão de resumo do dashboard. */
export function StatCard({
  titulo,
  children,
  alerta = false,
  rodape,
}: {
  titulo: string;
  children: React.ReactNode;
  alerta?: boolean;
  rodape?: React.ReactNode;
}) {
  return (
    <Card className={alerta ? "border-l-4 border-l-alerta p-5" : "p-5"}>
      <p className={`label-caps ${alerta ? "text-alerta" : ""}`}>{titulo}</p>
      <div className="mt-3 text-xl text-ink">{children}</div>
      {rodape && <div className="mt-1 text-sm font-medium text-alerta">{rodape}</div>}
    </Card>
  );
}

/** Avatar emoji (placeholder offline e barato da foto do usuário). */
export function Avatar({ emoji, size = 40 }: { emoji: string; size?: number }) {
  return (
    <span
      className="inline-flex items-center justify-center rounded-full bg-brand-soft"
      style={{ width: size, height: size, fontSize: size * 0.5 }}
      aria-hidden
    >
      {emoji}
    </span>
  );
}

/** Skeleton de carregamento. */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-2 ${className}`} />;
}

/** Estado vazio: convida à ação. */
export function EmptyState({
  titulo,
  descricao,
  acao,
}: {
  titulo: string;
  descricao: string;
  acao?: React.ReactNode;
}) {
  return (
    <Card className="flex flex-col items-center gap-3 p-10 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-soft text-brand-dark">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M5 12h14M12 5v14" strokeLinecap="round" />
        </svg>
      </div>
      <h3 className="font-display text-lg font-semibold text-ink">{titulo}</h3>
      <p className="max-w-sm text-sm text-muted">{descricao}</p>
      {acao}
    </Card>
  );
}

/** Estado de erro: explica o que houve e como resolver. */
export function ErrorState({
  titulo = "Algo deu errado ao carregar",
  descricao = "Tente novamente em instantes.",
  acao,
}: {
  titulo?: string;
  descricao?: string;
  acao?: React.ReactNode;
}) {
  return (
    <Card className="flex flex-col items-center gap-3 p-10 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-saida/10 text-saida">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 8v5M12 16.5v.5" strokeLinecap="round" />
          <circle cx="12" cy="12" r="9" />
        </svg>
      </div>
      <h3 className="font-display text-lg font-semibold text-ink">{titulo}</h3>
      <p className="max-w-sm text-sm text-muted">{descricao}</p>
      {acao}
    </Card>
  );
}

/** Botão primário (marca escura, texto branco). */
export function BotaoPrimario({
  children,
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`rounded-md bg-brand-dark px-5 py-3 font-body font-semibold text-brand-fg transition-colors hover:bg-brand focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-soft ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
