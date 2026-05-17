from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import close_old_connections
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.api.exceptions import DomainConflict
from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.requisitions.domain.types import (
    ItemAtendimentoData,
    ItemAutorizacaoData,
    ItemRascunhoData,
)
from apps.requisitions.models import (
    ItemRequisicao,
    Requisicao,
    SequenciaNumeroRequisicao,
    StatusRequisicao,
    TipoEvento,
)
from apps.requisitions.sequences import gerar_numero_publico as _gerar_numero_publico
from apps.requisitions.services import (
    atender_requisicao,
    atender_requisicao_com_itens,
    atender_requisicao_completa,
    atualizar_rascunho_requisicao,
    autorizar_requisicao,
    cancelar_requisicao,
    criar_rascunho_requisicao,
    descartar_rascunho_nunca_enviado,
    enviar_para_autorizacao,
    recusar_requisicao,
    retirar_requisicao,
    retornar_para_rascunho,
)
from apps.stock.models import EstoqueMaterial, MovimentacaoEstoque, TipoMovimentacao
from apps.users.models import PapelChoices, Setor, User
from tests.requisitions.helpers import StubStockPort


@pytest.mark.django_db(transaction=True)
class TestSequenciaNumeroRequisicaoService:
    def test_gera_numeros_incrementais_no_mesmo_ano(self):
        primeiro = _gerar_numero_publico(ano=2026)
        segundo = _gerar_numero_publico(ano=2026)

        assert primeiro == "REQ-2026-000001"
        assert segundo == "REQ-2026-000002"

    def test_reinicia_sequencia_em_novo_ano(self):
        numero_2026 = _gerar_numero_publico(ano=2026)
        numero_2027 = _gerar_numero_publico(ano=2027)

        assert numero_2026 == "REQ-2026-000001"
        assert numero_2027 == "REQ-2027-000001"

    @pytest.mark.postgres
    def test_gera_numeros_distintos_quando_duas_threads_criam_mesmo_ano_inaugural(self):
        barrier = Barrier(2)

        def gerar():
            close_old_connections()
            try:
                barrier.wait()
                return _gerar_numero_publico(ano=2028)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futuro_a = executor.submit(gerar)
            futuro_b = executor.submit(gerar)

        resultados = {futuro_a.result(), futuro_b.result()}
        close_old_connections()

        sequencia = SequenciaNumeroRequisicao.objects.get(ano=2028)

        assert resultados == {"REQ-2028-000001", "REQ-2028-000002"}
        assert sequencia.ultimo_numero == 2


