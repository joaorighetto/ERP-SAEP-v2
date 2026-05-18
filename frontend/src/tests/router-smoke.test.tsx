import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  RouterProvider,
  createMemoryHistory,
  createRouter,
} from "@tanstack/react-router";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { routeTree } from "../routeTree.gen";
import { NEUTRAL_ROUTE_MESSAGE, neutralRoutes } from "../shared/config/neutral-routes";

function renderRoute(initialLocation: string) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  const router = createRouter({
    routeTree,
    history: createMemoryHistory({ initialEntries: [initialLocation] }),
    context: { queryClient },
  });
  const view = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );

  return { ...view, queryClient };
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("neutral frontend reset routes", () => {
  it("renders the technical route index", async () => {
    const { queryClient } = renderRoute("/");

    expect(await screen.findByRole("heading", { name: "Índice técnico" })).toBeVisible();
    expect(screen.getByText(NEUTRAL_ROUTE_MESSAGE)).toBeVisible();

    for (const route of neutralRoutes) {
      expect(screen.getByRole("link", { name: route.title })).toBeVisible();
    }

    queryClient.clear();
  });

  for (const route of neutralRoutes) {
    it(`renders neutral contract for ${route.href}`, async () => {
      const { queryClient } = renderRoute(route.href);

      expect(await screen.findByRole("heading", { name: route.title })).toBeVisible();
      expect(screen.getByText(NEUTRAL_ROUTE_MESSAGE)).toBeVisible();

      queryClient.clear();
    });
  }
});
