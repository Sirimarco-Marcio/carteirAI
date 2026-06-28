"""Testes RED para o WorkerIngestao. Contratos: WORKER-01..06.
Referência: docs/tdd/09-contratos-worker.md

A classe alvo `carteirai.orquestracao.worker.WorkerIngestao` ainda NÃO existe —
este arquivo deve falhar com ImportError (fase RED esperada).
"""

from __future__ import annotations

from datetime import datetime
from typing import Union

import pytest
from sqlalchemy import create_engine

from carteirai.dominio.dtos import ResultadoProcessamento, TransacaoExtraida
from carteirai.fila.fila_ingestao import FilaIngestao, ItemFilaIngestao
from tests.fakes import RelogioFake

# ---------------------------------------------------------------------------
# Importação da classe alvo — deve falhar (RED)
# ---------------------------------------------------------------------------

from carteirai.orquestracao.worker import WorkerIngestao  # noqa: E402  (RED)

# ---------------------------------------------------------------------------
# Helpers e constantes
# ---------------------------------------------------------------------------

TEMPO_INICIO = datetime(2025, 3, 10, 10, 0, 0)
DATA_HORA_TX = datetime(2025, 3, 10, 9, 30, 0)

_ItemSequencia = Union[ResultadoProcessamento, Exception]


def _resultado_ok() -> ResultadoProcessamento:
    """Retorna um ResultadoProcessamento de sucesso."""
    return ResultadoProcessamento(
        status="PENDENTE_APROVACAO",
        possivel_duplicata=False,
        transacao=TransacaoExtraida(
            valor="50.00",
            data_hora=DATA_HORA_TX,
            estabelecimento="Mercado",
            categoria="Mercado",
            forma="debito",
            tipo="saida",
        ),
        motivo_erro=None,
        tentativas=1,
    )


def _enfileirar(fila: FilaIngestao, texto: str, usuario_id: str = "u1") -> ItemFilaIngestao:
    """Utilitário: insere um item PENDENTE na fila."""
    return fila.enqueue(
        texto_bruto=texto,
        usuario_id=usuario_id,
        origem="notificacao",
        package_name=None,
        data_hora=DATA_HORA_TX,
    )


# ---------------------------------------------------------------------------
# Fakes locais
# ---------------------------------------------------------------------------


class FakeOrquestrador:
    """Fake programável por sequência de resultados/exceções.

    Cada chamada a processar() consome o próximo item da sequência:
    - Se for Exception → levanta.
    - Se for ResultadoProcessamento → retorna.

    Atributo público:
        processados: lista de ItemFilaIngestao recebidos (na ordem de chamada).
    """

    def __init__(self, sequencia: list[_ItemSequencia] | None = None) -> None:
        self._sequencia: list[_ItemSequencia] = list(sequencia) if sequencia else []
        self.processados: list[ItemFilaIngestao] = []

    async def processar(self, item: ItemFilaIngestao) -> ResultadoProcessamento:
        self.processados.append(item)
        if not self._sequencia:
            return _resultado_ok()
        proximo = self._sequencia.pop(0)
        if isinstance(proximo, Exception):
            raise proximo
        return proximo  # type: ignore[return-value]


class FakeNotificador:
    """Fake do notificador; registra chamadas como tuplas (resultado, item).

    Atributo público:
        notificacoes: lista de tuplas (ResultadoProcessamento, ItemFilaIngestao).
    """

    def __init__(self) -> None:
        self.notificacoes: list[tuple[ResultadoProcessamento, ItemFilaIngestao]] = []

    def notificar(self, resultado: ResultadoProcessamento, item: ItemFilaIngestao) -> None:
        self.notificacoes.append((resultado, item))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def relogio() -> RelogioFake:
    return RelogioFake(TEMPO_INICIO)


@pytest.fixture
def engine():
    """Engine SQLite em memória — isola cada teste."""
    return create_engine("sqlite://")


@pytest.fixture
def fila(engine, relogio: RelogioFake) -> FilaIngestao:
    return FilaIngestao(engine, relogio=relogio)


# ---------------------------------------------------------------------------
# WORKER-01: reaper chamado exatamente uma vez por tick
# ---------------------------------------------------------------------------