@pytest.mark.django_db(transaction=True)
class TestAutorizacaoRequisicaoService:
    @staticmethod
    def _criar_setor(nome: str, chefe_matricula: str, papel=PapelChoices.CHEFE_SETOR) -> Setor:
        chefe = User.objects.create(
            matricula_funcional=chefe_matricula,
            nome_completo=f"Chefe {nome}",
            papel=papel,
            is_active=True,
        )
        setor = Setor.objects.create(nome=nome, chefe_responsavel=chefe)
        chefe.setor = setor
        chefe.save(update_fields=["setor"])
        return setor

    @staticmethod
    def _criar_usuario(
        matricula: str,
        nome: str,
        *,
        papel=PapelChoices.SOLICITANTE,
        setor: Setor | None = None,
        is_active: bool = True,
    ) -> User:
        return User.objects.create(
            matricula_funcional=matricula,
            nome_completo=nome,
            papel=papel,
            setor=setor,
            is_active=is_active,
        )

    @staticmethod
    def _criar_material_com_estoque(
        codigo: str,
        *,
        saldo_fisico: Decimal = Decimal("10"),
        saldo_reservado: Decimal = Decimal("0"),
    ) -> Material:
        grupo_codigo, subgrupo_codigo, sequencial = codigo.split(".")
        grupo, _ = GrupoMaterial.objects.get_or_create(
            codigo_grupo=grupo_codigo,
            defaults={"nome": f"Grupo {grupo_codigo}"},
        )
        subgrupo, _ = SubgrupoMaterial.objects.get_or_create(
            grupo=grupo,
            codigo_subgrupo=subgrupo_codigo,
            defaults={"nome": f"Subgrupo {subgrupo_codigo}"},
        )
        material = Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo=codigo,
            sequencial=sequencial,
            nome=f"Material {codigo}",
            unidade_medida="UN",
            is_active=True,
        )
        EstoqueMaterial.objects.create(
            material=material,
            saldo_fisico=saldo_fisico,
            saldo_reservado=saldo_reservado,
        )
        return material

    @staticmethod
    def _criar_requisicao_aguardando(
        *,
        criador: User,
        beneficiario: User,
        numero_publico: str,
        item_quantidade: Decimal,
        material: Material,
    ) -> tuple[Requisicao, ItemRequisicao]:
        requisicao = Requisicao.objects.create(
            criador=criador,
            beneficiario=beneficiario,
            setor_beneficiario=beneficiario.setor,
            numero_publico=numero_publico,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=item_quantidade,
        )
        return requisicao, item

    def test_autoriza_total_persiste_reserva_e_timeline(self):
        setor = self._criar_setor("Compras", "91001")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("11001", "Solicitante Compras", setor=setor)
        material = self._criar_material_com_estoque("001.002.001", saldo_fisico=Decimal("10"))
        requisicao, item = self._criar_requisicao_aguardando(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-100001",
            item_quantidade=Decimal("4"),
            material=material,
        )

        autorizado = autorizar_requisicao(
            requisicao=requisicao,
            ator=chefe,
            itens=[
                ItemAutorizacaoData(
                    item_id=item.id,
                    quantidade_autorizada=Decimal("4"),
                )
            ],
        )

        autorizado.refresh_from_db()
        item.refresh_from_db()
        material.estoque.refresh_from_db()

        assert autorizado.status == StatusRequisicao.AUTORIZADA
        assert autorizado.chefe_autorizador_id == chefe.id
        assert autorizado.eventos.filter(tipo_evento=TipoEvento.AUTORIZACAO_TOTAL).exists()
        assert item.quantidade_autorizada == Decimal("4")
        assert item.justificativa_autorizacao_parcial == ""
        assert material.estoque.saldo_fisico == Decimal("10")
        assert material.estoque.saldo_reservado == Decimal("4")
        assert (
            MovimentacaoEstoque.objects.filter(
                tipo=TipoMovimentacao.RESERVA_POR_AUTORIZACAO,
                requisicao=autorizado,
                item_requisicao=item,
            ).count()
            == 1
        )

    def test_autoriza_parcial_e_zero_com_justificativa(self):
        setor = self._criar_setor("Apoio", "91002")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("11002", "Solicitante Apoio", setor=setor)
        material_a = self._criar_material_com_estoque("001.002.002", saldo_fisico=Decimal("8"))
        material_b = self._criar_material_com_estoque("001.002.003", saldo_fisico=Decimal("8"))
        requisicao = Requisicao.objects.create(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-100002",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        item_a = requisicao.itens.create(
            material=material_a,
            unidade_medida=material_a.unidade_medida,
            quantidade_solicitada=Decimal("5"),
        )
        item_b = requisicao.itens.create(
            material=material_b,
            unidade_medida=material_b.unidade_medida,
            quantidade_solicitada=Decimal("3"),
        )

        autorizado = autorizar_requisicao(
            requisicao=requisicao,
            ator=chefe,
            itens=[
                ItemAutorizacaoData(
                    item_id=item_a.id,
                    quantidade_autorizada=Decimal("4"),
                    justificativa_autorizacao_parcial="Saldo limitado",
                ),
                ItemAutorizacaoData(
                    item_id=item_b.id,
                    quantidade_autorizada=Decimal("0"),
                    justificativa_autorizacao_parcial="Sem prioridade",
                ),
            ],
        )

        autorizado.refresh_from_db()
        item_a.refresh_from_db()
        item_b.refresh_from_db()
        material_a.estoque.refresh_from_db()
        material_b.estoque.refresh_from_db()

        assert autorizado.status == StatusRequisicao.AUTORIZADA
        assert autorizado.eventos.filter(tipo_evento=TipoEvento.AUTORIZACAO_PARCIAL).exists()
        assert item_a.quantidade_autorizada == Decimal("4")
        assert item_a.justificativa_autorizacao_parcial == "Saldo limitado"
        assert item_b.quantidade_autorizada == Decimal("0")
        assert item_b.justificativa_autorizacao_parcial == "Sem prioridade"
        assert material_a.estoque.saldo_reservado == Decimal("4")
        assert material_b.estoque.saldo_reservado == Decimal("0")

    def test_autoriza_parcial_sem_justificativa_falha(self):
        setor = self._criar_setor("Oficina", "91003")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("11003", "Solicitante Oficina", setor=setor)
        material = self._criar_material_com_estoque("001.002.004", saldo_fisico=Decimal("8"))
        requisicao, item = self._criar_requisicao_aguardando(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-100003",
            item_quantidade=Decimal("5"),
            material=material,
        )

        with pytest.raises(ValidationError):
            autorizar_requisicao(
                requisicao=requisicao,
                ator=chefe,
                itens=[
                    ItemAutorizacaoData(
                        item_id=item.id,
                        quantidade_autorizada=Decimal("4"),
                    )
                ],
            )

    def test_autoriza_parcial_com_justificativa_so_com_espacos_falha(self):
        setor = self._criar_setor("Oficina Pesada", "91031")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("11031", "Solicitante Oficina Pesada", setor=setor)
        material = self._criar_material_com_estoque("001.002.031", saldo_fisico=Decimal("8"))
        requisicao, item = self._criar_requisicao_aguardando(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-100031",
            item_quantidade=Decimal("5"),
            material=material,
        )

        with pytest.raises(ValidationError):
            autorizar_requisicao(
                requisicao=requisicao,
                ator=chefe,
                itens=[
                    ItemAutorizacaoData(
                        item_id=item.id,
                        quantidade_autorizada=Decimal("4"),
                        justificativa_autorizacao_parcial="   ",
                    )
                ],
            )

    def test_autoriza_quantidade_negativa_falha_no_service(self):
        setor = self._criar_setor("Planejamento", "91032")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("11032", "Solicitante Planejamento", setor=setor)
        material = self._criar_material_com_estoque("001.002.032", saldo_fisico=Decimal("8"))
        requisicao, item = self._criar_requisicao_aguardando(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-100032",
            item_quantidade=Decimal("5"),
            material=material,
        )

        with pytest.raises(ValidationError):
            autorizar_requisicao(
                requisicao=requisicao,
                ator=chefe,
                itens=[
                    ItemAutorizacaoData(
                        item_id=item.id,
                        quantidade_autorizada=Decimal("-1"),
                        justificativa_autorizacao_parcial="Inválida",
                    )
                ],
            )

    def test_autoriza_todos_itens_zerados_falha(self):
        setor = self._criar_setor("Financeiro", "91004")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("11004", "Solicitante Financeiro", setor=setor)
        material = self._criar_material_com_estoque("001.002.005", saldo_fisico=Decimal("8"))
        requisicao, item = self._criar_requisicao_aguardando(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-100004",
            item_quantidade=Decimal("5"),
            material=material,
        )

        with pytest.raises(DomainConflict):
            autorizar_requisicao(
                requisicao=requisicao,
                ator=chefe,
                itens=[
                    ItemAutorizacaoData(
                        item_id=item.id,
                        quantidade_autorizada=Decimal("0"),
                        justificativa_autorizacao_parcial="Não autorizado",
                    )
                ],
            )

    def test_autoriza_recalcula_saldo_atual(self):
        setor = self._criar_setor("Patrimonio", "91005")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("11005", "Solicitante Patrimonio", setor=setor)
        material = self._criar_material_com_estoque("001.002.006", saldo_fisico=Decimal("5"))
        requisicao, item = self._criar_requisicao_aguardando(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-100005",
            item_quantidade=Decimal("4"),
            material=material,
        )
        material.estoque.saldo_fisico = Decimal("2")
        material.estoque.save(update_fields=["saldo_fisico", "updated_at"])

        with pytest.raises(DomainConflict):
            autorizar_requisicao(
                requisicao=requisicao,
                ator=chefe,
                itens=[
                    ItemAutorizacaoData(
                        item_id=item.id,
                        quantidade_autorizada=Decimal("4"),
                    )
                ],
            )

    def test_recusa_exige_motivo_e_nao_reserva(self):
        setor = self._criar_setor("Transporte", "91006")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("11006", "Solicitante Transporte", setor=setor)
        material = self._criar_material_com_estoque("001.002.007", saldo_fisico=Decimal("5"))
        requisicao, _ = self._criar_requisicao_aguardando(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-100006",
            item_quantidade=Decimal("2"),
            material=material,
        )

        recusada = recusar_requisicao(
            requisicao=requisicao,
            ator=chefe,
            motivo_recusa="Requisição fora de prioridade",
        )

        recusada.refresh_from_db()
        material.estoque.refresh_from_db()

        assert recusada.status == StatusRequisicao.RECUSADA
        assert recusada.motivo_recusa == "Requisição fora de prioridade"
        assert recusada.chefe_autorizador_id == chefe.id
        assert recusada.eventos.filter(tipo_evento=TipoEvento.RECUSA).exists()
        assert material.estoque.saldo_reservado == Decimal("0")
        assert (
            MovimentacaoEstoque.objects.filter(
                requisicao=recusada,
                tipo=TipoMovimentacao.RESERVA_POR_AUTORIZACAO,
            ).count()
            == 0
        )

    def test_recusa_sem_motivo_falha(self):
        setor = self._criar_setor("Apoio Administrativo", "91007")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("11007", "Solicitante Apoio Administrativo", setor=setor)
        material = self._criar_material_com_estoque("001.002.008")
        requisicao, _ = self._criar_requisicao_aguardando(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-100007",
            item_quantidade=Decimal("1"),
            material=material,
        )

        with pytest.raises(ValidationError):
            recusar_requisicao(requisicao=requisicao, ator=chefe, motivo_recusa="   ")

    @pytest.mark.postgres
    def test_autorizacoes_concorrentes_nao_dividem_mesmo_saldo(self):
        setor = self._criar_setor("Logistica", "91008")
        chefe = setor.chefe_responsavel
        requisitante_a = self._criar_usuario("11008", "Solicitante A", setor=setor)
        requisitante_b = self._criar_usuario("11009", "Solicitante B", setor=setor)
        material = self._criar_material_com_estoque("001.002.009", saldo_fisico=Decimal("5"))
        req_a, item_a = self._criar_requisicao_aguardando(
            criador=requisitante_a,
            beneficiario=requisitante_a,
            numero_publico="REQ-2026-100008",
            item_quantidade=Decimal("5"),
            material=material,
        )
        req_b, item_b = self._criar_requisicao_aguardando(
            criador=requisitante_b,
            beneficiario=requisitante_b,
            numero_publico="REQ-2026-100009",
            item_quantidade=Decimal("5"),
            material=material,
        )

        barrier = Barrier(2)

        def autorizar(req_id: int, item_id: int):
            close_old_connections()
            try:
                barrier.wait()
                requisicao = Requisicao.objects.get(pk=req_id)
                autorizar_requisicao(
                    requisicao=requisicao,
                    ator=chefe,
                    itens=[
                        ItemAutorizacaoData(
                            item_id=item_id,
                            quantidade_autorizada=Decimal("5"),
                        )
                    ],
                )
                return "ok"
            except Exception as exc:  # noqa: BLE001
                return type(exc).__name__
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultado_a = executor.submit(autorizar, req_a.id, item_a.id)
            resultado_b = executor.submit(autorizar, req_b.id, item_b.id)

        resultados = {resultado_a.result(), resultado_b.result()}
        close_old_connections()

        material.estoque.refresh_from_db()
        req_a.refresh_from_db()
        req_b.refresh_from_db()

        assert resultados == {"ok", "DomainConflict"}
        assert material.estoque.saldo_reservado == Decimal("5")
        assert {req_a.status, req_b.status} == {
            StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            StatusRequisicao.AUTORIZADA,
        }

    @pytest.mark.postgres
    def test_autorizacoes_concorrentes_multi_item_respeitam_lock_order_canonico(self):
        setor = self._criar_setor("Lock Order", "91010")
        chefe = setor.chefe_responsavel
        requisitante_a = self._criar_usuario("11010", "Solicitante Lock A", setor=setor)
        requisitante_b = self._criar_usuario("11011", "Solicitante Lock B", setor=setor)
        material_a = self._criar_material_com_estoque("001.002.010", saldo_fisico=Decimal("4"))
        material_b = self._criar_material_com_estoque("001.002.011", saldo_fisico=Decimal("4"))

        requisicao_a = Requisicao.objects.create(
            criador=requisitante_a,
            beneficiario=requisitante_a,
            setor_beneficiario=requisitante_a.setor,
            numero_publico="REQ-2026-100010",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        item_a1 = requisicao_a.itens.create(
            material=material_b,
            unidade_medida=material_b.unidade_medida,
            quantidade_solicitada=Decimal("2"),
        )
        item_a2 = requisicao_a.itens.create(
            material=material_a,
            unidade_medida=material_a.unidade_medida,
            quantidade_solicitada=Decimal("2"),
        )

        requisicao_b = Requisicao.objects.create(
            criador=requisitante_b,
            beneficiario=requisitante_b,
            setor_beneficiario=requisitante_b.setor,
            numero_publico="REQ-2026-100011",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        item_b1 = requisicao_b.itens.create(
            material=material_a,
            unidade_medida=material_a.unidade_medida,
            quantidade_solicitada=Decimal("2"),
        )
        item_b2 = requisicao_b.itens.create(
            material=material_b,
            unidade_medida=material_b.unidade_medida,
            quantidade_solicitada=Decimal("2"),
        )

        barrier = Barrier(2)

        def autorizar(req_id: int, item_ids: tuple[int, int]):
            close_old_connections()
            try:
                barrier.wait()
                requisicao = Requisicao.objects.get(pk=req_id)
                autorizar_requisicao(
                    requisicao=requisicao,
                    ator=chefe,
                    itens=[
                        ItemAutorizacaoData(
                            item_id=item_ids[0],
                            quantidade_autorizada=Decimal("2"),
                        ),
                        ItemAutorizacaoData(
                            item_id=item_ids[1],
                            quantidade_autorizada=Decimal("2"),
                        ),
                    ],
                )
                return "ok"
            except Exception as exc:  # noqa: BLE001
                return type(exc).__name__
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futuro_a = executor.submit(autorizar, requisicao_a.id, (item_a1.id, item_a2.id))
            futuro_b = executor.submit(autorizar, requisicao_b.id, (item_b1.id, item_b2.id))

        resultados = {futuro_a.result(), futuro_b.result()}
        close_old_connections()

        requisicao_a.refresh_from_db()
        requisicao_b.refresh_from_db()
        material_a.estoque.refresh_from_db()
        material_b.estoque.refresh_from_db()

        # Both authorizations should succeed because each material has stock for both requests.
        assert resultados == {"ok"}
        assert requisicao_a.status == StatusRequisicao.AUTORIZADA
        assert requisicao_b.status == StatusRequisicao.AUTORIZADA
        assert material_a.estoque.saldo_reservado == Decimal("4")
        assert material_b.estoque.saldo_reservado == Decimal("4")


@pytest.mark.django_db(transaction=True)
class TestAtendimentoRequisicaoService:
    @staticmethod
    def _criar_setor(nome: str, chefe_matricula: str) -> Setor:
        chefe = User.objects.create(
            matricula_funcional=chefe_matricula,
            nome_completo=f"Chefe {nome}",
            papel=PapelChoices.CHEFE_SETOR,
            is_active=True,
        )
        setor = Setor.objects.create(nome=nome, chefe_responsavel=chefe)
        chefe.setor = setor
        chefe.save(update_fields=["setor"])
        return setor

    @staticmethod
    def _criar_usuario(
        matricula: str,
        nome: str,
        *,
        papel=PapelChoices.SOLICITANTE,
        setor: Setor | None = None,
        is_active: bool = True,
    ) -> User:
        return User.objects.create(
            matricula_funcional=matricula,
            nome_completo=nome,
            papel=papel,
            setor=setor,
            is_active=is_active,
        )

    @staticmethod
    def _criar_material_com_estoque(
        codigo: str,
        *,
        saldo_fisico: Decimal = Decimal("10"),
        saldo_reservado: Decimal = Decimal("0"),
    ) -> Material:
        grupo_codigo, subgrupo_codigo, sequencial = codigo.split(".")
        grupo, _ = GrupoMaterial.objects.get_or_create(
            codigo_grupo=grupo_codigo,
            defaults={"nome": f"Grupo {grupo_codigo}"},
        )
        subgrupo, _ = SubgrupoMaterial.objects.get_or_create(
            grupo=grupo,
            codigo_subgrupo=subgrupo_codigo,
            defaults={"nome": f"Subgrupo {subgrupo_codigo}"},
        )
        material = Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo=codigo,
            sequencial=sequencial,
            nome=f"Material {codigo}",
            unidade_medida="UN",
            is_active=True,
        )
        EstoqueMaterial.objects.create(
            material=material,
            saldo_fisico=saldo_fisico,
            saldo_reservado=saldo_reservado,
        )
        return material

    @staticmethod
    def _criar_requisicao_autorizada(
        *,
        criador: User,
        beneficiario: User,
        numero_publico: str,
        material: Material,
        quantidade_autorizada: Decimal,
    ) -> tuple[Requisicao, ItemRequisicao]:
        requisicao = Requisicao.objects.create(
            criador=criador,
            beneficiario=beneficiario,
            setor_beneficiario=beneficiario.setor,
            numero_publico=numero_publico,
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=quantidade_autorizada,
            quantidade_autorizada=quantidade_autorizada,
        )
        return requisicao, item

    def test_atendimento_completo_baixa_fisico_consumindo_reserva_e_timeline(self):
        setor = self._criar_setor("Operacional", "92001")
        requisitante = self._criar_usuario("12001", "Solicitante Operacional", setor=setor)
        atendente = self._criar_usuario(
            "12002",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.003.001",
            saldo_fisico=Decimal("10"),
            saldo_reservado=Decimal("4"),
        )
        requisicao, item = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200001",
            material=material,
            quantidade_autorizada=Decimal("4"),
        )

        atendida = atender_requisicao_completa(
            requisicao=requisicao,
            ator=atendente,
            observacao_atendimento="Retirada no balcão",
        )

        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert atendida.status == StatusRequisicao.PRONTA_PARA_RETIRADA
        assert atendida.responsavel_atendimento_id == atendente.id
        assert atendida.retirante_fisico == ""
        assert atendida.observacao_atendimento == "Retirada no balcão"
        assert atendida.eventos.filter(tipo_evento=TipoEvento.ATENDIMENTO).exists()
        assert item.quantidade_entregue == Decimal("4")
        assert material.estoque.saldo_fisico == Decimal("10")
        assert material.estoque.saldo_reservado == Decimal("4")
        assert not MovimentacaoEstoque.objects.filter(
            requisicao=atendida,
            tipo=TipoMovimentacao.SAIDA_POR_ATENDIMENTO,
        ).exists()

        retirada = retirar_requisicao(
            requisicao=atendida,
            ator=atendente,
            retirante_fisico="Responsável Retirada",
        )
        material.estoque.refresh_from_db()
        assert retirada.status == StatusRequisicao.RETIRADA
        assert material.estoque.saldo_fisico == Decimal("6")
        assert material.estoque.saldo_reservado == Decimal("0")
        assert MovimentacaoEstoque.objects.filter(
            requisicao=atendida,
            item_requisicao=item,
            tipo=TipoMovimentacao.SAIDA_POR_ATENDIMENTO,
        ).exists()

    def test_atendimento_completo_ignora_item_autorizado_zero(self):
        setor = self._criar_setor("Oficina", "92002")
        requisitante = self._criar_usuario("12003", "Solicitante Oficina", setor=setor)
        atendente = self._criar_usuario(
            "12004",
            "Chefe Almoxarifado",
            papel=PapelChoices.CHEFE_ALMOXARIFADO,
            setor=setor,
        )
        material_a = self._criar_material_com_estoque(
            "001.003.002",
            saldo_fisico=Decimal("8"),
            saldo_reservado=Decimal("3"),
        )
        material_b = self._criar_material_com_estoque("001.003.003", saldo_fisico=Decimal("8"))
        requisicao, item_a = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200002",
            material=material_a,
            quantidade_autorizada=Decimal("3"),
        )
        item_b = requisicao.itens.create(
            material=material_b,
            unidade_medida=material_b.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("0"),
            justificativa_autorizacao_parcial="Não autorizado",
        )

        atendida = atender_requisicao_completa(requisicao=requisicao, ator=atendente)

        item_a.refresh_from_db()
        item_b.refresh_from_db()
        material_a.estoque.refresh_from_db()
        material_b.estoque.refresh_from_db()
        assert item_a.quantidade_entregue == Decimal("3")
        assert item_b.quantidade_entregue == Decimal("0")
        assert material_a.estoque.saldo_fisico == Decimal("8")
        assert material_a.estoque.saldo_reservado == Decimal("3")
        assert material_b.estoque.saldo_fisico == Decimal("8")
        assert material_b.estoque.saldo_reservado == Decimal("0")

        retirada = retirar_requisicao(
            requisicao=atendida,
            ator=atendente,
            retirante_fisico="Responsável Retirada",
        )
        material_a.estoque.refresh_from_db()
        assert retirada.status == StatusRequisicao.RETIRADA
        assert material_a.estoque.saldo_fisico == Decimal("5")
        assert material_a.estoque.saldo_reservado == Decimal("0")

    def test_atendimento_parcial_entrega_item_e_libera_reserva_nao_entregue(self):
        setor = self._criar_setor("Atendimento Parcial", "92020")
        requisitante = self._criar_usuario("12020", "Solicitante Parcial", setor=setor)
        atendente = self._criar_usuario(
            "12021",
            "Auxiliar Almoxarifado Parcial",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.003.020",
            saldo_fisico=Decimal("10"),
            saldo_reservado=Decimal("5"),
        )
        requisicao, item = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200020",
            material=material,
            quantidade_autorizada=Decimal("5"),
        )

        atendida = atender_requisicao_com_itens(
            requisicao=requisicao,
            ator=atendente,
            itens=[
                ItemAtendimentoData(
                    item_id=item.id,
                    quantidade_entregue=Decimal("3"),
                    justificativa_atendimento_parcial="Estoque físico divergente",
                )
            ],
        )

        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert atendida.status == StatusRequisicao.PRONTA_PARA_RETIRADA_PARCIAL
        assert atendida.eventos.filter(tipo_evento=TipoEvento.ATENDIMENTO_PARCIAL).exists()
        assert item.quantidade_entregue == Decimal("3")
        assert item.justificativa_atendimento_parcial == "Estoque físico divergente"
        assert material.estoque.saldo_fisico == Decimal("10")
        assert material.estoque.saldo_reservado == Decimal("5")
        assert not MovimentacaoEstoque.objects.filter(
            requisicao=atendida,
            tipo=TipoMovimentacao.SAIDA_POR_ATENDIMENTO,
        ).exists()

        retirada = retirar_requisicao(
            requisicao=atendida,
            ator=atendente,
            retirante_fisico="Responsável Retirada",
        )
        material.estoque.refresh_from_db()
        assert retirada.status == StatusRequisicao.RETIRADA
        assert material.estoque.saldo_fisico == Decimal("7")
        assert material.estoque.saldo_reservado == Decimal("0")
        assert MovimentacaoEstoque.objects.filter(
            requisicao=atendida,
            item_requisicao=item,
            tipo=TipoMovimentacao.SAIDA_POR_ATENDIMENTO,
            quantidade=Decimal("3"),
        ).exists()
        assert MovimentacaoEstoque.objects.filter(
            requisicao=atendida,
            item_requisicao=item,
            tipo=TipoMovimentacao.LIBERACAO_RESERVA_ATENDIMENTO,
            quantidade=Decimal("2"),
        ).exists()

    def test_atendimento_parcial_multi_item_mistura_entrega_total_e_parcial(self):
        setor = self._criar_setor("Atendimento Multi Item", "92030")
        requisitante = self._criar_usuario("12030", "Solicitante Multi", setor=setor)
        atendente = self._criar_usuario(
            "12031",
            "Auxiliar Almoxarifado Multi",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material_total = self._criar_material_com_estoque(
            "001.003.030",
            saldo_fisico=Decimal("10"),
            saldo_reservado=Decimal("4"),
        )
        material_parcial = self._criar_material_com_estoque(
            "001.003.031",
            saldo_fisico=Decimal("10"),
            saldo_reservado=Decimal("5"),
        )
        requisicao, item_total = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200030",
            material=material_total,
            quantidade_autorizada=Decimal("4"),
        )
        item_parcial = requisicao.itens.create(
            material=material_parcial,
            unidade_medida=material_parcial.unidade_medida,
            quantidade_solicitada=Decimal("5"),
            quantidade_autorizada=Decimal("5"),
        )

        atendida = atender_requisicao(
            requisicao=requisicao,
            ator=atendente,
            itens=[
                ItemAtendimentoData(item_id=item_total.id, quantidade_entregue=Decimal("4")),
                ItemAtendimentoData(
                    item_id=item_parcial.id,
                    quantidade_entregue=Decimal("2"),
                    justificativa_atendimento_parcial="Retirada parcial solicitada",
                ),
            ],
        )

        item_total.refresh_from_db()
        item_parcial.refresh_from_db()
        material_total.estoque.refresh_from_db()
        material_parcial.estoque.refresh_from_db()
        assert atendida.status == StatusRequisicao.PRONTA_PARA_RETIRADA_PARCIAL
        assert atendida.eventos.filter(tipo_evento=TipoEvento.ATENDIMENTO_PARCIAL).exists()
        assert item_total.quantidade_entregue == Decimal("4")
        assert item_total.justificativa_atendimento_parcial == ""
        assert item_parcial.quantidade_entregue == Decimal("2")
        assert item_parcial.justificativa_atendimento_parcial == "Retirada parcial solicitada"
        assert material_total.estoque.saldo_fisico == Decimal("10")
        assert material_total.estoque.saldo_reservado == Decimal("4")
        assert material_parcial.estoque.saldo_fisico == Decimal("10")
        assert material_parcial.estoque.saldo_reservado == Decimal("5")
        assert not MovimentacaoEstoque.objects.filter(requisicao=atendida).exists()

        retirada = retirar_requisicao(
            requisicao=atendida,
            ator=atendente,
            retirante_fisico="Responsável Retirada",
        )
        material_total.estoque.refresh_from_db()
        material_parcial.estoque.refresh_from_db()
        assert retirada.status == StatusRequisicao.RETIRADA
        assert material_total.estoque.saldo_fisico == Decimal("6")
        assert material_total.estoque.saldo_reservado == Decimal("0")
        assert material_parcial.estoque.saldo_fisico == Decimal("8")
        assert material_parcial.estoque.saldo_reservado == Decimal("0")
        assert not MovimentacaoEstoque.objects.filter(
            requisicao=atendida,
            item_requisicao=item_total,
            tipo=TipoMovimentacao.LIBERACAO_RESERVA_ATENDIMENTO,
        ).exists()
        assert MovimentacaoEstoque.objects.filter(
            requisicao=atendida,
            item_requisicao=item_parcial,
            tipo=TipoMovimentacao.LIBERACAO_RESERVA_ATENDIMENTO,
            quantidade=Decimal("3"),
        ).exists()

    def test_atendimento_com_itens_integral_preserva_status_atendida(self):
        setor = self._criar_setor("Atendimento Integral", "92022")
        requisitante = self._criar_usuario("12022", "Solicitante Integral", setor=setor)
        atendente = self._criar_usuario(
            "12023",
            "Auxiliar Almoxarifado Integral",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.003.021",
            saldo_fisico=Decimal("6"),
            saldo_reservado=Decimal("2"),
        )
        requisicao, item = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200021",
            material=material,
            quantidade_autorizada=Decimal("2"),
        )

        atendida = atender_requisicao_com_itens(
            requisicao=requisicao,
            ator=atendente,
            itens=[ItemAtendimentoData(item_id=item.id, quantidade_entregue=Decimal("2"))],
        )

        item.refresh_from_db()
        assert atendida.status == StatusRequisicao.PRONTA_PARA_RETIRADA
        assert atendida.eventos.filter(tipo_evento=TipoEvento.ATENDIMENTO).exists()
        assert item.quantidade_entregue == Decimal("2")
        assert item.justificativa_atendimento_parcial == ""

    def test_atendimento_parcial_exige_justificativa_e_alguma_entrega(self):
        setor = self._criar_setor("Atendimento Zero", "92024")
        requisitante = self._criar_usuario("12024", "Solicitante Zero", setor=setor)
        atendente = self._criar_usuario(
            "12025",
            "Auxiliar Almoxarifado Zero",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.003.022",
            saldo_fisico=Decimal("6"),
            saldo_reservado=Decimal("2"),
        )
        requisicao, item = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200022",
            material=material,
            quantidade_autorizada=Decimal("2"),
        )

        with pytest.raises(DomainConflict):
            atender_requisicao_com_itens(
                requisicao=requisicao,
                ator=atendente,
                itens=[ItemAtendimentoData(item_id=item.id, quantidade_entregue=Decimal("1"))],
            )
        with pytest.raises(DomainConflict):
            atender_requisicao_com_itens(
                requisicao=requisicao,
                ator=atendente,
                itens=[
                    ItemAtendimentoData(
                        item_id=item.id,
                        quantidade_entregue=Decimal("0"),
                        justificativa_atendimento_parcial="Sem retirada",
                    )
                ],
            )

        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert item.quantidade_entregue == Decimal("0")
        assert material.estoque.saldo_fisico == Decimal("6")
        assert material.estoque.saldo_reservado == Decimal("2")
        assert MovimentacaoEstoque.objects.count() == 0

    def test_cancelamento_autorizada_sem_saldo_libera_reserva_e_registra_motivo(self):
        setor = self._criar_setor("Cancelamento Sem Saldo", "92040")
        requisitante = self._criar_usuario("12040", "Solicitante Sem Saldo", setor=setor)
        atendente = self._criar_usuario(
            "12041",
            "Auxiliar Almoxarifado Sem Saldo",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.003.040",
            saldo_fisico=Decimal("0"),
            saldo_reservado=Decimal("3"),
        )
        requisicao, item = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200040",
            material=material,
            quantidade_autorizada=Decimal("3"),
        )

        cancelada = cancelar_requisicao(
            requisicao=requisicao,
            ator=atendente,
            motivo_cancelamento="Divergência física total no atendimento",
        )

        material.estoque.refresh_from_db()
        item.refresh_from_db()
        assert cancelada.status == StatusRequisicao.CANCELADA
        assert cancelada.motivo_cancelamento == "Divergência física total no atendimento"
        assert cancelada.responsavel_atendimento_id == atendente.id
        assert cancelada.eventos.filter(tipo_evento=TipoEvento.CANCELAMENTO).exists()
        assert item.quantidade_entregue == Decimal("0")
        assert material.estoque.saldo_fisico == Decimal("0")
        assert material.estoque.saldo_reservado == Decimal("0")
        assert MovimentacaoEstoque.objects.filter(
            requisicao=cancelada,
            item_requisicao=item,
            tipo=TipoMovimentacao.LIBERACAO_RESERVA_ATENDIMENTO,
            quantidade=Decimal("3"),
        ).exists()

    def test_cancelamento_autorizada_sem_saldo_permite_criador(self):
        setor = self._criar_setor("Cancelamento Criador", "92041")
        requisitante = self._criar_usuario("12045", "Solicitante Cancelamento", setor=setor)
        material = self._criar_material_com_estoque(
            "001.003.043",
            saldo_fisico=Decimal("0"),
            saldo_reservado=Decimal("2"),
        )
        requisicao, item = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200043",
            material=material,
            quantidade_autorizada=Decimal("2"),
        )

        cancelada = cancelar_requisicao(
            requisicao=requisicao,
            ator=requisitante,
            motivo_cancelamento="Sem saldo fisico para retirada",
        )

        material.estoque.refresh_from_db()
        item.refresh_from_db()
        assert cancelada.status == StatusRequisicao.CANCELADA
        assert cancelada.responsavel_atendimento_id == requisitante.id
        assert material.estoque.saldo_fisico == Decimal("0")
        assert material.estoque.saldo_reservado == Decimal("0")

    def test_cancelamento_autorizada_sem_saldo_bloqueia_se_ainda_ha_saldo_fisico(self):
        setor = self._criar_setor("Cancelamento Com Saldo", "92042")
        requisitante = self._criar_usuario("12042", "Solicitante Com Saldo", setor=setor)
        atendente = self._criar_usuario(
            "12043",
            "Auxiliar Almoxarifado Com Saldo",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.003.041",
            saldo_fisico=Decimal("1"),
            saldo_reservado=Decimal("3"),
        )
        requisicao, item = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200041",
            material=material,
            quantidade_autorizada=Decimal("3"),
        )

        with pytest.raises(DomainConflict):
            cancelar_requisicao(
                requisicao=requisicao,
                ator=atendente,
                motivo_cancelamento="Ainda existe saldo",
            )

        requisicao.refresh_from_db()
        material.estoque.refresh_from_db()
        item.refresh_from_db()
        assert requisicao.status == StatusRequisicao.AUTORIZADA
        assert requisicao.motivo_cancelamento == ""
        assert item.quantidade_entregue == Decimal("0")
        assert material.estoque.saldo_reservado == Decimal("3")
        assert MovimentacaoEstoque.objects.count() == 0

    def test_cancelamento_autorizada_sem_saldo_exige_motivo(self):
        setor = self._criar_setor("Cancelamento Permissao", "92044")
        solicitante = self._criar_usuario("12044", "Solicitante Permissao", setor=setor)
        material = self._criar_material_com_estoque(
            "001.003.042",
            saldo_fisico=Decimal("0"),
            saldo_reservado=Decimal("2"),
        )
        requisicao, _ = self._criar_requisicao_autorizada(
            criador=solicitante,
            beneficiario=solicitante,
            numero_publico="REQ-2026-200042",
            material=material,
            quantidade_autorizada=Decimal("2"),
        )

        with pytest.raises(ValidationError):
            cancelar_requisicao(
                requisicao=requisicao,
                ator=solicitante,
                motivo_cancelamento="   ",
            )

    def test_cancelamento_autorizada_sem_saldo_bloqueia_usuario_visivel_sem_permissao(self):
        setor = self._criar_setor("Cancelamento Sem Permissao", "92046")
        solicitante = self._criar_usuario("12046", "Solicitante Sem Permissao", setor=setor)
        chefe_setor = setor.chefe_responsavel
        material = self._criar_material_com_estoque(
            "001.003.044",
            saldo_fisico=Decimal("0"),
            saldo_reservado=Decimal("2"),
        )
        requisicao, _ = self._criar_requisicao_autorizada(
            criador=solicitante,
            beneficiario=solicitante,
            numero_publico="REQ-2026-200044",
            material=material,
            quantidade_autorizada=Decimal("2"),
        )

        with pytest.raises(PermissionDenied):
            cancelar_requisicao(
                requisicao=requisicao,
                ator=chefe_setor,
                motivo_cancelamento="Sem saldo físico",
            )

    def test_atendimento_com_itens_rejeita_payload_incompleto_duplicado_ou_excessivo(self):
        setor = self._criar_setor("Atendimento Payload", "92026")
        requisitante = self._criar_usuario("12026", "Solicitante Payload", setor=setor)
        atendente = self._criar_usuario(
            "12027",
            "Auxiliar Almoxarifado Payload",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material_a = self._criar_material_com_estoque(
            "001.003.023",
            saldo_fisico=Decimal("6"),
            saldo_reservado=Decimal("2"),
        )
        material_b = self._criar_material_com_estoque(
            "001.003.024",
            saldo_fisico=Decimal("6"),
            saldo_reservado=Decimal("2"),
        )
        requisicao, item_a = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200023",
            material=material_a,
            quantidade_autorizada=Decimal("2"),
        )
        item_b = requisicao.itens.create(
            material=material_b,
            unidade_medida=material_b.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        cenarios_validation_error = [
            [ItemAtendimentoData(item_id=item_a.id, quantidade_entregue=Decimal("2"))],
            [
                ItemAtendimentoData(item_id=item_a.id, quantidade_entregue=Decimal("2")),
                ItemAtendimentoData(item_id=item_a.id, quantidade_entregue=Decimal("2")),
            ],
            [
                ItemAtendimentoData(item_id=item_a.id, quantidade_entregue=Decimal("2")),
                ItemAtendimentoData(item_id=item_b.id + 999, quantidade_entregue=Decimal("2")),
            ],
        ]
        for itens in cenarios_validation_error:
            with pytest.raises(ValidationError):
                atender_requisicao_com_itens(
                    requisicao=requisicao,
                    ator=atendente,
                    itens=itens,
                )

        cenarios_domain_conflict = [
            [
                ItemAtendimentoData(item_id=item_a.id, quantidade_entregue=Decimal("3")),
                ItemAtendimentoData(item_id=item_b.id, quantidade_entregue=Decimal("2")),
            ],
        ]
        for itens in cenarios_domain_conflict:
            with pytest.raises(DomainConflict):
                atender_requisicao_com_itens(
                    requisicao=requisicao,
                    ator=atendente,
                    itens=itens,
                )

        item_a.refresh_from_db()
        item_b.refresh_from_db()
        material_a.estoque.refresh_from_db()
        material_b.estoque.refresh_from_db()
        assert item_a.quantidade_entregue == Decimal("0")
        assert item_b.quantidade_entregue == Decimal("0")
        assert material_a.estoque.saldo_reservado == Decimal("2")
        assert material_b.estoque.saldo_reservado == Decimal("2")
        assert MovimentacaoEstoque.objects.count() == 0

    def test_atendimento_bloqueia_usuario_sem_permissao_e_status_invalido(self):
        setor = self._criar_setor("Financeiro", "92003")
        solicitante = self._criar_usuario("12005", "Solicitante Financeiro", setor=setor)
        material = self._criar_material_com_estoque(
            "001.003.004",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("2"),
        )
        requisicao, _ = self._criar_requisicao_autorizada(
            criador=solicitante,
            beneficiario=solicitante,
            numero_publico="REQ-2026-200003",
            material=material,
            quantidade_autorizada=Decimal("2"),
        )

        with pytest.raises(PermissionDenied):
            atender_requisicao_completa(requisicao=requisicao, ator=solicitante)
        with pytest.raises(PermissionDenied):
            atender_requisicao_com_itens(
                requisicao=requisicao,
                ator=solicitante,
                itens=[ItemAtendimentoData(item_id=_.id, quantidade_entregue=Decimal("2"))],
            )

        atendente = self._criar_usuario(
            "12006",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        requisicao.status = StatusRequisicao.PRONTA_PARA_RETIRADA
        requisicao.save(update_fields=["status", "updated_at"])

        with pytest.raises(DomainConflict):
            atender_requisicao_completa(requisicao=requisicao, ator=atendente)

    def test_atendimento_bloqueia_saldo_fisico_insuficiente(self):
        setor = self._criar_setor("Logistica", "92004")
        requisitante = self._criar_usuario("12007", "Solicitante Logistica", setor=setor)
        atendente = self._criar_usuario(
            "12008",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.003.005",
            saldo_fisico=Decimal("1"),
            saldo_reservado=Decimal("3"),
        )
        requisicao, item = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200004",
            material=material,
            quantidade_autorizada=Decimal("3"),
        )

        atendida = atender_requisicao_completa(requisicao=requisicao, ator=atendente)
        assert atendida.status == StatusRequisicao.PRONTA_PARA_RETIRADA

        with pytest.raises(DomainConflict):
            retirar_requisicao(
                requisicao=atendida,
                ator=atendente,
                retirante_fisico="Responsável",
            )

        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert item.quantidade_entregue == Decimal("3")
        assert material.estoque.saldo_fisico == Decimal("1")
        assert material.estoque.saldo_reservado == Decimal("3")
        assert MovimentacaoEstoque.objects.count() == 0

    def test_atendimento_bloqueia_saldo_reservado_insuficiente(self):
        setor = self._criar_setor("Logistica Reserva", "92006")
        requisitante = self._criar_usuario("12011", "Solicitante Logistica Reserva", setor=setor)
        atendente = self._criar_usuario(
            "12012",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.003.007",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("1"),
        )
        requisicao, item = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200006",
            material=material,
            quantidade_autorizada=Decimal("3"),
        )

        atendida = atender_requisicao_completa(requisicao=requisicao, ator=atendente)
        assert atendida.status == StatusRequisicao.PRONTA_PARA_RETIRADA

        with pytest.raises(DomainConflict):
            retirar_requisicao(
                requisicao=atendida,
                ator=atendente,
                retirante_fisico="Responsável",
            )

        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert item.quantidade_entregue == Decimal("3")
        assert material.estoque.saldo_fisico == Decimal("5")
        assert material.estoque.saldo_reservado == Decimal("1")
        assert MovimentacaoEstoque.objects.count() == 0

    @pytest.mark.postgres
    def test_atendimentos_concorrentes_nao_duplicam_baixa(self):
        setor = self._criar_setor("Almoxarifado", "92005")
        requisitante = self._criar_usuario("12009", "Solicitante Almoxarifado", setor=setor)
        atendente = self._criar_usuario(
            "12010",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.003.006",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("5"),
        )
        requisicao, _ = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200005",
            material=material,
            quantidade_autorizada=Decimal("5"),
        )

        barrier = Barrier(2)

        def atender(req_id: int):
            close_old_connections()
            try:
                barrier.wait()
                requisicao_atendimento = Requisicao.objects.get(pk=req_id)
                atender_requisicao_completa(
                    requisicao=requisicao_atendimento,
                    ator=atendente,
                )
                return "ok"
            except Exception as exc:  # noqa: BLE001
                return type(exc).__name__
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultado_a = executor.submit(atender, requisicao.id)
            resultado_b = executor.submit(atender, requisicao.id)

        resultados = {resultado_a.result(), resultado_b.result()}
        close_old_connections()

        material.estoque.refresh_from_db()
        requisicao.refresh_from_db()

        assert resultados == {"ok", "DomainConflict"}
        assert requisicao.status == StatusRequisicao.PRONTA_PARA_RETIRADA
        assert material.estoque.saldo_fisico == Decimal("5")
        assert material.estoque.saldo_reservado == Decimal("5")
        assert (
            MovimentacaoEstoque.objects.filter(
                requisicao=requisicao,
                tipo=TipoMovimentacao.SAIDA_POR_ATENDIMENTO,
            ).count()
            == 0
        )

        retirada = retirar_requisicao(
            requisicao=requisicao,
            ator=atendente,
            retirante_fisico="Responsável",
        )
        material.estoque.refresh_from_db()
        assert retirada.status == StatusRequisicao.RETIRADA
        assert material.estoque.saldo_fisico == Decimal("0")
        assert material.estoque.saldo_reservado == Decimal("0")
        assert (
            MovimentacaoEstoque.objects.filter(
                requisicao=requisicao,
                tipo=TipoMovimentacao.SAIDA_POR_ATENDIMENTO,
            ).count()
            == 1
        )

    @pytest.mark.postgres
    def test_cancelamentos_concorrentes_nao_duplicam_liberacao_reserva(self):
        setor = self._criar_setor("Cancelamento Concorrente", "92047")
        requisitante = self._criar_usuario("12047", "Solicitante Concorrente", setor=setor)
        material = self._criar_material_com_estoque(
            "001.003.045",
            saldo_fisico=Decimal("0"),
            saldo_reservado=Decimal("4"),
        )
        requisicao, item = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200045",
            material=material,
            quantidade_autorizada=Decimal("4"),
        )

        barrier = Barrier(2)

        def cancelar(req_id: int):
            close_old_connections()
            try:
                barrier.wait()
                requisicao_cancelamento = Requisicao.objects.get(pk=req_id)
                cancelar_requisicao(
                    requisicao=requisicao_cancelamento,
                    ator=requisitante,
                    motivo_cancelamento="Sem saldo fisico",
                )
                return "ok"
            except Exception as exc:  # noqa: BLE001
                return type(exc).__name__
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultado_a = executor.submit(cancelar, requisicao.id)
            resultado_b = executor.submit(cancelar, requisicao.id)

        resultados = {resultado_a.result(), resultado_b.result()}
        close_old_connections()

        requisicao.refresh_from_db()
        item.refresh_from_db()
        material.estoque.refresh_from_db()

        assert resultados == {"ok", "DomainConflict"}
        assert requisicao.status == StatusRequisicao.CANCELADA
        assert material.estoque.saldo_fisico == Decimal("0")
        assert material.estoque.saldo_reservado == Decimal("0")
        assert (
            MovimentacaoEstoque.objects.filter(
                requisicao=requisicao,
                item_requisicao=item,
                tipo=TipoMovimentacao.LIBERACAO_RESERVA_ATENDIMENTO,
                quantidade=Decimal("4"),
            ).count()
            == 1
        )

    @pytest.mark.postgres
    def test_atendimentos_parciais_concorrentes_nao_duplicam_saida_ou_liberacao(self):
        setor = self._criar_setor("Atendimento Parcial", "92048")
        requisitante = self._criar_usuario("12048", "Solicitante Parcial", setor=setor)
        atendente = self._criar_usuario(
            "12049",
            "Atendente Parcial",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.003.046",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("5"),
        )
        requisicao, item = self._criar_requisicao_autorizada(
            criador=requisitante,
            beneficiario=requisitante,
            numero_publico="REQ-2026-200046",
            material=material,
            quantidade_autorizada=Decimal("5"),
        )

        barrier = Barrier(2)

        def atender(req_id: int, item_id: int):
            close_old_connections()
            try:
                barrier.wait()
                requisicao_atendimento = Requisicao.objects.get(pk=req_id)
                atender_requisicao_com_itens(
                    requisicao=requisicao_atendimento,
                    ator=atendente,
                    itens=[
                        ItemAtendimentoData(
                            item_id=item_id,
                            quantidade_entregue=Decimal("3"),
                            justificativa_atendimento_parcial="Saldo parcial liberado",
                        )
                    ],
                )
                return "ok"
            except Exception as exc:  # noqa: BLE001
                return type(exc).__name__
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futuro_a = executor.submit(atender, requisicao.id, item.id)
            futuro_b = executor.submit(atender, requisicao.id, item.id)

        resultados = {futuro_a.result(), futuro_b.result()}
        close_old_connections()

        requisicao.refresh_from_db()
        item.refresh_from_db()
        material.estoque.refresh_from_db()

        assert resultados == {"ok", "DomainConflict"}
        assert requisicao.status == StatusRequisicao.PRONTA_PARA_RETIRADA_PARCIAL
        assert item.quantidade_entregue == Decimal("3")
        assert material.estoque.saldo_fisico == Decimal("5")
        assert material.estoque.saldo_reservado == Decimal("5")
        assert MovimentacaoEstoque.objects.filter(requisicao=requisicao).count() == 0

        retirada = retirar_requisicao(
            requisicao=requisicao,
            ator=atendente,
            retirante_fisico="Responsável",
        )
        material.estoque.refresh_from_db()
        assert retirada.status == StatusRequisicao.RETIRADA
        assert material.estoque.saldo_fisico == Decimal("2")
        assert material.estoque.saldo_reservado == Decimal("0")
        assert material.estoque.saldo_fisico >= 0
        assert material.estoque.saldo_reservado >= 0
        assert (
            MovimentacaoEstoque.objects.filter(
                requisicao=requisicao,
                item_requisicao=item,
                tipo=TipoMovimentacao.SAIDA_POR_ATENDIMENTO,
                quantidade=Decimal("3"),
            ).count()
            == 1
        )
        assert (
            MovimentacaoEstoque.objects.filter(
                requisicao=requisicao,
                item_requisicao=item,
                tipo=TipoMovimentacao.LIBERACAO_RESERVA_ATENDIMENTO,
                quantidade=Decimal("2"),
            ).count()
            == 1
        )

    @pytest.mark.postgres
    def test_atendimentos_concorrentes_de_requisicoes_distintas_nao_dividem_mesmo_saldo(self):
        setor = self._criar_setor("Atendimento Distinto", "92049")
        requisitante_a = self._criar_usuario("12050", "Solicitante Distinto A", setor=setor)
        requisitante_b = self._criar_usuario("12051", "Solicitante Distinto B", setor=setor)
        atendente = self._criar_usuario(
            "12052",
            "Atendente Distinto",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.003.047",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("10"),
        )
        requisicao_a, _ = self._criar_requisicao_autorizada(
            criador=requisitante_a,
            beneficiario=requisitante_a,
            numero_publico="REQ-2026-200047",
            material=material,
            quantidade_autorizada=Decimal("5"),
        )
        requisicao_b, _ = self._criar_requisicao_autorizada(
            criador=requisitante_b,
            beneficiario=requisitante_b,
            numero_publico="REQ-2026-200048",
            material=material,
            quantidade_autorizada=Decimal("5"),
        )

        atender_requisicao_completa(requisicao=requisicao_a, ator=atendente)
        atender_requisicao_completa(requisicao=requisicao_b, ator=atendente)
        requisicao_a.refresh_from_db()
        requisicao_b.refresh_from_db()
        assert requisicao_a.status == StatusRequisicao.PRONTA_PARA_RETIRADA
        assert requisicao_b.status == StatusRequisicao.PRONTA_PARA_RETIRADA

        barrier = Barrier(2)

        def retirar(req_id: int):
            close_old_connections()
            try:
                barrier.wait()
                req = Requisicao.objects.get(pk=req_id)
                retirar_requisicao(
                    requisicao=req,
                    ator=atendente,
                    retirante_fisico="Servidor Retirante",
                )
                return "ok"
            except Exception as exc:  # noqa: BLE001
                return type(exc).__name__
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futuro_a = executor.submit(retirar, requisicao_a.id)
            futuro_b = executor.submit(retirar, requisicao_b.id)

        resultados = {futuro_a.result(), futuro_b.result()}
        close_old_connections()

        requisicao_a.refresh_from_db()
        requisicao_b.refresh_from_db()
        material.estoque.refresh_from_db()

        assert resultados == {"ok", "DomainConflict"}
        assert {requisicao_a.status, requisicao_b.status} == {
            StatusRequisicao.PRONTA_PARA_RETIRADA,
            StatusRequisicao.RETIRADA,
        }
        assert material.estoque.saldo_fisico == Decimal("0")
        assert material.estoque.saldo_reservado == Decimal("5")
        assert material.estoque.saldo_fisico >= 0
        assert material.estoque.saldo_reservado >= 0
        assert (
            MovimentacaoEstoque.objects.filter(
                material=material,
                tipo=TipoMovimentacao.SAIDA_POR_ATENDIMENTO,
            ).count()
            == 1
        )


