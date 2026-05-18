import { Link } from "@tanstack/react-router";

import { NEUTRAL_ROUTE_MESSAGE } from "../config/neutral-routes";

type NeutralRoutePageProps = {
  title: string;
};

export function NeutralRoutePage({ title }: NeutralRoutePageProps) {
  return (
    <main className="neutral-page">
      <section className="neutral-panel" aria-labelledby="route-title">
        <p className="neutral-eyebrow">SPA do piloto</p>
        <h1 id="route-title">{title}</h1>
        <p>{NEUTRAL_ROUTE_MESSAGE}</p>
        <Link className="neutral-link" to="/">
          Voltar ao índice técnico
        </Link>
      </section>
    </main>
  );
}
