import { createFileRoute } from "@tanstack/react-router";

import { NeutralRoutePage } from "../../shared/ui/neutral-route";

export const Route = createFileRoute("/requisicoes/$id")({
  component: DetalheRequisicaoPage,
});

function DetalheRequisicaoPage() {
  return <NeutralRoutePage title="Detalhe da requisição" />;
}
