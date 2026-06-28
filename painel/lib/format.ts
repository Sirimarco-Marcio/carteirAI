/** Formatação e mapeamentos de apresentação (PT-BR / BRL). */

export function brl(valor: number): string {
  return valor.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
  });
}

/** Valor com sinal explícito para entradas/saídas (+/-). */
export function brlSinal(valor: number, tipo: "entrada" | "saida"): string {
  const sinal = tipo === "entrada" ? "+" : "-";
  return `${sinal}${brl(Math.abs(valor))}`;
}

export const MESES_PT = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];

/** Cor (hex) por categoria — estável em todo o app (corrige a inconsistência do Stitch).
 *  Usada via `style` inline para evitar classes dinâmicas que o Tailwind JIT não geraria. */
export const CORES_CATEGORIA: Record<string, string> = {
  Moradia: "#2f6f5e",
  Mercado: "#d4a017",
  Transporte: "#3b82c4",
  Educação: "#d97b35",
  Alimentação: "#d97b35",
  Lazer: "#8a5cd1",
  Saúde: "#d1495b",
  Assinaturas: "#8a5cd1",
  Pix: "#1e6f5c",
  Transferências: "#1e6f5c",
};

export function corCategoria(nome: string): string {
  return CORES_CATEGORIA[nome] ?? "#5c6661";
}