@pytest.mark.django_db(transaction=True)
class TestRetiradaRequisicaoService:
    @staticmethod
    def _criar_setor(nome: str, chefe_matricula: str) -> Setor:
        chefe = User.objects.create(
            matricula_funcional=chefe_matricula,
            nome_completo=f"Chefe {nome}",
            papel=PapelChoices.CHEFE_SETOR,
            is_active=True,
        )
        setor = Setor.objects.create(nome=nome, chefe_responsavel=chefe)
        chefe.setor = setor
        chefe.save(update_fields=["setor"])
        return setor

    @staticmethod
    def _criar_usuario(matricula: str, nome: str, setor, papel=PapelChoices.SOLICITANTE) -> User:
        return User.objects.create(
            matricula_funcional=matricula,
            nome_completo=nome,
            papel=papel,
            setor=setor,
            is_active=True,
        )

    @staticmethod
    def _criar_material_com_estoque(
        codigo: str, saldo_fisico=Decimal("10"), saldo_reservado=Decimal("0")
    ):
        from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial

        grupo_codigo, subgrupo_codigo, sequencial = codigo.split(".")
        grupo, _ = GrupoMaterial.objects.get_or_create(
            codigo_grupo=grupo_codigo, defaults={"nome": f"Grupo {grupo_codigo}"}
        )
        subgrupo, _ = SubgrupoMaterial.objects.get_or_create(
            grupo=grupo,
            codigo_subgrupo=subgrupo_codigo,
            defaults={"nome": f"Subgrupo {subgrupo_codigo}"},
        )
        material = Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo=codigo,
            sequencial=sequencial,
            nome=f"Material {codigo}",
            unidade_medida="UN",
            is_active=True,
        )
        EstoqueMaterial.objects.create(
            material=material, saldo_fisico=saldo_fisico, saldo_reservado=saldo_reservado
        )
        return material

    def _criar_requisicao_pronta(
        self, criador, beneficiario, numero_publico, material, quantidade_autorizada, parcial=False
    ):
        status = (
            StatusRequisicao.PRONTA_PARA_RETIRADA_PARCIAL
            if parcial
            else StatusRequisicao.PRONTA_PARA_RETIRADA
        )
        requisicao = Requisicao.objects.create(
            criador=criador,
            beneficiario=beneficiario,
            setor_beneficiario=beneficiario.setor,
            numero_publico=numero_publico,
            status=status,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
            data_finalizacao="2026-04-30T12:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=quantidade_autorizada,
            quantidade_autorizada=quantidade_autorizada,
            quantidade_entregue=quantidade_autorizada,
        )
        return requisicao

    def test_retirada_completa_persiste_retirante_e_data(self):
        setor = self._criar_setor("Almox Retirada", "77001")
        solicitante = self._criar_usuario("77002", "Solicitante Retirada", setor=setor)
        almoxarife = self._criar_usuario(
            "77003", "Almoxarife Retirada", setor=setor, papel=PapelChoices.AUXILIAR_ALMOXARIFADO
        )
        material = self._criar_material_com_estoque(
            "001.001.901", saldo_fisico=Decimal("5"), saldo_reservado=Decimal("2")
        )
        requisicao = self._criar_requisicao_pronta(
            criador=solicitante,
            beneficiario=solicitante,
            numero_publico="REQ-2026-770001",
            material=material,
            quantidade_autorizada=Decimal("2"),
        )

        retirada = retirar_requisicao(
            requisicao=requisicao,
            ator=almoxarife,
            retirante_fisico="Servidor Retirante",
        )

        assert retirada.status == StatusRequisicao.RETIRADA
        assert retirada.retirante_fisico == "Servidor Retirante"
        assert retirada.data_retirada is not None
        assert retirada.eventos.filter(tipo_evento=TipoEvento.RETIRADA).exists()

    def test_retirada_parcial_transita_para_retirada(self):
        setor = self._criar_setor("Almox Retirada Parcial", "77010")
        solicitante = self._criar_usuario("77011", "Solicitante Parcial", setor=setor)
        almoxarife = self._criar_usuario(
            "77012", "Almoxarife Parcial", setor=setor, papel=PapelChoices.CHEFE_ALMOXARIFADO
        )
        material = self._criar_material_com_estoque(
            "001.001.902", saldo_fisico=Decimal("5"), saldo_reservado=Decimal("2")
        )
        requisicao = self._criar_requisicao_pronta(
            criador=solicitante,
            beneficiario=solicitante,
            numero_publico="REQ-2026-770002",
            material=material,
            quantidade_autorizada=Decimal("2"),
            parcial=True,
        )

        retirada = retirar_requisicao(
            requisicao=requisicao,
            ator=almoxarife,
            retirante_fisico="Servidor Parcial",
        )

        assert retirada.status == StatusRequisicao.RETIRADA

    def test_retirada_bloqueia_papel_solicitante(self):
        setor = self._criar_setor("Almox Perm", "77020")
        solicitante = self._criar_usuario("77021", "Solicitante Perm", setor=setor)
        material = self._criar_material_com_estoque("001.001.903", saldo_fisico=Decimal("5"))
        requisicao = self._criar_requisicao_pronta(
            criador=solicitante,
            beneficiario=solicitante,
            numero_publico="REQ-2026-770003",
            material=material,
            quantidade_autorizada=Decimal("2"),
        )

        with pytest.raises(PermissionDenied):
            retirar_requisicao(
                requisicao=requisicao,
                ator=solicitante,
                retirante_fisico="Indevido",
            )

    def test_retirada_bloqueia_status_invalido(self):
        setor = self._criar_setor("Almox Status", "77030")
        solicitante = self._criar_usuario("77031", "Solicitante Status", setor=setor)
        almoxarife = self._criar_usuario(
            "77032", "Almoxarife Status", setor=setor, papel=PapelChoices.AUXILIAR_ALMOXARIFADO
        )
        _material = self._criar_material_com_estoque("001.001.904", saldo_fisico=Decimal("5"))
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-770004",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )

        with pytest.raises(DomainConflict):
            retirar_requisicao(
                requisicao=requisicao,
                ator=almoxarife,
                retirante_fisico="Servidor",
            )


