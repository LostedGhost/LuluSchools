import { Link } from "react-router-dom";
import { Btn, EmptyState } from "../components/ui";
import { Compass } from "lucide-react";

export function NotFoundPage() {
  return (
    <div className="page-content" style={{ display: "flex", justifyContent: "center", paddingTop: "80px" }}>
      <EmptyState
        icon={<Compass size={28} />}
        title="Page introuvable"
        desc="Cette page n'existe pas ou plus. Vérifiez l'adresse, ou revenez à l'accueil."
        action={
          <Link to="/">
            <Btn variant="primary" size="sm">
              Retour à l'accueil
            </Btn>
          </Link>
        }
      />
    </div>
  );
}
