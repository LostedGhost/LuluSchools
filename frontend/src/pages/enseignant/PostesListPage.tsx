import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listerEtablissements } from "../../api/etablissements";
import { listerPostes } from "../../api/recrutement";
import { messageErreur } from "../../api/client";
import type { EtablissementOut, PosteOut } from "../../types/api";
import { Badge, Card, ErrorBanner, SectionHead, EmptyState, Field, Select, Btn } from "../../components/ui";

export function PostesListPage() {
  const [etablissements, setEtablissements] = useState<EtablissementOut[]>([]);
  const [etablissementId, setEtablissementId] = useState("");
  const [postes, setPostes] = useState<PosteOut[]>([]);
  const [erreur, setErreur] = useState<string | null>(null);
  const [filterStatut, setFilterStatut] = useState<"Tous" | "ouvert" | "ferme">("Tous");

  useEffect(() => {
    listerEtablissements()
      .then((res) => setEtablissements(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  }, []);

  useEffect(() => {
    if (!etablissementId) {
      setPostes([]);
      return;
    }
    listerPostes(etablissementId)
      .then((res) => setPostes(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  }, [etablissementId]);

  const filteredPostes = postes.filter(p => filterStatut === "Tous" ? true : p.statut === filterStatut);

  return (
    <div className="page-content">
      <div className="flex items-center justify-between mb-8">
        <SectionHead 
          title="Postes ouverts"
          desc="Découvrez les opportunités d'enseignement et postulez." 
        />
        <Badge tone="magic">{postes.length} postes</Badge>
      </div>

      <ErrorBanner>{erreur}</ErrorBanner>

      <Card className="mb-8 card-soft">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex-1 min-w-[250px]">
            <Field label="Établissement">
              <Select
                value={etablissementId}
                onChange={(e) => setEtablissementId(e.target.value)}
              >
                <option value="">Choisir un établissement...</option>
                {etablissements.map((etab) => (
                  <option key={etab.id} value={etab.id}>
                    {etab.nom} ({etab.code_etablissement})
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <div className="flex gap-2 items-end pb-1">
            <Btn 
              variant={filterStatut === "Tous" ? "primary" : "ghost"} 
              size="sm" 
              onClick={() => setFilterStatut("Tous")}
            >
              Tous
            </Btn>
            <Btn 
              variant={filterStatut === "ouvert" ? "primary" : "ghost"} 
              size="sm" 
              onClick={() => setFilterStatut("ouvert")}
            >
              Ouverts
            </Btn>
            <Btn 
              variant={filterStatut === "ferme" ? "primary" : "ghost"} 
              size="sm" 
              onClick={() => setFilterStatut("ferme")}
            >
              Fermés
            </Btn>
          </div>
        </div>
      </Card>

      {!etablissementId ? (
        <EmptyState 
          title="Sélectionnez un établissement" 
          desc="Veuillez choisir un établissement pour voir les postes disponibles." 
        />
      ) : filteredPostes.length === 0 ? (
        <EmptyState 
          title="Aucun poste" 
          desc="Aucun poste ne correspond à vos critères." 
        />
      ) : (
        <div className="grid-2">
          {filteredPostes.map((poste, idx) => (
            <Card key={poste.id} className={`anim-float-in delay-${(idx % 5) + 1} flex flex-col justify-between`}>
              <div>
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-title text-ink mb-1">{poste.titre}</h3>
                    <p className="text-sm text-ink-soft">
                      Documents requis : {poste.criteres.map((c) => c.type_document).join(", ")}
                    </p>
                  </div>
                  <Badge tone={poste.statut === "ouvert" ? "success" : "neutral"}>
                    {poste.statut}
                  </Badge>
                </div>
              </div>
              <div className="mt-6 flex items-center justify-end gap-3 pt-4 border-t" style={{ borderColor: 'var(--border)' }}>
                <Link to={poste.statut === "ouvert" ? `/enseignant/postes/${poste.id}/postuler` : "#"}>
                  <Btn variant="primary" disabled={poste.statut !== "ouvert"}>
                    Postuler
                  </Btn>
                </Link>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
