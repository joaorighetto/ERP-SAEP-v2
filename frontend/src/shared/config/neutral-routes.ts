export const NEUTRAL_ROUTE_MESSAGE = "Interface do piloto em reconstrucao.";

export type NeutralRoute = {
  title: string;
  href: string;
};

export const neutralRoutes = [
  { title: "Login", href: "/login" },
  { title: "Minhas requisições", href: "/minhas-requisicoes" },
  { title: "Nova requisição", href: "/requisicoes/nova" },
  { title: "Detalhe da requisição", href: "/requisicoes/1" },
  { title: "Fila de autorizações", href: "/autorizacoes" },
  { title: "Fila de atendimento", href: "/atendimentos" },
  { title: "Papel desconhecido", href: "/unknown-role" },
] as const satisfies readonly NeutralRoute[];
