import type { NavigationGroup } from "./types";

export const navigationGroups: NavigationGroup[] = [
  {
    label: "Gestao Comercial",
    items: [
      { label: "Dashboard", href: "/dashboard", description: "Visao geral, metas e status operacional" },
      { label: "Consultores", href: "/consultores", description: "Ranking, cards e carteira por vendedor" },
      { label: "Clientes", href: "/clientes", description: "Contatos, status comercial e exportacao" },
      { label: "SIP", href: "/sip", description: "Cadastro, metas, recados e link publico" },
      { label: "Foco Semanal", href: "/foco-semanal", description: "Acoes por produto, molecula e consultor" },
      { label: "Acoes Promocionais", href: "/acoes-promocionais", description: "Antes, durante e crescimento das campanhas" },
      { label: "Produtos / Mix", href: "/produtos-mix", description: "Auditoria de mix e produtos fora do template" },
      { label: "Oportunidades", href: "/oportunidades", description: "Clientes e produtos para priorizar" },
      { label: "Mercado Farma", href: "/mercado-farma", description: "Precos, estoque, UF e extracoes" },
      { label: "Desafio", href: "/desafio-gigantes", description: "Campanha Desafio de Gigantes" },
      { label: "Historico", href: "/historico", description: "Metas e realizados de meses anteriores" },
    ],
  },
  {
    label: "Bases",
    items: [
      { label: "Importacao", href: "/importacao", description: "Uploads, backups e diagnostico" },
      { label: "Templates", href: "/templates", description: "Modelos oficiais das bases" },
    ],
  },
  {
    label: "Configuracoes",
    items: [
      { label: "Configuracoes", href: "/configuracoes", description: "Empresa, usuarios, metas e logs" },
    ],
  },
];

