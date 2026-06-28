import { NextRequest, NextResponse } from "next/server";
import { neon } from "@neondatabase/serverless";
import { createHash } from "node:crypto";

/**
 * POST /api/ingestao — porta de entrada da notificação do app Android (docs/06 Chunk A).
 *
 * Fluxo: valida auth → pré-filtro (sem IA) → INSERT na fila_ingestao do Neon.
 * O worker do Pi faz polling dessa tabela. A Vercel é serverless: nada de estado em memória.
 *
 * PENDENTE (precisa de ambiente real):
 *  - Trocar o segredo compartilhado (INGEST_SECRET) por verificação de token do Neon Auth e
 *    DERIVAR o usuario_id do token (não confiar no corpo) — ver docs/06 A.3 / S3.
 *  - Pré-filtro completo: validar que package_name está mapeado a uma conta do usuário
 *    (consulta à tabela de mapeamento) — hoje só checamos se há valor monetário.
 */

export const runtime = "nodejs";

interface Payload {
  usuario_id?: string;
  package_name?: string;
  title?: string | null;
  text?: string | null;
  posted_at?: number; // ms
  client_msg_id?: string | null;
  latitude?: number;
  longitude?: number;
}

/** hash exato — espelha carteirai.dedup.dedup.hash_exato (normaliza e SHA-256). */
function hashExato(textoBruto: string): string {
  const normalizado = textoBruto.trim().replace(/\s+/g, " ").toLowerCase();
  return createHash("sha256").update(normalizado, "utf8").digest("hex");
}

/** Pré-filtro barato (sem IA): há valor monetário no texto? (docs/06 A.5) */
function temValorMonetario(texto: string): boolean {
  return /\d[\d.,]*\d|\d/.test(texto);
}

export async function POST(req: NextRequest) {
  // --- Auth (provisório: segredo compartilhado; trocar por Neon Auth) ---
  const auth = req.headers.get("authorization") || "";
  const segredo = process.env.INGEST_SECRET;
  if (!segredo || auth !== `Bearer ${segredo}`) {
    return NextResponse.json({ erro: "não autorizado" }, { status: 401 });
  }

  let corpo: Payload;
  try {
    corpo = (await req.json()) as Payload;
  } catch {
    return NextResponse.json({ erro: "JSON inválido" }, { status: 400 });
  }

  // Monta texto_bruto a partir de title/text
  const partes = [corpo.title, corpo.text].filter((p): p is string => !!p && p.trim() !== "");
  const textoBruto = partes.join(" ").trim();
  if (!textoBruto) {
    return NextResponse.json({ erro: "title e text ambos ausentes" }, { status: 422 });
  }
  if (!corpo.usuario_id || !corpo.package_name) {
    return NextResponse.json({ erro: "usuario_id e package_name obrigatórios" }, { status: 422 });
  }

  // --- Pré-filtro: sem valor monetário → descarta (não é transação) ---
  if (!temValorMonetario(textoBruto)) {
    return NextResponse.json({ status: "descartado", motivo: "sem valor monetário" }, { status: 202 });
  }

  const dataHora = corpo.posted_at ? new Date(corpo.posted_at) : new Date();
  const idHash = hashExato(textoBruto);

  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) {
    return NextResponse.json({ erro: "DATABASE_URL não configurada" }, { status: 500 });
  }
  const sql = neon(dbUrl);

  try {
    // Idempotência por client_msg_id (UNIQUE) — ON CONFLICT DO NOTHING.
    const linhas = await sql`
      INSERT INTO fila_ingestao
        (id_hash, texto_bruto, usuario_id, package_name, origem, status, tentativas, data_hora, client_msg_id, criada_em)
      VALUES
        (${idHash}, ${textoBruto}, ${corpo.usuario_id}, ${corpo.package_name}, 'notificacao', 'PENDENTE', 0, ${dataHora.toISOString()}, ${corpo.client_msg_id ?? null}, now())
      ON CONFLICT (client_msg_id) DO NOTHING
      RETURNING id
    `;
    const fila_id = linhas[0]?.id ?? null;
    return NextResponse.json({ status: "enfileirado", fila_id }, { status: 202 });
  } catch (e) {
    return NextResponse.json({ erro: "falha ao enfileirar", detalhe: String(e) }, { status: 500 });
  }
}
