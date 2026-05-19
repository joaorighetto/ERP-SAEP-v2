"""Selectors de materiais para o frontend server-rendered.

Retornam querysets ou listas prontas para uso em templates e partials HTMX.
Não contêm regra de negócio — apenas filtros de apresentação.
"""

from django.db.models import F

from apps.materials.models import Material


def buscar_materiais_para_requisicao(q: str, *, limit: int = 20) -> list[Material]:
    """Busca materiais válidos para inclusão em rascunho de requisição.

    Filtra:
    - ativos (is_active=True);
    - com estoque associado;
    - sem divergência crítica (saldo_disponivel >= 0, i.e. fisico >= reservado);
    - com saldo disponível > 0.

    A validação final de saldo e divergência ocorre no service com lock.
    Este selector é apenas para a UI de lookup — não é garantia de aceitação.
    """
    if not q or len(q) < 3:
        return []

    return list(
        Material.objects.select_related("estoque", "subgrupo__grupo")
        .filter(
            is_active=True,
            estoque__isnull=False,
            estoque__saldo_fisico__gt=F("estoque__saldo_reservado"),
        )
        .filter(
            nome__icontains=q,
        )
        .order_by("nome")[:limit]
    )
