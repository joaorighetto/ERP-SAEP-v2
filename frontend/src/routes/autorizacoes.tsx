import { createFileRoute } from "@tanstack/react-router";

import { NeutralRoutePage } from "../shared/ui/neutral-route";

export const Route = createFileRoute("/autorizacoes")({
  component: AutorizacoesPage,
});

function AutorizacoesPage() {
  return <NeutralRoutePage title="Fila de autorizações" />;
}
