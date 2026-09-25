import { api } from "./client";
import type { ClasseOut, EtablissementOut } from "../types/api";

export function listerEtablissements() {
  return api.get<EtablissementOut[]>("/etablissements");
}

export function listerClasses(etablissementId: string) {
  return api.get<ClasseOut[]>(`/etablissements/${etablissementId}/classes`);
}