@pytest.mark.django_db(transaction=True)
class TestMaquinaEstadosRequisicao:
    @staticmethod
    def _criar_setor(nome: str, chefe_matricula: str) -> Setor:
        chefe = User.objects.create(
            matricula_funcional=chefe_matricula,
            nome_completo=f"Chefe {nome}",
            papel=PapelChoices.CHEFE_SETOR,
            is_active=True,
        )
        setor = Setor.objects.create(nome=nome, chefe_responsavel=chefe)
        chefe.setor = setor
        chefe.save(update_fields=["setor"])
        return setor

    @staticmethod
    def _criar_usuario(
        matricula: str,
        nome: str,
        *,
        papel=PapelChoices.SOLICITANTE,
        setor: Setor | None = None,
    ) -> User:
        return User.objects.create(
            matricula_funcional=matricula,
            nome_completo=nome,
            papel=papel,
            setor=setor,
            is_active=True,
        )

    @staticmethod
    def _criar_material_com_estoque(
        codigo: str,
        *,
        saldo_fisico: Decimal = Decimal("10"),
    ) -> Material:
        from apps.materials.models import GrupoMaterial, SubgrupoMaterial

        grupo_codigo, subgrupo_codigo, sequencial = codigo.split(".")
        grupo, _ = GrupoMaterial.objects.get_or_create(
            codigo_grupo=grupo_codigo, defaults={"nome": f"Grupo {grupo_codigo}"}
        )
        subgrupo, _ = SubgrupoMaterial.objects.get_or_create(
            grupo=grupo,
            codigo_subgrupo=subgrupo_codigo,
            defaults={"nome": f"Subgrupo {subgrupo_codigo}"},
        )
        material = Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo=codigo,
            sequencial=sequencial,
            nome=f"Material {codigo}",
            unidade_medida="UN",
            is_active=True,
        )
        EstoqueMaterial.objects.create(
            material=material, saldo_fisico=saldo_fisico, saldo_reservado=Decimal("0")
        )
        return material

    @staticmethod
    def _criar_rascunho_com_item(*, criador: User, material: Material) -> Requisicao:
        requisicao = Requisicao.objects.create(
            criador=criador,
            beneficiario=criador,
            setor_beneficiario=criador.setor,
            status=StatusRequisicao.RASCUNHO,
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
        )
        return requisicao

    def test_enviar_para_autorizacao_primeiro_envio_gera_numero_e_evento(self):
        setor = self._criar_setor("Envio01", "SM001")
        solicitante = self._criar_usuario("SM002", "Solicitante Envio01", setor=setor)
        material = self._criar_material_com_estoque("001.001.901")
        requisicao = self._criar_rascunho_com_item(criador=solicitante, material=material)

        resultado = enviar_para_autorizacao(requisicao=requisicao, ator=solicitante)

        assert resultado.status == StatusRequisicao.AGUARDANDO_AUTORIZACAO
        assert resultado.numero_publico is not None
        assert resultado.numero_publico.startswith("REQ-")
        assert resultado.data_envio_autorizacao is not None
        evento = resultado.eventos.get(tipo_evento=TipoEvento.ENVIO_AUTORIZACAO)
        assert evento.usuario == solicitante

    def test_reenviar_para_autorizacao_preserva_numero_publico_e_registra_reenvio(self):
        setor = self._criar_setor("Envio02", "SM010")
        solicitante = self._criar_usuario("SM011", "Solicitante Envio02", setor=setor)
        material = self._criar_material_com_estoque("001.001.902")
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            status=StatusRequisicao.RASCUNHO,
            numero_publico="REQ-2026-900001",
            data_envio_autorizacao="2026-01-01T10:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
        )

        resultado = enviar_para_autorizacao(requisicao=requisicao, ator=solicitante)

        assert resultado.status == StatusRequisicao.AGUARDANDO_AUTORIZACAO
        assert resultado.numero_publico == "REQ-2026-900001"
        assert resultado.eventos.filter(tipo_evento=TipoEvento.REENVIO_AUTORIZACAO).exists()
        assert not resultado.eventos.filter(tipo_evento=TipoEvento.ENVIO_AUTORIZACAO).exists()

    def test_retornar_para_rascunho_muda_status_e_registra_evento(self):
        setor = self._criar_setor("Retorno01", "SM020")
        solicitante = self._criar_usuario("SM021", "Solicitante Retorno01", setor=setor)
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-900002",
            data_envio_autorizacao="2026-01-02T10:00:00Z",
        )

        resultado = retornar_para_rascunho(requisicao=requisicao, ator=solicitante)

        assert resultado.status == StatusRequisicao.RASCUNHO
        evento = resultado.eventos.get(tipo_evento=TipoEvento.RETORNO_RASCUNHO)
        assert evento.usuario == solicitante

    def test_enviar_de_status_invalido_levanta_domain_conflict(self):
        setor = self._criar_setor("Invalido01", "SM030")
        solicitante = self._criar_usuario("SM031", "Solicitante Invalido01", setor=setor)
        material = self._criar_material_com_estoque("001.001.903")
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-900003",
            data_envio_autorizacao="2026-01-03T10:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        with pytest.raises(DomainConflict) as excinfo:
            enviar_para_autorizacao(requisicao=requisicao, ator=solicitante)
        assert "Transição inválida" in str(excinfo.value.detail)

    def test_retornar_para_rascunho_de_status_invalido_levanta_domain_conflict(self):
        setor = self._criar_setor("Invalido02", "SM040")
        solicitante = self._criar_usuario("SM041", "Solicitante Invalido02", setor=setor)
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            status=StatusRequisicao.AUTORIZADA,
            numero_publico="REQ-2026-900004",
            data_envio_autorizacao="2026-01-04T10:00:00Z",
            data_autorizacao_ou_recusa="2026-01-04T11:00:00Z",
        )

        with pytest.raises(DomainConflict) as excinfo:
            retornar_para_rascunho(requisicao=requisicao, ator=solicitante)
        assert "Transição inválida" in str(excinfo.value.detail)

    def test_autorizar_de_status_invalido_levanta_domain_conflict(self):
        setor = self._criar_setor("Invalido03", "SM050")
        chefe = setor.chefe_responsavel
        solicitante = self._criar_usuario("SM051", "Solicitante Invalido03", setor=setor)
        material = self._criar_material_com_estoque("001.001.905")
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            status=StatusRequisicao.CANCELADA,
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        with pytest.raises(DomainConflict) as excinfo:
            autorizar_requisicao(
                requisicao=requisicao,
                ator=chefe,
                itens=[ItemAutorizacaoData(item_id=item.id, quantidade_autorizada=Decimal("1"))],
            )
        assert "Transição inválida" in str(excinfo.value.detail)

    def test_retirar_de_status_invalido_levanta_domain_conflict(self):
        setor = self._criar_setor("Invalido04", "SM060")
        solicitante = self._criar_usuario("SM061", "Solicitante Invalido04", setor=setor)
        almoxarife = self._criar_usuario(
            "SM062",
            "Almoxarife Invalido04",
            setor=setor,
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            status=StatusRequisicao.AUTORIZADA,
            numero_publico="REQ-2026-900006",
            data_envio_autorizacao="2026-01-06T10:00:00Z",
            data_autorizacao_ou_recusa="2026-01-06T11:00:00Z",
        )

        with pytest.raises(DomainConflict) as excinfo:
            retirar_requisicao(requisicao=requisicao, ator=almoxarife, retirante_fisico="Teste")
        assert "Transição inválida" in str(excinfo.value.detail)


