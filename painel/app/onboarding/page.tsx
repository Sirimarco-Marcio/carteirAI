"use client";

import { useState } from "react";
import Link from "next/link";

// ---------------------------------------------------------------------------
// Tipos locais
// ---------------------------------------------------------------------------

interface Membro {
  id: number;
  nome: string;
  telegram: string;
}

interface Banco {
  id: number;
  nome: string;
  pacote: string;
  temConta: boolean;
  saldoInicial: string;
  temCartao: boolean;
  limite: string;
  fechamento: string;
  vencimento: string;
}

interface FonteRenda {
  id: number;
  nome: string;
  tipo: "fixo" | "dia";
  valorFixo: string;
  valorDia: string;
  alimentacaoDia: string;
  transporteDia: string;
  dias: boolean[]; // [seg, ter, qua, qui, sex, sab, dom]
}

interface Divida {
  id: number;
  contraparte: string;
  valor: string;
  vencimento: string;
  direcao: "devo" | "me-devem";
}

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------

const DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
const PASSOS = ["Família", "Contas", "Renda", "Dívidas", "Revisão"];
const TOTAL_PASSOS = 5;

// ---------------------------------------------------------------------------
// Helpers de apresentação
// ---------------------------------------------------------------------------

function brl(v: string) {
  const n = parseFloat(v.replace(",", "."));
  if (isNaN(n)) return "—";
  return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

// ---------------------------------------------------------------------------
// Sub-componentes de input
// ---------------------------------------------------------------------------

function Input({
  label,
  type = "text",
  value,
  onChange,
  placeholder,
  required,
}: {
  label?: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-xs font-semibold uppercase tracking-[0.05em] text-muted">
          {label}
        </label>
      )}
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        className="w-full rounded-md border border-line bg-surface px-4 py-2.5 text-sm text-ink outline-none transition focus:border-brand focus:ring-[3px] focus:ring-brand-soft placeholder:text-muted/60"
      />
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  children,
}: {
  label?: string;
  value: string;
  onChange: (v: string) => void;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-xs font-semibold uppercase tracking-[0.05em] text-muted">
          {label}
        </label>
      )}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-line bg-surface px-4 py-2.5 text-sm text-ink outline-none transition focus:border-brand focus:ring-[3px] focus:ring-brand-soft"
      >
        {children}
      </select>
    </div>
  );
}

function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      aria-pressed={checked}
      className={`rounded-md border px-3 py-1.5 text-xs font-semibold transition-colors ${
        checked
          ? "border-brand bg-brand-soft text-brand"
          : "border-line bg-surface text-muted hover:border-brand/40"
      }`}
    >
      {label}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Passo 1 — Família & membros
// ---------------------------------------------------------------------------

