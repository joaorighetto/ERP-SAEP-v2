import { createFileRoute } from "@tanstack/react-router";

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
                <a className="neutral-link" href={route.href}>
                  {route.title}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </section>
    </main>
  );
}