@pytest.mark.django_db(transaction=True)
class TestPortAdapterStock:
    """Testes de unidade do contrato Port/Adapter entre requisitions e stock.

    Usam StubStockPort — não dependem de EstoqueMaterial nem MovimentacaoEstoque.
    """

    @staticmethod
    def _criar_setor(nome: str, matricula: str) -> Setor:
        chefe = User.objects.create(
            matricula_funcional=matricula,
            nome_completo=f"Chefe {nome}",
            papel=PapelChoices.CHEFE_SETOR,
            is_active=True,
        )
        setor = Setor.objects.create(nome=nome, chefe_responsavel=chefe)
        chefe.setor = setor
        chefe.save(update_fields=["setor"])
        return setor

    @staticmethod
    def _criar_usuario(matricula: str, nome: str, *, setor: Setor) -> User:
        return User.objects.create(
            matricula_funcional=matricula,
            nome_completo=nome,
            papel=PapelChoices.SOLICITANTE,
            setor=setor,
            is_active=True,
        )

    @staticmethod
    def _criar_material(codigo: str) -> Material:
        from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial

        g, _ = GrupoMaterial.objects.get_or_create(
            codigo_grupo=codigo.split(".")[0],
            defaults={"nome": f"G{codigo}"},
        )
        s, _ = SubgrupoMaterial.objects.get_or_create(
            grupo=g,
            codigo_subgrupo=codigo.split(".")[1],
            defaults={"nome": f"S{codigo}"},
        )
        return Material.objects.create(
            subgrupo=s,
            codigo_completo=codigo,
            sequencial=codigo.split(".")[2],
            nome=f"Mat {codigo}",
            unidade_medida="UN",
            is_active=True,
        )

    def _criar_requisicao_aguardando(
        self, *, criador: User, setor: Setor, material: Material, quantidade: Decimal
    ) -> tuple[Requisicao, ItemRequisicao]:
        from apps.requisitions.models import StatusRequisicao

        req = Requisicao.objects.create(
            criador=criador,
            beneficiario=criador,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-990001",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-01-01T00:00:00Z",
        )
        item = req.itens.create(
            material=material,
            unidade_medida="UN",
            quantidade_solicitada=quantidade,
        )
        return req, item

    def _criar_requisicao_autorizada(
        self,
        *,
        criador: User,
        setor: Setor,
        chefe: User,
        material: Material,
        quantidade: Decimal,
    ) -> tuple[Requisicao, ItemRequisicao]:
        from django.utils import timezone

        from apps.requisitions.models import StatusRequisicao

        req = Requisicao.objects.create(
            criador=criador,
            beneficiario=criador,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-990002",
            status=StatusRequisicao.AUTORIZADA,
            chefe_autorizador=chefe,
            data_envio_autorizacao="2026-01-01T00:00:00Z",
            data_autorizacao_ou_recusa=timezone.now(),
        )
        item = req.itens.create(
            material=material,
            unidade_medida="UN",
            quantidade_solicitada=quantidade,
            quantidade_autorizada=quantidade,
        )
        return req, item

    def _criar_requisicao_pronta(
        self,
        *,
        criador: User,
        setor: Setor,
        chefe: User,
        atendente: User,
        material: Material,
        quantidade: Decimal,
    ) -> tuple[Requisicao, ItemRequisicao]:
        from django.utils import timezone

        from apps.requisitions.models import StatusRequisicao

        req = Requisicao.objects.create(
            criador=criador,
            beneficiario=criador,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-990003",
            status=StatusRequisicao.PRONTA_PARA_RETIRADA,
            chefe_autorizador=chefe,
            responsavel_atendimento=atendente,
            data_envio_autorizacao="2026-01-01T00:00:00Z",
            data_autorizacao_ou_recusa=timezone.now(),
            data_finalizacao=timezone.now(),
        )
        item = req.itens.create(
            material=material,
            unidade_medida="UN",
            quantidade_solicitada=quantidade,
            quantidade_autorizada=quantidade,
            quantidade_entregue=quantidade,
        )
        return req, item

    def test_autorizar_chama_port_com_itens_autorizados(self):
        setor = self._criar_setor("Port Setor", "PA001")
        chefe = setor.chefe_responsavel
        req_user = self._criar_usuario("PA002", "Solicitante Port", setor=setor)
        material = self._criar_material("099.001.001")
        req, item = self._criar_requisicao_aguardando(
            criador=req_user, setor=setor, material=material, quantidade=Decimal("3")
        )
        stub = StubStockPort()

        autorizar_requisicao(
            requisicao=req,
            ator=chefe,
            itens=[ItemAutorizacaoData(item_id=item.id, quantidade_autorizada=Decimal("3"))],
            stock=stub,
        )

        assert len(stub.reservas_aplicadas) == 1
        req_chamado, itens_chamados = stub.reservas_aplicadas[0]
        assert req_chamado.pk == req.pk
        assert len(itens_chamados) == 1
        assert itens_chamados[0].quantidade_autorizada == Decimal("3")

    def test_autorizar_nao_chama_port_quando_todos_itens_zerados(self):
        setor = self._criar_setor("Port Setor Zero", "PA010")
        chefe = setor.chefe_responsavel
        req_user = self._criar_usuario("PA011", "Solicitante Zero", setor=setor)
        material = self._criar_material("099.001.002")
        req, item = self._criar_requisicao_aguardando(
            criador=req_user, setor=setor, material=material, quantidade=Decimal("3")
        )
        stub = StubStockPort()

        with pytest.raises(DomainConflict):
            autorizar_requisicao(
                requisicao=req,
                ator=chefe,
                itens=[
                    ItemAutorizacaoData(
                        item_id=item.id,
                        quantidade_autorizada=Decimal("0"),
                        justificativa_autorizacao_parcial="Sem estoque",
                    )
                ],
                stock=stub,
            )

        assert len(stub.reservas_aplicadas) == 0

    def test_falha_no_port_reverte_transicao_autorizacao(self):
        from apps.requisitions.models import EventoTimeline

        setor = self._criar_setor("Port Rollback Auth", "PA020")
        chefe = setor.chefe_responsavel
        req_user = self._criar_usuario("PA021", "Solicitante Rollback", setor=setor)
        material = self._criar_material("099.001.003")
        req, item = self._criar_requisicao_aguardando(
            criador=req_user, setor=setor, material=material, quantidade=Decimal("2")
        )
        timeline_antes = EventoTimeline.objects.filter(requisicao=req).count()
        stub = StubStockPort()
        stub.deve_falhar_em = "aplicar_reservas_autorizacao"

        with pytest.raises(DomainConflict):
            autorizar_requisicao(
                requisicao=req,
                ator=chefe,
                itens=[ItemAutorizacaoData(item_id=item.id, quantidade_autorizada=Decimal("2"))],
                stock=stub,
            )

        req.refresh_from_db()
        item.refresh_from_db()
        assert req.status == StatusRequisicao.AGUARDANDO_AUTORIZACAO
        assert req.data_autorizacao_ou_recusa is None
        assert item.quantidade_autorizada == Decimal("0")
        assert EventoTimeline.objects.filter(requisicao=req).count() == timeline_antes

    def test_cancelar_autorizada_chama_port_liberar_reservas(self):
        setor = self._criar_setor("Port Cancel", "PA030")
        chefe = setor.chefe_responsavel
        req_user = self._criar_usuario("PA031", "Solicitante Cancel", setor=setor)
        material = self._criar_material("099.001.004")
        req, _ = self._criar_requisicao_autorizada(
            criador=req_user, setor=setor, chefe=chefe, material=material, quantidade=Decimal("2")
        )
        stub = StubStockPort()

        cancelar_requisicao(
            requisicao=req,
            ator=req_user,
            motivo_cancelamento="Teste port",
            stock=stub,
        )

        assert len(stub.cancelamentos_liberados) == 1
        req_chamado, itens_chamados = stub.cancelamentos_liberados[0]
        assert req_chamado.pk == req.pk
        assert len(itens_chamados) == 1

    def test_falha_no_port_reverte_cancelamento(self):
        from apps.requisitions.models import EventoTimeline

        setor = self._criar_setor("Port Rollback Cancel", "PA040")
        chefe = setor.chefe_responsavel
        req_user = self._criar_usuario("PA041", "Solicitante RB Cancel", setor=setor)
        material = self._criar_material("099.001.005")
        req, _ = self._criar_requisicao_autorizada(
            criador=req_user, setor=setor, chefe=chefe, material=material, quantidade=Decimal("2")
        )
        timeline_antes = EventoTimeline.objects.filter(requisicao=req).count()
        stub = StubStockPort()
        stub.deve_falhar_em = "liberar_reservas_cancelamento"

        with pytest.raises(DomainConflict):
            cancelar_requisicao(
                requisicao=req,
                ator=req_user,
                motivo_cancelamento="Rollback test",
                stock=stub,
            )

        req.refresh_from_db()
        assert req.status == StatusRequisicao.AUTORIZADA
        assert req.motivo_cancelamento == ""
        assert req.data_finalizacao is None
        assert EventoTimeline.objects.filter(requisicao=req).count() == timeline_antes

    def test_retirar_chama_port_saidas_e_liberacoes(self):
        setor = self._criar_setor("Port Retirada", "PA050")
        chefe = setor.chefe_responsavel
        req_user = self._criar_usuario("PA051", "Solicitante Retirada", setor=setor)
        atendente = User.objects.create(
            matricula_funcional="PA052",
            nome_completo="Atendente Port",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
            is_active=True,
        )
        material = self._criar_material("099.001.006")
        req, _ = self._criar_requisicao_pronta(
            criador=req_user,
            setor=setor,
            chefe=chefe,
            atendente=atendente,
            material=material,
            quantidade=Decimal("3"),
        )
        stub = StubStockPort()

        retirar_requisicao(
            requisicao=req,
            ator=atendente,
            retirante_fisico="Fulano",
            stock=stub,
        )

        assert len(stub.retiradas_aplicadas) == 1
        req_chamado, itens_chamados = stub.retiradas_aplicadas[0]
        assert req_chamado.pk == req.pk
        assert len(itens_chamados) == 1

    def test_falha_no_port_reverte_retirada(self):
        from apps.requisitions.models import EventoTimeline

        setor = self._criar_setor("Port Rollback Retirada", "PA060")
        chefe = setor.chefe_responsavel
        req_user = self._criar_usuario("PA061", "Solicitante RB Retirada", setor=setor)
        atendente = User.objects.create(
            matricula_funcional="PA062",
            nome_completo="Atendente RB",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
            is_active=True,
        )
        material = self._criar_material("099.001.007")
        req, _ = self._criar_requisicao_pronta(
            criador=req_user,
            setor=setor,
            chefe=chefe,
            atendente=atendente,
            material=material,
            quantidade=Decimal("3"),
        )
        timeline_antes = EventoTimeline.objects.filter(requisicao=req).count()
        stub = StubStockPort()
        stub.deve_falhar_em = "aplicar_saidas_e_liberacoes_retirada"

        with pytest.raises(DomainConflict):
            retirar_requisicao(
                requisicao=req,
                ator=atendente,
                retirante_fisico="Fulano",
                stock=stub,
            )

        req.refresh_from_db()
        assert req.status == StatusRequisicao.PRONTA_PARA_RETIRADA
        assert req.data_retirada is None
        assert req.retirante_fisico == ""
        assert EventoTimeline.objects.filter(requisicao=req).count() == timeline_antes