function PassoFamilia({
  membros,
  setMembros,
}: {
  membros: Membro[];
  setMembros: React.Dispatch<React.SetStateAction<Membro[]>>;
}) {
  const [nome, setNome] = useState("");
  const [telegram, setTelegram] = useState("");
  const nextId = membros.length > 0 ? Math.max(...membros.map((m) => m.id)) + 1 : 1;

  function adicionar() {
    if (!nome.trim()) return;
    setMembros((prev) => [...prev, { id: nextId, nome: nome.trim(), telegram: telegram.trim() }]);
    setNome("");
    setTelegram("");
  }

  function remover(id: number) {
    setMembros((prev) => prev.filter((m) => m.id !== id));
  }

  return (
    <div className="flex flex-col gap-6">
      <p className="text-sm text-muted">
        Adicione todos os membros da família que vão usar o carteirAI. O primeiro será o
        administrador.
      </p>

      {/* Formulário de adição */}
      <div className="rounded-lg border border-line bg-surface-2 p-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.05em] text-muted">
          Novo membro
        </p>
        <div className="flex flex-col gap-3">
          <Input
            label="Nome"
            value={nome}
            onChange={setNome}
            placeholder="Ex.: Lucas"
            required
          />
          <Input
            label="Telegram (opcional)"
            value={telegram}
            onChange={setTelegram}
            placeholder="@usuario_telegram"
          />
          <button
            type="button"
            onClick={adicionar}
            disabled={!nome.trim()}
            className="self-start rounded-md border border-brand px-4 py-2 text-sm font-semibold text-brand transition-colors hover:bg-brand-soft disabled:cursor-not-allowed disabled:opacity-40"
          >
            + Adicionar membro
          </button>
        </div>
      </div>

      {/* Lista de membros */}
      {membros.length === 0 ? (
        <p className="text-center text-sm text-muted">Nenhum membro adicionado ainda.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {membros.map((m, idx) => (
            <li
              key={m.id}
              className="flex items-center gap-3 rounded-lg border border-line bg-surface px-4 py-3"
            >
              {/* Avatar inicial */}
              <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-brand-soft text-sm font-bold text-brand">
                {m.nome[0].toUpperCase()}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-ink">
                  {m.nome}
                  {idx === 0 && (
                    <span className="ml-2 rounded-full bg-brand-soft px-2 py-0.5 text-[10px] font-semibold text-brand">
                      Administrador
                    </span>
                  )}
                </p>
                {m.telegram && (
                  <p className="truncate text-xs text-muted">{m.telegram}</p>
                )}
              </div>
              {idx > 0 && (
                <button
                  type="button"
                  onClick={() => remover(m.id)}
                  aria-label={`Remover ${m.nome}`}
                  className="text-muted hover:text-saida transition-colors"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Passo 2 — Contas & Bancos
// ---------------------------------------------------------------------------

function PassoContas({
  bancos,
  setBancos,
}: {
  bancos: Banco[];
  setBancos: React.Dispatch<React.SetStateAction<Banco[]>>;
}) {
  const emptyBanco = (): Omit<Banco, "id"> => ({
    nome: "",
    pacote: "",
    temConta: true,
    saldoInicial: "",
    temCartao: false,
    limite: "",
    fechamento: "",
    vencimento: "",
  });
  const [form, setForm] = useState<Omit<Banco, "id">>(emptyBanco());

  function set<K extends keyof Omit<Banco, "id">>(k: K, v: Omit<Banco, "id">[K]) {
    setForm((prev) => ({ ...prev, [k]: v }));
  }

  const nextId = bancos.length > 0 ? Math.max(...bancos.map((b) => b.id)) + 1 : 1;

  function adicionar() {
    if (!form.nome.trim()) return;
    setBancos((prev) => [...prev, { id: nextId, ...form }]);
    setForm(emptyBanco());
  }

  function remover(id: number) {
    setBancos((prev) => prev.filter((b) => b.id !== id));
  }

  return (
    <div className="flex flex-col gap-6">
      <p className="text-sm text-muted">
        Cadastre os bancos e apps financeiros da família. Para cada um, informe se tem conta
        corrente, cartão ou ambos.
      </p>

      {/* Formulário */}
      <div className="rounded-lg border border-line bg-surface-2 p-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.05em] text-muted">
          Novo banco / app
        </p>
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-3">
            <Input label="Nome do banco" value={form.nome} onChange={(v) => set("nome", v)} placeholder="Ex.: Nubank" />
            <Input label="App (pacote Android)" value={form.pacote} onChange={(v) => set("pacote", v)} placeholder="com.nubank.nubank" />
          </div>

          {/* Conta corrente */}
          <div className="rounded-md border border-line bg-surface p-3">
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                checked={form.temConta}
                onChange={(e) => set("temConta", e.target.checked)}
                className="h-4 w-4 rounded border-line accent-brand"
              />
              <span className="text-sm font-semibold text-ink">Tem conta corrente</span>
            </label>
            {form.temConta && (
              <div className="mt-3">
                <Input
                  label="Saldo inicial"
                  type="number"
                  value={form.saldoInicial}
                  onChange={(v) => set("saldoInicial", v)}
                  placeholder="0,00"
                />
              </div>
            )}
          </div>

          {/* Cartão */}
          <div className="rounded-md border border-line bg-surface p-3">
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                checked={form.temCartao}
                onChange={(e) => set("temCartao", e.target.checked)}
                className="h-4 w-4 rounded border-line accent-brand"
              />
              <span className="text-sm font-semibold text-ink">Tem cartão de crédito</span>
            </label>
            {form.temCartao && (
              <div className="mt-3 grid grid-cols-3 gap-3">
                <Input label="Limite (R$)" type="number" value={form.limite} onChange={(v) => set("limite", v)} placeholder="5000" />
                <Input label="Fechamento (dia)" type="number" value={form.fechamento} onChange={(v) => set("fechamento", v)} placeholder="20" />
                <Input label="Vencimento (dia)" type="number" value={form.vencimento} onChange={(v) => set("vencimento", v)} placeholder="27" />
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={adicionar}
            disabled={!form.nome.trim()}
            className="self-start rounded-md border border-brand px-4 py-2 text-sm font-semibold text-brand transition-colors hover:bg-brand-soft disabled:cursor-not-allowed disabled:opacity-40"
          >
            + Adicionar banco
          </button>
        </div>
      </div>

      {/* Lista */}
      {bancos.length === 0 ? (
        <p className="text-center text-sm text-muted">Nenhum banco adicionado ainda.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {bancos.map((b) => (
            <li key={b.id} className="flex items-start gap-3 rounded-lg border border-line bg-surface px-4 py-3">
              <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-brand-soft text-sm font-bold text-brand">
                {b.nome[0].toUpperCase()}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-ink">{b.nome}</p>
                {b.pacote && <p className="truncate text-xs text-muted">{b.pacote}</p>}
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {b.temConta && (
                    <span className="rounded-full bg-surface-2 px-2 py-0.5 text-[10px] font-medium text-muted">
                      Conta {b.saldoInicial ? `· ${brl(b.saldoInicial)}` : ""}
                    </span>
                  )}
                  {b.temCartao && (
                    <span className="rounded-full bg-surface-2 px-2 py-0.5 text-[10px] font-medium text-muted">
                      Cartão {b.limite ? `· limite ${brl(b.limite)}` : ""}{b.fechamento ? ` · fecha dia ${b.fechamento}` : ""}
                    </span>
                  )}
                </div>
              </div>
              <button
                type="button"
                onClick={() => remover(b.id)}
                aria-label={`Remover ${b.nome}`}
                className="text-muted hover:text-saida transition-colors"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Passo 3 — Fontes de renda
// ---------------------------------------------------------------------------

function PassoRenda({
  fontes,
  setFontes,
}: {
  fontes: FonteRenda[];
  setFontes: React.Dispatch<React.SetStateAction<FonteRenda[]>>;
}) {
  const emptyFonte = (): Omit<FonteRenda, "id"> => ({
    nome: "",
    tipo: "fixo",
    valorFixo: "",
    valorDia: "",
    alimentacaoDia: "",
    transporteDia: "",
    dias: [true, true, true, true, true, false, false],
  });
  const [form, setForm] = useState<Omit<FonteRenda, "id">>(emptyFonte());

  function set<K extends keyof Omit<FonteRenda, "id">>(k: K, v: Omit<FonteRenda, "id">[K]) {
    setForm((prev) => ({ ...prev, [k]: v }));
  }

  function toggleDia(i: number) {
    setForm((prev) => {
      const dias = [...prev.dias];
      dias[i] = !dias[i];
      return { ...prev, dias };
    });
  }

  const nextId = fontes.length > 0 ? Math.max(...fontes.map((f) => f.id)) + 1 : 1;

  function adicionar() {
    if (!form.nome.trim()) return;
    setFontes((prev) => [...prev, { id: nextId, ...form }]);
    setForm(emptyFonte());
  }

  function remover(id: number) {
    setFontes((prev) => prev.filter((f) => f.id !== id));
  }

  return (
    <div className="flex flex-col gap-6">
      <p className="text-sm text-muted">
        Informe as fontes de renda da família. Rendas fixas mensais (salário, aluguel recebido)
        ou por dia trabalhado (autônomo, diária).
      </p>

      <div className="rounded-lg border border-line bg-surface-2 p-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.05em] text-muted">
          Nova fonte de renda
        </p>
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-3">
            <Input label="Nome" value={form.nome} onChange={(v) => set("nome", v)} placeholder="Ex.: Salário Lucas" />
            <Select label="Tipo" value={form.tipo} onChange={(v) => set("tipo", v as "fixo" | "dia")}>
              <option value="fixo">Fixo mensal</option>
              <option value="dia">Por dia trabalhado</option>
            </Select>
          </div>

          {form.tipo === "fixo" ? (
            <Input label="Valor mensal (R$)" type="number" value={form.valorFixo} onChange={(v) => set("valorFixo", v)} placeholder="8000" />
          ) : (
            <>
              <div className="grid grid-cols-3 gap-3">
                <Input label="Valor/dia (R$)" type="number" value={form.valorDia} onChange={(v) => set("valorDia", v)} placeholder="250" />
                <Input label="Alimentação/dia (R$)" type="number" value={form.alimentacaoDia} onChange={(v) => set("alimentacaoDia", v)} placeholder="40" />
                <Input label="Transporte/dia (R$)" type="number" value={form.transporteDia} onChange={(v) => set("transporteDia", v)} placeholder="20" />
              </div>
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-[0.05em] text-muted">
                  Dias da semana
                </p>
                <div className="flex flex-wrap gap-2">
                  {DIAS_SEMANA.map((d, i) => (
                    <Toggle
                      key={d}
                      label={d}
                      checked={form.dias[i]}
                      onChange={() => toggleDia(i)}
                    />
                  ))}
                </div>
              </div>
            </>
          )}

          <button
            type="button"
            onClick={adicionar}
            disabled={!form.nome.trim()}
            className="self-start rounded-md border border-brand px-4 py-2 text-sm font-semibold text-brand transition-colors hover:bg-brand-soft disabled:cursor-not-allowed disabled:opacity-40"
          >
            + Adicionar renda
          </button>
        </div>
      </div>

      {fontes.length === 0 ? (
        <p className="text-center text-sm text-muted">Nenhuma renda adicionada ainda.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {fontes.map((f) => (
            <li key={f.id} className="flex items-start gap-3 rounded-lg border border-line bg-surface px-4 py-3">
              <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-entrada/10 text-sm">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#1f7a5c" strokeWidth="2">
                  <rect x="2" y="7" width="20" height="14" rx="2" />
                  <path d="M16 7V5a2 2 0 0 0-4 0v2M8 7V5a2 2 0 0 0-4 0v2" strokeLinecap="round" />
                </svg>
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-ink">{f.nome}</p>
                {f.tipo === "fixo" ? (
                  <p className="text-xs text-muted">
                    Fixo mensal{f.valorFixo ? ` · ${brl(f.valorFixo)}/mês` : ""}
                  </p>
                ) : (
                  <>
                    <p className="text-xs text-muted">
                      Por dia{f.valorDia ? ` · ${brl(f.valorDia)}/dia` : ""}
                      {f.alimentacaoDia ? ` · alim. ${brl(f.alimentacaoDia)}` : ""}
                      {f.transporteDia ? ` · transp. ${brl(f.transporteDia)}` : ""}
                    </p>
                    <p className="text-xs text-muted">
                      {DIAS_SEMANA.filter((_, i) => f.dias[i]).join(", ")}
                    </p>
                  </>
                )}
              </div>
              <button
                type="button"
                onClick={() => remover(f.id)}
                aria-label={`Remover ${f.nome}`}
                className="text-muted hover:text-saida transition-colors"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Passo 4 — Dívidas (opcional)
// ---------------------------------------------------------------------------

function PassoDividas({
  dividas,
  setDividas,
}: {
  dividas: Divida[];
  setDividas: React.Dispatch<React.SetStateAction<Divida[]>>;
}) {
  const emptyDivida = (): Omit<Divida, "id"> => ({
    contraparte: "",
    valor: "",
    vencimento: "",
    direcao: "devo",
  });
  const [form, setForm] = useState<Omit<Divida, "id">>(emptyDivida());

  function set<K extends keyof Omit<Divida, "id">>(k: K, v: Omit<Divida, "id">[K]) {
    setForm((prev) => ({ ...prev, [k]: v }));
  }

  const nextId = dividas.length > 0 ? Math.max(...dividas.map((d) => d.id)) + 1 : 1;

  function adicionar() {
    if (!form.contraparte.trim() || !form.valor.trim()) return;
    setDividas((prev) => [...prev, { id: nextId, ...form }]);
    setForm(emptyDivida());
  }

  function remover(id: number) {
    setDividas((prev) => prev.filter((d) => d.id !== id));
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start gap-3 rounded-lg border border-alerta/30 bg-alerta/5 p-4">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#c8852e" strokeWidth="2" className="mt-0.5 flex-shrink-0">
          <path d="M12 8v5M12 16.5v.5" strokeLinecap="round" />
          <circle cx="12" cy="12" r="9" />
        </svg>
        <p className="text-sm text-muted">
          Este passo é <strong className="text-ink">opcional</strong>. Registre dívidas ativas
          para que o painel possa alertar sobre vencimentos próximos.
        </p>
      </div>

      <div className="rounded-lg border border-line bg-surface-2 p-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.05em] text-muted">
          Nova dívida
        </p>
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-3">
            <Input label="Contraparte" value={form.contraparte} onChange={(v) => set("contraparte", v)} placeholder="Ex.: João Silva" />
            <Input label="Valor (R$)" type="number" value={form.valor} onChange={(v) => set("valor", v)} placeholder="500" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Vencimento" type="date" value={form.vencimento} onChange={(v) => set("vencimento", v)} />
            <Select label="Direção" value={form.direcao} onChange={(v) => set("direcao", v as "devo" | "me-devem")}>
              <option value="devo">Eu devo</option>
              <option value="me-devem">Me devem</option>
            </Select>
          </div>
          <button
            type="button"
            onClick={adicionar}
            disabled={!form.contraparte.trim() || !form.valor.trim()}
            className="self-start rounded-md border border-brand px-4 py-2 text-sm font-semibold text-brand transition-colors hover:bg-brand-soft disabled:cursor-not-allowed disabled:opacity-40"
          >
            + Adicionar dívida
          </button>
        </div>
      </div>

      {dividas.length === 0 ? (
        <p className="text-center text-sm text-muted">Nenhuma dívida registrada. Pode pular.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {dividas.map((d) => (
            <li key={d.id} className="flex items-center gap-3 rounded-lg border border-line bg-surface px-4 py-3">
              <span
                className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                  d.direcao === "devo"
                    ? "bg-saida/10 text-saida"
                    : "bg-entrada/10 text-entrada"
                }`}
              >
                {d.direcao === "devo" ? "−" : "+"}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-ink">{d.contraparte}</p>
                <p className="text-xs text-muted">
                  {d.direcao === "devo" ? "Eu devo" : "Me devem"} · {brl(d.valor)}
                  {d.vencimento ? ` · vence ${d.vencimento}` : ""}
                </p>
              </div>
              <button
                type="button"
                onClick={() => remover(d.id)}
                aria-label={`Remover dívida de ${d.contraparte}`}
                className="text-muted hover:text-saida transition-colors"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Passo 5 — Revisão
// ---------------------------------------------------------------------------

function PassoRevisao({
  membros,
  bancos,
  fontes,
  dividas,
  irParaPasso,
}: {
  membros: Membro[];
  bancos: Banco[];
  fontes: FonteRenda[];
  dividas: Divida[];
  irParaPasso: (p: number) => void;
}) {
  function BlocoRevisao({
    titulo,
    passo,
    vazio,
    children,
  }: {
    titulo: string;
    passo: number;
    vazio: boolean;
    children?: React.ReactNode;
  }) {
    return (
      <div className="rounded-lg border border-line bg-surface">
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <p className="text-sm font-semibold text-ink">{titulo}</p>
          <button
            type="button"
            onClick={() => irParaPasso(passo)}
            className="flex items-center gap-1 text-xs font-semibold text-brand hover:underline"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" strokeLinecap="round" />
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5Z" strokeLinecap="round" />
            </svg>
            Editar
          </button>
        </div>
        {vazio ? (
          <p className="px-4 py-3 text-sm text-muted">Nenhum item.</p>
        ) : (
          <div className="divide-y divide-line">{children}</div>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted">
        Tudo certo? Revise as informações antes de começarmos a organizar as finanças da sua
        família.
      </p>

      {/* Membros */}
      <BlocoRevisao titulo="Família & Membros" passo={1} vazio={membros.length === 0}>
        {membros.map((m, idx) => (
          <div key={m.id} className="flex items-center gap-3 px-4 py-3">
            <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-brand-soft text-xs font-bold text-brand">
              {m.nome[0].toUpperCase()}
            </span>
            <div className="min-w-0 flex-1">
              <span className="text-sm text-ink">{m.nome}</span>
              {m.telegram && <span className="ml-2 text-xs text-muted">{m.telegram}</span>}
            </div>
            {idx === 0 && (
              <span className="rounded-full bg-brand-soft px-2 py-0.5 text-[10px] font-semibold text-brand">
                Admin
              </span>
            )}
          </div>
        ))}
      </BlocoRevisao>

      {/* Contas */}
      <BlocoRevisao titulo="Contas & Cartões" passo={2} vazio={bancos.length === 0}>
        {bancos.map((b) => (
          <div key={b.id} className="flex items-start gap-3 px-4 py-3">
            <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-brand-soft text-xs font-bold text-brand">
              {b.nome[0].toUpperCase()}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-ink">{b.nome}</p>
              <div className="flex flex-wrap gap-1.5 mt-0.5">
                {b.temConta && (
                  <span className="text-[10px] text-muted">
                    Conta{b.saldoInicial ? ` ${brl(b.saldoInicial)}` : ""}
                  </span>
                )}
                {b.temCartao && (
                  <span className="text-[10px] text-muted">
                    · Cartão{b.limite ? ` limite ${brl(b.limite)}` : ""}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </BlocoRevisao>

      {/* Renda */}
      <BlocoRevisao titulo="Fontes de Renda" passo={3} vazio={fontes.length === 0}>
        {fontes.map((f) => (
          <div key={f.id} className="flex items-center gap-3 px-4 py-3">
            <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-entrada/10">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#1f7a5c" strokeWidth="2">
                <rect x="2" y="7" width="20" height="14" rx="2" />
                <path d="M16 7V5a2 2 0 0 0-4 0v2" strokeLinecap="round" />
              </svg>
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm text-ink">{f.nome}</p>
              <p className="text-xs text-muted">
                {f.tipo === "fixo"
                  ? `Fixo mensal${f.valorFixo ? ` · ${brl(f.valorFixo)}` : ""}`
                  : `Por dia${f.valorDia ? ` · ${brl(f.valorDia)}/dia` : ""}`}
              </p>
            </div>
          </div>
        ))}
      </BlocoRevisao>

      {/* Dívidas */}
      <BlocoRevisao
        titulo="Dívidas"
        passo={4}
        vazio={dividas.length === 0}
      >
        {dividas.map((d) => (
          <div key={d.id} className="flex items-center gap-3 px-4 py-3">
            <span
              className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                d.direcao === "devo" ? "bg-saida/10 text-saida" : "bg-entrada/10 text-entrada"
              }`}
            >
              {d.direcao === "devo" ? "−" : "+"}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm text-ink">{d.contraparte}</p>
              <p className="text-xs text-muted">
                {d.direcao === "devo" ? "Devo" : "Me devem"} · {brl(d.valor)}
                {d.vencimento ? ` · vence ${d.vencimento}` : ""}
              </p>
            </div>
          </div>
        ))}
      </BlocoRevisao>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Componente raiz do wizard
// ---------------------------------------------------------------------------

export default function OnboardingPage() {
  const [passo, setPasso] = useState(1);
  const [membros, setMembros] = useState<Membro[]>([
    { id: 1, nome: "Você", telegram: "" },
  ]);
  const [bancos, setBancos] = useState<Banco[]>([]);
  const [fontes, setFontes] = useState<FonteRenda[]>([]);
  const [dividas, setDividas] = useState<Divida[]>([]);

  const titulos = [
    "Família & membros",
    "Contas & bancos",
    "Fontes de renda",
    "Dívidas",
    "Tudo pronto?",
  ];

  const subtitulos = [
    "Quem vai usar o carteirAI?",
    "Onde a família guarda o dinheiro?",
    "De onde vem a renda da família?",
    "Alguma dívida ativa no momento?",
    "Revise antes de começar.",
  ];

  const progresso = (passo / TOTAL_PASSOS) * 100;

  function avancar() {
    if (passo < TOTAL_PASSOS) setPasso((p) => p + 1);
  }

  function voltar() {
    if (passo > 1) setPasso((p) => p - 1);
  }

  const podePular = passo === 4; // dívidas é opcional

  return (
    <div className="flex min-h-screen flex-col bg-paper">
      {/* Barra de progresso — fina, fixa no topo */}
      <div
        className="fixed left-0 right-0 top-0 z-50 h-[3px] bg-line"
        role="progressbar"
        aria-valuenow={passo}
        aria-valuemin={1}
        aria-valuemax={TOTAL_PASSOS}
        aria-label={`Passo ${passo} de ${TOTAL_PASSOS}`}
      >
        <div
          className="h-full bg-brand transition-all duration-500 ease-in-out"
          style={{ width: `${progresso}%` }}
        />
      </div>

      {/* Cabeçalho da página */}
      <header className="sticky top-[3px] z-40 border-b border-line bg-paper/90 backdrop-blur-sm">
        <div className="mx-auto flex max-w-xl items-center justify-between px-4 py-4">
          <Link href="/login" className="font-display text-lg font-bold text-brand">
            carteirAI
          </Link>
          <p className="text-xs font-semibold text-muted">
            Passo {passo} de {TOTAL_PASSOS}
          </p>
        </div>
      </header>

      {/* Conteúdo central */}
      <main className="mx-auto w-full max-w-xl flex-1 px-4 pb-32 pt-8">
        {/* Título do passo */}
        <div className="mb-6">
          <h1 className="font-display text-2xl font-semibold text-ink" style={{ textWrap: "balance" } as React.CSSProperties}>
            {titulos[passo - 1]}
          </h1>
          <p className="mt-1 text-sm text-muted">{subtitulos[passo - 1]}</p>
        </div>

        {/* Indicador visual de etapas */}
        <div className="mb-8 flex items-center gap-1">
          {PASSOS.map((nome, i) => {
            const num = i + 1;
            const ativo = num === passo;
            const concluido = num < passo;
            return (
              <div key={nome} className="flex flex-1 flex-col items-center gap-1">
                <div
                  className={`h-1 w-full rounded-full transition-colors ${
                    concluido
                      ? "bg-brand"
                      : ativo
                      ? "bg-brand/50"
                      : "bg-line"
                  }`}
                />
                <span
                  className={`text-[10px] font-medium transition-colors ${
                    ativo ? "text-brand" : concluido ? "text-brand/70" : "text-muted/50"
                  }`}
                >
                  {nome}
                </span>
              </div>
            );
          })}
        </div>

        {/* Conteúdo do passo atual */}
        {passo === 1 && <PassoFamilia membros={membros} setMembros={setMembros} />}
        {passo === 2 && <PassoContas bancos={bancos} setBancos={setBancos} />}
        {passo === 3 && <PassoRenda fontes={fontes} setFontes={setFontes} />}
        {passo === 4 && <PassoDividas dividas={dividas} setDividas={setDividas} />}
        {passo === 5 && (
          <PassoRevisao
            membros={membros}
            bancos={bancos}
            fontes={fontes}
            dividas={dividas}
            irParaPasso={setPasso}
          />
        )}
      </main>

      {/* Rodapé fixo com navegação */}
      <footer className="fixed bottom-0 left-0 right-0 z-40 border-t border-line bg-paper/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-xl items-center justify-between gap-3 px-4 py-4">
          {passo > 1 ? (
            <button
              type="button"
              onClick={voltar}
              className="flex items-center gap-1.5 rounded-md border border-line bg-surface px-5 py-3 text-sm font-semibold text-ink transition-colors hover:bg-surface-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-soft"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M19 12H5M12 19l-7-7 7-7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Voltar
            </button>
          ) : (
            <Link
              href="/login"
              className="flex items-center gap-1.5 rounded-md border border-line bg-surface px-5 py-3 text-sm font-semibold text-ink transition-colors hover:bg-surface-2"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M19 12H5M12 19l-7-7 7-7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Já tenho conta
            </Link>
          )}

          <div className="flex items-center gap-2">
            {podePular && passo < TOTAL_PASSOS && (
              <button
                type="button"
                onClick={avancar}
                className="rounded-md px-4 py-3 text-sm font-medium text-muted transition-colors hover:text-ink focus:outline-none"
              >
                Pular
              </button>
            )}

            {passo < TOTAL_PASSOS ? (
              <button
                type="button"
                onClick={avancar}
                className="flex items-center gap-1.5 rounded-md bg-brand-dark px-5 py-3 text-sm font-semibold text-brand-fg transition-colors hover:bg-brand focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-soft"
              >
                Continuar
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            ) : (
              <Link
                href="/"
                className="flex items-center gap-1.5 rounded-md bg-brand-dark px-5 py-3 text-sm font-semibold text-brand-fg transition-colors hover:bg-brand focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-soft"
              >
                Concluir e ir pro painel
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </Link>
            )}
          </div>
        </div>
      </footer>
    </div>
  );
}
