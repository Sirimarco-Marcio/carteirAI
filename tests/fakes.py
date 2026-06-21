"""Dublês de teste (fakes) compartilhados entre os testes unitários.
Referência: docs/tdd/00-estrategia-tdd.md §4."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Union

from carteirai.dedup.dedup import HistoricoPort, TransacaoSimilar
from carteirai.dominio.dtos import TransacaoExtraida
from carteirai.ia.base_llm import BaseLLM, LLMError


class RelogioFake:
    """Relógio controlável para testes determinísticos.
    Referência: docs/tdd/00-estrategia-tdd.md §4 (RelogioFake).

    Uso:
        relogio = RelogioFake(datetime(2024, 1, 1, 12, 0, 0))
        relogio.agora()  # datetime(2024, 1, 1, 12, 0, 0)
        relogio.avancar(minutos=5)
        relogio.agora()  # datetime(2024, 1, 1, 12, 5, 0)

    Também é callable: relogio() == relogio.agora()
    """

    def __init__(self, inicio: datetime | None = None) -> None:
        self._agora = inicio or datetime(2024, 1, 1, 12, 0, 0)

    def agora(self) -> datetime:
        return self._agora

    def __call__(self) -> datetime:
        return self._agora

    def avancar(self, segundos: int = 0, minutos: int = 0, horas: int = 0) -> None:
        """Avança o relógio pelo delta especificado."""
        self._agora += timedelta(seconds=segundos, minutes=minutos, hours=horas)

    def definir(self, novo_tempo: datetime) -> None:
        """Define o tempo diretamente."""
        self._agora = novo_tempo


class FakeTransacaoRepo:
    """Implementa HistoricoPort e RepoTransacoes (ORQ) para testes unitários.
    Referência: docs/tdd/00-estrategia-tdd.md §4 (FakeTransacaoRepo).

    Args:
        hashes: conjunto de hashes já processados.
        transacoes_por_usuario: mapeamento usuario_id -> lista de TransacaoSimilar.

    Atributo público:
        salvos: lista de tuplas (usuario_id, hash, transacao, possivel_duplicata)
            gravadas via salvar() — usada pelos testes ORQ.
    """

    def __init__(
        self,
        hashes: set[str] | None = None,
        transacoes_por_usuario: dict[str, list[TransacaoSimilar]] | None = None,
    ) -> None:
        self._hashes: set[str] = hashes or set()
        self._transacoes: dict[str, list[TransacaoSimilar]] = (
            transacoes_por_usuario or {}
        )
        self.salvos: list[tuple] = []

    def hash_existe(self, hash: str) -> bool:
        return hash in self._hashes

    def transacoes(self, usuario_id: str) -> list[TransacaoSimilar]:
        return self._transacoes.get(usuario_id, [])

    def salvar(
        self,
        usuario_id: str,
        hash: str,
        transacao: TransacaoExtraida,
        possivel_duplicata: bool,
    ) -> None:
        """Registra a transação salva (usada pelos testes ORQ para verificar persistência)."""
        self.salvos.append((usuario_id, hash, transacao, possivel_duplicata))


class FakeFila:
    """Fake da fila de mensagens para testes ORQ.

    Registra todas as chamadas a marcar() na lista pública `marcacoes`.
    Cada entrada é uma tupla (item_id, status).
    """

    def __init__(self) -> None:
        self.marcacoes: list[tuple] = []

    def marcar(self, item_id: int, status: str) -> None:
        """Registra a marcação de status de um item da fila."""
        self.marcacoes.append((item_id, status))


# Tipo para itens da sequência do FakeLLM: retorna transação ou levanta erro.
_ItemSequencia = Union[TransacaoExtraida, LLMError, Exception]


# ---------------------------------------------------------------------------
# Fakes para ServicoTransacoes (TRANS-01..06)
# ---------------------------------------------------------------------------


class FakeContaRepo:
    """Implementa ContaRepo para testes de ServicoTransacoes.

    Guarda Conta(s) num dict por id. Permite consulta e atualização de saldo.
    """

    def __init__(self, contas: list | None = None) -> None:
        from carteirai.dominio.dtos import Conta

        self._contas: dict[str, Conta] = {}
        for conta in (contas or []):
            self._contas[conta.id] = conta

    def buscar(self, conta_id: str):
        return self._contas.get(conta_id)

    def atualizar_saldo(self, conta_id: str, novo_saldo) -> None:
        conta = self._contas[conta_id]
        self._contas[conta_id] = conta.model_copy(update={"saldo_atual": novo_saldo})


class FakeTransacaoStore:
    """Implementa TransacaoRepo (TRANS) para testes de ServicoTransacoes.

    Guarda Transacao(s) num dict por id. Suporta salvar/buscar/atualizar.
    """

    def __init__(self) -> None:
        from carteirai.dominio.dtos import Transacao

        self._transacoes: dict[str, Transacao] = {}

    def salvar(self, transacao) -> None:
        self._transacoes[transacao.id] = transacao

    def buscar(self, transacao_id: str):
        return self._transacoes.get(transacao_id)

    def atualizar(self, transacao) -> None:
        self._transacoes[transacao.id] = transacao


# ---------------------------------------------------------------------------
# Fakes para ServicoFaturas (FAT-01..09)
# ---------------------------------------------------------------------------


class FakeFaturaRepo:
    """Implementa FaturaRepo para testes de ServicoFaturas.

    Guarda Fatura(s) num dict por id. Gera ids incrementais ("f1", "f2", …).
    """

    def __init__(self, faturas: list | None = None) -> None:
        from carteirai.dominio.dtos import Fatura

        self._faturas: dict[str, Fatura] = {}
        self._contador: int = 0
        for fatura in (faturas or []):
            self._faturas[fatura.id] = fatura

    def _proximo_id(self) -> str:
        self._contador += 1
        return f"f{self._contador}"

    def buscar(self, fatura_id: str):
        return self._faturas.get(fatura_id)

    def buscar_aberta(self, conta_id: str, mes: int, ano: int):
        for fatura in self._faturas.values():
            if (
                fatura.conta_id == conta_id
                and fatura.mes == mes
                and fatura.ano == ano
                and fatura.status == "ABERTA"
            ):
                return fatura
        return None

    def criar(self, conta_id: str, mes: int, ano: int):
        from decimal import Decimal
        from carteirai.dominio.dtos import Fatura

        fatura = Fatura(
            id=self._proximo_id(),
            conta_id=conta_id,
            mes=mes,
            ano=ano,
            valor_total=Decimal("0"),
            status="ABERTA",
        )
        self._faturas[fatura.id] = fatura
        return fatura

    def atualizar(self, fatura) -> None:
        self._faturas[fatura.id] = fatura

    def abertas(self, conta_id: str) -> list:
        return [
            f for f in self._faturas.values()
            if f.conta_id == conta_id and f.status == "ABERTA"
        ]


# ---------------------------------------------------------------------------
# Fakes para ServicoAprovacao (APROV-01..09)
# ---------------------------------------------------------------------------


class FakeTelegram:
    """Implementa TelegramPort para testes de ServicoAprovacao.

    Captura todas as chamadas a enviar() na lista pública `enviados`.
    Cada entrada é uma tupla (chat_id, texto, botoes).
    """

    def __init__(self) -> None:
        self.enviados: list[tuple] = []

    def enviar(
        self, chat_id: str, texto: str, botoes: list[tuple[str, str]] | None = None
    ) -> None:
        self.enviados.append((chat_id, texto, botoes))


class FakeUsuarioRepo:
    """Implementa UsuarioRepo para testes de ServicoAprovacao.

    Construído com dict `usuario_id -> chat_id`; suporta lookup direto e inverso.
    """

    def __init__(self, mapeamento: dict[str, str] | None = None) -> None:
        self._mapa: dict[str, str] = mapeamento or {}
        self._inverso: dict[str, str] = {v: k for k, v in self._mapa.items()}

    def chat_id_de(self, usuario_id: str) -> str | None:
        return self._mapa.get(usuario_id)

    def usuario_de_chat(self, chat_id: str) -> str | None:
        return self._inverso.get(chat_id)


# ---------------------------------------------------------------------------
# Fakes para ServicoCompetencia (COMP-01..06)
# ---------------------------------------------------------------------------


class FakeTransacaoRepoComp:
    """Implementa TransacaoRepoComp para testes de ServicoCompetencia.

    Recebe a lista de saídas CONFIRMADAS que devem ser devolvidas por
    saidas_confirmadas(). O caller é responsável por passar apenas as
    transações que um repo real devolveria (CONFIRMADA + tipo saida).
    """

    def __init__(self, saidas: list | None = None) -> None:
        self._saidas: list = saidas or []

    def saidas_confirmadas(self, competencia_id: str) -> list:
        return list(self._saidas)


class FakeFonteRepo:
    """Implementa FonteRepo para testes de ServicoCompetencia.

    Devolve todas as fontes em ativas(), opcionalmente filtrando por familia_id
    se o atributo 'usuario_id' da FonteRenda for tratado como família.
    Para simplificar os testes unitários, devolve todas sem filtrar.
    """

    def __init__(self, fontes: list | None = None) -> None:
        self._fontes: list = fontes or []

    def ativas(self, familia_id: str) -> list:
        return list(self._fontes)


class FakeRegistroDiaRepo:
    """Implementa RegistroDiaRepo para testes de ServicoCompetencia.

    Recebe um dict mapeando fonte_renda_id -> list[RegistroDia].
    do_mes() devolve os registros correspondentes (ignorando mes/ano neste fake).
    """

    def __init__(self, registros: dict | None = None) -> None:
        self._registros: dict = registros or {}

    def do_mes(self, fonte_renda_id: str, mes: int, ano: int) -> list:
        return list(self._registros.get(fonte_renda_id, []))


class FakeFamiliaRepo:
    """Implementa FamiliaRepo para testes de ServicoCompetencia.

    Guarda uma única Familia. buscar() a retorna; atualizar_saldo() muta o objeto
    (usando model_copy) para que o teste possa inspecionar o novo saldo.
    """

    def __init__(self, familia) -> None:
        self._familia = familia

    def buscar(self, familia_id: str):
        return self._familia

    def atualizar_saldo(self, familia_id: str, novo_saldo) -> None:
        from decimal import Decimal
        self._familia = self._familia.model_copy(
            update={"saldo_acumulado": Decimal(str(novo_saldo))}
        )

    @property
    def familia(self):
        """Acesso direto ao objeto mutado — usado nos asserts dos testes."""
        return self._familia


class FakeLLM(BaseLLM):
    """Fake do BaseLLM para testes unitários.

    Modos (exclusivos — `respostas` tem prioridade sobre os demais):
    - `respostas`: sequência de respostas; cada extrair() consome o próximo item.
        - TransacaoExtraida → retorna o valor;
        - LLMError ou Exception → levanta a exceção.
    - `transacao` + `modo_erro=False`: retorna sempre a mesma TransacaoExtraida.
    - `modo_erro=True`: levanta sempre LLMError (simula timeout/falha de rede).

    Atributos públicos:
        chamadas: contador de chamadas a extrair().
        ultimo_feedback: último valor de `feedback` recebido (None na 1ª chamada).
    """

    def __init__(
        self,
        transacao: TransacaoExtraida | None = None,
        modo_erro: bool = False,
        mensagem_erro: str = "LLM indisponível (fake)",
        respostas: list[_ItemSequencia] | None = None,
    ) -> None:
        self._transacao = transacao
        self._modo_erro = modo_erro
        self._mensagem_erro = mensagem_erro
        self._respostas: list[_ItemSequencia] = list(respostas) if respostas else []
        self.chamadas: int = 0
        self.ultimo_feedback: list[str] | None = None

    async def extrair(self, texto: str, feedback: list[str] | None = None) -> TransacaoExtraida:
        self.chamadas += 1
        self.ultimo_feedback = feedback

        # Modo sequência: consome o próximo item da lista.
        if self._respostas:
            item = self._respostas.pop(0)
            if isinstance(item, Exception):
                raise item
            return item  # type: ignore[return-value]

        # Modo legado: erro fixo ou transação fixa.
        if self._modo_erro:
            raise LLMError(self._mensagem_erro)
        if self._transacao is None:
            raise LLMError("FakeLLM sem transação programada")
        return self._transacao
