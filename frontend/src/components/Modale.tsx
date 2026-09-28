import { createContext, useCallback, useContext, useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, X } from "lucide-react";
import { Btn } from "./ui";

/* ═══════════════════════════════════════════════════════════════
   Modale : fenêtre de dialogue accessible (Échap, focus piégé et restauré, défilement
   de la page bloqué). Sur téléphone, elle s'affiche en panneau bas plein largeur.
   ═══════════════════════════════════════════════════════════════ */

const FOCUSABLES = 'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function Modale({
  ouvert,
  titre,
  onFermer,
  children,
  pied,
  largeur = 520,
}: {
  ouvert: boolean;
  titre: ReactNode;
  onFermer: () => void;
  children: ReactNode;
  pied?: ReactNode;
  largeur?: number;
}) {
  const idTitre = useId();
  const boite = useRef<HTMLDivElement>(null);
  const fermer = useRef(onFermer);
  useEffect(() => {
    fermer.current = onFermer;
  });

  useEffect(() => {
    if (!ouvert) return;
    const precedent = document.activeElement as HTMLElement | null;
    const debordement = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const premier = boite.current?.querySelector<HTMLElement>(FOCUSABLES);
    (premier ?? boite.current)?.focus();

    const clavier = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        fermer.current();
        return;
      }
      if (e.key !== "Tab" || !boite.current) return;
      const elements = Array.from(boite.current.querySelectorAll<HTMLElement>(FOCUSABLES));
      if (elements.length === 0) return;
      const [debut, fin] = [elements[0], elements[elements.length - 1]];
      if (e.shiftKey && document.activeElement === debut) {
        e.preventDefault();
        fin.focus();
      } else if (!e.shiftKey && document.activeElement === fin) {
        e.preventDefault();
        debut.focus();
      }
    };
    document.addEventListener("keydown", clavier);
    return () => {
      document.removeEventListener("keydown", clavier);
      document.body.style.overflow = debordement;
      precedent?.focus?.();
    };
  }, [ouvert]);

  if (!ouvert) return null;
  return createPortal(
    <div className="modale-fond" onMouseDown={(e) => e.target === e.currentTarget && onFermer()}>
      <div
        ref={boite}
        className="modale anim-pop-in"
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitre}
        tabIndex={-1}
        style={{ maxWidth: `${largeur}px` }}
      >
        <div className="modale-entete">
          <h2 id={idTitre} className="modale-titre">{titre}</h2>
          <button type="button" className="modale-fermer" onClick={onFermer} aria-label="Fermer">
            <X size={18} />
          </button>
        </div>
        <div className="modale-corps">{children}</div>
        {pied && <div className="modale-pied">{pied}</div>}
      </div>
    </div>,
    document.body,
  );
}

/* ═══════════════════════════════════════════════════════════════
   Confirmation : const confirmer = useConfirmation();
   if (!(await confirmer({ titre, message, action: "Supprimer", danger: true }))) return;
   ═══════════════════════════════════════════════════════════════ */

export interface DemandeConfirmation {
  titre: string;
  message?: ReactNode;
  action?: string;
  danger?: boolean;
}

type Confirmer = (demande: DemandeConfirmation) => Promise<boolean>;

const ContexteConfirmation = createContext<Confirmer | null>(null);

export function ConfirmationProvider({ children }: { children: ReactNode }) {
  const [demande, setDemande] = useState<DemandeConfirmation | null>(null);
  const resolution = useRef<((ok: boolean) => void) | null>(null);

  const confirmer = useCallback<Confirmer>(
    (d) =>
      new Promise<boolean>((resoudre) => {
        resolution.current?.(false);
        resolution.current = resoudre;
        setDemande(d);
      }),
    [],
  );

  const repondre = (ok: boolean) => {
    resolution.current?.(ok);
    resolution.current = null;
    setDemande(null);
  };

  return (
    <ContexteConfirmation.Provider value={confirmer}>
      {children}
      <Modale
        ouvert={demande !== null}
        titre={
          <span style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
            {demande?.danger && <AlertTriangle size={18} style={{ color: "var(--action-deep)" }} aria-hidden="true" />}
            {demande?.titre}
          </span>
        }
        onFermer={() => repondre(false)}
        largeur={460}
        pied={
          <>
            <Btn variant="ghost" onClick={() => repondre(false)}>Annuler</Btn>
            <Btn variant={demande?.danger ? "action" : "primary"} onClick={() => repondre(true)}>
              {demande?.action ?? "Confirmer"}
            </Btn>
          </>
        }
      >
        {demande?.message && <div className="text-sm" style={{ color: "var(--ink-soft)", lineHeight: 1.6 }}>{demande.message}</div>}
      </Modale>
    </ContexteConfirmation.Provider>
  );
}

export function useConfirmation(): Confirmer {
  const ctx = useContext(ContexteConfirmation);
  if (!ctx) throw new Error("useConfirmation doit être utilisé dans ConfirmationProvider");
  return ctx;
}
