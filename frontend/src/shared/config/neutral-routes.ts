export const NEUTRAL_ROUTE_MESSAGE = "Interface do piloto em reconstrucao.";

export type NeutralRoute = {
  title: string;
  href: string;
} & (
  | {
      to:
        | "/login"
        | "/minhas-requisicoes"
        | "/requisicoes/nova"
        | "/autorizacoes"
        | "/atendimentos"
        | "/unknown-role";
      params?: never;
    }
  | {
      to: "/requisicoes/$id";
      params: { id: string };
    }
);

export const neutralRoutes = [
  { title: "Login", href: "/login", to: "/login" },
  {
    title: "Minhas requisições",
    href: "/minhas-requisicoes",
    to: "/minhas-requisicoes",
  },
  { title: "Nova requisição", href: "/requisicoes/nova", to: "/requisicoes/nova" },
  {
    title: "Detalhe da requisição",
    href: "/requisicoes/1",
    to: "/requisicoes/$id",
    params: { id: "1" },
  },
  { title: "Fila de autorizações", href: "/autorizacoes", to: "/autorizacoes" },
  { title: "Fila de atendimento", href: "/atendimentos", to: "/atendimentos" },
  { title: "Papel desconhecido", href: "/unknown-role", to: "/unknown-role" },
] as const satisfies readonly NeutralRoute[];
