import { useAdminEtab } from "../../admin/AdminEtabContext";
import { ATraiterPage } from "./ATraiterPage";

export function ATraiterEtablissementPage() {
  return <ATraiterPage etablissement={useAdminEtab()} />;
}
