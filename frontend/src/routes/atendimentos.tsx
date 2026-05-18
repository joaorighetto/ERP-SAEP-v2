import { createFileRoute } from "@tanstack/react-router";

import { NeutralRoutePage } from "../shared/ui/neutral-route";

export const Route = createFileRoute("/atendimentos")({
  component: AtendimentosPage,
});

function AtendimentosPage() {
  return <NeutralRoutePage title="Fila de atendimento" />;
}
