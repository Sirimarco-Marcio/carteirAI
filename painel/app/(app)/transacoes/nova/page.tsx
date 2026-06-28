"use client";

import { useState } from "react";
import { Card, BotaoPrimario } from "@/components/ui";
import Link from "next/link";

const CATEGORIAS = [
  "Alimentação",
  "Mercado",
  "Transporte",
  "Moradia",
  "Saúde",
  "Educação",
  "Lazer",
  "Assinaturas",
  "Vestuário",
  "Lanche na rua",
  "Presentes",
  "Pix",
  "Transferências",
  "Investimentos/Reserva",
  "Outros",
];

const FORMAS = [
  { value: "pix", label: "Pix" },
  { value: "debito", label: "Débito" },
  { value: "credito", label: "Crédito" },
  { value: "dinheiro", label: "Dinheiro" },
] as const;

export default function NovaTransacaoPage() {
  const [tipo, setTipo] = useState<"saida" | "entrada">("saida");

  return (
    <div className="mx-auto max-w-6xl">
      {/* Cabeçalho */}
      <header className="pr-28 lg:pr-0">
        <div className="flex items-center gap-3">
          <Link
            href="/transacoes"
            className="flex h-8 w-8 items-center justify-center rounded-full border border-line bg-surface text-muted transition-colors hover:bg-surface-2"
            aria-label="Voltar"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M15 18l-6-6 6-6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </Link>
          <h1 className="font-display text-3xl font-bold text-ink">Adicionar entrada</h1>
        </div>
        <p className="mt-1 pl-11 text-muted">Registre uma transação manualmente</p>
      </header>

      {/* Formulário */}
      <div className="mt-6 lg:max-w-lg">
        <Card className="p-6">
          <form className="space-y-5" onSubmit={(e) => e.preventDefault()}>

            {/* Tipo (entrada / saída) */}
            <div>
              <p className="label-caps mb-2">Tipo</p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setTipo("saida")}
                  className={`flex-1 rounded-md border py-2.5 text-sm font-semibold transition-colors ${
                    tipo === "saida"
                      ? "border-saida/40 bg-saida/10 text-saida"
                      : "border-line bg-surface text-muted hover:bg-surface-2"
                  }`}
                >
                  Saída
                </button>
                <button
                  type="button"
                  onClick={() => setTipo("entrada")}
                  className={`flex-1 rounded-md border py-2.5 text-sm font-semibold transition-colors ${
                    tipo === "entrada"
                      ? "border-entrada/40 bg-entrada/10 text-entrada"
                      : "border-line bg-surface text-muted hover:bg-surface-2"
                  }`}
                >
                  Entrada
                </button>
              </div>
            </div>

            {/* Valor */}
            <div>
              <label htmlFor="valor" className="label-caps mb-2 block">
                Valor (R$)
              </label>
              <div className="relative">
                <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-sm text-muted">
                  R$
                </span>
                <input
                  id="valor"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0,00"
                  className="money w-full rounded-md border border-line bg-surface py-3 pl-10 pr-4 text-right text-ink outline-none transition focus:border-brand focus:ring-[3px] focus:ring-brand-soft"
                />
              </div>
            </div>

            {/* Descrição / Estabelecimento */}
            <div>
              <label htmlFor="descricao" className="label-caps mb-2 block">
                Descrição / Estabelecimento
              </label>
              <input
                id="descricao"
                type="text"
                placeholder="Ex: Padaria Central"
                className="w-full rounded-md border border-line bg-surface px-4 py-3 text-ink outline-none transition focus:border-brand focus:ring-[3px] focus:ring-brand-soft"
              />
            </div>

            {/* Categoria */}
            <div>
              <label htmlFor="categoria" className="label-caps mb-2 block">
                Categoria
              </label>
              <select
                id="categoria"
                className="w-full rounded-md border border-line bg-surface px-4 py-3 text-ink outline-none transition focus:border-brand focus:ring-[3px] focus:ring-brand-soft"
              >
                <option value="">Selecionar categoria</option>
                {CATEGORIAS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            {/* Forma de pagamento */}
            <div>
              <label htmlFor="forma" className="label-caps mb-2 block">
                Forma de pagamento
              </label>
              <select
                id="forma"
                className="w-full rounded-md border border-line bg-surface px-4 py-3 text-ink outline-none transition focus:border-brand focus:ring-[3px] focus:ring-brand-soft"
              >
                <option value="">Selecionar forma</option>
                {FORMAS.map((f) => (
                  <option key={f.value} value={f.value}>
                    {f.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Data */}
            <div>
              <label htmlFor="data" className="label-caps mb-2 block">
                Data
              </label>
              <input
                id="data"
                type="date"
                className="w-full rounded-md border border-line bg-surface px-4 py-3 text-ink outline-none transition focus:border-brand focus:ring-[3px] focus:ring-brand-soft"
              />
            </div>

            {/* Ações */}
            <div className="flex gap-3 pt-2">
              <Link
                href="/transacoes"
                className="flex-1 rounded-md border border-line bg-surface py-3 text-center text-sm font-semibold text-muted transition-colors hover:bg-surface-2"
              >
                Cancelar
              </Link>
              <BotaoPrimario type="submit" className="flex-1">
                Salvar
              </BotaoPrimario>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
