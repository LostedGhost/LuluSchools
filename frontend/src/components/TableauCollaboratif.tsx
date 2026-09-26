import { useCallback, useEffect, useRef, useState } from "react";
import {
  accorderDemandeCraie,
  ajouterPanneauTableau,
  ajouterTraitTableau,
  demanderLaCraie,
  effacerPanneauTableau,
  listerDemandesCraie,
  obtenirEtatTableau,
  preterLaCraie,
  refuserDemandeCraie,
  revoquerLaCraie,
} from "../api/cours_direct";
import { messageErreur } from "../api/client";
import type {
  DemandeCraieOut,
  EtatTableauOut,
  EvenementTempsReelSessionLive,
  PanneauAvecTraitsOut,
  PermissionEcritureOut,
  TraitTableauOut,
} from "../types/api";
import { Btn, ErrorBanner, TextInput } from "./ui";
import { ChevronLeft, ChevronRight, Eraser, PenLine, Plus, Type, X } from "lucide-react";

/**
 * Tableau de classe collaboratif ("craie/chiffon") - voir le cahier des charges du
 * volet Professeur, §3.1. Le canvas travaille en coordonnees NORMALISEES (0..1),
 * converties a l'affichage/saisie selon la taille reelle du <canvas> - ce qui rend le
 * tableau independant de la resolution de chaque participant (essentiel : professeur et
 * eleves n'ont jamais le meme ecran).
 */