async def test_worker_01_reaper_a_cada_tick(fila: FilaIngestao, relogio: RelogioFake) -> None:
    """tick() chama recuperar_orfaos() exatamente uma vez.

    Estratégia: enfileira um item, faz claim (→ PROCESSANDO), avança o relógio
    além do visibility_timeout (30 min) e chama tick(). Se o reaper rodou, o item
    volta a PENDENTE — caso contrário permanece em PROCESSANDO ou indefinido.
    """
    item = _enfileirar(fila, "orphan R$10")
    fila.claim()  # coloca em PROCESSANDO

    # Avança 31 minutos → item se torna órfão
    relogio.avancar(minutos=31)

    orquestrador = FakeOrquestrador()
    notificador = FakeNotificador()
    worker = WorkerIngestao(fila, orquestrador, notificador)

    await worker.tick()

    # O reaper deve ter devolvido o item a PENDENTE
    item_apos = fila.buscar(item.id)
    assert item_apos is not None
    assert item_apos.status == "PENDENTE", (
        "Esperava PENDENTE após reaper — reaper não foi chamado ou não rodou corretamente"
    )


# ---------------------------------------------------------------------------
# WORKER-02: drena todos os itens PENDENTE
# ---------------------------------------------------------------------------


async def test_worker_02_drena_todos_os_pendentes(fila: FilaIngestao, relogio: RelogioFake) -> None:
    """Com N itens PENDENTE, tick() chama processar N vezes; ao fim não há PENDENTE."""
    n = 3
    for i in range(n):
        _enfileirar(fila, f"transação {i} R${(i + 1) * 10}")

    orquestrador = FakeOrquestrador(sequencia=[_resultado_ok() for _ in range(n)])
    notificador = FakeNotificador()
    worker = WorkerIngestao(fila, orquestrador, notificador)

    await worker.tick()

    # processar deve ter sido chamado N vezes
    assert len(orquestrador.processados) == n

    # Não deve restar PENDENTE após drenagem
    pendentes = fila.listar_por_status("PENDENTE")
    assert pendentes == [], f"Esperava fila vazia, mas restaram {len(pendentes)} PENDENTE(s)"


# ---------------------------------------------------------------------------
# WORKER-03: ordem FIFO dos itens processados
# ---------------------------------------------------------------------------


async def test_worker_03_ordem_fifo(fila: FilaIngestao, relogio: RelogioFake) -> None:
    """Os itens são processados na ordem de enfileiramento (menor id primeiro)."""
    item_a = _enfileirar(fila, "primeiro R$10")
    item_b = _enfileirar(fila, "segundo R$20")
    item_c = _enfileirar(fila, "terceiro R$30")

    orquestrador = FakeOrquestrador()
    notificador = FakeNotificador()
    worker = WorkerIngestao(fila, orquestrador, notificador)

    await worker.tick()

    ids_processados = [i.id for i in orquestrador.processados]
    assert ids_processados == [item_a.id, item_b.id, item_c.id], (
        f"Esperava ordem FIFO {[item_a.id, item_b.id, item_c.id]}, obteve {ids_processados}"
    )


# ---------------------------------------------------------------------------
# WORKER-04: fila vazia — não chama processar nem notificar, mas roda reaper
# ---------------------------------------------------------------------------


async def test_worker_04_fila_vazia_nao_processa_nem_notifica(
    fila: FilaIngestao, relogio: RelogioFake
) -> None:
    """Sem PENDENTE, tick() roda o reaper mas não chama processar nem notificar.

    Verificação do reaper: enfileira+clama um item ANTES, avança 31 min, marca
    como CONCLUIDO (para que o reaper não o encontre como órfão). Fila fica vazia.
    Como não há PENDENTE, processar e notificar não devem ser chamados.
    """
    # Garante que não há PENDENTE
    orquestrador = FakeOrquestrador()
    notificador = FakeNotificador()
    worker = WorkerIngestao(fila, orquestrador, notificador)

    await worker.tick()

    assert orquestrador.processados == [], "processar não deve ser chamado com fila vazia"
    assert notificador.notificacoes == [], "notificar não deve ser chamado com fila vazia"

    # Para verificar que o reaper rodou: enfileira um item, clama, avança e confere
    # (feito em sub-verificação sem nova instância de worker)
    item = _enfileirar(fila, "orphan check R$5")
    fila.claim()
    relogio.avancar(minutos=31)

    worker2 = WorkerIngestao(fila, FakeOrquestrador(), FakeNotificador())
    await worker2.tick()

    item_apos = fila.buscar(item.id)
    assert item_apos is not None
    assert item_apos.status == "PENDENTE", (
        "Reaper deve ter rodado mesmo com fila originalmente vazia"
    )


