"use client";

import { useState } from "react";
import Link from "next/link";

// ---------------------------------------------------------------------------
// Tipos locais
// ---------------------------------------------------------------------------

interface Membro {
  id: number;
  nome: string;
  appUserId: string;      // UUID do app Android (só relevante para o admin)
  telegramChatId: string; // chat_id do Telegram
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
  dias: boolean[]; // [seg, ter, qua, qui, sex, sab, dom] → índices 1..7
}

interface Divida {
  id: number;
  contraparte: string;
  valor: string;
  vencimento: string;
  direcao: "devo" | "me-devem";
}

// Resultado retornado pela API após o onboarding
interface OnboardingResult {
  familia_id: string;
  usuarios: { id: string; nome: string; role: string }[];
}

const UUID_RE  = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------

const DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
// Índices ISO: Seg=1, Ter=2, ..., Dom=7  (padrão do banco)
const DIAS_ISO_IDX = [1, 2, 3, 4, 5, 6, 7];

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
  hint,
}: {
  label?: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
  hint?: string;
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
      {hint && <p className="text-[11px] text-muted/70">{hint}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Card de vinculação do app (substitui o input plano)
// ---------------------------------------------------------------------------

function AppVinculoCard({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const [expandido, setExpandido] = useState(false);
  const vinculado = UUID_RE.test(value.trim());
  const invalido = value.trim().length > 0 && !vinculado;

  if (vinculado) {
    return (
      <div className="rounded-lg border border-entrada/40 bg-entrada/5 p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-entrada/15">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#1f7a5c" strokeWidth="2.5">
                <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-entrada">App vinculado</p>
              <p className="font-mono text-[10px] text-muted/70 truncate">{value.slice(0, 8)}…{value.slice(-4)}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => { onChange(""); setExpandido(true); }}
            className="text-xs font-medium text-muted hover:text-brand transition-colors"
          >
            Alterar
          </button>
        </div>
      </div>
    );
  }

  if (!expandido) {
    return (
      <div className="rounded-lg border border-line bg-surface-2 p-4">
        <div className="flex items-start gap-3">
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-brand-soft">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#1f7a5c" strokeWidth="2">
              <rect x="5" y="2" width="14" height="20" rx="2" />
              <circle cx="12" cy="18" r="1" fill="#1f7a5c" />
            </svg>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-ink">Vincular app Notifier</p>
            <p className="text-xs text-muted mt-0.5 leading-relaxed">
              Sem vínculo, gastos de notificações não serão registrados automaticamente.
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => setExpandido(true)}
                className="rounded-md bg-brand-dark px-3 py-1.5 text-xs font-semibold text-brand-fg hover:bg-brand transition-colors"
              >
                Tenho o app instalado →
              </button>
              <span className="text-xs text-muted">ou vincular depois</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-brand/30 bg-brand-soft/10 p-4">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-brand-soft">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#1f7a5c" strokeWidth="2">
              <rect x="5" y="2" width="14" height="20" rx="2" />
              <circle cx="12" cy="18" r="1" fill="#1f7a5c" />
            </svg>
          </div>
          <p className="text-sm font-semibold text-ink">Vincular app Notifier</p>
        </div>
        <button
          type="button"
          onClick={() => setExpandido(false)}
          className="text-xs text-muted hover:text-ink transition-colors"
        >
          Fechar
        </button>
      </div>

      <ol className="mb-4 flex flex-col gap-3">
        {[
          <>Abra o <strong className="text-ink">CarteirAI Notifier</strong> no celular</>,
          <>Na tela inicial, toque em <strong className="text-ink">Copiar ID</strong></>,
          <>Cole o ID copiado no campo abaixo</>,
        ].map((texto, i) => (
          <li key={i} className="flex items-start gap-3">
            <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-brand-soft text-[10px] font-bold text-brand">
              {i + 1}
            </span>
            <p className="pt-0.5 text-xs text-muted">{texto}</p>
          </li>
        ))}
      </ol>

      <Input
        label="ID copiado do app"
        value={value}
        onChange={onChange}
        placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
      />
      {invalido && (
        <p className="mt-1 text-[11px] text-saida">
          Formato inválido — cole o UUID exatamente como aparece no app.
        </p>
      )}
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
  familiaName,
  setFamiliaName,
  membros,
  setMembros,
  email,
  setEmail,
  senha,
  setSenha,
  confirmar,
  setConfirmar,
}: {
  familiaName: string;
  setFamiliaName: (v: string) => void;
  membros: Membro[];
  setMembros: React.Dispatch<React.SetStateAction<Membro[]>>;
  email: string;
  setEmail: (v: string) => void;
  senha: string;
  setSenha: (v: string) => void;
  confirmar: string;
  setConfirmar: (v: string) => void;
}) {
  const [nome, setNome] = useState("");
  const [telegram, setTelegram] = useState("");
  const nextId = membros.length > 0 ? Math.max(...membros.map((m) => m.id)) + 1 : 2;

  function adicionar() {
    if (!nome.trim()) return;
    setMembros((prev) => [
      ...prev,
      { id: nextId, nome: nome.trim(), appUserId: "", telegramChatId: telegram.trim() },
    ]);
    setNome("");
    setTelegram("");
  }

  function remover(id: number) {
    setMembros((prev) => prev.filter((m) => m.id !== id));
  }

  // Atualiza campos do admin (primeiro membro)
  function setAdminField(field: "appUserId" | "telegramChatId", value: string) {
    setMembros((prev) =>
      prev.map((m, idx) => (idx === 0 ? { ...m, [field]: value } : m))
    );
  }

  const admin = membros[0];

  return (
    <div className="flex flex-col gap-6">
      {/* Nome da família */}
      <div className="rounded-lg border border-line bg-surface-2 p-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.05em] text-muted">
          Nome da família
        </p>
        <Input
          label="Como sua família se chama?"
          value={familiaName}
          onChange={setFamiliaName}
          placeholder="Ex.: Família Silva"
          required
        />
      </div>

      {/* Admin — campos especiais */}
      {admin && (
        <div className="rounded-lg border border-brand/30 bg-brand-soft/20 p-4">
          <div className="mb-3 flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-soft text-xs font-bold text-brand">
              {admin.nome?.[0]?.toUpperCase() ?? "?"}
            </span>
            <p className="text-sm font-semibold text-ink">
              {admin.nome || "Você"}
              <span className="ml-2 rounded-full bg-brand-soft px-2 py-0.5 text-[10px] font-semibold text-brand">
                Administrador
              </span>
            </p>
          </div>
          <div className="flex flex-col gap-3">
            <Input
              label="Seu nome"
              value={admin.nome}
              onChange={(v) =>
                setMembros((prev) =>
                  prev.map((m, idx) => (idx === 0 ? { ...m, nome: v } : m))
                )
              }
              placeholder="Ex.: Lucas, Maria…"
              required
            />
            {/* Credenciais de acesso ao painel */}
            <div className="rounded-md border border-line bg-surface p-3 flex flex-col gap-3">
              <p className="text-xs font-semibold uppercase tracking-[0.05em] text-muted">
                Acesso ao painel (e-mail e senha)
              </p>
              <Input
                label="E-mail"
                type="email"
                value={email}
                onChange={setEmail}
                placeholder="seu@email.com"
                required
              />
              {email && !EMAIL_RE.test(email) && (
                <p className="text-[11px] text-saida">E-mail inválido.</p>
              )}
              <Input
                label="Senha"
                type="password"
                value={senha}
                onChange={setSenha}
                placeholder="Mínimo 8 caracteres"
                required
              />
              {senha && senha.length < 8 && (
                <p className="text-[11px] text-saida">Senha deve ter ao menos 8 caracteres.</p>
              )}
              <Input
                label="Confirmar senha"
                type="password"
                value={confirmar}
                onChange={setConfirmar}
                placeholder="Repita a senha"
                required
              />
              {confirmar && confirmar !== senha && (
                <p className="text-[11px] text-saida">As senhas não coincidem.</p>
              )}
              {email && EMAIL_RE.test(email) && senha.length >= 8 && confirmar === senha && (
                <div className="flex items-center gap-1.5">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#1f7a5c" strokeWidth="2.5">
                    <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <p className="text-[11px] font-semibold text-entrada">Credenciais válidas</p>
                </div>
              )}
            </div>

            <AppVinculoCard
              value={admin.appUserId}
              onChange={(v) => setAdminField("appUserId", v)}
            />
            <Input
              label="Chat do Telegram (opcional)"
              value={admin.telegramChatId}
              onChange={(v) => setAdminField("telegramChatId", v)}
              placeholder="@usuario ou número do chat_id"
            />
          </div>
        </div>
      )}

      {/* Formulário de adição de membros extras */}
      <div className="rounded-lg border border-line bg-surface-2 p-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.05em] text-muted">
          Adicionar outro membro
        </p>
        <div className="flex flex-col gap-3">
          <Input
            label="Nome"
            value={nome}
            onChange={setNome}
            placeholder="Ex.: Maria"
            required
          />
          <Input
            label="Chat do Telegram (opcional)"
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

      {/* Lista de membros extras */}
      {membros.length > 1 && (
        <ul className="flex flex-col gap-2">
          {membros.slice(1).map((m) => (
            <li
              key={m.id}
              className="flex items-center gap-3 rounded-lg border border-line bg-surface px-4 py-3"
            >
              <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-brand-soft text-sm font-bold text-brand">
                {m.nome[0].toUpperCase()}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-ink">{m.nome}</p>
                {m.telegramChatId && (
                  <p className="truncate text-xs text-muted">{m.telegramChatId}</p>
                )}
              </div>
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
              {m.telegramChatId && <span className="ml-2 text-xs text-muted">{m.telegramChatId}</span>}
              {idx === 0 && m.appUserId && (
                <p className="text-[10px] text-muted/70 font-mono truncate">{m.appUserId}</p>
              )}
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
      <BlocoRevisao titulo="Dívidas" passo={4} vazio={dividas.length === 0}>
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
// Tela de sucesso
// ---------------------------------------------------------------------------

function TelaSucesso({
  resultado,
  appVinculado,
}: {
  resultado: OnboardingResult;
  appVinculado: boolean;
}) {
  const admin = resultado.usuarios.find((u) => u.role === "admin") ?? resultado.usuarios[0];
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-paper px-4 py-8">
      <div className="w-full max-w-sm rounded-2xl border border-line bg-surface p-8 text-center shadow-sm">
        {/* Ícone de check */}
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-entrada/10">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#1f7a5c" strokeWidth="2.5">
            <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <h1 className="font-display text-2xl font-semibold text-ink">Família criada!</h1>
        <p className="mt-2 text-sm text-muted">
          Conta configurada com sucesso no carteirAI.
        </p>

        {/* Alerta se app não vinculado */}
        {!appVinculado && admin && (
          <div className="mt-5 rounded-lg border border-alerta/40 bg-alerta/5 p-4 text-left">
            <div className="flex items-center gap-2 mb-2">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#c8852e" strokeWidth="2" className="flex-shrink-0">
                <path d="M12 8v5M12 16.5v.5" strokeLinecap="round" />
                <circle cx="12" cy="12" r="9" />
              </svg>
              <p className="text-xs font-semibold text-alerta">App não vinculado</p>
            </div>
            <p className="text-xs text-muted mb-3 leading-relaxed">
              Gastos de notificações só funcionam com o app vinculado. Abra o <strong className="text-ink">CarteirAI Notifier</strong>, toque em <strong className="text-ink">Copiar ID</strong> e anote — você precisará desse ID para refazer o cadastro vinculando o app.
            </p>
            <div className="rounded-md bg-surface px-3 py-2">
              <p className="text-[10px] text-muted mb-0.5">ID gerado para você (para referência)</p>
              <p className="font-mono text-[11px] text-ink break-all">{admin.id}</p>
            </div>
          </div>
        )}

        {/* Badge app vinculado */}
        {appVinculado && (
          <div className="mt-5 flex items-center justify-center gap-2 rounded-lg border border-entrada/30 bg-entrada/5 px-4 py-2.5">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#1f7a5c" strokeWidth="2.5">
              <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <p className="text-xs font-semibold text-entrada">App Notifier vinculado</p>
          </div>
        )}

        {/* Detalhes colapsados */}
        <details className="mt-4 text-left">
          <summary className="cursor-pointer text-xs font-medium text-muted hover:text-ink transition-colors">
            Ver identificadores
          </summary>
          <div className="mt-3 rounded-lg border border-line bg-surface-2 p-3">
            <div className="flex flex-col gap-1.5">
              <div>
                <p className="text-[10px] text-muted">ID da família</p>
                <p className="font-mono text-[11px] text-ink break-all">{resultado.familia_id}</p>
              </div>
              {admin && (
                <div className="mt-1">
                  <p className="text-[10px] text-muted">ID do admin ({admin.nome})</p>
                  <p className="font-mono text-[11px] text-ink break-all">{admin.id}</p>
                </div>
              )}
            </div>
          </div>
        </details>

        <div className="mt-6 flex flex-col gap-3">
          <Link
            href="/inicio"
            className="flex w-full items-center justify-center gap-1.5 rounded-md bg-brand-dark px-5 py-3 text-sm font-semibold text-brand-fg transition-colors hover:bg-brand"
          >
            Ir para o painel
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </Link>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Componente raiz do wizard
// ---------------------------------------------------------------------------

export default function OnboardingPage() {
  const [passo, setPasso] = useState(1);
  const [familiaName, setFamiliaName] = useState("");
  const [membros, setMembros] = useState<Membro[]>([
    { id: 1, nome: "", appUserId: "", telegramChatId: "" },
  ]);
  const [email, setEmail]       = useState("");
  const [senha, setSenha]       = useState("");
  const [confirmar, setConfirmar] = useState("");
  const [bancos, setBancos] = useState<Banco[]>([]);
  const [fontes, setFontes] = useState<FonteRenda[]>([]);
  const [dividas, setDividas] = useState<Divida[]>([]);

  // Estado de submissão
  const [enviando, setEnviando] = useState(false);
  const [erroEnvio, setErroEnvio] = useState<string | null>(null);
  const [resultado, setResultado] = useState<OnboardingResult | null>(null);

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

  // Passo 1 só avança com credenciais válidas
  const credenciaisValidas =
    EMAIL_RE.test(email.trim()) &&
    senha.length >= 8 &&
    senha === confirmar;

  // -------------------------------------------------------------------------
  // Monta o payload e chama a API
  // -------------------------------------------------------------------------
  async function concluir() {
    setErroEnvio(null);
    setEnviando(true);

    // Monta membros para o payload
    const membrosPayload = membros.map((m, idx) => ({
      nome: m.nome.trim() || (idx === 0 ? "Admin" : "Membro"),
      role: (idx === 0 ? "admin" : "membro") as "admin" | "membro",
      usuario_id: idx === 0 && m.appUserId.trim() ? m.appUserId.trim() : undefined,
      telegram_chat_id: m.telegramChatId.trim() || undefined,
    }));

    // Monta contas: um banco pode gerar conta corrente e/ou cartão
    const contasPayload: {
      banco: string;
      package_name?: string;
      tipo: "corrente" | "credito" | "dinheiro";
      saldo?: number;
      limite?: number;
      dia_fechamento?: number;
      dia_vencimento?: number;
    }[] = [];
    for (const b of bancos) {
      if (b.temConta) {
        contasPayload.push({
          banco: b.nome,
          package_name: b.pacote || undefined,
          tipo: "corrente",
          saldo: b.saldoInicial ? parseFloat(b.saldoInicial) : 0,
        });
      }
      if (b.temCartao) {
        contasPayload.push({
          banco: b.nome,
          package_name: b.pacote || undefined,
          tipo: "credito",
          limite: b.limite ? parseFloat(b.limite) : undefined,
          dia_fechamento: b.fechamento ? parseInt(b.fechamento) : undefined,
          dia_vencimento: b.vencimento ? parseInt(b.vencimento) : undefined,
        });
      }
    }

    // Monta fontes de renda
    const fontesPayload = fontes.map((f) => {
      const diasSemana = f.tipo === "dia"
        ? DIAS_ISO_IDX.filter((_, i) => f.dias[i])
        : [];
      return {
        nome: f.nome,
        tipo_calculo: (f.tipo === "fixo" ? "fixo_mensal" : "por_dia") as "fixo_mensal" | "por_dia",
        valor_base: parseFloat(f.tipo === "fixo" ? f.valorFixo || "0" : f.valorDia || "0"),
        valor_alimentacao_dia: f.alimentacaoDia ? parseFloat(f.alimentacaoDia) : undefined,
        valor_transporte_dia: f.transporteDia ? parseFloat(f.transporteDia) : undefined,
        dias_semana: diasSemana,
      };
    });

    // Monta dívidas
    const dividasPayload = dividas.map((d) => ({
      contraparte_nome: d.contraparte,
      valor: parseFloat(d.valor),
      tipo: (d.direcao === "me-devem" ? "me_devem" : "devo") as "devo" | "me_devem",
      vencimento: d.vencimento || undefined,
    }));

    const payload = {
      familia: { nome: familiaName.trim() || "Minha Família" },
      membros: membrosPayload,
      admin_email: email.trim().toLowerCase(),
      admin_senha: senha,
      contas: contasPayload.length > 0 ? contasPayload : undefined,
      fontes: fontesPayload.length > 0 ? fontesPayload : undefined,
      dividas: dividasPayload.length > 0 ? dividasPayload : undefined,
    };

    try {
      const res = await fetch("/api/onboarding", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok) {
        setErroEnvio(data?.erro ?? `Erro ${res.status}`);
      } else {
        setResultado(data as OnboardingResult);
      }
    } catch (err) {
      setErroEnvio("Falha de rede. Verifique a conexão e tente novamente.");
      console.error("[onboarding] fetch error:", err);
    } finally {
      setEnviando(false);
    }
  }

  // Tela de sucesso substitui o wizard por completo
  if (resultado) {
    return (
      <TelaSucesso
        resultado={resultado}
        appVinculado={UUID_RE.test(membros[0]?.appUserId?.trim() ?? "")}
      />
    );
  }

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
        {passo === 1 && (
          <PassoFamilia
            familiaName={familiaName}
            setFamiliaName={setFamiliaName}
            membros={membros}
            setMembros={setMembros}
            email={email}
            setEmail={setEmail}
            senha={senha}
            setSenha={setSenha}
            confirmar={confirmar}
            setConfirmar={setConfirmar}
          />
        )}
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
        <div className="mx-auto flex max-w-xl flex-col gap-2 px-4 py-4">
          {/* Mensagem de erro de envio */}
          {erroEnvio && passo === TOTAL_PASSOS && (
            <div className="flex items-start gap-2 rounded-md border border-saida/30 bg-saida/5 px-4 py-2.5 text-sm text-saida">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mt-0.5 flex-shrink-0">
                <circle cx="12" cy="12" r="9" /><path d="M12 8v5M12 16.5v.5" strokeLinecap="round" />
              </svg>
              <span>{erroEnvio}</span>
            </div>
          )}

          <div className="flex items-center justify-between gap-3">
            {passo > 1 ? (
              <button
                type="button"
                onClick={voltar}
                disabled={enviando}
                className="flex items-center gap-1.5 rounded-md border border-line bg-surface px-5 py-3 text-sm font-semibold text-ink transition-colors hover:bg-surface-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-soft disabled:opacity-40"
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
                  disabled={passo === 1 && !credenciaisValidas}
                  title={passo === 1 && !credenciaisValidas ? "Preencha e-mail e senha válidos para continuar" : undefined}
                  className="flex items-center gap-1.5 rounded-md bg-brand-dark px-5 py-3 text-sm font-semibold text-brand-fg transition-colors hover:bg-brand focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-soft disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Continuar
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={concluir}
                  disabled={enviando}
                  className="flex items-center gap-1.5 rounded-md bg-brand-dark px-5 py-3 text-sm font-semibold text-brand-fg transition-colors hover:bg-brand focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-soft disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {enviando ? (
                    <>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="animate-spin">
                        <circle cx="12" cy="12" r="9" strokeOpacity="0.25" />
                        <path d="M12 3a9 9 0 0 1 9 9" strokeLinecap="round" />
                      </svg>
                      Salvando...
                    </>
                  ) : (
                    <>
                      Concluir e ir pro painel
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
