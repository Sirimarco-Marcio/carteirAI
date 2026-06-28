import { getDispositivos, type Dispositivo } from "@/lib/fake-data";
import { Card, EmptyState } from "@/components/ui";

export default async function DispositivosPage() {
  const ds = await getDispositivos();

  return (
    <div className="mx-auto max-w-2xl">
      {/* Cabeçalho */}
      <header className="pr-28 lg:pr-0">
        <a
          href="/conta"
          className="inline-flex items-center gap-1 text-sm font-medium text-brand hover:text-brand-dark focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-soft"
        >
          ← Conta
        </a>
        <h1 className="mt-2 font-display text-3xl font-bold text-ink">
          Aparelhos conectados
        </h1>
        <p className="mt-1 text-muted">
          Celulares que enviam notificações de pagamento para o carteirAI.
        </p>
      </header>

      {/* Aviso sobre revogação */}
      <p className="mt-5 rounded-md border border-line bg-surface-2 px-4 py-3 text-sm text-muted">
        Revogar um aparelho bloqueia permanentemente o envio de notificações
        daquele celular. O aparelho precisará fazer login novamente no app para
        voltar a funcionar.
      </p>

      {/* Lista ou estado vazio */}
      <div className="mt-6">
        {ds.length === 0 ? (
          <EmptyState
            titulo="Nenhum aparelho conectado"
            descricao="Conecte o app fazendo login nele."
          />
        ) : (
          <ul className="space-y-3">
            {ds.map((d) => (
              <LinhaDispositivo key={d.id} dispositivo={d} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function LinhaDispositivo({ dispositivo: d }: { dispositivo: Dispositivo }) {
  return (
    <li>
      <Card className="flex items-center gap-4 px-5 py-4">
        {/* Ícone + indicador de status */}
        <div className="relative shrink-0">
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-2 text-xl">
            📱
          </span>
          <span
            aria-hidden
            className={`absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-surface ${
              d.ativo ? "bg-brand" : "bg-muted/40"
            }`}
          />
        </div>

        {/* Nome e último envio */}
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium text-ink">{d.nome}</p>
          <p className="mt-0.5 text-xs text-muted">
            último envio:{" "}
            <span className={d.ativo ? "text-brand-dark font-medium" : ""}>
              {d.ultimoEnvio}
            </span>
          </p>
        </div>

        {/* Badge de status + botão revogar */}
        <div className="flex shrink-0 flex-col items-end gap-2 sm:flex-row sm:items-center sm:gap-3">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${
              d.ativo
                ? "bg-brand-soft text-brand-dark"
                : "bg-surface-2 text-muted"
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${d.ativo ? "bg-brand-dark" : "bg-muted/60"}`}
              aria-hidden
            />
            {d.ativo ? "ativo" : "inativo"}
          </span>

          <button
            type="button"
            className="rounded-md border border-line px-3 py-1.5 text-xs font-semibold text-saida transition-colors hover:border-saida hover:bg-saida/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-saida/40"
            aria-label={`Revogar acesso de ${d.nome}`}
          >
            Revogar acesso
          </button>
        </div>
      </Card>
    </li>
  );
}
