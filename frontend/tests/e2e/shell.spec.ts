import { expect, test } from "@playwright/test";

const neutralRoutes = [
  { title: "Login", path: "/login" },
  { title: "Minhas requisições", path: "/minhas-requisicoes" },
  { title: "Nova requisição", path: "/requisicoes/nova" },
  { title: "Detalhe da requisição", path: "/requisicoes/1" },
  { title: "Fila de autorizações", path: "/autorizacoes" },
  { title: "Fila de atendimento", path: "/atendimentos" },
  { title: "Papel desconhecido", path: "/unknown-role" },
] as const;

test("renders technical route index with preserved routes @qa-final", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Índice técnico" })).toBeVisible();
  await expect(page.getByText("Interface do piloto em reconstrucao.")).toBeVisible();

  for (const route of neutralRoutes) {
    await expect(page.getByRole("link", { name: route.title })).toBeVisible();
  }
});

for (const route of neutralRoutes) {
  test(`renders neutral contract for ${route.path} @qa-final`, async ({ page }) => {
    await page.goto(route.path);

    await expect(page.getByRole("heading", { name: route.title })).toBeVisible();
    await expect(page.getByText("Interface do piloto em reconstrucao.")).toBeVisible();
  });
}
