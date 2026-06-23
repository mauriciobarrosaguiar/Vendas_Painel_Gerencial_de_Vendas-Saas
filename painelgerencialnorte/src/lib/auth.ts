import type { UserRole } from "./types";

export type SessionUser = {
  id: string;
  email: string;
  nome: string;
  empresaId: string;
  empresaNome: string;
  papel: UserRole;
};

export function canManageBases(role: UserRole) {
  return role === "admin_master" || role === "admin_empresa" || role === "gestor";
}

export function canManageUsers(role: UserRole) {
  return role === "admin_master" || role === "admin_empresa";
}

