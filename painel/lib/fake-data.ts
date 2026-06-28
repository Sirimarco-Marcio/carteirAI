/**
 * Camada de dados FALSOS (mock data source) — simula a API/Neon.
 *
 * Nada é hardcoded nas telas: as páginas consomem estas funções assíncronas (com
 * atraso simulado, para exercitar os estados de carregamento). Quando o backend real
 * existir, basta trocar a implementação destas funções por chamadas às API Routes.
 */

export type Tipo = "entrada" | "saida";

export interface Usuario {
  id: string;
  nome: string;
  iniciais: string;
  emoji: string;
  papel: "admin" | "membro";
}

export interface Transacao {
  id: string;
  estabelecimento: string;
  categoria: string;
  pessoa: string;
  conta: string;
  valor: number;
  tipo: Tipo;
  forma: "debito" | "credito" | "pix" | "dinheiro";
  data: string; // ISO
  possivelDuplicata?: boolean;
}

export interface GastoCategoria {
  categoria: string;
  valor: number;
  percentual: number;
}

export interface ResumoPainel {
  saudacao: string;
  competencia: string;
  saldoAcumulado: number;
  variacaoPct: number;
  saldoGiro: number;
  totalGasto: number;
  faturasAberto: number;
  faturaVenceEmDias: number;
  pendencias: number;
  sparkline: number[]; // 30 pontos
  gastosPorCategoria: GastoCategoria[];
  ultimasTransacoes: Transacao[];
}

export interface Cartao {
  id: string;
  banco: string;
  limite: number;
  usado: number;
  diaFechamento: number;
  diaVencimento: number;
}

export interface Notificacao {
  id: string;
  titulo: string;
  detalhe: string;
  quando: string;
  lida: boolean;
}

export interface Dispositivo {
  id: string;
  nome: string;
  ultimoEnvio: string;
  ativo: boolean;
}

// --- atraso simulado para exercitar telas de carregamento ---
const atraso = <T>(dado: T, ms = 700): Promise<T> =>
  new Promise((resolve) => setTimeout(() => resolve(dado), ms));

export const USUARIO_ATUAL: Usuario = {
  id: "u1",
  nome: "Marcio",
  iniciais: "M",
  emoji: "🦊",
  papel: "admin",
};

const SPARKLINE = [
  12, 11.6, 11.9, 12.4, 12.2, 12.8, 13.1, 12.9, 13.4, 13.2, 13.0, 13.6, 14.1, 13.8,
  14.0, 13.5, 13.9, 14.3, 14.6, 14.2, 14.0, 14.4, 14.8, 14.5, 14.1, 14.3, 14.7, 14.9,
  14.6, 14.52,
];

const ULTIMAS: Transacao[] = [
  { id: "t1", estabelecimento: "Padaria Central", categoria: "Alimentação", pessoa: "Marcio", conta: "Nubank", valor: 45.5, tipo: "saida", forma: "debito", data: "2026-06-27T08:10:00" },
  { id: "t2", estabelecimento: "Pix recebido — João", categoria: "Pix", pessoa: "Marcio", conta: "Nubank", valor: 250, tipo: "entrada", forma: "pix", data: "2026-06-26T19:02:00" },
  { id: "t3", estabelecimento: "Posto Ipiranga", categoria: "Transporte", pessoa: "Esposa", conta: "Itaú", valor: 188, tipo: "saida", forma: "credito", data: "2026-06-26T17:40:00" },
  { id: "t4", estabelecimento: "Supermercado Pão de Açúcar", categoria: "Mercado", pessoa: "Marcio", conta: "Itaú", valor: 450.2, tipo: "saida", forma: "credito", data: "2026-06-25T12:30:00", possivelDuplicata: true },
  { id: "t5", estabelecimento: "Salário Maria", categoria: "Transferências", pessoa: "Esposa", conta: "Itaú", valor: 8500, tipo: "entrada", forma: "pix", data: "2026-06-25T09:00:00" },
];

export async function getResumoPainel(): Promise<ResumoPainel> {
  return atraso({
    saudacao: "Bom dia, Família",
    competencia: "Junho 2026",
    saldoAcumulado: 14520,
    variacaoPct: 2.4,
    saldoGiro: 4250,
    totalGasto: 3840.5,
    faturasAberto: 1200,
    faturaVenceEmDias: 2,
    pendencias: 3,
    sparkline: SPARKLINE,
    gastosPorCategoria: [
      { categoria: "Moradia", valor: 2500, percentual: 45 },
      { categoria: "Mercado", valor: 850, percentual: 30 },
      { categoria: "Transporte", valor: 400, percentual: 15 },
      { categoria: "Educação", valor: 290.5, percentual: 10 },
    ],
    ultimasTransacoes: ULTIMAS,
  });
}

export async function getTransacoes(): Promise<Transacao[]> {
  return atraso(ULTIMAS);
}

export async function getCartoes(): Promise<Cartao[]> {
  return atraso([
    { id: "c1", banco: "Nubank", limite: 5000, usado: 1200, diaFechamento: 3, diaVencimento: 10 },
    { id: "c2", banco: "Itaú", limite: 8000, usado: 3640.2, diaFechamento: 20, diaVencimento: 27 },
  ]);
}