@pytest.mark.django_db(transaction=True)
class TestRascunhoCRUDEAtendimentoService:
    """Cobertura de service para criar/atualizar/descartar rascunho e atendimento.

    ADR 0007: toda regra de domínio deve ter cobertura em test_services antes de test_api.
    Issue #83.
    """

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _criar_setor(nome: str, chefe_matricula: str) -> Setor:
        chefe = User.objects.create(
            matricula_funcional=chefe_matricula,
            nome_completo=f"Chefe {nome}",
            papel=PapelChoices.CHEFE_SETOR,
            is_active=True,
        )
        setor = Setor.objects.create(nome=nome, chefe_responsavel=chefe)
        chefe.setor = setor
        chefe.save(update_fields=["setor"])
        return setor

    @staticmethod
    def _criar_usuario(
        matricula: str,
        nome: str,
        *,
        papel=PapelChoices.SOLICITANTE,
        setor: Setor | None = None,
        is_superuser: bool = False,
    ) -> User:
        return User.objects.create(
            matricula_funcional=matricula,
            nome_completo=nome,
            papel=papel,
            setor=setor,
            is_active=True,
            is_superuser=is_superuser,
        )

    @staticmethod
    def _criar_material(
        codigo: str,
        *,
        saldo_fisico: Decimal = Decimal("10"),
        is_active: bool = True,
    ) -> Material:
        from apps.materials.models import GrupoMaterial, SubgrupoMaterial

        grupo_codigo, subgrupo_codigo, sequencial = codigo.split(".")
        grupo, _ = GrupoMaterial.objects.get_or_create(
            codigo_grupo=grupo_codigo, defaults={"nome": f"Grupo {grupo_codigo}"}
        )
        subgrupo, _ = SubgrupoMaterial.objects.get_or_create(
            grupo=grupo,
            codigo_subgrupo=subgrupo_codigo,
            defaults={"nome": f"Subgrupo {subgrupo_codigo}"},
        )
        material = Material.objects.create(
            subgrupo=subgrupo,
            codigo_completo=codigo,
            sequencial=sequencial,
            nome=f"Material {codigo}",
            unidade_medida="UN",
            is_active=is_active,
        )
        EstoqueMaterial.objects.create(
            material=material,
            saldo_fisico=saldo_fisico,
            saldo_reservado=Decimal("0"),
        )
        return material

    # -------------------------------------------------------------------------
    # criar_rascunho_requisicao
    # -------------------------------------------------------------------------

    def test_criar_rascunho_happy_path(self):
        setor = self._criar_setor("Criar01", "CR001")
        solicitante = self._criar_usuario("CR002", "Solicitante Criar01", setor=setor)
        material = self._criar_material("099.001.001")

        resultado = criar_rascunho_requisicao(
            criador=solicitante,
            beneficiario=solicitante,
            observacao="obs",
            itens=[ItemRascunhoData(material_id=material.pk, quantidade_solicitada=Decimal("3"))],
        )

        assert resultado.status == StatusRequisicao.RASCUNHO
        assert resultado.criador == solicitante
        assert resultado.itens.filter(material=material).exists()

    def test_criar_rascunho_material_inativo(self):
        setor = self._criar_setor("Criar02", "CR010")
        solicitante = self._criar_usuario("CR011", "Solicitante Criar02", setor=setor)
        material = self._criar_material("099.001.002", is_active=False)

        with pytest.raises(DomainConflict):
            criar_rascunho_requisicao(
                criador=solicitante,
                beneficiario=solicitante,
                observacao="",
                itens=[
                    ItemRascunhoData(material_id=material.pk, quantidade_solicitada=Decimal("1"))
                ],
            )

    def test_criar_rascunho_quantidade_acima_saldo(self):
        setor = self._criar_setor("Criar03", "CR020")
        solicitante = self._criar_usuario("CR021", "Solicitante Criar03", setor=setor)
        material = self._criar_material("099.001.003", saldo_fisico=Decimal("2"))

        with pytest.raises(DomainConflict):
            criar_rascunho_requisicao(
                criador=solicitante,
                beneficiario=solicitante,
                observacao="",
                itens=[
                    ItemRascunhoData(material_id=material.pk, quantidade_solicitada=Decimal("5"))
                ],
            )

    def test_criar_rascunho_sem_itens(self):
        setor = self._criar_setor("Criar04", "CR030")
        solicitante = self._criar_usuario("CR031", "Solicitante Criar04", setor=setor)

        with pytest.raises(ValidationError) as excinfo:
            criar_rascunho_requisicao(
                criador=solicitante,
                beneficiario=solicitante,
                observacao="",
                itens=[],
            )
        assert "itens" in excinfo.value.detail

    # -------------------------------------------------------------------------
    # atualizar_rascunho_requisicao
    # -------------------------------------------------------------------------

    def test_atualizar_rascunho_happy_path(self):
        setor = self._criar_setor("Atualizar01", "AT001")
        # AUXILIAR_ALMOXARIFADO pode criar/editar para qualquer beneficiário
        criador = self._criar_usuario(
            "AT002", "Almoxarife Atualizar01", papel=PapelChoices.AUXILIAR_ALMOXARIFADO, setor=setor
        )
        beneficiario_novo = self._criar_usuario("AT003", "Beneficiario Novo", setor=setor)
        material = self._criar_material("099.001.004")
        material_antigo = self._criar_material("099.001.014")
        requisicao = Requisicao.objects.create(
            criador=criador,
            beneficiario=criador,
            setor_beneficiario=setor,
            status=StatusRequisicao.RASCUNHO,
        )
        item_antigo = requisicao.itens.create(
            material=material_antigo,
            unidade_medida=material_antigo.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        resultado = atualizar_rascunho_requisicao(
            requisicao_id=requisicao.pk,
            ator=criador,
            beneficiario_id=beneficiario_novo.pk,
            observacao="nova obs",
            itens=[ItemRascunhoData(material_id=material.pk, quantidade_solicitada=Decimal("2"))],
        )

        assert resultado.beneficiario_id == beneficiario_novo.pk
        assert resultado.itens.filter(material=material).exists()
        assert not resultado.itens.filter(pk=item_antigo.pk).exists()
        assert resultado.itens.count() == 1

    def test_atualizar_rascunho_status_invalido(self):
        setor = self._criar_setor("Atualizar02", "AT010")
        solicitante = self._criar_usuario("AT011", "Solicitante Atualizar02", setor=setor)
        material = self._criar_material("099.001.005")
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-990001",
            data_envio_autorizacao="2026-01-01T10:00:00Z",
        )

        with pytest.raises(DomainConflict) as excinfo:
            atualizar_rascunho_requisicao(
                requisicao_id=requisicao.pk,
                ator=solicitante,
                beneficiario_id=solicitante.pk,
                observacao="",
                itens=[
                    ItemRascunhoData(material_id=material.pk, quantidade_solicitada=Decimal("1"))
                ],
            )
        assert "rascunho" in str(excinfo.value.detail).lower()

    def test_atualizar_rascunho_ator_sem_permissao(self):
        """Superuser passa pode_visualizar_requisicao mas falha em pode_manipular_pre_autorizacao."""
        setor = self._criar_setor("Atualizar03", "AT020")
        criador = self._criar_usuario("AT021", "Criador Atualizar03", setor=setor)
        superuser = self._criar_usuario("AT022", "Super Atualizar03", is_superuser=True)
        material = self._criar_material("099.001.006")
        requisicao = Requisicao.objects.create(
            criador=criador,
            beneficiario=criador,
            setor_beneficiario=setor,
            status=StatusRequisicao.RASCUNHO,
        )

        with pytest.raises(PermissionDenied):
            atualizar_rascunho_requisicao(
                requisicao_id=requisicao.pk,
                ator=superuser,
                beneficiario_id=criador.pk,
                observacao="",
                itens=[
                    ItemRascunhoData(material_id=material.pk, quantidade_solicitada=Decimal("1"))
                ],
            )

    # -------------------------------------------------------------------------
    # descartar_rascunho_nunca_enviado
    # -------------------------------------------------------------------------

    def test_descartar_rascunho_happy_path(self):
        setor = self._criar_setor("Descartar01", "DS001")
        solicitante = self._criar_usuario("DS002", "Solicitante Descartar01", setor=setor)
        material = self._criar_material("099.001.007")
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            status=StatusRequisicao.RASCUNHO,
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )
        requisicao_id = requisicao.pk
        item_id = item.pk

        descartar_rascunho_nunca_enviado(requisicao=requisicao, ator=solicitante)

        assert not Requisicao.objects.filter(pk=requisicao_id).exists()
        assert not ItemRequisicao.objects.filter(pk=item_id).exists()

    def test_descartar_rascunho_ja_formalizado(self):
        setor = self._criar_setor("Descartar02", "DS010")
        solicitante = self._criar_usuario("DS011", "Solicitante Descartar02", setor=setor)
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            status=StatusRequisicao.RASCUNHO,
            numero_publico="REQ-2026-990002",
            data_envio_autorizacao="2026-01-02T10:00:00Z",
        )

        with pytest.raises(DomainConflict) as excinfo:
            descartar_rascunho_nunca_enviado(requisicao=requisicao, ator=solicitante)
        assert "formalizado" in str(excinfo.value.detail).lower()

    def test_descartar_rascunho_ator_sem_permissao(self):
        setor = self._criar_setor("Descartar03", "DS020")
        criador = self._criar_usuario("DS021", "Criador Descartar03", setor=setor)
        outro = self._criar_usuario("DS022", "Outro Descartar03", setor=setor)
        requisicao = Requisicao.objects.create(
            criador=criador,
            beneficiario=criador,
            setor_beneficiario=setor,
            status=StatusRequisicao.RASCUNHO,
        )

        with pytest.raises(PermissionDenied):
            descartar_rascunho_nunca_enviado(requisicao=requisicao, ator=outro)

    # -------------------------------------------------------------------------
    # atender_requisicao — entrega acima do autorizado
    # -------------------------------------------------------------------------

    def test_atender_entrega_acima_do_autorizado(self):
        setor = self._criar_setor("Atender01", "ATE001")
        solicitante = self._criar_usuario("ATE002", "Solicitante Atender01", setor=setor)
        almoxarife = self._criar_usuario(
            "ATE003",
            "Almoxarife Atender01",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material("099.001.008", saldo_fisico=Decimal("10"))
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            status=StatusRequisicao.AUTORIZADA,
            numero_publico="REQ-2026-990003",
            data_envio_autorizacao="2026-01-03T10:00:00Z",
            data_autorizacao_ou_recusa="2026-01-03T11:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
            quantidade_autorizada=Decimal("3"),
        )

        with pytest.raises(DomainConflict) as excinfo:
            atender_requisicao_com_itens(
                requisicao=requisicao,
                ator=almoxarife,
                itens=[
                    ItemAtendimentoData(
                        item_id=item.pk,
                        quantidade_entregue=Decimal("5"),
                        justificativa_atendimento_parcial="",
                    )
                ],
            )
        assert "autorizada" in str(excinfo.value.detail).lower()
