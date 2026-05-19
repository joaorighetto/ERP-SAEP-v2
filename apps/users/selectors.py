"""Selectors de usuários para o frontend server-rendered.

Retornam querysets ou listas prontas para uso em templates e partials HTMX.
Não contêm regra de negócio — apenas filtros de escopo de apresentação.
"""

from apps.users.models import PapelChoices, User


def buscar_beneficiarios_no_escopo(q: str, criador: User, *, limit: int = 15) -> list[User]:
    """Busca usuários elegíveis como beneficiário dado o escopo do criador.

    Regras (alinhadas com pode_criar_requisicao_para):
    - SOLICITANTE: apenas ele mesmo → não usa este selector.
    - AUXILIAR_SETOR / CHEFE_SETOR: apenas usuários do mesmo setor (criador.setor).
    - AUXILIAR_ALMOXARIFADO / CHEFE_ALMOXARIFADO: qualquer usuário ativo.
    - SUPERUSUARIO: sem resultado (não opera como criador).

    A validação de autorização real ocorre na view + service via
    `pode_criar_requisicao_para`. Este selector é apenas para a UI de lookup.
    """
    if not q or len(q) < 3:
        return []

    base_qs = User.objects.filter(is_active=True, nome_completo__icontains=q).order_by(
        "nome_completo"
    )

    papel = getattr(criador, "papel", None)

    if papel in (PapelChoices.AUXILIAR_ALMOXARIFADO, PapelChoices.CHEFE_ALMOXARIFADO):
        return list(base_qs[:limit])

    if papel in (PapelChoices.AUXILIAR_SETOR, PapelChoices.CHEFE_SETOR):
        if not criador.setor_id:
            return []
        return list(base_qs.filter(setor_id=criador.setor_id)[:limit])

    # SOLICITANTE e superusuário: não devem usar este selector.
    return []