export async function getNotificacoes(): Promise<Notificacao[]> {
  return atraso([
    { id: "n1", titulo: "Fatura Nubank vence em 2 dias", detalhe: "R$ 1.200,00", quando: "há 1h", lida: false },
    { id: "n2", titulo: "3 transações pendentes de aprovação", detalhe: "Toque para revisar", quando: "há 3h", lida: false },
    { id: "n3", titulo: "Pix recebido — João", detalhe: "+R$ 250,00", quando: "ontem", lida: true },
  ]);
}

export async function getDispositivos(): Promise<Dispositivo[]> {
  return atraso([
    { id: "d1", nome: "Galaxy S23 (Marcio)", ultimoEnvio: "há 12 min", ativo: true },
    { id: "d2", nome: "Moto G (Esposa)", ultimoEnvio: "há 2 dias", ativo: true },
  ]);
}

// --- Renda & fechamento ---
export interface FonteRenda {
  id: string;
  nome: string;
  tipo: "fixo_mensal" | "por_dia";
  previsto: number;
  realizado?: number;
}
export interface DiaTrabalho {
  data: string; // ISO (dia)
  status: "presencial" | "remoto" | "falta";
}
export interface ResumoRenda {
  competencia: string;
  fontes: FonteRenda[];
  previstoTotal: number;
  realizadoTotal?: number;
  totalGasto: number;
  sobra?: number;
  dias: DiaTrabalho[]; // dias do mês com status (para o calendário)
}

export async function getRenda(): Promise<ResumoRenda> {
  const dias: DiaTrabalho[] = [];
  for (let d = 1; d <= 30; d++) {
    const dow = new Date(2026, 5, d).getDay();
    if (dow === 0 || dow === 6) continue; // fim de semana fora
    let status: DiaTrabalho["status"] = "presencial";
    if (d === 12) status = "falta";
    else if (d === 18 || d === 25) status = "remoto";
    dias.push({ data: `2026-06-${String(d).padStart(2, "0")}`, status });
  }
  return atraso({
    competencia: "Junho 2026",
    fontes: [
      { id: "f1", nome: "UERJ", tipo: "fixo_mensal", previsto: 300, realizado: 300 },
      { id: "f2", nome: "Convem", tipo: "fixo_mensal", previsto: 1500, realizado: 1500 },
      { id: "f3", nome: "BNDES", tipo: "por_dia", previsto: 3200, realizado: 2980 },
    ],
    previstoTotal: 5000,
    realizadoTotal: 4780,
    totalGasto: 3840.5,
    sobra: 939.5,
    dias,
  });
}

// --- Relatório mensal ---
export interface ResumoRelatorio {
  competencia: string;
  rendaPorFonte: { nome: string; valor: number }[];
  gastosPorCategoria: GastoCategoria[];
  diasTrabalhados: number;
  diasRemotos: number;
  diasFaltados: number;
  rendaRealizada: number;
  totalGasto: number;
  sobra: number;
  evolucaoSaldo: number[];
}

export async function getRelatorio(): Promise<ResumoRelatorio> {
  return atraso({
    competencia: "Junho 2026",
    rendaPorFonte: [
      { nome: "UERJ", valor: 300 },
      { nome: "Convem", valor: 1500 },
      { nome: "BNDES", valor: 2980 },
    ],
    gastosPorCategoria: [
      { categoria: "Moradia", valor: 2500, percentual: 45 },
      { categoria: "Mercado", valor: 850, percentual: 30 },
      { categoria: "Transporte", valor: 400, percentual: 15 },
      { categoria: "Educação", valor: 290.5, percentual: 10 },
    ],
    diasTrabalhados: 18,
    diasRemotos: 2,
    diasFaltados: 1,
    rendaRealizada: 4780,
    totalGasto: 3840.5,
    sobra: 939.5,
    evolucaoSaldo: [12, 12.4, 12.9, 13.4, 13.2, 13.8, 14.1, 14.0, 14.4, 14.52],
  });
}

// --- Configurações / Conta ---
export interface ContaCadastro {
  id: string;
  banco: string;
  tipo: "conta" | "cartao" | "ambos";
  packageName: string;
  saldo?: number;
  limite?: number;
}
export interface MembroFamilia {
  id: string;
  nome: string;
  emoji: string;
  papel: "admin" | "membro";
}
export interface DadosConfig {
  contas: ContaCadastro[];
  categorias: string[];
  membros: MembroFamilia[];
}

export async function getConfig(): Promise<DadosConfig> {
  return atraso({
    contas: [
      { id: "co1", banco: "Nubank", tipo: "ambos", packageName: "com.nu.production", saldo: 4250, limite: 5000 },
      { id: "co2", banco: "Itaú", tipo: "ambos", packageName: "com.itau", saldo: 980, limite: 8000 },
      { id: "co3", banco: "Mercado Pago", tipo: "conta", packageName: "com.mercadopago.wallet", saldo: 320 },
    ],
    categorias: [
      "Alimentação", "Mercado", "Transporte", "Moradia", "Saúde", "Educação",
      "Lazer", "Assinaturas", "Vestuário", "Lanche na rua", "Presentes", "Pix",
      "Transferências", "Investimentos/Reserva", "Outros",
    ],
    membros: [
      { id: "u1", nome: "Marcio", emoji: "🦊", papel: "admin" },
      { id: "u2", nome: "Esposa", emoji: "🐱", papel: "membro" },
    ],
  });
}
