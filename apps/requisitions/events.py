from enum import StrEnum


class RequisicaoEvent(StrEnum):
    ENVIADA = "requisicao.enviada"
    AUTORIZADA = "requisicao.autorizada"
    RECUSADA = "requisicao.recusada"
    ATENDIDA = "requisicao.atendida"
    ATENDIDA_PARCIALMENTE = "requisicao.atendida_parcialmente"
    CANCELADA = "requisicao.cancelada"
