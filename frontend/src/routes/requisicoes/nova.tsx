import { createFileRoute } from "@tanstack/react-router";

import { NeutralRoutePage } from "../../shared/ui/neutral-route";

export const Route = createFileRoute("/requisicoes/nova")({
  component: NovaRequisicaoPage,
});

function NovaRequisicaoPage() {
  return <NeutralRoutePage title="Nova requisição" />;
}
