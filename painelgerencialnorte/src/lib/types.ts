export type UserRole =
  | "admin_master"
  | "admin_empresa"
  | "gestor"
  | "consultor"
  | "visualizador";

export type MetricStatus = "ok" | "warning" | "danger" | "muted";

export type DashboardMetric = {
  label: string;
  value: string;
  detail?: string;
  status?: MetricStatus;
};

export type BaseStatus = {
  name: string;
  type: string;
  updatedAt: string;
  source: string;
  status: "ok" | "missing" | "invalid";
};

export type NavigationItem = {
  label: string;
  href: string;
  description: string;
};

export type NavigationGroup = {
  label: string;
  items: NavigationItem[];
};

export type DashboardSnapshot = {
  available: boolean;
  empty?: boolean;
  apiConnected?: boolean;
  supabaseConnected?: boolean;
  metrics: DashboardMetric[];
  operational: DashboardMetric[];
  bases: BaseStatus[];
  message?: string;
};

