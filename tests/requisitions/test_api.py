from decimal import Decimal

import pytest
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from rest_framework.test import APIClient

from apps.materials.models import GrupoMaterial, Material, SubgrupoMaterial
from apps.notifications.models import Notificacao
from apps.requisitions.models import EventoTimeline, Requisicao, StatusRequisicao, TipoEvento
from apps.requisitions.policies import (
    pode_visualizar_requisicao,
    queryset_requisicoes_pessoais,
    queryset_requisicoes_visiveis,
)
from apps.stock.models import EstoqueMaterial, MovimentacaoEstoque, TipoMovimentacao
from apps.users.models import PapelChoices, Setor, User


@pytest.mark.django_db
class TestRequisicaoAPI:
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
        is_superuser: bool = False,
    ) -> User:
        return User.objects.create(
            matricula_funcional=matricula,
            nome_completo=nome,
            papel=papel,
            setor=setor,
            is_active=is_active,
            is_superuser=is_superuser,
        )

    @staticmethod
    def _criar_material_com_estoque(
        codigo: str,
        *,
        saldo_fisico: Decimal = Decimal("10"),
        saldo_reservado: Decimal = Decimal("0"),
        is_active: bool = True,
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
            is_active=is_active,
        )
        EstoqueMaterial.objects.create(
            material=material,
            saldo_fisico=saldo_fisico,
            saldo_reservado=saldo_reservado,
        )
        return material

    @staticmethod
    def _payload_requisicao(*, beneficiario_id: int, material_id: int, quantidade="2.000"):
        return {
            "beneficiario_id": beneficiario_id,
            "observacao": "Observacao de teste",
            "itens": [
                {
                    "material_id": material_id,
                    "quantidade_solicitada": quantidade,
                    "observacao": "Item de teste",
                }
            ],
        }

    @staticmethod
    def _payload_autorizacao(*, item_id: int, quantidade_autorizada: str, justificativa: str = ""):
        return {
            "itens": [
                {
                    "item_id": item_id,
                    "quantidade_autorizada": quantidade_autorizada,
                    "justificativa_autorizacao_parcial": justificativa,
                }
            ]
        }

    @staticmethod
    def _idempotency_header(key: str = "fulfill-test-key") -> dict[str, str]:
        return {"HTTP_IDEMPOTENCY_KEY": key}

    @staticmethod
    def _criar_requisicao_com_item(
        *,
        criador: User,
        beneficiario: User,
        material: Material,
        status: str = StatusRequisicao.RASCUNHO,
        numero_publico: str | None = None,
        observacao: str = "",
        quantidade_solicitada: str = "2",
    ) -> Requisicao:
        requisicao = Requisicao.objects.create(
            criador=criador,
            beneficiario=beneficiario,
            status=status,
            numero_publico=numero_publico,
            observacao=observacao,
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal(quantidade_solicitada),
        )
        return requisicao

    def test_cria_rascunho_para_si(self):
        setor = self._criar_setor("Operacional", "90001")
        usuario = self._criar_usuario("10001", "Solicitante", setor=setor)
        material = self._criar_material_com_estoque("001.001.001")

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(
            reverse("requisicao-list"),
            self._payload_requisicao(beneficiario_id=usuario.id, material_id=material.id),
            format="json",
        )

        assert response.status_code == 201
        assert response.data["status"] == StatusRequisicao.RASCUNHO
        assert response.data["numero_publico"] is None
        assert response.data["beneficiario"]["id"] == usuario.id
        assert response.data["setor_beneficiario"]["id"] == setor.id
        assert response.data["itens"][0]["material"]["id"] == material.id
        assert Requisicao.objects.count() == 1

    def test_bloqueia_criacao_para_outro_setor_por_solicitante(self):
        setor_a = self._criar_setor("Financeiro", "90002")
        setor_b = self._criar_setor("Obras", "90003")
        solicitante = self._criar_usuario("10002", "Solicitante A", setor=setor_a)
        beneficiario = self._criar_usuario("10003", "Beneficiario B", setor=setor_b)
        material = self._criar_material_com_estoque("001.001.002")

        client = APIClient()
        client.force_authenticate(user=solicitante)
        response = client.post(
            reverse("requisicao-list"),
            self._payload_requisicao(beneficiario_id=beneficiario.id, material_id=material.id),
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_auxiliar_setor_pode_criar_para_funcionario_do_mesmo_setor(self):
        setor = self._criar_setor("TI", "90004")
        auxiliar = self._criar_usuario(
            "10004",
            "Auxiliar TI",
            papel=PapelChoices.AUXILIAR_SETOR,
            setor=setor,
        )
        beneficiario = self._criar_usuario("10005", "Funcionario TI", setor=setor)
        material = self._criar_material_com_estoque("001.001.003")

        client = APIClient()
        client.force_authenticate(user=auxiliar)
        response = client.post(
            reverse("requisicao-list"),
            self._payload_requisicao(beneficiario_id=beneficiario.id, material_id=material.id),
            format="json",
        )

        assert response.status_code == 201
        assert response.data["beneficiario"]["id"] == beneficiario.id

    def test_bloqueia_rascunho_sem_itens(self):
        setor = self._criar_setor("RH", "90005")
        usuario = self._criar_usuario("10006", "Solicitante RH", setor=setor)

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(
            reverse("requisicao-list"),
            {"beneficiario_id": usuario.id, "itens": []},
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"

    def test_bloqueia_criacao_com_material_inativo(self):
        setor = self._criar_setor("Compras", "90006")
        usuario = self._criar_usuario("10007", "Solicitante Compras", setor=setor)
        material = self._criar_material_com_estoque("001.001.004", is_active=False)

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(
            reverse("requisicao-list"),
            self._payload_requisicao(beneficiario_id=usuario.id, material_id=material.id),
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"

    def test_bloqueia_criacao_com_quantidade_maior_que_saldo(self):
        setor = self._criar_setor("Juridico", "90007")
        usuario = self._criar_usuario("10008", "Solicitante Juridico", setor=setor)
        material = self._criar_material_com_estoque("001.001.005", saldo_fisico=Decimal("3"))

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(
            reverse("requisicao-list"),
            self._payload_requisicao(
                beneficiario_id=usuario.id,
                material_id=material.id,
                quantidade="5.000",
            ),
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"

    def test_criacao_com_beneficiario_inexistente_retorna_not_found(self):
        setor = self._criar_setor("Cadastro", "900071")
        usuario = self._criar_usuario("100081", "Solicitante Cadastro", setor=setor)
        material = self._criar_material_com_estoque("001.001.051")

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(
            reverse("requisicao-list"),
            self._payload_requisicao(beneficiario_id=999999, material_id=material.id),
            format="json",
        )

        assert response.status_code == 404
        assert response.data["error"]["code"] == "not_found"

    def test_criacao_rejeita_material_id_zero(self):
        setor = self._criar_setor("Cadastro", "900091")
        usuario = self._criar_usuario("100091", "Solicitante Zero Mat", setor=setor)

        client = APIClient()
        client.force_authenticate(user=usuario)
        payload = {
            "beneficiario_id": usuario.pk,
            "itens": [{"material_id": 0, "quantidade_solicitada": "1.000"}],
        }
        response = client.post(reverse("requisicao-list"), payload, format="json")

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"

    def test_criacao_rejeita_quantidade_zero(self):
        setor = self._criar_setor("Cadastro", "900092")
        usuario = self._criar_usuario("100092", "Solicitante Zero Qty", setor=setor)
        material = self._criar_material_com_estoque("001.001.092")

        client = APIClient()
        client.force_authenticate(user=usuario)
        payload = {
            "beneficiario_id": usuario.pk,
            "itens": [{"material_id": material.pk, "quantidade_solicitada": "0.000"}],
        }
        response = client.post(reverse("requisicao-list"), payload, format="json")

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"

    def test_lista_requisicoes_visiveis_paginada_e_leve(self):
        setor = self._criar_setor("Operacoes", "900072")
        outro_setor = self._criar_setor("Financeiro", "900073")
        usuario = self._criar_usuario("100082", "Solicitante Operacoes", setor=setor)
        outro_usuario = self._criar_usuario("100083", "Solicitante Financeiro", setor=outro_setor)
        material = self._criar_material_com_estoque("001.001.052")

        rascunho = self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=usuario,
            material=material,
            observacao="Rascunho visivel",
        )
        submetida = self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=usuario,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000111",
            observacao="Requisicao enviada",
        )
        rascunho_terceiro_como_beneficiario = self._criar_requisicao_com_item(
            criador=outro_usuario,
            beneficiario=usuario,
            material=material,
            status=StatusRequisicao.RASCUNHO,
        )
        self._criar_requisicao_com_item(
            criador=outro_usuario,
            beneficiario=outro_usuario,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000222",
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("requisicao-list"))

        assert response.status_code == 200
        assert response.data["count"] == 2
        assert response.data["page"] == 1
        assert response.data["page_size"] == 20
        resultado_ids = [item["id"] for item in response.data["results"]]
        assert resultado_ids == [submetida.id, rascunho.id]
        assert rascunho_terceiro_como_beneficiario.id not in resultado_ids
        assert response.data["results"][1]["numero_publico"] is None
        assert response.data["results"][0]["total_itens"] == 1
        assert "itens" not in response.data["results"][0]
        assert "eventos" not in response.data["results"][0]

    def test_lista_requisicoes_nao_autenticado_retorna_403(self):
        client = APIClient()

        response = client.get(reverse("requisicao-list"))

        assert response.status_code == 403
        assert response.data["error"]["code"] == "not_authenticated"

    def test_lista_requisicoes_almoxarife_ve_todos_os_setores(self):
        setor_a = self._criar_setor("Almoxarifado", "900079")
        setor_b = self._criar_setor("Manutencao", "900080")
        almoxarife = self._criar_usuario(
            "100090",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor_a,
        )
        usuario_b = self._criar_usuario("100091", "Solicitante B", setor=setor_b)
        material = self._criar_material_com_estoque("001.001.057")
        requisicao = self._criar_requisicao_com_item(
            criador=usuario_b,
            beneficiario=usuario_b,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000777",
        )
        rascunho_terceiro = self._criar_requisicao_com_item(
            criador=usuario_b,
            beneficiario=usuario_b,
            material=material,
            status=StatusRequisicao.RASCUNHO,
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.get(reverse("requisicao-list"))

        assert response.status_code == 200
        assert response.data["count"] >= 1
        assert any(item["id"] == requisicao.id for item in response.data["results"])
        assert all(item["id"] != rascunho_terceiro.id for item in response.data["results"])

    def test_lista_requisicoes_chefe_almoxarifado_ve_todos_os_setores(self):
        setor_almoxarifado = self._criar_setor(
            "Almoxarifado Chefia",
            "9000801",
            papel=PapelChoices.CHEFE_ALMOXARIFADO,
        )
        chefe_almoxarifado = setor_almoxarifado.chefe_responsavel
        setor_outro = self._criar_setor("Patrimonio Chefia", "9000802")
        usuario_outro = self._criar_usuario(
            "100091",
            "Solicitante Patrimonio Chefia",
            setor=setor_outro,
        )
        material = self._criar_material_com_estoque("001.001.151")
        requisicao = self._criar_requisicao_com_item(
            criador=usuario_outro,
            beneficiario=usuario_outro,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000778",
        )
        rascunho_terceiro = self._criar_requisicao_com_item(
            criador=usuario_outro,
            beneficiario=usuario_outro,
            material=material,
            status=StatusRequisicao.RASCUNHO,
        )

        client = APIClient()
        client.force_authenticate(user=chefe_almoxarifado)
        response = client.get(reverse("requisicao-list"))

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert any(item["id"] == requisicao.id for item in response.data["results"])
        assert all(item["id"] != rascunho_terceiro.id for item in response.data["results"])

    def test_lista_requisicoes_chefe_setor_ve_apenas_proprio_setor_e_pessoais(self):
        setor_a = self._criar_setor("Planejamento Lista", "9000803")
        setor_b = self._criar_setor("Frota Lista", "9000804")
        chefe_setor = setor_a.chefe_responsavel
        usuario_setor_a = self._criar_usuario("100092", "Usuario Setor A", setor=setor_a)
        usuario_setor_b = self._criar_usuario("100093", "Usuario Setor B", setor=setor_b)
        material = self._criar_material_com_estoque("001.001.152")
        requisicao_setor_a = self._criar_requisicao_com_item(
            criador=usuario_setor_a,
            beneficiario=usuario_setor_a,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000779",
        )
        rascunho_setor_a = self._criar_requisicao_com_item(
            criador=usuario_setor_a,
            beneficiario=usuario_setor_a,
            material=material,
            status=StatusRequisicao.RASCUNHO,
        )
        requisicao_setor_b = self._criar_requisicao_com_item(
            criador=usuario_setor_b,
            beneficiario=usuario_setor_b,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000780",
        )

        client = APIClient()
        client.force_authenticate(user=chefe_setor)
        response = client.get(reverse("requisicao-list"))

        assert response.status_code == 200
        resultado_ids = {item["id"] for item in response.data["results"]}
        assert response.data["count"] == len(resultado_ids) == 1
        assert requisicao_setor_a.id in resultado_ids
        assert rascunho_setor_a.id not in resultado_ids
        assert requisicao_setor_b.id not in resultado_ids

    def test_mine_lista_apenas_requisicoes_criadas_ou_como_beneficiario(self):
        setor_a = self._criar_setor("Operacao Mine", "900081")
        setor_b = self._criar_setor("Suporte Mine", "900082")
        setor_almoxarifado = self._criar_setor("Almoxarifado Mine", "900083")
        chefe_setor = setor_a.chefe_responsavel
        almoxarife = self._criar_usuario(
            "100092",
            "Auxiliar Almoxarifado Mine",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor_almoxarifado,
        )
        usuario = self._criar_usuario("100093", "Usuario Mine", setor=setor_a)
        outro_usuario_setor_a = self._criar_usuario(
            "100094",
            "Outro Usuario Setor A",
            setor=setor_a,
        )
        outro_usuario_setor_b = self._criar_usuario(
            "100095",
            "Outro Usuario Setor B",
            setor=setor_b,
        )
        material = self._criar_material_com_estoque("001.001.058")

        criada_pelo_usuario = self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=usuario,
            material=material,
            status=StatusRequisicao.RASCUNHO,
        )
        rascunho_terceiro_como_beneficiario = self._criar_requisicao_com_item(
            criador=outro_usuario_setor_a,
            beneficiario=usuario,
            material=material,
            status=StatusRequisicao.RASCUNHO,
        )
        beneficiario_usuario = self._criar_requisicao_com_item(
            criador=outro_usuario_setor_a,
            beneficiario=usuario,
            material=material,
            status=StatusRequisicao.AUTORIZADA,
            numero_publico="REQ-2026-000901",
        )
        terceiro_beneficiario = self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=outro_usuario_setor_b,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000902",
        )
        apenas_setor_do_chefe = self._criar_requisicao_com_item(
            criador=outro_usuario_setor_a,
            beneficiario=outro_usuario_setor_a,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000903",
        )
        apenas_visivel_almoxarifado = self._criar_requisicao_com_item(
            criador=outro_usuario_setor_b,
            beneficiario=outro_usuario_setor_b,
            material=material,
            status=StatusRequisicao.AUTORIZADA,
            numero_publico="REQ-2026-000904",
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("requisicao-mine"))

        assert response.status_code == 200
        assert response.data["count"] == 3
        resultado_ids = {item["id"] for item in response.data["results"]}
        assert resultado_ids == {
            criada_pelo_usuario.id,
            beneficiario_usuario.id,
            terceiro_beneficiario.id,
        }
        assert rascunho_terceiro_como_beneficiario.id not in resultado_ids
        assert apenas_setor_do_chefe.id not in resultado_ids
        assert apenas_visivel_almoxarifado.id not in resultado_ids

        response_search = client.get(reverse("requisicao-mine"), {"search": "000902"})
        assert response_search.status_code == 200
        assert response_search.data["count"] == 1
        assert response_search.data["results"][0]["id"] == terceiro_beneficiario.id

        response_status = client.get(
            reverse("requisicao-mine"),
            {"status": StatusRequisicao.AUTORIZADA},
        )
        assert response_status.status_code == 200
        assert response_status.data["count"] == 1
        assert response_status.data["results"][0]["id"] == beneficiario_usuario.id

        client.force_authenticate(user=chefe_setor)
        response_chefe = client.get(reverse("requisicao-mine"))
        assert response_chefe.status_code == 200
        assert response_chefe.data["count"] == 0

        client.force_authenticate(user=almoxarife)
        response_almoxarife = client.get(reverse("requisicao-mine"))
        assert response_almoxarife.status_code == 200
        assert response_almoxarife.data["count"] == 0

    def test_mine_queryset_pessoais_retorna_apenas_criador_ou_beneficiario(self):
        setor_a = self._criar_setor("Operacao Mine Queryset", "9000831")
        setor_b = self._criar_setor("Suporte Mine Queryset", "9000832")
        usuario = self._criar_usuario("100094", "Usuario Mine Queryset", setor=setor_a)
        outro_setor_a = self._criar_usuario("100095", "Outro Setor A", setor=setor_a)
        outro_setor_b = self._criar_usuario("100096", "Outro Setor B", setor=setor_b)
        material = self._criar_material_com_estoque("001.001.153")

        criada_pelo_usuario = self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=outro_setor_b,
            material=material,
            status=StatusRequisicao.RASCUNHO,
        )
        rascunho_terceiro_como_beneficiario = self._criar_requisicao_com_item(
            criador=outro_setor_a,
            beneficiario=usuario,
            material=material,
            status=StatusRequisicao.RASCUNHO,
        )
        beneficiario_usuario = self._criar_requisicao_com_item(
            criador=outro_setor_a,
            beneficiario=usuario,
            material=material,
            status=StatusRequisicao.AUTORIZADA,
            numero_publico="REQ-2026-000905",
        )
        fora_escopo = self._criar_requisicao_com_item(
            criador=outro_setor_a,
            beneficiario=outro_setor_b,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000906",
        )

        queryset_ids = set(
            queryset_requisicoes_pessoais(usuario, skip_prefetch=True).values_list("id", flat=True)
        )

        assert queryset_ids == {criada_pelo_usuario.id, beneficiario_usuario.id}
        assert rascunho_terceiro_como_beneficiario.id not in queryset_ids
        assert fora_escopo.id not in queryset_ids

    def test_mine_queryset_superuser_nao_trata_base_inteira_como_pessoal(self):
        setor = self._criar_setor("Operacao Super Mine", "9000833")
        usuario = self._criar_usuario("100097", "Usuario Super Mine", setor=setor)
        superuser = User.objects.create_superuser(
            matricula_funcional="99003",
            password="testpass123",
            nome_completo="Super Mine",
        )
        superuser.setor = setor
        superuser.save(update_fields=["setor"])
        material = self._criar_material_com_estoque("001.001.154")

        requisicao_superuser = self._criar_requisicao_com_item(
            criador=superuser,
            beneficiario=superuser,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000907",
        )
        requisicao_outro = self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=usuario,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000908",
        )

        queryset_ids = set(
            queryset_requisicoes_pessoais(superuser, skip_prefetch=True).values_list(
                "id", flat=True
            )
        )

        assert queryset_ids == {requisicao_superuser.id}
        assert requisicao_outro.id not in queryset_ids

    def test_lista_requisicoes_filtra_por_status_e_busca_textual(self):
        setor = self._criar_setor("Compras", "900074")
        usuario = self._criar_usuario("100084", "Solicitante Compras", setor=setor)
        material = self._criar_material_com_estoque("001.001.053")

        self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=usuario,
            material=material,
            observacao="Rascunho para edicao",
        )
        aguardando = self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=usuario,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000333",
            observacao="Fluxo de autorizacao",
        )

        client = APIClient()
        client.force_authenticate(user=usuario)

        response_status = client.get(
            reverse("requisicao-list"),
            {"status": StatusRequisicao.AGUARDANDO_AUTORIZACAO},
        )
        assert response_status.status_code == 200
        assert response_status.data["count"] == 1
        assert response_status.data["results"][0]["id"] == aguardando.id

        response_search = client.get(reverse("requisicao-list"), {"search": "000333"})
        assert response_search.status_code == 200
        assert response_search.data["count"] == 1
        assert response_search.data["results"][0]["id"] == aguardando.id

    def test_detail_retorna_itens_justificativas_e_eventos(self):
        setor = self._criar_setor("Patrimonio", "900075")
        usuario = self._criar_usuario("100085", "Solicitante Patrimonio", setor=setor)
        autorizador = self._criar_usuario(
            "100086",
            "Chefe Patrimonio",
            papel=PapelChoices.CHEFE_SETOR,
            setor=setor,
        )
        material = self._criar_material_com_estoque("001.001.054")
        requisicao = self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=usuario,
            material=material,
            status=StatusRequisicao.AUTORIZADA,
            numero_publico="REQ-2026-000444",
        )
        item = requisicao.itens.get()
        item.quantidade_autorizada = Decimal("1")
        item.justificativa_autorizacao_parcial = "Saldo parcial"
        item.save(update_fields=["quantidade_autorizada", "justificativa_autorizacao_parcial"])
        EventoTimeline.objects.create(
            requisicao=requisicao,
            tipo_evento=TipoEvento.AUTORIZACAO_PARCIAL,
            usuario=autorizador,
            observacao="Autorizado parcialmente por saldo.",
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("requisicao-detail", args=[requisicao.id]))

        assert response.status_code == 200
        assert response.data["id"] == requisicao.id
        assert response.data["itens"][0]["justificativa_autorizacao_parcial"] == "Saldo parcial"
        assert response.data["eventos"][0]["tipo_evento"] == TipoEvento.AUTORIZACAO_PARCIAL
        assert response.data["eventos"][0]["usuario"]["id"] == autorizador.id
        assert response.data["eventos"][0]["observacao"] == "Autorizado parcialmente por saldo."

    def test_detail_beneficiario_nao_visualiza_rascunho_de_terceiro_e_visualiza_apos_envio(self):
        setor = self._criar_setor("Patrimonio Beneficiario", "9000751")
        criador = self._criar_usuario(
            "1000861",
            "Auxiliar Patrimonio Beneficiario",
            papel=PapelChoices.AUXILIAR_SETOR,
            setor=setor,
        )
        beneficiario = self._criar_usuario("1000862", "Beneficiario Patrimonio", setor=setor)
        material = self._criar_material_com_estoque("001.001.154")
        rascunho = self._criar_requisicao_com_item(
            criador=criador,
            beneficiario=beneficiario,
            material=material,
            status=StatusRequisicao.RASCUNHO,
        )
        requisicao_enviada = self._criar_requisicao_com_item(
            criador=criador,
            beneficiario=beneficiario,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000445",
        )

        client = APIClient()
        client.force_authenticate(user=beneficiario)
        response_rascunho = client.get(reverse("requisicao-detail", args=[rascunho.id]))
        response_enviada = client.get(reverse("requisicao-detail", args=[requisicao_enviada.id]))

        assert response_rascunho.status_code == 404
        assert response_rascunho.data["error"]["code"] == "not_found"
        assert response_enviada.status_code == 200
        assert response_enviada.data["id"] == requisicao_enviada.id

    def test_detail_chefe_setor_visualiza_requisicao_do_proprio_setor(self):
        setor = self._criar_setor("Patrimonio Chefia Detail", "9000752")
        chefe_setor = setor.chefe_responsavel
        usuario = self._criar_usuario("1000863", "Solicitante Chefia Detail", setor=setor)
        material = self._criar_material_com_estoque("001.001.155")
        requisicao = self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=usuario,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000446",
        )

        client = APIClient()
        client.force_authenticate(user=chefe_setor)
        response = client.get(reverse("requisicao-detail", args=[requisicao.id]))

        assert response.status_code == 200
        assert response.data["id"] == requisicao.id

    def test_detail_requisicao_fora_do_escopo_retorna_404(self):
        setor_a = self._criar_setor("TI", "900076")
        setor_b = self._criar_setor("Frota", "900077")
        usuario = self._criar_usuario("100087", "Solicitante TI", setor=setor_a)
        outro_usuario = self._criar_usuario("100088", "Solicitante Frota", setor=setor_b)
        material = self._criar_material_com_estoque("001.001.055")
        requisicao = self._criar_requisicao_com_item(
            criador=outro_usuario,
            beneficiario=outro_usuario,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000555",
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(reverse("requisicao-detail", args=[requisicao.id]))

        assert response.status_code == 404
        assert response.data["error"]["code"] == "not_found"

    def test_detail_chefe_setor_nao_visualiza_requisicao_de_outro_setor(self):
        setor_a = self._criar_setor("TI Chefia", "9000761")
        setor_b = self._criar_setor("Frota Chefia", "9000762")
        chefe_setor = setor_a.chefe_responsavel
        usuario_b = self._criar_usuario("1000881", "Solicitante Frota Chefia", setor=setor_b)
        material = self._criar_material_com_estoque("001.001.156")
        requisicao = self._criar_requisicao_com_item(
            criador=usuario_b,
            beneficiario=usuario_b,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000556",
        )

        client = APIClient()
        client.force_authenticate(user=chefe_setor)
        response = client.get(reverse("requisicao-detail", args=[requisicao.id]))

        assert response.status_code == 404
        assert response.data["error"]["code"] == "not_found"

    def test_detail_auxiliar_almoxarifado_visualiza_requisicao_de_qualquer_setor(self):
        setor_almoxarifado = self._criar_setor("Almoxarifado Detail", "9000763")
        setor_outro = self._criar_setor("Frota Detail", "9000764")
        almoxarife = self._criar_usuario(
            "1000882",
            "Auxiliar Almoxarifado Detail",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor_almoxarifado,
        )
        usuario_outro = self._criar_usuario(
            "1000883", "Solicitante Frota Detail", setor=setor_outro
        )
        material = self._criar_material_com_estoque("001.001.157")
        requisicao = self._criar_requisicao_com_item(
            criador=usuario_outro,
            beneficiario=usuario_outro,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000557",
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.get(reverse("requisicao-detail", args=[requisicao.id]))

        assert response.status_code == 200
        assert response.data["id"] == requisicao.id

    def test_detail_chefe_almoxarifado_visualiza_requisicao_de_qualquer_setor(self):
        setor_almoxarifado = self._criar_setor(
            "Almoxarifado Detail Chefia",
            "9000765",
            papel=PapelChoices.CHEFE_ALMOXARIFADO,
        )
        chefe_almoxarifado = setor_almoxarifado.chefe_responsavel
        setor_outro = self._criar_setor("Frota Detail Chefia", "9000766")
        usuario_outro = self._criar_usuario(
            "1000884", "Solicitante Frota Detail Chefia", setor=setor_outro
        )
        material = self._criar_material_com_estoque("001.001.158")
        requisicao = self._criar_requisicao_com_item(
            criador=usuario_outro,
            beneficiario=usuario_outro,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000558",
        )

        client = APIClient()
        client.force_authenticate(user=chefe_almoxarifado)
        response = client.get(reverse("requisicao-detail", args=[requisicao.id]))

        assert response.status_code == 200
        assert response.data["id"] == requisicao.id

    def test_detail_usuario_inativo_nao_visualiza_requisicao(self):
        setor = self._criar_setor("Patrimonio Inativo", "9000767")
        usuario_inativo = self._criar_usuario(
            "1000885",
            "Solicitante Inativo Detail",
            setor=setor,
            is_active=False,
        )
        material = self._criar_material_com_estoque("001.001.159")
        requisicao = self._criar_requisicao_com_item(
            criador=usuario_inativo,
            beneficiario=usuario_inativo,
            material=material,
            status=StatusRequisicao.RASCUNHO,
        )

        client = APIClient()
        client.force_authenticate(user=usuario_inativo)
        response = client.get(reverse("requisicao-detail", args=[requisicao.id]))

        assert response.status_code == 404
        assert response.data["error"]["code"] == "not_found"

    def test_detail_superuser_visualiza_requisicao(self):
        setor = self._criar_setor("Patrimonio Superuser", "9000768")
        usuario = self._criar_usuario("1000886", "Solicitante Superuser Detail", setor=setor)
        superuser = User.objects.create_superuser(
            matricula_funcional="99004",
            password="testpass123",
            nome_completo="Super Admin Detail",
        )
        material = self._criar_material_com_estoque("001.001.160")
        requisicao = self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=usuario,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000559",
        )

        client = APIClient()
        client.force_authenticate(user=superuser)
        response = client.get(reverse("requisicao-detail", args=[requisicao.id]))

        assert response.status_code == 200
        assert response.data["id"] == requisicao.id

    def test_detail_anonimo_nao_visualiza_requisicao(self):
        setor = self._criar_setor("Patrimonio Anonimo", "9000769")
        usuario = self._criar_usuario("1000887", "Solicitante Anonimo Detail", setor=setor)
        material = self._criar_material_com_estoque("001.001.161")
        requisicao = self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=usuario,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000560",
        )

        client = APIClient()
        response = client.get(reverse("requisicao-detail", args=[requisicao.id]))

        assert response.status_code == 403
        assert response.data["error"]["code"] == "not_authenticated"

    def test_detail_ignora_filtros_de_listagem_na_url(self):
        setor = self._criar_setor("Obras", "900078")
        usuario = self._criar_usuario("100089", "Solicitante Obras", setor=setor)
        material = self._criar_material_com_estoque("001.001.056")
        requisicao = self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=usuario,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000666",
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.get(
            reverse("requisicao-detail", args=[requisicao.id]),
            {"status": StatusRequisicao.RASCUNHO, "search": "nao-corresponde"},
        )

        assert response.status_code == 200
        assert response.data["id"] == requisicao.id

    def test_lista_requisicoes_coerente_com_pode_visualizar_detail_nos_cenarios_principais(self):
        setor_a = self._criar_setor("Coerencia Setor A", "9000771")
        setor_b = self._criar_setor("Coerencia Setor B", "9000772")
        setor_almoxarifado = self._criar_setor(
            "Coerencia Almoxarifado",
            "9000773",
            papel=PapelChoices.CHEFE_ALMOXARIFADO,
        )
        criador = self._criar_usuario(
            "1000888",
            "Criador Coerencia",
            papel=PapelChoices.AUXILIAR_SETOR,
            setor=setor_a,
        )
        beneficiario = self._criar_usuario("1000889", "Beneficiario Coerencia", setor=setor_a)
        auxiliar_setor = self._criar_usuario(
            "1000890",
            "Auxiliar Setor Coerencia",
            papel=PapelChoices.AUXILIAR_SETOR,
            setor=setor_a,
        )
        chefe_setor = setor_a.chefe_responsavel
        solicitante_outro_setor = self._criar_usuario(
            "1000891",
            "Solicitante Outro Setor Coerencia",
            setor=setor_b,
        )
        auxiliar_almoxarifado = self._criar_usuario(
            "1000892",
            "Auxiliar Almoxarifado Coerencia",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor_almoxarifado,
        )
        chefe_almoxarifado = setor_almoxarifado.chefe_responsavel
        usuario_inativo = self._criar_usuario(
            "1000893",
            "Usuario Inativo Coerencia",
            setor=setor_a,
            is_active=False,
        )
        superuser = User.objects.create_superuser(
            matricula_funcional="99005",
            password="testpass123",
            nome_completo="Super Admin Coerencia",
        )
        material = self._criar_material_com_estoque("001.001.162")
        requisicao_rascunho = self._criar_requisicao_com_item(
            criador=criador,
            beneficiario=beneficiario,
            material=material,
            status=StatusRequisicao.RASCUNHO,
        )
        requisicao_aguardando = self._criar_requisicao_com_item(
            criador=criador,
            beneficiario=beneficiario,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000561",
        )

        cenarios = [
            (criador, True, True),
            (beneficiario, False, True),
            (chefe_setor, False, True),
            (auxiliar_setor, False, False),
            (solicitante_outro_setor, False, False),
            (auxiliar_almoxarifado, False, True),
            (chefe_almoxarifado, False, True),
            (usuario_inativo, False, False),
            (superuser, True, True),
        ]
        for user, esperado_rascunho, esperado_aguardando in cenarios:
            queryset_ids = set(
                queryset_requisicoes_visiveis(user, skip_prefetch=True).values_list("id", flat=True)
            )
            user_id = getattr(user, "matricula_funcional", "<anon>")
            assert pode_visualizar_requisicao(user, requisicao_rascunho) is esperado_rascunho, (
                f"user={user_id} rascunho pode_visualizar esperado={esperado_rascunho}"
            )
            assert (requisicao_rascunho.id in queryset_ids) is esperado_rascunho, (
                f"user={user_id} rascunho queryset esperado={esperado_rascunho}"
            )
            assert pode_visualizar_requisicao(user, requisicao_aguardando) is esperado_aguardando, (
                f"user={user_id} aguardando pode_visualizar esperado={esperado_aguardando}"
            )
            assert (requisicao_aguardando.id in queryset_ids) is esperado_aguardando, (
                f"user={user_id} aguardando queryset esperado={esperado_aguardando}"
            )

        queryset_anonimo = queryset_requisicoes_visiveis(AnonymousUser(), skip_prefetch=True)
        assert pode_visualizar_requisicao(AnonymousUser(), requisicao_rascunho) is False
        assert pode_visualizar_requisicao(AnonymousUser(), requisicao_aguardando) is False
        assert queryset_anonimo.count() == 0

    def test_submit_gera_numero_publico_e_entrada_na_fila(self):
        setor = self._criar_setor("Planejamento", "90008")
        usuario = self._criar_usuario("10009", "Solicitante Planejamento", setor=setor)
        material = self._criar_material_com_estoque("001.001.006")
        requisicao = Requisicao.objects.create(criador=usuario, beneficiario=usuario)
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
        )
        assert item.quantidade_autorizada == 0

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(reverse("requisicao-submit", args=[requisicao.id]))

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.AGUARDANDO_AUTORIZACAO
        assert response.data["numero_publico"] == "REQ-2026-000001"
        requisicao.refresh_from_db()
        assert requisicao.numero_publico == "REQ-2026-000001"
        assert requisicao.eventos.filter(tipo_evento=TipoEvento.ENVIO_AUTORIZACAO).exists()

    def test_return_to_draft_preserva_numero_publico(self):
        setor = self._criar_setor("Patrimonio", "90009")
        usuario = self._criar_usuario("10010", "Solicitante Patrimonio", setor=setor)
        material = self._criar_material_com_estoque("001.001.007")
        requisicao = Requisicao.objects.create(
            criador=usuario,
            beneficiario=usuario,
            numero_publico="REQ-2026-000010",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(reverse("requisicao-return-to-draft", args=[requisicao.id]))

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.RASCUNHO
        assert response.data["numero_publico"] == "REQ-2026-000010"
        assert EventoTimeline.objects.filter(
            requisicao=requisicao,
            tipo_evento=TipoEvento.RETORNO_RASCUNHO,
        ).exists()

    def test_return_to_draft_beneficiario_pode_retornar_mas_perde_acesso_ao_rascunho(self):
        setor = self._criar_setor("Patrimonio Retorno Beneficiario", "90009A")
        criador = self._criar_usuario("10010A", "Criador Retorno", setor=setor)
        beneficiario = self._criar_usuario("10010B", "Beneficiario Retorno", setor=setor)
        material = self._criar_material_com_estoque("001.001.177")
        requisicao = Requisicao.objects.create(
            criador=criador,
            beneficiario=beneficiario,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000011",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=beneficiario)
        response = client.post(reverse("requisicao-return-to-draft", args=[requisicao.id]))

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.RASCUNHO
        assert response.data["numero_publico"] == "REQ-2026-000011"

        detail_response = client.get(reverse("requisicao-detail", args=[requisicao.id]))
        mine_response = client.get(reverse("requisicao-mine"))

        assert detail_response.status_code == 404
        assert detail_response.data["error"]["code"] == "not_found"
        assert mine_response.status_code == 200
        assert mine_response.data["count"] == 0

    def test_update_draft_substitui_beneficiario_observacao_e_itens(self):
        setor = self._criar_setor("Patio", "900091")
        criador = self._criar_usuario(
            "100101",
            "Criador Patio",
            papel=PapelChoices.AUXILIAR_SETOR,
            setor=setor,
        )
        beneficiario_inicial = self._criar_usuario("100102", "Beneficiario Inicial", setor=setor)
        beneficiario_novo = self._criar_usuario("100103", "Beneficiario Novo", setor=setor)
        material_antigo = self._criar_material_com_estoque("001.001.071")
        material_atualizado = self._criar_material_com_estoque("001.001.072")
        material_novo = self._criar_material_com_estoque("001.001.073")
        requisicao = Requisicao.objects.create(
            criador=criador,
            beneficiario=beneficiario_inicial,
            observacao="Observacao antiga",
        )
        item_antigo = requisicao.itens.create(
            material=material_antigo,
            unidade_medida=material_antigo.unidade_medida,
            quantidade_solicitada=Decimal("1"),
            observacao="Item antigo",
        )
        requisicao.itens.create(
            material=material_atualizado,
            unidade_medida=material_atualizado.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            observacao="Item manter",
        )

        client = APIClient()
        client.force_authenticate(user=criador)
        response = client.put(
            reverse("requisicao-update-draft", args=[requisicao.id]),
            {
                "beneficiario_id": beneficiario_novo.id,
                "observacao": "Observacao nova",
                "itens": [
                    {
                        "material_id": material_atualizado.id,
                        "quantidade_solicitada": "5.000",
                        "observacao": "Item atualizado",
                    },
                    {
                        "material_id": material_novo.id,
                        "quantidade_solicitada": "3.000",
                        "observacao": "Item novo",
                    },
                ],
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.RASCUNHO
        assert response.data["beneficiario"]["id"] == beneficiario_novo.id
        assert response.data["observacao"] == "Observacao nova"
        assert len(response.data["itens"]) == 2
        assert {
            (
                item["material"]["id"],
                item["quantidade_solicitada"],
                item["observacao"],
            )
            for item in response.data["itens"]
        } == {
            (material_atualizado.id, "5.000", "Item atualizado"),
            (material_novo.id, "3.000", "Item novo"),
        }

        requisicao.refresh_from_db()
        assert requisicao.beneficiario_id == beneficiario_novo.id
        assert requisicao.setor_beneficiario_id == beneficiario_novo.setor_id
        assert requisicao.observacao == "Observacao nova"
        assert not requisicao.itens.filter(id=item_antigo.id).exists()
        assert {
            (
                item.material_id,
                item.quantidade_solicitada,
                item.observacao,
            )
            for item in requisicao.itens.all()
        } == {
            (material_atualizado.id, Decimal("5.000"), "Item atualizado"),
            (material_novo.id, Decimal("3.000"), "Item novo"),
        }

    def test_update_draft_bloqueia_requisicao_fora_de_rascunho(self):
        setor = self._criar_setor("Patio Status", "900092")
        criador = self._criar_usuario(
            "100111",
            "Criador Patio Status",
            papel=PapelChoices.AUXILIAR_SETOR,
            setor=setor,
        )
        beneficiario = self._criar_usuario("100112", "Beneficiario Status", setor=setor)
        material = self._criar_material_com_estoque("001.001.074")
        requisicao = self._criar_requisicao_com_item(
            criador=criador,
            beneficiario=beneficiario,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000321",
        )

        client = APIClient()
        client.force_authenticate(user=criador)
        response = client.put(
            reverse("requisicao-update-draft", args=[requisicao.id]),
            self._payload_requisicao(beneficiario_id=beneficiario.id, material_id=material.id),
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"
        assert response.data["error"]["details"]["status_atual"] == (
            StatusRequisicao.AGUARDANDO_AUTORIZACAO
        )

    def test_update_draft_bloqueia_usuario_sem_permissao(self):
        setor = self._criar_setor("Patio Permissao", "900093")
        outro_setor = self._criar_setor("Outro Patio", "900094")
        criador = self._criar_usuario("100121", "Criador", setor=setor)
        beneficiario = self._criar_usuario("100122", "Beneficiario", setor=setor)
        intruso = self._criar_usuario("100123", "Intruso", setor=outro_setor)
        material = self._criar_material_com_estoque("001.001.075")
        requisicao = self._criar_requisicao_com_item(
            criador=criador,
            beneficiario=beneficiario,
            material=material,
        )

        client = APIClient()
        client.force_authenticate(user=intruso)
        response = client.put(
            reverse("requisicao-update-draft", args=[requisicao.id]),
            self._payload_requisicao(beneficiario_id=beneficiario.id, material_id=material.id),
            format="json",
        )

        assert response.status_code == 404

    def test_update_draft_bloqueia_beneficiario_terceiro_em_rascunho(self):
        setor = self._criar_setor("Patio Beneficiario Rascunho", "900093A")
        criador = self._criar_usuario("100123A", "Criador Rascunho", setor=setor)
        beneficiario = self._criar_usuario("100123B", "Beneficiario Rascunho", setor=setor)
        material = self._criar_material_com_estoque("001.001.178")
        requisicao = self._criar_requisicao_com_item(
            criador=criador,
            beneficiario=beneficiario,
            material=material,
        )

        client = APIClient()
        client.force_authenticate(user=beneficiario)
        response = client.put(
            reverse("requisicao-update-draft", args=[requisicao.id]),
            self._payload_requisicao(beneficiario_id=beneficiario.id, material_id=material.id),
            format="json",
        )

        assert response.status_code == 404
        assert response.data["error"]["code"] == "not_found"

    def test_update_draft_bloqueia_chefe_almox_visivel_sem_permissao_contextual(self):
        setor = self._criar_setor("Patio Permissao Contextual", "900096")
        setor_almox = self._criar_setor(
            "Almoxarifado",
            "900097",
            papel=PapelChoices.CHEFE_ALMOXARIFADO,
        )
        criador = self._criar_usuario("100141", "Criador", setor=setor)
        beneficiario = self._criar_usuario("100142", "Beneficiario", setor=setor)
        chefe_almox = setor_almox.chefe_responsavel
        material = self._criar_material_com_estoque("001.001.077")
        requisicao = self._criar_requisicao_com_item(
            criador=criador,
            beneficiario=beneficiario,
            material=material,
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            numero_publico="REQ-2026-000322",
        )

        client = APIClient()
        client.force_authenticate(user=chefe_almox)
        response = client.put(
            reverse("requisicao-update-draft", args=[requisicao.id]),
            self._payload_requisicao(beneficiario_id=beneficiario.id, material_id=material.id),
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_update_draft_exige_autenticacao(self):
        setor = self._criar_setor("Patio Auth", "900095")
        usuario = self._criar_usuario("100131", "Usuario Auth", setor=setor)
        material = self._criar_material_com_estoque("001.001.076")
        requisicao = self._criar_requisicao_com_item(
            criador=usuario,
            beneficiario=usuario,
            material=material,
        )

        client = APIClient()
        response = client.put(
            reverse("requisicao-update-draft", args=[requisicao.id]),
            self._payload_requisicao(beneficiario_id=usuario.id, material_id=material.id),
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "not_authenticated"

    def test_update_draft_rejeita_pk_invalido_com_envelope_padrao(self):
        setor = self._criar_setor("Patio PK", "900095A")
        usuario = self._criar_usuario("100131A", "Usuario PK", setor=setor)
        material = self._criar_material_com_estoque("001.001.176")

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.put(
            reverse("requisicao-update-draft", args=["abc"]),
            self._payload_requisicao(beneficiario_id=usuario.id, material_id=material.id),
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        assert response.data["error"]["details"] == {
            "pk": ["Identificador de requisição inválido."]
        }

    def test_reenvio_preserva_numero_publico(self):
        setor = self._criar_setor("Frota", "90010")
        usuario = self._criar_usuario("10011", "Solicitante Frota", setor=setor)
        material = self._criar_material_com_estoque("001.001.008")
        requisicao = Requisicao.objects.create(
            criador=usuario,
            beneficiario=usuario,
            numero_publico="REQ-2026-000123",
            status=StatusRequisicao.RASCUNHO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(reverse("requisicao-submit", args=[requisicao.id]))

        assert response.status_code == 200
        assert response.data["numero_publico"] == "REQ-2026-000123"
        assert EventoTimeline.objects.filter(
            requisicao=requisicao,
            tipo_evento=TipoEvento.REENVIO_AUTORIZACAO,
        ).exists()

    def test_submit_beneficiario_terceiro_nao_pode_enviar_rascunho_de_outro(self):
        setor = self._criar_setor("Frota Submit Terceiro", "90010A")
        criador = self._criar_usuario("10011A", "Criador Submit", setor=setor)
        beneficiario = self._criar_usuario("10011B", "Beneficiario Submit", setor=setor)
        material = self._criar_material_com_estoque("001.001.179")
        requisicao = Requisicao.objects.create(criador=criador, beneficiario=beneficiario)
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=beneficiario)
        response = client.post(reverse("requisicao-submit", args=[requisicao.id]))

        assert response.status_code == 404
        assert response.data["error"]["code"] == "not_found"

    def test_discard_remove_rascunho_nunca_enviado(self):
        setor = self._criar_setor("Fiscal", "90011")
        usuario = self._criar_usuario("10012", "Solicitante Fiscal", setor=setor)
        material = self._criar_material_com_estoque("001.001.009")
        requisicao = Requisicao.objects.create(criador=usuario, beneficiario=usuario)
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.delete(reverse("requisicao-discard", args=[requisicao.id]))

        assert response.status_code == 204
        assert not Requisicao.objects.filter(pk=requisicao.pk).exists()

    def test_discard_beneficiario_terceiro_nao_pode_descartar_rascunho_de_outro(self):
        setor = self._criar_setor("Fiscal Terceiro", "90011A")
        criador = self._criar_usuario("10012A", "Criador Fiscal", setor=setor)
        beneficiario = self._criar_usuario("10012B", "Beneficiario Fiscal", setor=setor)
        material = self._criar_material_com_estoque("001.001.180")
        requisicao = Requisicao.objects.create(criador=criador, beneficiario=beneficiario)
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=beneficiario)
        response = client.delete(reverse("requisicao-discard", args=[requisicao.id]))

        assert response.status_code == 404
        assert response.data["error"]["code"] == "not_found"
        assert Requisicao.objects.filter(pk=requisicao.pk).exists()

    def test_discard_rascunho_formalizado_retorna_domain_conflict(self):
        setor = self._criar_setor("Fiscal Formalizado", "900111")
        usuario = self._criar_usuario("100121", "Solicitante Fiscal Formalizado", setor=setor)
        material = self._criar_material_com_estoque("001.001.099")
        requisicao = Requisicao.objects.create(
            criador=usuario,
            beneficiario=usuario,
            numero_publico="REQ-2026-009999",
            status=StatusRequisicao.RASCUNHO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.delete(reverse("requisicao-discard", args=[requisicao.id]))

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"
        assert Requisicao.objects.filter(pk=requisicao.pk).exists()

    def test_cancela_rascunho_numerado_sem_justificativa(self):
        setor = self._criar_setor("Almox Interno", "90012")
        usuario = self._criar_usuario("10013", "Solicitante Almox Interno", setor=setor)
        material = self._criar_material_com_estoque("001.001.010")
        requisicao = Requisicao.objects.create(
            criador=usuario,
            beneficiario=usuario,
            numero_publico="REQ-2026-000200",
            status=StatusRequisicao.RASCUNHO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(reverse("requisicao-cancel", args=[requisicao.id]))

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.CANCELADA
        assert response.data["numero_publico"] == "REQ-2026-000200"

    def test_cancel_beneficiario_terceiro_nao_pode_cancelar_rascunho_numerado_de_outro(self):
        setor = self._criar_setor("Almox Interno Terceiro", "90012A")
        criador = self._criar_usuario("10013A", "Criador Almox", setor=setor)
        beneficiario = self._criar_usuario("10013B", "Beneficiario Almox", setor=setor)
        material = self._criar_material_com_estoque("001.001.181")
        requisicao = Requisicao.objects.create(
            criador=criador,
            beneficiario=beneficiario,
            numero_publico="REQ-2026-000201",
            status=StatusRequisicao.RASCUNHO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=beneficiario)
        response = client.post(reverse("requisicao-cancel", args=[requisicao.id]))

        assert response.status_code == 404
        assert response.data["error"]["code"] == "not_found"
        requisicao.refresh_from_db()
        assert requisicao.status == StatusRequisicao.RASCUNHO

    def test_authorize_total_reserva_estoque_e_define_autorizador(self):
        setor = self._criar_setor("Producao", "90016")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("10017", "Solicitante Producao", setor=setor)
        material = self._criar_material_com_estoque("001.001.012", saldo_fisico=Decimal("10"))
        requisicao = Requisicao.objects.create(
            criador=requisitante,
            beneficiario=requisitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000400",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("4"),
        )

        client = APIClient()
        client.force_authenticate(user=chefe)
        response = client.post(
            reverse("requisicao-authorize", args=[requisicao.id]),
            self._payload_autorizacao(item_id=item.id, quantidade_autorizada="4.000"),
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.AUTORIZADA
        assert response.data["chefe_autorizador"]["id"] == chefe.id
        assert response.data["itens"][0]["quantidade_autorizada"] == "4.000"
        requisicao.refresh_from_db()
        material.estoque.refresh_from_db()
        assert requisicao.chefe_autorizador_id == chefe.id
        assert requisicao.eventos.filter(tipo_evento=TipoEvento.AUTORIZACAO_TOTAL).exists()
        estoque = material.estoque
        assert estoque.saldo_fisico == Decimal("10")
        assert estoque.saldo_reservado == Decimal("4")

    def test_refuse_requer_motivo_e_nao_reserva_estoque(self):
        setor = self._criar_setor("Transporte", "90017")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("10018", "Solicitante Transporte", setor=setor)
        material = self._criar_material_com_estoque("001.001.013", saldo_fisico=Decimal("7"))
        requisicao = Requisicao.objects.create(
            criador=requisitante,
            beneficiario=requisitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000401",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=chefe)
        response = client.post(
            reverse("requisicao-refuse", args=[requisicao.id]),
            {"motivo_recusa": "Item fora de prioridade"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.RECUSADA
        assert response.data["motivo_recusa"] == "Item fora de prioridade"
        assert response.data["chefe_autorizador"]["id"] == chefe.id
        requisicao.refresh_from_db()
        assert requisicao.eventos.filter(tipo_evento=TipoEvento.RECUSA).exists()
        material.estoque.refresh_from_db()
        assert material.estoque.saldo_reservado == Decimal("0")

    def test_authorize_bloqueia_usuario_sem_permissao(self):
        setor = self._criar_setor("Oficina", "90018")
        usuario = self._criar_usuario("10019", "Solicitante Oficina", setor=setor)
        material = self._criar_material_com_estoque("001.001.014")
        requisicao = Requisicao.objects.create(
            criador=usuario,
            beneficiario=usuario,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000402",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=usuario)
        response = client.post(
            reverse("requisicao-authorize", args=[requisicao.id]),
            self._payload_autorizacao(item_id=item.id, quantidade_autorizada="1.000"),
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_authorize_rejeita_saldo_estavel_insuficiente(self):
        setor = self._criar_setor("Logistica", "90019")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("10020", "Solicitante Logistica", setor=setor)
        material = self._criar_material_com_estoque("001.001.015", saldo_fisico=Decimal("5"))
        requisicao = Requisicao.objects.create(
            criador=requisitante,
            beneficiario=requisitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000403",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("4"),
        )
        material.estoque.saldo_fisico = Decimal("2")
        material.estoque.save(update_fields=["saldo_fisico", "updated_at"])

        client = APIClient()
        client.force_authenticate(user=chefe)
        response = client.post(
            reverse("requisicao-authorize", args=[requisicao.id]),
            self._payload_autorizacao(item_id=item.id, quantidade_autorizada="4.000"),
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"
        material.estoque.refresh_from_db()
        assert material.estoque.saldo_reservado == Decimal("0")

    def test_authorize_partial_and_zero_require_justificativa(self):
        setor = self._criar_setor("Apoio", "90020")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("10021", "Solicitante Apoio", setor=setor)
        material_a = self._criar_material_com_estoque("001.001.016", saldo_fisico=Decimal("8"))
        material_b = self._criar_material_com_estoque("001.001.017", saldo_fisico=Decimal("8"))
        requisicao = Requisicao.objects.create(
            criador=requisitante,
            beneficiario=requisitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000404",
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

        client = APIClient()
        client.force_authenticate(user=chefe)
        response = client.post(
            reverse("requisicao-authorize", args=[requisicao.id]),
            {
                "itens": [
                    {
                        "item_id": item_a.id,
                        "quantidade_autorizada": "4.000",
                        "justificativa_autorizacao_parcial": "Saldo limitado",
                    },
                    {
                        "item_id": item_b.id,
                        "quantidade_autorizada": "0.000",
                        "justificativa_autorizacao_parcial": "Não prioritário",
                    },
                ]
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.AUTORIZADA
        assert response.data["chefe_autorizador"]["id"] == chefe.id
        assert response.data["itens"][0]["quantidade_autorizada"] == "4.000"
        requisicao.refresh_from_db()
        material_a.estoque.refresh_from_db()
        material_b.estoque.refresh_from_db()
        assert requisicao.eventos.filter(tipo_evento=TipoEvento.AUTORIZACAO_PARCIAL).exists()
        assert material_a.estoque.saldo_reservado == Decimal("4")
        assert material_b.estoque.saldo_reservado == Decimal("0")

    def test_authorize_partial_and_zero_sem_justificativa_falha(self):
        setor = self._criar_setor("Apoio Financeiro", "90024")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("10024", "Solicitante Apoio Financeiro", setor=setor)
        material_a = self._criar_material_com_estoque("001.001.020", saldo_fisico=Decimal("8"))
        material_b = self._criar_material_com_estoque("001.001.021", saldo_fisico=Decimal("8"))
        requisicao = Requisicao.objects.create(
            criador=requisitante,
            beneficiario=requisitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000406",
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

        client = APIClient()
        client.force_authenticate(user=chefe)
        response = client.post(
            reverse("requisicao-authorize", args=[requisicao.id]),
            {
                "itens": [
                    {
                        "item_id": item_a.id,
                        "quantidade_autorizada": "4.000",
                        "justificativa_autorizacao_parcial": "",
                    },
                    {
                        "item_id": item_b.id,
                        "quantidade_autorizada": "0.000",
                        "justificativa_autorizacao_parcial": "",
                    },
                ]
            },
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        assert response.data["error"]["details"]["itens"][0]["justificativa_autorizacao_parcial"]
        assert response.data["error"]["details"]["itens"][1]["justificativa_autorizacao_parcial"]

        requisicao.refresh_from_db()
        material_a.estoque.refresh_from_db()
        material_b.estoque.refresh_from_db()
        assert requisicao.status == StatusRequisicao.AGUARDANDO_AUTORIZACAO
        assert not requisicao.eventos.exists()
        assert material_a.estoque.saldo_reservado == Decimal("0")
        assert material_b.estoque.saldo_reservado == Decimal("0")

    def test_authorize_rejeita_status_invalido(self):
        setor = self._criar_setor("Qualidade", "90021")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("10022", "Solicitante Qualidade", setor=setor)
        material = self._criar_material_com_estoque("001.001.018")
        requisicao = Requisicao.objects.create(
            criador=requisitante,
            beneficiario=requisitante,
            setor_beneficiario=setor,
            status=StatusRequisicao.CANCELADA,
            numero_publico="REQ-2026-000404",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=chefe)
        response = client.post(
            reverse("requisicao-authorize", args=[requisicao.id]),
            self._payload_autorizacao(item_id=item.id, quantidade_autorizada="1.000"),
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"

    def test_refuse_sem_motivo_falha_validacao(self):
        setor = self._criar_setor("Fiscalizacao", "90022")
        chefe = setor.chefe_responsavel
        requisitante = self._criar_usuario("10023", "Solicitante Fiscalizacao", setor=setor)
        material = self._criar_material_com_estoque("001.001.019")
        requisicao = Requisicao.objects.create(
            criador=requisitante,
            beneficiario=requisitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000405",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=chefe)
        response = client.post(
            reverse("requisicao-refuse", args=[requisicao.id]), {}, format="json"
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"

    def test_fila_autorizacao_retorna_apenas_setor_do_chefe(self):
        setor_a = self._criar_setor("Administrativo", "90013")
        setor_b = self._criar_setor("Obras B", "90014")
        chefe_a = setor_a.chefe_responsavel
        solicitante_a = self._criar_usuario("10014", "Solicitante A", setor=setor_a)
        solicitante_b = self._criar_usuario("10015", "Solicitante B", setor=setor_b)
        material = self._criar_material_com_estoque("001.001.011")

        req_a = Requisicao.objects.create(
            criador=solicitante_a,
            beneficiario=solicitante_a,
            numero_publico="REQ-2026-000300",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        req_a.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )
        req_b = Requisicao.objects.create(
            criador=solicitante_b,
            beneficiario=solicitante_b,
            numero_publico="REQ-2026-000301",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T11:00:00Z",
        )
        req_b.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=chefe_a)
        response = client.get(reverse("requisicao-pending-approvals"))

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == req_a.id
        assert response.data["results"][0]["numero_publico"] == "REQ-2026-000300"
        assert response.data["results"][0]["total_itens"] == 1
        assert req_b.id not in [item["id"] for item in response.data["results"]]

    def test_fila_autorizacao_chefe_almoxarifado_retorna_apenas_setor_sob_responsabilidade(self):
        setor_almox = self._criar_setor(
            "Almoxarifado",
            "900141",
            papel=PapelChoices.CHEFE_ALMOXARIFADO,
        )
        setor_outro = self._criar_setor("Obras Aprova", "900142")
        chefe_almox = setor_almox.chefe_responsavel
        solicitante_almox = self._criar_usuario("100141", "Solicitante Almox", setor=setor_almox)
        solicitante_outro = self._criar_usuario("100142", "Solicitante Obras", setor=setor_outro)
        material = self._criar_material_com_estoque("001.001.112")

        req_almox = Requisicao.objects.create(
            criador=solicitante_almox,
            beneficiario=solicitante_almox,
            numero_publico="REQ-2026-000302",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T12:00:00Z",
        )
        req_almox.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )
        req_outro = Requisicao.objects.create(
            criador=solicitante_outro,
            beneficiario=solicitante_outro,
            numero_publico="REQ-2026-000303",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T13:00:00Z",
        )
        req_outro.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=chefe_almox)
        response = client.get(reverse("requisicao-pending-approvals"))

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == req_almox.id
        assert req_outro.id not in [item["id"] for item in response.data["results"]]

    def test_fila_autorizacao_bloqueia_papel_sem_permissao(self):
        setor = self._criar_setor("Gabinete", "90015")
        solicitante = self._criar_usuario("10016", "Solicitante Gabinete", setor=setor)

        client = APIClient()
        client.force_authenticate(user=solicitante)
        response = client.get(reverse("requisicao-pending-approvals"))

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_fila_atendimento_lista_requisicoes_autorizadas_para_almoxarifado(self):
        setor = self._criar_setor("Saneamento", "90030")
        almoxarife = self._criar_usuario(
            "10030",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        solicitante = self._criar_usuario("10031", "Solicitante Saneamento", setor=setor)
        material = self._criar_material_com_estoque(
            "001.001.030",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("2"),
        )
        autorizada = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000500",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        autorizada.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )
        pendente = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000501",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        pendente.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("1"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.get(reverse("requisicao-pending-fulfillments"))

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == autorizada.id
        assert response.data["results"][0]["numero_publico"] == "REQ-2026-000500"
        assert response.data["results"][0]["chefe_autorizador"] is None
        assert response.data["results"][0]["total_itens"] == 1
        assert pendente.id not in [item["id"] for item in response.data["results"]]

    def test_fila_atendimento_almoxarifado_ve_requisicoes_de_outros_setores(self):
        setor_almoxarifado = self._criar_setor("Almoxarifado", "90035")
        setor_obras = self._criar_setor("Obras", "90036")
        almoxarife = self._criar_usuario(
            "10038",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor_almoxarifado,
        )
        solicitante_obras = self._criar_usuario(
            "10039",
            "Solicitante Obras",
            setor=setor_obras,
        )
        material = self._criar_material_com_estoque(
            "001.001.034",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("2"),
        )
        autorizada_outro_setor = Requisicao.objects.create(
            criador=solicitante_obras,
            beneficiario=solicitante_obras,
            setor_beneficiario=setor_obras,
            numero_publico="REQ-2026-000505",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        autorizada_outro_setor.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.get(reverse("requisicao-pending-fulfillments"))

        # matriz-permissoes.md: Almoxarifado vê requisições de todos os setores
        # e fila de atendimento; não há isolamento por setor nesta fila.
        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == autorizada_outro_setor.id
        assert response.data["results"][0]["setor_beneficiario"]["id"] == setor_obras.id

    def test_fila_atendimento_bloqueia_papel_sem_permissao(self):
        setor = self._criar_setor("Apoio Operacional", "90031")
        solicitante = self._criar_usuario("10032", "Solicitante Apoio", setor=setor)

        client = APIClient()
        client.force_authenticate(user=solicitante)
        response = client.get(reverse("requisicao-pending-fulfillments"))

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_fila_atendimento_bloqueia_superuser(self):
        setor = self._criar_setor("Apoio Superuser", "90037")
        superuser = self._criar_usuario(
            "10042",
            "Superuser Apoio",
            setor=setor,
            is_superuser=True,
        )

        client = APIClient()
        client.force_authenticate(user=superuser)
        response = client.get(reverse("requisicao-pending-fulfillments"))

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_fila_atendimento_bloqueia_usuario_inativo(self):
        setor = self._criar_setor("Apoio Inativo", "90038")
        usuario_inativo = self._criar_usuario(
            "10043",
            "Usuario Inativo Apoio",
            setor=setor,
            is_active=False,
        )

        client = APIClient()
        client.force_authenticate(user=usuario_inativo)
        response = client.get(reverse("requisicao-pending-fulfillments"))

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_fulfill_atendimento_completo_baixa_estoque_e_registra_retirada(self):
        setor = self._criar_setor("Manutencao", "90032")
        solicitante = self._criar_usuario("10033", "Solicitante Manutencao", setor=setor)
        almoxarife = self._criar_usuario(
            "10034",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.001.031",
            saldo_fisico=Decimal("7"),
            saldo_reservado=Decimal("3"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000502",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
            quantidade_autorizada=Decimal("3"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {
                "observacao_atendimento": "Entrega no balcão",
            },
            format="json",
            **self._idempotency_header("fulfill-completo"),
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.PRONTA_PARA_RETIRADA
        assert response.data["responsavel_atendimento"]["id"] == almoxarife.id
        assert response.data["retirante_fisico"] == ""
        assert response.data["observacao_atendimento"] == "Entrega no balcão"
        assert response.data["itens"][0]["quantidade_entregue"] == "3.000"
        requisicao.refresh_from_db()
        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert requisicao.eventos.filter(tipo_evento=TipoEvento.ATENDIMENTO).exists()
        assert item.quantidade_entregue == Decimal("3")
        assert material.estoque.saldo_fisico == Decimal("7")
        assert material.estoque.saldo_reservado == Decimal("3")

        pickup_response = client.post(
            reverse("requisicao-pickup", args=[requisicao.id]),
            {"retirante_fisico": "Servidor Retirador"},
            format="json",
            **self._idempotency_header("pickup-completo-test-fulfill"),
        )
        assert pickup_response.status_code == 200
        material.estoque.refresh_from_db()
        assert material.estoque.saldo_fisico == Decimal("4")
        assert material.estoque.saldo_reservado == Decimal("0")

    def test_fulfill_sem_idempotency_key_retorna_validation_error(self):
        setor = self._criar_setor("Manutencao Sem Chave", "90132")
        solicitante = self._criar_usuario("10133", "Solicitante Sem Chave", setor=setor)
        almoxarife = self._criar_usuario(
            "10134",
            "Auxiliar Sem Chave",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.001.131",
            saldo_fisico=Decimal("7"),
            saldo_reservado=Decimal("3"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000602",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
            quantidade_autorizada=Decimal("3"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {},
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        assert "Idempotency-Key" in response.data["error"]["details"]
        requisicao.refresh_from_db()
        material.estoque.refresh_from_db()
        assert requisicao.status == StatusRequisicao.AUTORIZADA
        assert material.estoque.saldo_fisico == Decimal("7")
        assert material.estoque.saldo_reservado == Decimal("3")

    def test_fulfill_retry_mesma_chave_retorna_sucesso_sem_duplicar_efeitos(self):
        setor = self._criar_setor("Manutencao Idempotente", "90139")
        solicitante = self._criar_usuario("10144", "Solicitante Idempotente", setor=setor)
        almoxarife = self._criar_usuario(
            "10145",
            "Auxiliar Idempotente",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.001.136",
            saldo_fisico=Decimal("7"),
            saldo_reservado=Decimal("3"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000607",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
            quantidade_autorizada=Decimal("3"),
        )
        payload = {
            "itens": [
                {
                    "item_id": item.id,
                    "quantidade_entregue": "1.000",
                    "justificativa_atendimento_parcial": "Saldo físico divergente",
                }
            ],
        }

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        first_response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            payload,
            format="json",
            **self._idempotency_header("retry-sucesso"),
        )
        movement_count = MovimentacaoEstoque.objects.filter(requisicao=requisicao).count()
        timeline_count = EventoTimeline.objects.filter(requisicao=requisicao).count()
        notification_count = Notificacao.objects.filter(object_id=requisicao.id).count()

        retry_response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            payload,
            format="json",
            **self._idempotency_header("retry-sucesso"),
        )

        assert first_response.status_code == 200
        assert retry_response.status_code == 200
        assert retry_response.data["status"] == StatusRequisicao.PRONTA_PARA_RETIRADA_PARCIAL
        assert MovimentacaoEstoque.objects.filter(requisicao=requisicao).count() == movement_count
        assert EventoTimeline.objects.filter(requisicao=requisicao).count() == timeline_count
        assert Notificacao.objects.filter(object_id=requisicao.id).count() == notification_count
        material.estoque.refresh_from_db()
        assert material.estoque.saldo_fisico == Decimal("7")
        assert material.estoque.saldo_reservado == Decimal("3")

    def test_fulfill_mesma_chave_payload_diferente_retorna_domain_conflict_sem_efeitos(self):
        setor = self._criar_setor("Manutencao Chave Conflito", "90140")
        solicitante = self._criar_usuario("10146", "Solicitante Chave Conflito", setor=setor)
        almoxarife = self._criar_usuario(
            "10147",
            "Auxiliar Chave Conflito",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.001.137",
            saldo_fisico=Decimal("7"),
            saldo_reservado=Decimal("3"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000608",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
            quantidade_autorizada=Decimal("3"),
        )
        first_payload = {
            "itens": [
                {
                    "item_id": item.id,
                    "quantidade_entregue": "1.000",
                    "justificativa_atendimento_parcial": "Saldo físico divergente",
                }
            ],
        }
        conflicting_payload = {
            "itens": [
                {
                    "item_id": item.id,
                    "quantidade_entregue": "2.000",
                    "justificativa_atendimento_parcial": "Nova retirada",
                }
            ],
        }

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        first_response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            first_payload,
            format="json",
            **self._idempotency_header("payload-conflitante"),
        )
        movement_count = MovimentacaoEstoque.objects.filter(requisicao=requisicao).count()
        timeline_count = EventoTimeline.objects.filter(requisicao=requisicao).count()
        notification_count = Notificacao.objects.filter(object_id=requisicao.id).count()

        conflict_response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            conflicting_payload,
            format="json",
            **self._idempotency_header("payload-conflitante"),
        )

        assert first_response.status_code == 200
        assert conflict_response.status_code == 409
        assert conflict_response.data["error"]["code"] == "domain_conflict"
        assert MovimentacaoEstoque.objects.filter(requisicao=requisicao).count() == movement_count
        assert EventoTimeline.objects.filter(requisicao=requisicao).count() == timeline_count
        assert Notificacao.objects.filter(object_id=requisicao.id).count() == notification_count
        material.estoque.refresh_from_db()
        assert material.estoque.saldo_fisico == Decimal("7")
        assert material.estoque.saldo_reservado == Decimal("3")

    def test_fulfill_com_itens_registra_atendimento_parcial_e_libera_reserva(self):
        setor = self._criar_setor("Manutencao Parcial", "90039")
        solicitante = self._criar_usuario("10044", "Solicitante Manutencao Parcial", setor=setor)
        almoxarife = self._criar_usuario(
            "10045",
            "Auxiliar Almoxarifado Parcial",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.001.036",
            saldo_fisico=Decimal("7"),
            saldo_reservado=Decimal("3"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000507",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
            quantidade_autorizada=Decimal("3"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {
                "itens": [
                    {
                        "item_id": item.id,
                        "quantidade_entregue": "1.000",
                        "justificativa_atendimento_parcial": "Saldo físico divergente",
                    }
                ],
            },
            format="json",
            **self._idempotency_header("fulfill-parcial"),
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.PRONTA_PARA_RETIRADA_PARCIAL
        assert response.data["retirante_fisico"] == ""
        assert response.data["itens"][0]["quantidade_entregue"] == "1.000"
        assert (
            response.data["itens"][0]["justificativa_atendimento_parcial"]
            == "Saldo físico divergente"
        )
        requisicao.refresh_from_db()
        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert requisicao.eventos.filter(tipo_evento=TipoEvento.ATENDIMENTO_PARCIAL).exists()
        assert item.quantidade_entregue == Decimal("1")
        assert material.estoque.saldo_fisico == Decimal("7")
        assert material.estoque.saldo_reservado == Decimal("3")
        assert not MovimentacaoEstoque.objects.filter(
            requisicao=requisicao,
            tipo=TipoMovimentacao.SAIDA_POR_ATENDIMENTO,
        ).exists()

        pickup_response = client.post(
            reverse("requisicao-pickup", args=[requisicao.id]),
            {"retirante_fisico": "Servidor Retirador"},
            format="json",
            **self._idempotency_header("pickup-parcial-test-fulfill"),
        )
        assert pickup_response.status_code == 200
        material.estoque.refresh_from_db()
        assert material.estoque.saldo_fisico == Decimal("6")
        assert material.estoque.saldo_reservado == Decimal("0")
        assert MovimentacaoEstoque.objects.filter(
            requisicao=requisicao,
            tipo=TipoMovimentacao.SAIDA_POR_ATENDIMENTO,
            quantidade=Decimal("1"),
        ).exists()
        assert MovimentacaoEstoque.objects.filter(
            requisicao=requisicao,
            tipo=TipoMovimentacao.LIBERACAO_RESERVA_ATENDIMENTO,
            quantidade=Decimal("2"),
        ).exists()

    def test_fulfill_com_itens_multi_item_mistura_entrega_total_e_parcial(self):
        setor = self._criar_setor("Manutencao Multi Item", "90052")
        solicitante = self._criar_usuario("10062", "Solicitante Multi Item", setor=setor)
        almoxarife = self._criar_usuario(
            "10063",
            "Auxiliar Almoxarifado Multi Item",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material_total = self._criar_material_com_estoque(
            "001.001.052",
            saldo_fisico=Decimal("10"),
            saldo_reservado=Decimal("4"),
        )
        material_parcial = self._criar_material_com_estoque(
            "001.001.053",
            saldo_fisico=Decimal("10"),
            saldo_reservado=Decimal("5"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000512",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item_total = requisicao.itens.create(
            material=material_total,
            unidade_medida=material_total.unidade_medida,
            quantidade_solicitada=Decimal("4"),
            quantidade_autorizada=Decimal("4"),
        )
        item_parcial = requisicao.itens.create(
            material=material_parcial,
            unidade_medida=material_parcial.unidade_medida,
            quantidade_solicitada=Decimal("5"),
            quantidade_autorizada=Decimal("5"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {
                "itens": [
                    {"item_id": item_total.id, "quantidade_entregue": "4.000"},
                    {
                        "item_id": item_parcial.id,
                        "quantidade_entregue": "2.000",
                        "justificativa_atendimento_parcial": "Retirada parcial solicitada",
                    },
                ],
            },
            format="json",
            **self._idempotency_header("fulfill-multi-item"),
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.PRONTA_PARA_RETIRADA_PARCIAL
        requisicao.refresh_from_db()
        item_total.refresh_from_db()
        item_parcial.refresh_from_db()
        material_total.estoque.refresh_from_db()
        material_parcial.estoque.refresh_from_db()
        assert requisicao.eventos.filter(tipo_evento=TipoEvento.ATENDIMENTO_PARCIAL).exists()
        assert item_total.quantidade_entregue == Decimal("4")
        assert item_total.justificativa_atendimento_parcial == ""
        assert item_parcial.quantidade_entregue == Decimal("2")
        assert item_parcial.justificativa_atendimento_parcial == "Retirada parcial solicitada"
        assert material_total.estoque.saldo_fisico == Decimal("10")
        assert material_total.estoque.saldo_reservado == Decimal("4")
        assert material_parcial.estoque.saldo_fisico == Decimal("10")
        assert material_parcial.estoque.saldo_reservado == Decimal("5")
        assert not MovimentacaoEstoque.objects.filter(requisicao=requisicao).exists()

        pickup_response = client.post(
            reverse("requisicao-pickup", args=[requisicao.id]),
            {"retirante_fisico": "Servidor Retirador"},
            format="json",
            **self._idempotency_header("pickup-multi-item-test-fulfill"),
        )
        assert pickup_response.status_code == 200
        material_total.estoque.refresh_from_db()
        material_parcial.estoque.refresh_from_db()
        assert material_total.estoque.saldo_fisico == Decimal("6")
        assert material_total.estoque.saldo_reservado == Decimal("0")
        assert material_parcial.estoque.saldo_fisico == Decimal("8")
        assert material_parcial.estoque.saldo_reservado == Decimal("0")
        assert not MovimentacaoEstoque.objects.filter(
            requisicao=requisicao,
            item_requisicao=item_total,
            tipo=TipoMovimentacao.LIBERACAO_RESERVA_ATENDIMENTO,
        ).exists()
        assert MovimentacaoEstoque.objects.filter(
            requisicao=requisicao,
            item_requisicao=item_parcial,
            tipo=TipoMovimentacao.LIBERACAO_RESERVA_ATENDIMENTO,
            quantidade=Decimal("3"),
        ).exists()

    def test_fulfill_com_itens_rejeita_parcial_sem_justificativa(self):
        setor = self._criar_setor("Manutencao Sem Justificativa", "90040")
        solicitante = self._criar_usuario("10046", "Solicitante Sem Justificativa", setor=setor)
        almoxarife = self._criar_usuario(
            "10047",
            "Auxiliar Almoxarifado Sem Justificativa",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.001.037",
            saldo_fisico=Decimal("7"),
            saldo_reservado=Decimal("3"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000508",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
            quantidade_autorizada=Decimal("3"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {"itens": [{"item_id": item.id, "quantidade_entregue": "1.000"}]},
            format="json",
            **self._idempotency_header("fulfill-sem-justificativa"),
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"
        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert item.quantidade_entregue == Decimal("0")
        assert material.estoque.saldo_fisico == Decimal("7")
        assert material.estoque.saldo_reservado == Decimal("3")
        assert not MovimentacaoEstoque.objects.filter(requisicao=requisicao).exists()

    def test_fulfill_com_itens_rejeita_entrega_acima_do_autorizado(self):
        setor = self._criar_setor("Manutencao Excesso", "90041")
        solicitante = self._criar_usuario("10048", "Solicitante Excesso", setor=setor)
        almoxarife = self._criar_usuario(
            "10049",
            "Auxiliar Almoxarifado Excesso",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.001.038",
            saldo_fisico=Decimal("10"),
            saldo_reservado=Decimal("3"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000509",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
            quantidade_autorizada=Decimal("3"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {
                "itens": [
                    {
                        "item_id": item.id,
                        "quantidade_entregue": "5.000",
                        "justificativa_atendimento_parcial": "Erro de quantidade",
                    }
                ]
            },
            format="json",
            **self._idempotency_header("fulfill-excesso"),
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"
        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert item.quantidade_entregue == Decimal("0")
        assert material.estoque.saldo_fisico == Decimal("10")
        assert material.estoque.saldo_reservado == Decimal("3")
        assert not MovimentacaoEstoque.objects.filter(requisicao=requisicao).exists()

    def test_fulfill_todos_itens_zerados_rejeita_sem_efeitos(self):
        setor = self._criar_setor("Manutencao Zero Total", "90053")
        solicitante = self._criar_usuario("10064", "Solicitante Zero Total", setor=setor)
        almoxarife = self._criar_usuario(
            "10065",
            "Auxiliar Almoxarifado Zero Total",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.001.054",
            saldo_fisico=Decimal("7"),
            saldo_reservado=Decimal("3"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000513",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
            quantidade_autorizada=Decimal("3"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {
                "itens": [
                    {
                        "item_id": item.id,
                        "quantidade_entregue": "0.000",
                        "justificativa_atendimento_parcial": "Sem saldo físico",
                    }
                ]
            },
            format="json",
            **self._idempotency_header("fulfill-zero-total"),
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"
        item.refresh_from_db()
        material.estoque.refresh_from_db()
        assert item.quantidade_entregue == Decimal("0")
        assert material.estoque.saldo_fisico == Decimal("7")
        assert material.estoque.saldo_reservado == Decimal("3")
        assert not MovimentacaoEstoque.objects.filter(requisicao=requisicao).exists()

    def test_cancel_autorizada_sem_saldo_libera_reserva(self):
        setor = self._criar_setor("Cancelamento Operacional", "90055")
        solicitante = self._criar_usuario("10068", "Solicitante Cancelamento", setor=setor)
        almoxarife = self._criar_usuario(
            "10069",
            "Auxiliar Almoxarifado Cancelamento",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.001.057",
            saldo_fisico=Decimal("0"),
            saldo_reservado=Decimal("3"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000515",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
            quantidade_autorizada=Decimal("3"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-cancel", args=[requisicao.id]),
            {"motivo_cancelamento": "Saldo físico zerado no momento da retirada"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.CANCELADA
        assert response.data["motivo_cancelamento"] == "Saldo físico zerado no momento da retirada"
        requisicao.refresh_from_db()
        material.estoque.refresh_from_db()
        assert requisicao.responsavel_atendimento_id == almoxarife.id
        assert requisicao.eventos.filter(tipo_evento=TipoEvento.CANCELAMENTO).exists()
        assert material.estoque.saldo_fisico == Decimal("0")
        assert material.estoque.saldo_reservado == Decimal("0")
        assert MovimentacaoEstoque.objects.filter(
            requisicao=requisicao,
            item_requisicao=item,
            tipo=TipoMovimentacao.LIBERACAO_RESERVA_ATENDIMENTO,
            quantidade=Decimal("3"),
        ).exists()

    def test_cancel_autorizada_sem_saldo_permite_criador(self):
        setor = self._criar_setor("Cancelamento Criador", "90061")
        solicitante = self._criar_usuario("10077", "Solicitante Criador", setor=setor)
        material = self._criar_material_com_estoque(
            "001.001.062",
            saldo_fisico=Decimal("0"),
            saldo_reservado=Decimal("2"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000520",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=solicitante)
        response = client.post(
            reverse("requisicao-cancel", args=[requisicao.id]),
            {"motivo_cancelamento": "Sem saldo fisico para retirada"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.CANCELADA
        requisicao.refresh_from_db()
        material.estoque.refresh_from_db()
        assert requisicao.responsavel_atendimento_id == solicitante.id
        assert material.estoque.saldo_reservado == Decimal("0")

    def test_cancel_autorizada_sem_saldo_exige_motivo(self):
        setor = self._criar_setor("Cancelamento Motivo", "90056")
        solicitante = self._criar_usuario("10070", "Solicitante Motivo", setor=setor)
        almoxarife = self._criar_usuario(
            "10071",
            "Auxiliar Almoxarifado Motivo",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.001.058",
            saldo_fisico=Decimal("0"),
            saldo_reservado=Decimal("2"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000516",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-cancel", args=[requisicao.id]),
            {"motivo_cancelamento": "   "},
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        requisicao.refresh_from_db()
        material.estoque.refresh_from_db()
        assert requisicao.status == StatusRequisicao.AUTORIZADA
        assert material.estoque.saldo_reservado == Decimal("2")

    def test_cancel_autorizada_sem_saldo_bloqueia_quando_ainda_ha_saldo_fisico(self):
        setor = self._criar_setor("Cancelamento Parcial", "90057")
        solicitante = self._criar_usuario("10072", "Solicitante Parcial", setor=setor)
        almoxarife = self._criar_usuario(
            "10073",
            "Auxiliar Almoxarifado Parcial",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque(
            "001.001.059",
            saldo_fisico=Decimal("1"),
            saldo_reservado=Decimal("3"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000517",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
            quantidade_autorizada=Decimal("3"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-cancel", args=[requisicao.id]),
            {"motivo_cancelamento": "Tentativa de cancelar com saldo restante"},
            format="json",
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"
        requisicao.refresh_from_db()
        material.estoque.refresh_from_db()
        assert requisicao.status == StatusRequisicao.AUTORIZADA
        assert material.estoque.saldo_reservado == Decimal("3")

    def test_cancel_autorizada_sem_saldo_bloqueia_usuario_sem_permissao(self):
        setor = self._criar_setor("Cancelamento Permissao", "90058")
        solicitante = self._criar_usuario("10074", "Solicitante Permissao", setor=setor)
        chefe_setor = setor.chefe_responsavel
        material = self._criar_material_com_estoque(
            "001.001.060",
            saldo_fisico=Decimal("0"),
            saldo_reservado=Decimal("2"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000518",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=chefe_setor)
        response = client.post(
            reverse("requisicao-cancel", args=[requisicao.id]),
            {"motivo_cancelamento": "Sem saldo físico"},
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"
        requisicao.refresh_from_db()
        material.estoque.refresh_from_db()
        assert requisicao.status == StatusRequisicao.AUTORIZADA
        assert material.estoque.saldo_reservado == Decimal("2")

    def test_cancel_autorizada_sem_saldo_unauthenticated(self):
        setor = self._criar_setor("Cancelamento Auth", "90059")
        solicitante = self._criar_usuario("10075", "Solicitante Auth", setor=setor)
        material = self._criar_material_com_estoque(
            "001.001.061",
            saldo_fisico=Decimal("0"),
            saldo_reservado=Decimal("2"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000519",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        response = client.post(
            reverse("requisicao-cancel", args=[requisicao.id]),
            {"motivo_cancelamento": "Sem credenciais"},
            format="json",
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "not_authenticated"

    def test_cancel_autorizada_sem_saldo_not_found(self):
        setor = self._criar_setor("Cancelamento Not Found", "90060")
        almoxarife = self._criar_usuario(
            "10076",
            "Auxiliar Almoxarifado Not Found",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-cancel", args=[999999]),
            {"motivo_cancelamento": "Requisição inexistente"},
            format="json",
        )

        assert response.status_code == 404

    def test_fulfill_payload_incompleto_retorna_validation_error(self):
        setor = self._criar_setor("Manutencao Payload", "90054")
        solicitante = self._criar_usuario("10066", "Solicitante Payload", setor=setor)
        almoxarife = self._criar_usuario(
            "10067",
            "Auxiliar Almoxarifado Payload",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material_a = self._criar_material_com_estoque(
            "001.001.055",
            saldo_fisico=Decimal("7"),
            saldo_reservado=Decimal("2"),
        )
        material_b = self._criar_material_com_estoque(
            "001.001.056",
            saldo_fisico=Decimal("7"),
            saldo_reservado=Decimal("2"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000514",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item_a = requisicao.itens.create(
            material=material_a,
            unidade_medida=material_a.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )
        item_b = requisicao.itens.create(
            material=material_b,
            unidade_medida=material_b.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {"itens": [{"item_id": item_a.id, "quantidade_entregue": "2.000"}]},
            format="json",
            **self._idempotency_header("fulfill-payload-incompleto"),
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        assert response.data["error"]["details"]["item_ids"] == [str(item_b.id)]

    def test_fulfill_bloqueia_usuario_sem_permissao(self):
        setor = self._criar_setor("Controle", "90033")
        solicitante = self._criar_usuario("10035", "Solicitante Controle", setor=setor)
        material = self._criar_material_com_estoque(
            "001.001.032",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("2"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000503",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=solicitante)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {},
            **self._idempotency_header("fulfill-sem-permissao"),
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_fulfill_requisicao_fora_do_escopo_visivel_retorna_404(self):
        setor_origem = self._criar_setor("Controle Origem", "90042")
        setor_externo = self._criar_setor("Controle Externo", "90043")
        solicitante = self._criar_usuario("10050", "Solicitante Origem", setor=setor_origem)
        usuario_externo = self._criar_usuario("10051", "Solicitante Externo", setor=setor_externo)
        material = self._criar_material_com_estoque(
            "001.001.039",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("2"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor_origem,
            numero_publico="REQ-2026-000510",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=usuario_externo)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {},
            **self._idempotency_header("fulfill-fora-escopo"),
        )

        assert response.status_code == 404

    def test_fulfill_bloqueia_superuser(self):
        setor = self._criar_setor("Controle Superior", "90035")
        solicitante = self._criar_usuario("10038", "Solicitante Controle Superior", setor=setor)
        superuser = self._criar_usuario(
            "10039",
            "Superuser Controle",
            papel=PapelChoices.SOLICITANTE,
            setor=setor,
            is_superuser=True,
        )
        material = self._criar_material_com_estoque(
            "001.001.034",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("2"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000505",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        item = requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=superuser)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {"itens": [{"item_id": item.id, "quantidade_entregue": "2.000"}]},
            format="json",
            **self._idempotency_header("fulfill-superuser"),
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_fulfill_bloqueia_usuario_inativo(self):
        setor = self._criar_setor("Controle Inativo", "90036")
        solicitante = self._criar_usuario("10040", "Solicitante Controle Inativo", setor=setor)
        usuario_inativo = self._criar_usuario(
            "10041",
            "Usuario Inativo",
            setor=setor,
            is_active=False,
        )
        material = self._criar_material_com_estoque(
            "001.001.035",
            saldo_fisico=Decimal("5"),
            saldo_reservado=Decimal("2"),
        )
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000506",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=usuario_inativo)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {},
            **self._idempotency_header("fulfill-inativo"),
        )

        assert response.status_code == 404

    def test_fulfill_bloqueia_status_invalido(self):
        setor = self._criar_setor("Planejamento Campo", "90034")
        solicitante = self._criar_usuario("10036", "Solicitante Campo", setor=setor)
        almoxarife = self._criar_usuario(
            "10037",
            "Auxiliar Almoxarifado",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque("001.001.033")
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-000504",
            status=StatusRequisicao.AGUARDANDO_AUTORIZACAO,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-fulfill", args=[requisicao.id]),
            {},
            **self._idempotency_header("fulfill-status-invalido"),
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"

    def test_pickup_happy_path_pronta_para_retirada(self):
        setor = self._criar_setor("Retirada Setor", "88001")
        solicitante = self._criar_usuario("88002", "Solicitante Pickup", setor=setor)
        almoxarife = self._criar_usuario(
            "88003",
            "Almoxarife Pickup",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque("001.001.880", saldo_reservado=Decimal("2"))
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-880001",
            status=StatusRequisicao.PRONTA_PARA_RETIRADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
            data_finalizacao="2026-04-30T12:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
            quantidade_entregue=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-pickup", args=[requisicao.id]),
            {"retirante_fisico": "Servidor Retirador"},
            format="json",
            **self._idempotency_header("pickup-total"),
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.RETIRADA
        assert response.data["retirante_fisico"] == "Servidor Retirador"
        assert response.data["data_retirada"] is not None
        requisicao.refresh_from_db()
        assert requisicao.retirante_fisico == "Servidor Retirador"
        assert requisicao.data_retirada is not None
        assert requisicao.eventos.filter(tipo_evento=TipoEvento.RETIRADA).exists()
        material.estoque.refresh_from_db()
        assert material.estoque.saldo_fisico == Decimal("8")
        assert material.estoque.saldo_reservado == Decimal("0")

    def test_pickup_happy_path_pronta_para_retirada_parcial(self):
        setor = self._criar_setor("Retirada Parcial Setor", "88010")
        solicitante = self._criar_usuario("88011", "Solicitante Pickup Parcial", setor=setor)
        almoxarife = self._criar_usuario(
            "88012",
            "Almoxarife Pickup Parcial",
            papel=PapelChoices.CHEFE_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque("001.001.881", saldo_reservado=Decimal("3"))
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-880002",
            status=StatusRequisicao.PRONTA_PARA_RETIRADA_PARCIAL,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
            data_finalizacao="2026-04-30T12:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("3"),
            quantidade_autorizada=Decimal("3"),
            quantidade_entregue=Decimal("1"),
            justificativa_atendimento_parcial="Estoque insuficiente.",
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-pickup", args=[requisicao.id]),
            {"retirante_fisico": "Servidor Parcial"},
            format="json",
            **self._idempotency_header("pickup-parcial"),
        )

        assert response.status_code == 200
        assert response.data["status"] == StatusRequisicao.RETIRADA
        assert response.data["retirante_fisico"] == "Servidor Parcial"
        assert response.data["data_retirada"] is not None
        requisicao.refresh_from_db()
        assert requisicao.retirante_fisico == "Servidor Parcial"
        assert requisicao.data_retirada is not None
        assert requisicao.eventos.filter(tipo_evento=TipoEvento.RETIRADA).exists()
        material.estoque.refresh_from_db()
        assert material.estoque.saldo_fisico == Decimal("9")
        assert material.estoque.saldo_reservado == Decimal("0")

    def test_pickup_sem_idempotency_key_retorna_400(self):
        setor = self._criar_setor("Retirada Sem Chave", "88020")
        solicitante = self._criar_usuario("88021", "Solicitante Sem Chave", setor=setor)
        almoxarife = self._criar_usuario(
            "88022",
            "Almoxarife Sem Chave",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        _material = self._criar_material_com_estoque("001.001.882")
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-880003",
            status=StatusRequisicao.PRONTA_PARA_RETIRADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
            data_finalizacao="2026-04-30T12:00:00Z",
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-pickup", args=[requisicao.id]),
            {"retirante_fisico": "Servidor"},
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        assert "Idempotency-Key" in response.data["error"]["details"]

    def test_pickup_retirante_fisico_blank_retorna_400(self):
        setor = self._criar_setor("Retirada Blank", "88030")
        solicitante = self._criar_usuario("88031", "Solicitante Blank", setor=setor)
        almoxarife = self._criar_usuario(
            "88032",
            "Almoxarife Blank",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        _material = self._criar_material_com_estoque("001.001.883")
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-880004",
            status=StatusRequisicao.PRONTA_PARA_RETIRADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
            data_finalizacao="2026-04-30T12:00:00Z",
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-pickup", args=[requisicao.id]),
            {"retirante_fisico": ""},
            format="json",
            **self._idempotency_header("pickup-blank"),
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        assert "retirante_fisico" in response.data["error"]["details"]

    def test_pickup_bloqueia_papel_sem_permissao(self):
        setor = self._criar_setor("Retirada Perm", "88040")
        solicitante = self._criar_usuario("88041", "Solicitante Perm", setor=setor)
        _material = self._criar_material_com_estoque("001.001.884")
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-880005",
            status=StatusRequisicao.PRONTA_PARA_RETIRADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
            data_finalizacao="2026-04-30T12:00:00Z",
        )

        client = APIClient()
        client.force_authenticate(user=solicitante)
        response = client.post(
            reverse("requisicao-pickup", args=[requisicao.id]),
            {"retirante_fisico": "Indevido"},
            format="json",
            **self._idempotency_header("pickup-perm"),
        )

        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_pickup_bloqueia_status_invalido(self):
        setor = self._criar_setor("Retirada Status Invalido", "88050")
        solicitante = self._criar_usuario("88051", "Solicitante Status", setor=setor)
        almoxarife = self._criar_usuario(
            "88052",
            "Almoxarife Status",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        _material = self._criar_material_com_estoque("001.001.885")
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-880006",
            status=StatusRequisicao.AUTORIZADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        response = client.post(
            reverse("requisicao-pickup", args=[requisicao.id]),
            {"retirante_fisico": "Servidor"},
            format="json",
            **self._idempotency_header("pickup-status"),
        )

        assert response.status_code == 409
        assert response.data["error"]["code"] == "domain_conflict"

    def test_pickup_idempotency_same_key_same_payload_retorna_sucesso(self):
        setor = self._criar_setor("Retirada Idem Same", "88060")
        solicitante = self._criar_usuario("88061", "Solicitante Idem Same", setor=setor)
        almoxarife = self._criar_usuario(
            "88062",
            "Almoxarife Idem Same",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque("001.001.886", saldo_reservado=Decimal("2"))
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-880007",
            status=StatusRequisicao.PRONTA_PARA_RETIRADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
            data_finalizacao="2026-04-30T12:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
            quantidade_entregue=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        first_response = client.post(
            reverse("requisicao-pickup", args=[requisicao.id]),
            {"retirante_fisico": "Servidor Idem"},
            format="json",
            **self._idempotency_header("pickup-idem-same"),
        )
        movement_count = MovimentacaoEstoque.objects.filter(requisicao=requisicao).count()
        timeline_count = EventoTimeline.objects.filter(requisicao=requisicao).count()
        notification_count = Notificacao.objects.filter(object_id=requisicao.id).count()

        retry_response = client.post(
            reverse("requisicao-pickup", args=[requisicao.id]),
            {"retirante_fisico": "Servidor Idem"},
            format="json",
            **self._idempotency_header("pickup-idem-same"),
        )

        assert first_response.status_code == 200
        assert retry_response.status_code == 200
        assert retry_response.data["status"] == StatusRequisicao.RETIRADA
        assert MovimentacaoEstoque.objects.filter(requisicao=requisicao).count() == movement_count
        assert EventoTimeline.objects.filter(requisicao=requisicao).count() == timeline_count
        assert Notificacao.objects.filter(object_id=requisicao.id).count() == notification_count
        material.estoque.refresh_from_db()
        assert material.estoque.saldo_fisico == Decimal("8")
        assert material.estoque.saldo_reservado == Decimal("0")

    def test_pickup_idempotency_same_key_different_payload_retorna_409(self):
        setor = self._criar_setor("Retirada Idem Conflito", "88070")
        solicitante = self._criar_usuario("88071", "Solicitante Idem Conflito", setor=setor)
        almoxarife = self._criar_usuario(
            "88072",
            "Almoxarife Idem Conflito",
            papel=PapelChoices.AUXILIAR_ALMOXARIFADO,
            setor=setor,
        )
        material = self._criar_material_com_estoque("001.001.887", saldo_reservado=Decimal("2"))
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor,
            numero_publico="REQ-2026-880008",
            status=StatusRequisicao.PRONTA_PARA_RETIRADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
            data_finalizacao="2026-04-30T12:00:00Z",
        )
        requisicao.itens.create(
            material=material,
            unidade_medida=material.unidade_medida,
            quantidade_solicitada=Decimal("2"),
            quantidade_autorizada=Decimal("2"),
            quantidade_entregue=Decimal("2"),
        )

        client = APIClient()
        client.force_authenticate(user=almoxarife)
        first_response = client.post(
            reverse("requisicao-pickup", args=[requisicao.id]),
            {"retirante_fisico": "Servidor Original"},
            format="json",
            **self._idempotency_header("pickup-idem-conflito"),
        )
        movement_count = MovimentacaoEstoque.objects.filter(requisicao=requisicao).count()
        timeline_count = EventoTimeline.objects.filter(requisicao=requisicao).count()
        notification_count = Notificacao.objects.filter(object_id=requisicao.id).count()

        conflict_response = client.post(
            reverse("requisicao-pickup", args=[requisicao.id]),
            {"retirante_fisico": "Servidor Diferente"},
            format="json",
            **self._idempotency_header("pickup-idem-conflito"),
        )

        assert first_response.status_code == 200
        assert conflict_response.status_code == 409
        assert conflict_response.data["error"]["code"] == "domain_conflict"
        assert MovimentacaoEstoque.objects.filter(requisicao=requisicao).count() == movement_count
        assert EventoTimeline.objects.filter(requisicao=requisicao).count() == timeline_count
        assert Notificacao.objects.filter(object_id=requisicao.id).count() == notification_count
        material.estoque.refresh_from_db()
        assert material.estoque.saldo_fisico == Decimal("8")
        assert material.estoque.saldo_reservado == Decimal("0")

    def test_pickup_retorna_404_quando_fora_do_escopo(self):
        setor_req = self._criar_setor("Retirada Escopo Req", "88080")
        solicitante = self._criar_usuario("88081", "Solicitante Escopo", setor=setor_req)
        requisicao = Requisicao.objects.create(
            criador=solicitante,
            beneficiario=solicitante,
            setor_beneficiario=setor_req,
            numero_publico="REQ-2026-880009",
            status=StatusRequisicao.PRONTA_PARA_RETIRADA,
            data_envio_autorizacao="2026-04-30T10:00:00Z",
            data_autorizacao_ou_recusa="2026-04-30T11:00:00Z",
            data_finalizacao="2026-04-30T12:00:00Z",
        )

        setor_outro = self._criar_setor("Outro Setor Escopo", "88090")
        usuario_outro_setor = self._criar_usuario(
            "88091",
            "Solicitante Outro Setor",
            papel=PapelChoices.SOLICITANTE,
            setor=setor_outro,
        )

        client = APIClient()
        client.force_authenticate(user=usuario_outro_setor)
        response = client.post(
            reverse("requisicao-pickup", args=[requisicao.id]),
            {"retirante_fisico": "Invasor"},
            format="json",
            **self._idempotency_header("pickup-escopo"),
        )

        assert response.status_code == 404
        assert response.data["error"]["code"] == "not_found"