export function TableauCollaboratif({
  sessionId,
  estOrganisateur,
  monUtilisateurId,
  canal,
}: {
  sessionId: string;
  estOrganisateur: boolean;
  monUtilisateurId: string;
  /** Canal WebSocket partage avec le reste de la salle (chat inclus) - voir SalleLivePage. */
  canal: WebSocket | null;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [etat, setEtat] = useState<EtatTableauOut | null>(null);
  const [panneauIndex, setPanneauIndex] = useState(0);
  const [outil, setOutil] = useState<"craie" | "texte">("craie");
  const [erreur, setErreur] = useState<string | null>(null);
  const [demandes, setDemandes] = useState<DemandeCraieOut[]>([]);
  const [texteEnCours, setTexteEnCours] = useState<{ x: number; y: number; valeur: string } | null>(null);

  const traitEnCours = useRef<[number, number][]>([]);
  const enTrainDeDessiner = useRef(false);

  const permissionAccordee =
    estOrganisateur ||
    (etat?.permissions ?? []).some((p: PermissionEcritureOut) => p.eleve_utilisateur_id === monUtilisateurId);

  const chargerEtat = useCallback(() => {
    obtenirEtatTableau(sessionId)
      .then((res) => setEtat(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  }, [sessionId]);

  useEffect(chargerEtat, [chargerEtat]);

  useEffect(() => {
    if (!estOrganisateur) return;
    listerDemandesCraie(sessionId)
      .then((res) => setDemandes(res.data))
      .catch(() => undefined);
  }, [sessionId, estOrganisateur]);

  // Ecoute des evenements temps reel (voir cours_direct/realtime.py cote backend : le
  // canal ne fait que diffuser ce que les endpoints REST ont deja persiste et valide).
  useEffect(() => {
    if (!canal) return;
    const gestionnaire = (evt: MessageEvent) => {
      let message: EvenementTempsReelSessionLive;
      try {
        message = JSON.parse(evt.data);
      } catch {
        return;
      }
      if (message.type === "trait") {
        setEtat((prev) => (prev ? ajouterTraitDansEtat(prev, message.panneau_id, message.trait) : prev));
      } else if (message.type === "demande_craie" && estOrganisateur) {
        setDemandes((prev) => [...prev, message.demande]);
      } else if (message.type === "demande_craie_tranchee" && estOrganisateur) {
        setDemandes((prev) => prev.filter((d) => d.id !== message.demande.id));
      } else if (message.type === "permission_accordee" || message.type === "permission_revoquee") {
        chargerEtat();
      }
    };
    canal.addEventListener("message", gestionnaire);
    return () => canal.removeEventListener("message", gestionnaire);
  }, [canal, estOrganisateur, chargerEtat]);

  const panneaux = etat?.panneaux ?? [];
  const panneauCourant: PanneauAvecTraitsOut | undefined = panneaux[panneauIndex];

  const redessiner = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !panneauCourant) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const { width, height } = canvas;

    ctx.fillStyle = "#153322"; // vert tableau noir, coherent avec le rendu serveur (rendu_tableau.py)
    ctx.fillRect(0, 0, width, height);

    let visibles: TraitTableauOut[] = [];
    for (const trait of panneauCourant.traits) {
      if (trait.type === "effacement") visibles = [];
      else visibles.push(trait);
    }
    for (const trait of visibles) {
      if (trait.type === "trait_libre") {
        const points = (trait.donnees.points as [number, number][]) ?? [];
        if (points.length < 2) continue;
        ctx.strokeStyle = (trait.donnees.couleur as string) ?? "#f8fafc";
        ctx.lineWidth = ((trait.donnees.epaisseur as number) ?? 0.01) * Math.min(width, height);
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.beginPath();
        ctx.moveTo(points[0][0] * width, points[0][1] * height);
        for (const [x, y] of points.slice(1)) ctx.lineTo(x * width, y * height);
        ctx.stroke();
      } else if (trait.type === "texte") {
        const x = ((trait.donnees.x as number) ?? 0) * width;
        const y = ((trait.donnees.y as number) ?? 0) * height;
        const taille = ((trait.donnees.taille as number) ?? 0.035) * height;
        ctx.fillStyle = (trait.donnees.couleur as string) ?? "#f8fafc";
        ctx.font = `${taille}px "Comic Sans MS", var(--font-body, sans-serif)`;
        ctx.fillText(String(trait.donnees.texte ?? ""), x, y);
      }
    }

    // Trait en cours (dessin local optimiste, avant confirmation serveur).
    if (traitEnCours.current.length > 1) {
      ctx.strokeStyle = "#fde68a";
      ctx.lineWidth = 0.01 * Math.min(width, height);
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.beginPath();
      ctx.moveTo(traitEnCours.current[0][0] * width, traitEnCours.current[0][1] * height);
      for (const [x, y] of traitEnCours.current.slice(1)) ctx.lineTo(x * width, y * height);
      ctx.stroke();
    }
  }, [panneauCourant]);

  useEffect(redessiner, [redessiner]);

  useEffect(() => {
    const gererResize = () => redessiner();
    window.addEventListener("resize", gererResize);
    return () => window.removeEventListener("resize", gererResize);
  }, [redessiner]);

  const positionNormalisee = (e: React.PointerEvent<HTMLCanvasElement>): [number, number] => {
    const rect = e.currentTarget.getBoundingClientRect();
    return [(e.clientX - rect.left) / rect.width, (e.clientY - rect.top) / rect.height];
  };

  const debuterTrait = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!permissionAccordee || !panneauCourant) return;
    if (outil === "texte") {
      const [x, y] = positionNormalisee(e);
      setTexteEnCours({ x, y, valeur: "" });
      return;
    }
    enTrainDeDessiner.current = true;
    traitEnCours.current = [positionNormalisee(e)];
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const continuerTrait = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!enTrainDeDessiner.current) return;
    traitEnCours.current.push(positionNormalisee(e));
    redessiner();
  };

  const terminerTrait = async () => {
    if (!enTrainDeDessiner.current || !panneauCourant) return;
    enTrainDeDessiner.current = false;
    const points = traitEnCours.current;
    traitEnCours.current = [];
    if (points.length < 2) return;
    try {
      await ajouterTraitTableau(sessionId, panneauCourant.panneau.id, "trait_libre", {
        points,
        epaisseur: 0.01,
        couleur: "#f8fafc",
      });
    } catch (err) {
      setErreur(messageErreur(err, "Le trait n'a pas pu etre enregistre."));
      chargerEtat();
    }
  };

  const validerTexte = async () => {
    if (!texteEnCours || !panneauCourant || !texteEnCours.valeur.trim()) {
      setTexteEnCours(null);
      return;
    }
    try {
      await ajouterTraitTableau(sessionId, panneauCourant.panneau.id, "texte", {
        x: texteEnCours.x,
        y: texteEnCours.y,
        texte: texteEnCours.valeur.trim(),
        taille: 0.035,
        couleur: "#fde68a",
      });
      chargerEtat();
    } catch (err) {
      setErreur(messageErreur(err, "Le texte n'a pas pu etre ajoute."));
    } finally {
      setTexteEnCours(null);
    }
  };

  const effacer = async () => {
    if (!panneauCourant) return;
    try {
      await effacerPanneauTableau(sessionId, panneauCourant.panneau.id);
      chargerEtat();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'effacer le panneau."));
    }
  };

  const nouveauPanneau = async () => {
    try {
      await ajouterPanneauTableau(sessionId);
      chargerEtat();
      setPanneauIndex(panneaux.length);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'ajouter un panneau."));
    }
  };

  const demanderCraie = async () => {
    try {
      await demanderLaCraie(sessionId);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de demander la craie."));
    }
  };

  const trancherDemande = async (demande: DemandeCraieOut, accorder: boolean) => {
    try {
      if (accorder) await accorderDemandeCraie(sessionId, demande.id);
      else await refuserDemandeCraie(sessionId, demande.id);
      setDemandes((prev) => prev.filter((d) => d.id !== demande.id));
      chargerEtat();
    } catch (err) {
      setErreur(messageErreur(err));
    }
  };

  return (
    <div>
      <ErrorBanner>{erreur}</ErrorBanner>

      {/* Barre d'outils */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", marginBottom: "8px" }}>
        <Btn
          variant={outil === "craie" ? "primary" : "outline"}
          size="sm"
          leftIcon={<PenLine size={14} />}
          onClick={() => setOutil("craie")}
          disabled={!permissionAccordee}
        >
          Craie
        </Btn>
        <Btn
          variant={outil === "texte" ? "primary" : "outline"}
          size="sm"
          leftIcon={<Type size={14} />}
          onClick={() => setOutil("texte")}
          disabled={!permissionAccordee}
        >
          Texte
        </Btn>
        <Btn variant="outline" size="sm" leftIcon={<Eraser size={14} />} onClick={effacer} disabled={!permissionAccordee}>
          Chiffon
        </Btn>
        {estOrganisateur && (
          <Btn variant="outline" size="sm" leftIcon={<Plus size={14} />} onClick={nouveauPanneau}>
            Nouveau panneau
          </Btn>
        )}
        <div style={{ flex: 1 }} />
        {panneaux.length > 1 && (
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Btn
              variant="ghost"
              size="sm"
              onClick={() => setPanneauIndex((i) => Math.max(0, i - 1))}
              disabled={panneauIndex === 0}
            >
              <ChevronLeft size={16} />
            </Btn>
            <span style={{ fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>
              Panneau {panneauIndex + 1} / {panneaux.length}
            </span>
            <Btn
              variant="ghost"
              size="sm"
              onClick={() => setPanneauIndex((i) => Math.min(panneaux.length - 1, i + 1))}
              disabled={panneauIndex === panneaux.length - 1}
            >
              <ChevronRight size={16} />
            </Btn>
          </div>
        )}
        {!estOrganisateur && !permissionAccordee && (
          <Btn variant="action" size="sm" onClick={demanderCraie}>
            Demander la craie
          </Btn>
        )}
      </div>

      {/* File de demandes (organisateur uniquement) */}
      {estOrganisateur && demandes.length > 0 && (
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "8px",
            marginBottom: "8px",
            padding: "8px 12px",
            background: "var(--action-tint)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          {demandes.map((d) => (
            <div key={d.id} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontSize: "var(--text-sm)" }}>Demande de craie</span>
              <Btn variant="primary" size="sm" onClick={() => trancherDemande(d, true)}>
                Accorder
              </Btn>
              <Btn variant="ghost" size="sm" onClick={() => trancherDemande(d, false)}>
                Refuser
              </Btn>
            </div>
          ))}
        </div>
      )}

      {/* Tableau */}
      <div style={{ position: "relative", width: "100%", aspectRatio: "5 / 3", borderRadius: "var(--radius-md)", overflow: "hidden", boxShadow: "var(--shadow-md)" }}>
        <canvas
          ref={canvasRef}
          width={1000}
          height={600}
          style={{ width: "100%", height: "100%", touchAction: "none", cursor: permissionAccordee ? "crosshair" : "not-allowed" }}
          onPointerDown={debuterTrait}
          onPointerMove={continuerTrait}
          onPointerUp={terminerTrait}
          onPointerLeave={terminerTrait}
        />
        {texteEnCours && (
          <div
            style={{
              position: "absolute",
              left: `${texteEnCours.x * 100}%`,
              top: `${texteEnCours.y * 100}%`,
              display: "flex",
              gap: "4px",
              transform: "translateY(-50%)",
            }}
          >
            <TextInput
              autoFocus
              value={texteEnCours.valeur}
              onChange={(e) => setTexteEnCours({ ...texteEnCours, valeur: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && validerTexte()}
              style={{ width: "180px" }}
              placeholder="Ecrire..."
            />
            <Btn size="sm" variant="primary" onClick={validerTexte}>
              OK
            </Btn>
            <Btn size="sm" variant="ghost" onClick={() => setTexteEnCours(null)}>
              <X size={14} />
            </Btn>
          </div>
        )}
        {!permissionAccordee && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "flex-end",
              justifyContent: "center",
              padding: "12px",
              pointerEvents: "none",
            }}
          >
            <span
              style={{
                background: "rgba(0,0,0,0.55)",
                color: "#fff",
                padding: "4px 10px",
                borderRadius: "var(--radius-pill)",
                fontSize: "var(--text-xs)",
              }}
            >
              Lecture seule - vous n'avez pas la craie
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function ajouterTraitDansEtat(etat: EtatTableauOut, panneauId: string, trait: TraitTableauOut): EtatTableauOut {
  return {
    ...etat,
    panneaux: etat.panneaux.map((p) =>
      p.panneau.id === panneauId ? { ...p, traits: [...p.traits, trait] } : p,
    ),
  };
}

export function PanneauPermissionsOrganisateur({
  sessionId,
  eleves,
  permissions,
  onChange,
}: {
  sessionId: string;
  eleves: { utilisateur_id: string | null; nom: string; prenom: string }[];
  permissions: PermissionEcritureOut[];
  onChange: () => void;
}) {
  const [erreur, setErreur] = useState<string | null>(null);

  const preter = async (eleveUtilisateurId: string) => {
    try {
      await preterLaCraie(sessionId, eleveUtilisateurId);
      onChange();
    } catch (err) {
      setErreur(messageErreur(err));
    }
  };

  const revoquer = async (eleveUtilisateurId: string) => {
    try {
      await revoquerLaCraie(sessionId, eleveUtilisateurId);
      onChange();
    } catch (err) {
      setErreur(messageErreur(err));
    }
  };

  return (
    <div>
      <ErrorBanner>{erreur}</ErrorBanner>
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        {eleves
          .filter((e): e is { utilisateur_id: string; nom: string; prenom: string } => !!e.utilisateur_id)
          .map((e) => {
            const aLaCraie = permissions.some((p) => p.eleve_utilisateur_id === e.utilisateur_id);
            return (
              <div key={e.utilisateur_id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px" }}>
                <span style={{ fontSize: "var(--text-sm)" }}>
                  {e.prenom} {e.nom}
                </span>
                {aLaCraie ? (
                  <Btn size="sm" variant="ghost" onClick={() => revoquer(e.utilisateur_id)}>
                    Reprendre la craie
                  </Btn>
                ) : (
                  <Btn size="sm" variant="outline" onClick={() => preter(e.utilisateur_id)}>
                    Preter la craie
                  </Btn>
                )}
              </div>
            );
          })}
      </div>
    </div>
  );
}
