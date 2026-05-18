import { Link, createFileRoute } from "@tanstack/react-router";

import { neutralRoutes } from "../shared/config/neutral-routes";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  return (
    <main className="neutral-page">
      <section className="neutral-panel" aria-labelledby="route-index-title">
        <p className="neutral-eyebrow">SPA do piloto</p>
        <h1 id="route-index-title">Índice técnico</h1>
        <p>Interface do piloto em reconstrucao.</p>
        <nav aria-label="Rotas preservadas">
          <ul className="neutral-route-list">
            {neutralRoutes.map((route) => (
              <li key={route.href}>
                {"params" in route ? (
                  <Link className="neutral-link" to={route.to} params={route.params}>
                    {route.title}
                  </Link>
                ) : (
                  <Link className="neutral-link" to={route.to}>
                    {route.title}
                  </Link>
                )}
              </li>
            ))}
          </ul>
        </nav>
      </section>
    </main>
  );
}
