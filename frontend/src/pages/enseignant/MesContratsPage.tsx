import { useEffect, useState } from "react";
import { mesContrats, obtenirLienSignatureContrat, signerContrat } from "../../api/recrutement";
import { messageErreur } from "../../api/client";
import type { ContratOut } from "../../types/api";
import { Badge, Card, ErrorBanner, SectionHead, Btn, EmptyState } from "../../components/ui";
import { SignatureCanvas } from "../../components/SignatureCanvas";
import { ExternalLink, PenLine } from "lucide-react";

export function MesContratsPage() {
  const [contrats, setContrats] = useState<ContratOut[]>([]);
  const [contratASigner, setContratASigner] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [lienEnCoursId, setLienEnCoursId] = useState<string | null>(null);

  const voirSignature = async (contratId: string) => {
    setLienEnCoursId(contratId);
    setErreur(null);
    try {
      const res = await obtenirLienSignatureContrat(contratId);
      window.open(res.data.url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'ouvrir la signature pour le moment."));
    } finally {
      setLienEnCoursId(null);
    }
  };

  const charger = () => {
    mesContrats()
      .then((res) => setContrats(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  };

  useEffect(charger, []);

  const signer = async (contratId: string, blob: Blob) => {
    setEnCours(true);
    setErreur(null);
    try {
      await signerContrat(contratId, blob);
      setContratASigner(null);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  };

  return (
    <div className="page-content">
      <SectionHead 
        title="Mes contrats"
        desc="Gérez vos contrats et signatures avec les différents établissements." 
      />
      
      <ErrorBanner>{erreur}</ErrorBanner>
      
      {contrats.length === 0 ? (
        <EmptyState 
          title="Aucun contrat" 
          desc="Vous n'avez pas de contrats pour le moment." 
        />
      ) : (
        <div className="grid-2">
          {contrats.map((c, idx) => (
            <Card key={c.id} className={`anim-slide-up delay-${(idx % 5) + 1} flex flex-col`}>
              <div className="mb-4 flex items-center justify-between border-b pb-4" style={{ borderColor: 'var(--border)' }}>
                <div>
                  <h3 className="text-title text-ink">Contrat Enseignant</h3>
                  <p className="text-sm text-ink-soft">Jusqu'au {c.date_fin}</p>
                </div>
                <Badge tone={c.statut === "signe" ? "success" : "pending"}>
                  {c.statut === "signe" ? "Signé" : "En attente"}
                </Badge>
              </div>
              
              <div className="mb-6 flex-1">
                <p className="text-sm text-ink-soft bg-slate-50 p-3 rounded-lg" style={{ backgroundColor: 'var(--surface-2)' }}>
                  {c.syllabus}
                </p>
              </div>
              
              <div className="mt-auto border-t pt-4" style={{ borderColor: 'var(--border)' }}>
                {c.statut === "en_attente_signature" ? (
                  contratASigner === c.id ? (
                    <div className="space-y-3">
                      <p className="text-sm font-medium text-ink">Signez ci-dessous :</p>
                      <SignatureCanvas enCours={enCours} onSigner={(blob) => signer(c.id, blob)} />
                      <Btn variant="ghost" size="sm" onClick={() => setContratASigner(null)} disabled={enCours}>
                        Annuler
                      </Btn>
                    </div>
                  ) : (
                    <div className="flex gap-2">
                      <Btn variant="reward" onClick={() => setContratASigner(c.id)} className="w-full" leftIcon={<PenLine size={16} />}>
                        Signer ce contrat
                      </Btn>
                    </div>
                  )
                ) : (
                  <div className="flex justify-end gap-2">
                    <Btn
                      variant="outline"
                      size="sm"
                      loading={lienEnCoursId === c.id}
                      onClick={() => voirSignature(c.id)}
                      rightIcon={<ExternalLink size={14} />}
                    >
                      Voir ma signature
                    </Btn>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
