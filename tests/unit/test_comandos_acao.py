"""Testes unitários (RED) para comandos de ação (mutação) do bot Telegram.
Contratos: CMD-04 a CMD-11 (docs/tdd/06-contratos-comandos-acao.md).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from carteirai.dominio.dtos import Fatura, FonteRenda, Transacao
from carteirai.telegram.comandos import DespachanteComandos
from tests.fakes import (
    FakeConsultas,
    FakeFaturaServiceCmd,
    FakeRendaService,
    FakeTransacaoServiceCmd,
)


# ---------------------------------------------------------------------------
# CMD-04 a CMD-06 — /faltei
# ---------------------------------------------------------------------------

def test_cmd_04_faltei_sem_data_registra_hoje():
    """CMD-04: /faltei (sem data) -> cria registro para hoje e confirma."""
    fonte = FonteRenda(id="f1", usuario_id="u", nome="BNDES", tipo_calculo="por_dia")
    renda_svc = FakeRendaService(fonte_ativa=fonte)
    despachante = DespachanteComandos(FakeConsultas(), renda_svc=renda_svc)
    
    resposta = despachante.processar("/faltei", "u")
    
    assert "✅ Falta registrada para hoje" in resposta
    assert len(renda_svc.registros) == 1
    assert renda_svc.registros[0].data == date.today()
    assert renda_svc.registros[0].status == "falta"

def test_cmd_05_faltei_com_data():
    """CMD-05: /faltei 18/06 -> registra falta para 18/06 no ano atual."""
    fonte = FonteRenda(id="f1", usuario_id="u", nome="BNDES", tipo_calculo="por_dia")
    renda_svc = FakeRendaService(fonte_ativa=fonte)
    despachante = DespachanteComandos(FakeConsultas(), renda_svc=renda_svc)
    
    resposta = despachante.processar("/faltei 18/06", "u")
    
    assert "✅ Falta registrada para 18/06" in resposta
    assert len(renda_svc.registros) == 1
    assert renda_svc.registros[0].data == date(date.today().year, 6, 18)
    assert renda_svc.registros[0].status == "falta"

def test_cmd_05b_faltei_com_data_invalida():
    """CMD-05b: /faltei 99/99 -> informa erro de formatação."""
    fonte = FonteRenda(id="f1", usuario_id="u", nome="BNDES", tipo_calculo="por_dia")
    renda_svc = FakeRendaService(fonte_ativa=fonte)
    despachante = DespachanteComandos(FakeConsultas(), renda_svc=renda_svc)
    
    resposta = despachante.processar("/faltei 99/99", "u")
    
    assert "Data inválida" in resposta
    assert "Use: /faltei DD/MM" in resposta
    assert len(renda_svc.registros) == 0

def test_cmd_06_faltei_idempotente():
    """CMD-06: /faltei na mesma data faz upsert (validamos apenas o sucesso da resposta)."""
    fonte = FonteRenda(id="f1", usuario_id="u", nome="BNDES", tipo_calculo="por_dia")
    renda_svc = FakeRendaService(fonte_ativa=fonte)
    despachante = DespachanteComandos(FakeConsultas(), renda_svc=renda_svc)
    
    # A idempotência real fica no RendaService. Para o despachante, deve apenas
    # chamar registrar_dia e responder com sucesso sem duplicar a mensagem de erro.
    resposta = despachante.processar("/faltei 18/06", "u")
    assert "✅ Falta registrada" in resposta


# ---------------------------------------------------------------------------
# CMD-08 — /desfazer
# ---------------------------------------------------------------------------

def test_cmd_08_desfazer_com_transacao_confirmada():
    """CMD-08: /desfazer com transação confirmada reverte e avisa."""
    from datetime import datetime
    t_confirmada = Transacao(
        id="t1", conta_id="c1", usuario_id="u", valor=Decimal("15.50"),
        data_hora=datetime(2024, 6, 18, 12, 0), estabelecimento="Padaria",
        categoria="Alimentação", forma="pix", tipo="saida", status="CONFIRMADA"
    )
    transacao_svc = FakeTransacaoServiceCmd(ultima_transacao=t_confirmada)
    despachante = DespachanteComandos(FakeConsultas(), transacao_svc=transacao_svc)
    
    resposta = despachante.processar("/desfazer", "u")
    
    assert "↩️ Última transação desfeita" in resposta
    assert "15,50" in resposta
    assert "Padaria" in resposta

def test_cmd_08b_desfazer_sem_transacao_confirmada():
    """CMD-08b: /desfazer sem transação para reverter -> avisa usuário."""
    transacao_svc = FakeTransacaoServiceCmd(ultima_transacao=None)
    despachante = DespachanteComandos(FakeConsultas(), transacao_svc=transacao_svc)
    
    resposta = despachante.processar("/desfazer", "u")
    
    assert "Nenhuma transação para desfazer" in resposta


# ---------------------------------------------------------------------------
# CMD-09 — /pagar_fatura
# ---------------------------------------------------------------------------

def test_cmd_09_pagar_fatura_sem_fatura_aberta():
    """CMD-09: /pagar_fatura quando não há fatura ABERTA."""
    faturas_svc = FakeFaturaServiceCmd(faturas=[])
    despachante = DespachanteComandos(FakeConsultas(), faturas_svc=faturas_svc)
    
    resposta = despachante.processar("/pagar_fatura", "u")
    
    assert "Sem fatura em aberto" in resposta

def test_cmd_09b_pagar_fatura_com_fatura_aberta():
    """CMD-09b: /pagar_fatura com exata 1 fatura ABERTA -> paga direto."""
    fatura = Fatura(
        id="fat1", conta_id="c1", mes=6, ano=2024,
        valor_total=Decimal("500.00"), status="ABERTA"
    )
    faturas_svc = FakeFaturaServiceCmd(faturas=[fatura])
    despachante = DespachanteComandos(FakeConsultas(), faturas_svc=faturas_svc)
    
    resposta = despachante.processar("/pagar_fatura", "u")
    
    assert "✅ Fatura de R$ 500,00 paga" in resposta
    assert len(faturas_svc.pagamentos) == 1
    assert faturas_svc.pagamentos[0][0] == "fat1"

def test_cmd_09c_pagar_fatura_multiplas_faturas():
    """CMD-09c: /pagar_fatura com múltiplas faturas -> pede confirmação listando-as."""
    f1 = Fatura(id="fat1", conta_id="c1", mes=6, ano=2024, valor_total=Decimal("500.00"), status="ABERTA")
    f2 = Fatura(id="fat2", conta_id="c2", mes=6, ano=2024, valor_total=Decimal("300.00"), status="ABERTA")
    faturas_svc = FakeFaturaServiceCmd(faturas=[f1, f2])
    despachante = DespachanteComandos(FakeConsultas(), faturas_svc=faturas_svc)
    
    resposta = despachante.processar("/pagar_fatura", "u")
    
    assert "Qual fatura pagar?" in resposta
    assert len(faturas_svc.pagamentos) == 0


# ---------------------------------------------------------------------------
# CMD-11 — /lancar
# ---------------------------------------------------------------------------

def test_cmd_11_lancar_template():
    """CMD-11: /lancar vazio -> retorna o template de uso."""
    transacao_svc = FakeTransacaoServiceCmd()
    despachante = DespachanteComandos(FakeConsultas(), transacao_svc=transacao_svc)
    
    resposta = despachante.processar("/lancar", "u")
    
    assert "📝 Lançamento manual" in resposta
    assert "valor | categoria | forma" in resposta
    assert "Exemplo:" in resposta

def test_cmd_11b_lancar_com_payload():
    """CMD-11b: /lancar <args> -> cria transação pendente_aprovacao."""
    transacao_svc = FakeTransacaoServiceCmd()
    despachante = DespachanteComandos(FakeConsultas(), transacao_svc=transacao_svc)
    
    resposta = despachante.processar("/lancar 45.90 | Alimentação | pix | almoço no centro", "u")
    
    assert "✅ Transação criada" in resposta
    assert len(transacao_svc.manuais) == 1
    
    chamada = transacao_svc.manuais[0]
    assert chamada["valor"] == Decimal("45.90")
    assert chamada["categoria"] == "Alimentação"
    assert chamada["forma"] == "pix"
    assert chamada["descricao"] == "almoço no centro"

def test_cmd_11c_lancar_categoria_invalida():
    """CMD-11c: /lancar com categoria errada -> rejeita e lista corretas."""
    transacao_svc = FakeTransacaoServiceCmd()
    despachante = DespachanteComandos(FakeConsultas(), transacao_svc=transacao_svc)
    
    resposta = despachante.processar("/lancar 45.90 | CategoriaErrada | pix | almoço", "u")
    
    assert "Categoria inválida" in resposta
    # Deve listar categorias como Alimentação, Transporte, etc
    assert "Alimentação" in resposta
    assert len(transacao_svc.manuais) == 0
