export type BaseTemplate = {
  typeBase: string;
  title: string;
  description: string;
  arquivo: string;
  aba: string;
  colunas: string[];
  modelUrl: string;
};

const bussolaColumns = ["status_pedido", "nota_fiscal", "pedido_id", "data_do_pedido", "data_de_faturamento", "canal_de_vendas", "cod_representante", "representante", "cnpj_pdv", "centro_distribuicao", "uf_centro_distribuicao", "ean", "sku_produto", "produto", "quantidade_solicitada", "quantidade_atendida", "quantidade_faturada", "quantidade_cancelada", "preco_unitario_com_imposto", "preco_unitario_sem_imposto", "desconto_digitado", "desconto_aplicado_em_nota", "valor_total_solicitado_com_imposto", "valor_total_solicitado_sem_imposto", "total_atendido_sem_imposto", "total_atendido_com_imposto", "valor_faturado"];

export const baseTemplates: BaseTemplate[] = [
  { typeBase: "bussola", title: "Bussola", description: "Pedidos exportados da Bussola", arquivo: "modelo_bussola.xlsx", aba: "Pedidos", modelUrl: "/modelos/modelo_bussola.xlsx", colunas: bussolaColumns },
  { typeBase: "painel", title: "Painel clientes", description: "Base de clientes Equipe Norte", arquivo: "modelo_painel_clientes.xlsx", aba: "Planilha1", modelUrl: "/modelos/modelo_painel_clientes.xlsx", colunas: ["cnpj", "nome_pdv", "cidade", "uf", "situacao", "grupo_economico", "rede_associacao", "bandeira", "nome_gd", "nome_rep", "setor_rep", "foco_pex", "positivacao", "proprietario_diretor", "comprador_gerente_de_compras", "cargo", "celular", "email"] },
  { typeBase: "produtos_mix", title: "Produtos / Mix", description: "Classificacao de produtos", arquivo: "modelo_produtos_mix.xlsx", aba: "Produtos", modelUrl: "/modelos/modelo_produtos_mix.xlsx", colunas: ["ean", "produto", "tipo_mix"] },
  { typeBase: "acoes", title: "Acoes promocionais", description: "Campanhas e descontos", arquivo: "modelo_acoes_promocionais.xlsx", aba: "Acoes", modelUrl: "/modelos/modelo_acoes_promocionais.xlsx", colunas: ["campanha", "produto", "ean", "tipo_mix", "distribuidora", "desconto", "data_inicio", "data_fim", "consultor", "observacao", "status"] },
  { typeBase: "mercado_farma", title: "Mercado Farma", description: "Precos e estoque", arquivo: "modelo_mercado_farma.xlsx", aba: "Mercado Farma", modelUrl: "/modelos/modelo_mercado_farma.xlsx", colunas: ["consultor", "uf", "cnpj_referencia", "ean", "produto", "distribuidora", "estoque", "desconto", "pf_dist", "pf_fabrica", "preco_com_imposto", "preco_sem_imposto", "data_atualizacao", "status", "erro"] },
  { typeBase: "bussola_historico", title: "Historico Bussola", description: "Historico de pedidos", arquivo: "modelo_bussola_historico.xlsx", aba: "Pedidos", modelUrl: "/modelos/modelo_bussola_historico.xlsx", colunas: bussolaColumns },
];

export function getTemplate(typeBase: string): BaseTemplate | undefined {
  return baseTemplates.find((item) => item.typeBase === typeBase);
}
