import { createFileRoute } from "@tanstack/react-router";

import { NeutralRoutePage } from "../shared/ui/neutral-route";

export const Route = createFileRoute("/unknown-role")({
  component: UnknownRolePage,
});

function UnknownRolePage() {
  return <NeutralRoutePage title="Papel desconhecido" />;
}
