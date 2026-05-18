import { createFileRoute } from "@tanstack/react-router";

import { NeutralRoutePage } from "../shared/ui/neutral-route";

export const Route = createFileRoute("/minhas-requisicoes")({
  component: MinhasRequisicoesPage,
});

function MinhasRequisicoesPage() {
  return <NeutralRoutePage title="Minhas requisições" />;
}