# ---------------------------------------------------------------------------
# WORKER-05: notifica cada resultado com (resultado, item) corretos
# ---------------------------------------------------------------------------


async def test_worker_05_notifica_cada_resultado(
    fila: FilaIngestao, relogio: RelogioFake
) -> None:
    """Para cada item processado, notificador.notificar é chamado uma vez
    com o ResultadoProcessamento e o ItemFilaIngestao correspondentes."""
    item_a = _enfileirar(fila, "item A R$10")
    item_b = _enfileirar(fila, "item B R$20")

    resultado_a = ResultadoProcessamento(
        status="PENDENTE_APROVACAO",
        possivel_duplicata=False,
        transacao=None,
        motivo_erro=None,
        tentativas=1,
    )
    resultado_b = ResultadoProcessamento(
        status="IGNORADA",
        possivel_duplicata=False,
        transacao=None,
        motivo_erro=None,
        tentativas=1,
    )

    orquestrador = FakeOrquestrador(sequencia=[resultado_a, resultado_b])
    notificador = FakeNotificador()
    worker = WorkerIngestao(fila, orquestrador, notificador)

    await worker.tick()

    assert len(notificador.notificacoes) == 2

    res_notif_a, item_notif_a = notificador.notificacoes[0]
    assert res_notif_a is resultado_a
    assert item_notif_a.id == item_a.id

    res_notif_b, item_notif_b = notificador.notificacoes[1]
    assert res_notif_b is resultado_b
    assert item_notif_b.id == item_b.id


# ---------------------------------------------------------------------------
# WORKER-06: resiliência — exceção em 1 item não derruba o ciclo
# ---------------------------------------------------------------------------


async def test_worker_06_resilencia_excecao_em_um_item(
    fila: FilaIngestao, relogio: RelogioFake
) -> None:
    """Se processar() levantar exceção em 1 de N itens:
    - Esse item termina em ERRO (verificado via fila.buscar).
    - Os outros N-1 são processados normalmente.
    - tick() não propaga a exceção.
    - Não notifica o item que falhou (não há resultado).
    """
    item_ok_1 = _enfileirar(fila, "ok primeiro R$10")
    item_falho = _enfileirar(fila, "falha R$20")
    item_ok_2 = _enfileirar(fila, "ok terceiro R$30")

    resultado_ok_1 = _resultado_ok()
    resultado_ok_2 = _resultado_ok()
    erro_simulado = RuntimeError("LLM explodiu")

    orquestrador = FakeOrquestrador(
        sequencia=[resultado_ok_1, erro_simulado, resultado_ok_2]
    )
    notificador = FakeNotificador()
    worker = WorkerIngestao(fila, orquestrador, notificador)

    # tick() não deve propagar a exceção
    await worker.tick()

    # Item falho deve estar em ERRO
    item_falho_apos = fila.buscar(item_falho.id)
    assert item_falho_apos is not None
    assert item_falho_apos.status == "ERRO", (
        f"Item falho deve estar em ERRO, mas está {item_falho_apos.status!r}"
    )

    # Os outros dois devem ter sido processados (orquestrador registra os itens recebidos)
    ids_processados = [i.id for i in orquestrador.processados]
    assert item_ok_1.id in ids_processados
    assert item_ok_2.id in ids_processados
    assert len(ids_processados) == 3, (
        f"Esperava 3 chamadas a processar (incluindo a que falhou), obteve {len(ids_processados)}"
    )

    # Não deve notificar o item falho (apenas os 2 que tiveram resultado)
    assert len(notificador.notificacoes) == 2
    ids_notificados = [item.id for _, item in notificador.notificacoes]
    assert item_falho.id not in ids_notificados, (
        "Item falho não deve gerar notificação (não há resultado)"
    )
    assert item_ok_1.id in ids_notificados
    assert item_ok_2.id in ids_notificados
