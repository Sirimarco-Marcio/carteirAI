import { NextRequest, NextResponse } from "next/server";
import { neon } from "@neondatabase/serverless";

/**
 * POST /api/onboarding — persiste a configuração inicial da família no Neon.
 *
 * Cria em transação única:
 *   familias → usuarios → instituicoes + contas → fontes_renda → dividas_creditos
 *
 * TODO (B2): adicionar gating via Neon Auth antes de expor em produção.
 * Por ora sem autenticação (fluxo de setup inicial — B1).
 */

export const runtime = "nodejs";

// ---------------------------------------------------------------------------
// Tipos de entrada
// ---------------------------------------------------------------------------

interface MembroPayload {
  nome: string;
  usuario_id?: string; // UUID do app Android ("Copiar ID" no app Notifier)
  telegram_chat_id?: string;
  role: "admin" | "membro";
}

interface ContaPayload {
  banco: string;
  package_name?: string;
  tipo: "corrente" | "credito" | "dinheiro";
  saldo?: number;
  limite?: number;
  dia_fechamento?: number;
  dia_vencimento?: number;
}

interface FontePayload {
  nome: string;
  tipo_calculo: "fixo_mensal" | "por_dia";
  valor_base: number;
  valor_alimentacao_dia?: number;
  valor_transporte_dia?: number;
  dias_semana?: number[];
}

interface DividaPayload {
  contraparte_nome: string;
  valor: number;
  tipo: "devo" | "me_devem";
  vencimento?: string; // ISO date "YYYY-MM-DD"
}

interface OnboardingPayload {
  familia: { nome: string };
  membros: MembroPayload[];
  contas?: ContaPayload[];
  fontes?: FontePayload[];
  dividas?: DividaPayload[];
}

// ---------------------------------------------------------------------------
// Handler
// ---------------------------------------------------------------------------

export async function POST(req: NextRequest) {
  let body: OnboardingPayload;
  try {
    body = (await req.json()) as OnboardingPayload;
  } catch {
    return NextResponse.json({ erro: "JSON inválido" }, { status: 400 });
  }

  // --- Validação mínima ---
  if (!body?.familia?.nome?.trim()) {
    return NextResponse.json(
      { erro: "familia.nome é obrigatório" },
      { status: 422 }
    );
  }
  if (!Array.isArray(body.membros) || body.membros.length === 0) {
    return NextResponse.json(
      { erro: "É necessário ao menos um membro" },
      { status: 422 }
    );
  }
  const temAdmin = body.membros.some((m) => m.role === "admin");
  if (!temAdmin) {
    return NextResponse.json(
      { erro: "É necessário ao menos um membro com role 'admin'" },
      { status: 422 }
    );
  }

  const dbUrl = process.env.DATABASE_URL;
  if (!dbUrl) {
    return NextResponse.json(
      { erro: "DATABASE_URL não configurada" },
      { status: 500 }
    );
  }
  const sql = neon(dbUrl);

  try {
    // -------------------------------------------------------------------------
    // Gera IDs no JS para não depender de RETURNING em cada statement
    // -------------------------------------------------------------------------
    const familiaId = crypto.randomUUID();

    // Mapeia cada membro ao seu UUID final
    const membrosComId = body.membros.map((m) => {
      // O admin pode fornecer o UUID do app Android; demais sempre randomUUID
      const id =
        m.role === "admin" && m.usuario_id?.trim()
          ? m.usuario_id.trim()
          : crypto.randomUUID();
      return { ...m, _id: id };
    });

    // O "dono" das contas/fontes é o primeiro admin encontrado
    const adminMembro = membrosComId.find((m) => m.role === "admin")!;
    const adminId = adminMembro._id;

    // -------------------------------------------------------------------------
    // Monta lista de queries para a transação
    // -------------------------------------------------------------------------
    const queries: ReturnType<typeof sql>[] = [];

    // 1. Família
    queries.push(
      sql`
        INSERT INTO familias (id, nome, saldo_acumulado)
        VALUES (${familiaId}::uuid, ${body.familia.nome.trim()}, 0)
      `
    );

    // 2. Usuários
    for (const m of membrosComId) {
      const chatId = m.telegram_chat_id?.trim() || null;
      queries.push(
        sql`
          INSERT INTO usuarios (id, familia_id, nome, telegram_chat_id, role)
          VALUES (
            ${m._id}::uuid,
            ${familiaId}::uuid,
            ${m.nome.trim()},
            ${chatId},
            ${m.role}
          )
        `
      );
    }

    // 3. Contas — para cada conta: cria instituicao + conta
    for (const c of body.contas ?? []) {
      const instId = crypto.randomUUID();
      const contaId = crypto.randomUUID();

      // tipo da instituição: cartao se credito, banco se corrente/dinheiro
      const instTipo = c.tipo === "credito" ? "cartao" : "banco";

      queries.push(
        sql`
          INSERT INTO instituicoes (id, nome, tipo)
          VALUES (${instId}::uuid, ${c.banco.trim()}, ${instTipo})
        `
      );

      queries.push(
        sql`
          INSERT INTO contas (
            id, usuario_id, instituicao_id, tipo,
            saldo_atual, limite, dia_fechamento, dia_vencimento, package_name
          )
          VALUES (
            ${contaId}::uuid,
            ${adminId}::uuid,
            ${instId}::uuid,
            ${c.tipo},
            ${c.saldo ?? 0},
            ${c.limite ?? null},
            ${c.dia_fechamento ?? null},
            ${c.dia_vencimento ?? null},
            ${c.package_name?.trim() || null}
          )
        `
      );
    }

    // 4. Fontes de renda
    for (const f of body.fontes ?? []) {
      const fonteId = crypto.randomUUID();
      const diasSemana = JSON.stringify(f.dias_semana ?? []);

      queries.push(
        sql`
          INSERT INTO fontes_renda (
            id, usuario_id, nome, tipo_calculo,
            valor_base, valor_alimentacao_dia, valor_transporte_dia, dias_semana, ativa
          )
          VALUES (
            ${fonteId}::uuid,
            ${adminId}::uuid,
            ${f.nome.trim()},
            ${f.tipo_calculo},
            ${f.valor_base},
            ${f.valor_alimentacao_dia ?? 0},
            ${f.valor_transporte_dia ?? 0},
            ${diasSemana}::jsonb,
            true
          )
        `
      );
    }

    // 5. Dívidas
    for (const d of body.dividas ?? []) {
      const dividaId = crypto.randomUUID();

      queries.push(
        sql`
          INSERT INTO dividas_creditos (
            id, usuario_id, contraparte_nome, tipo, valor, vencimento, status
          )
          VALUES (
            ${dividaId}::uuid,
            ${adminId}::uuid,
            ${d.contraparte_nome.trim()},
            ${d.tipo},
            ${d.valor},
            ${d.vencimento || null},
            'aberta'
          )
        `
      );
    }

    // -------------------------------------------------------------------------
    // Executa tudo em transação única
    // -------------------------------------------------------------------------
    await sql.transaction(queries);

    // -------------------------------------------------------------------------
    // Resposta de sucesso
    // -------------------------------------------------------------------------
    return NextResponse.json(
      {
        familia_id: familiaId,
        usuarios: membrosComId.map((m) => ({
          id: m._id,
          nome: m.nome.trim(),
          role: m.role,
        })),
      },
      { status: 201 }
    );
  } catch (e) {
    console.error("[onboarding] erro ao persistir:", e);
    return NextResponse.json(
      { erro: "Falha ao salvar no banco", detalhe: String(e) },
      { status: 500 }
    );
  }
}
