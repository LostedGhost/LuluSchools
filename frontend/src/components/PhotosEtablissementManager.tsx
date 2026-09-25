import { useEffect, useRef, useState } from "react";
import { ajouterPhotoEtablissement, photosPubliques, supprimerPhotoEtablissement, type PhotoPublique } from "../api/etablissements";
import { messageErreur } from "../api/client";
import { ImagePlus, Trash2, ImageOff } from "lucide-react";
import { SectionHead, ErrorBanner } from "./ui";

const MAX_PHOTOS = 8;

/**
 * Gestion des photos d'un établissement (A+) : upload vers LuluFiles (ADR-003),
 * affichage en grille, suppression. Alimente l'annuaire public
 * (EtablissementsAnnuairePage) et son carrousel.
 */
export function PhotosEtablissementManager({ etablissementId }: { etablissementId: string }) {
  const [photos, setPhotos] = useState<PhotoPublique[] | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const charger = () => {
    photosPubliques(etablissementId)
      .then((res) => setPhotos(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  };

  useEffect(charger, [etablissementId]);

  const onFichierChoisi = async (fichier: File | undefined) => {
    if (!fichier) return;
    setErreur(null);
    setEnCours(true);
    try {
      await ajouterPhotoEtablissement(etablissementId, fichier);
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'envoyer la photo."));
    } finally {
      setEnCours(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const supprimer = async (photoId: string) => {
    setErreur(null);
    try {
      await supprimerPhotoEtablissement(etablissementId, photoId);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    }
  };

  const nbPhotos = photos?.length ?? 0;

  return (
    <div
      className="card anim-float-in"
      style={{ border: "1px solid var(--border)", boxShadow: "var(--shadow-sm)", background: "var(--surface)", padding: "var(--space-6)", marginTop: "var(--space-8)" }}
    >
      <SectionHead
        eyebrow="Annuaire public"
        title="Photos de l'établissement"
        desc="Ces photos apparaissent dans le carrousel de l'annuaire public des établissements — 8 maximum."
      />

      {erreur && (
        <div style={{ marginTop: "var(--space-3)" }}>
          <ErrorBanner>{erreur}</ErrorBanner>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: "var(--space-3)", marginTop: "var(--space-4)" }}>
        {photos === null && <p style={{ color: "var(--ink-faint)", fontSize: "var(--text-sm)" }}>Chargement...</p>}

        {photos !== null && photos.length === 0 && (
          <div
            style={{
              gridColumn: "1 / -1",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "8px",
              padding: "24px",
              color: "var(--ink-faint)",
              background: "var(--surface-2)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <ImageOff size={22} aria-hidden="true" />
            <span style={{ fontSize: "var(--text-sm)" }}>Aucune photo pour le moment.</span>
          </div>
        )}

        {photos?.map((p) => (
          <div key={p.id} style={{ position: "relative", aspectRatio: "4 / 3", borderRadius: "var(--radius-md)", overflow: "hidden", background: "var(--surface-2)" }}>
            <img src={p.url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }} />
            <button
              type="button"
              onClick={() => supprimer(p.id)}
              aria-label="Supprimer cette photo"
              style={{
                position: "absolute", top: "6px", right: "6px", width: "28px", height: "28px", borderRadius: "50%",
                border: "none", cursor: "pointer", background: "rgba(11,18,14,0.6)", color: "#fff",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      <div style={{ marginTop: "var(--space-4)" }}>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          disabled={enCours || nbPhotos >= MAX_PHOTOS}
          onChange={(e) => onFichierChoisi(e.target.files?.[0])}
          style={{ display: "none" }}
          id="photo-etablissement-input"
        />
        <label
          htmlFor="photo-etablissement-input"
          className={`btn btn-outline btn-sm ${enCours || nbPhotos >= MAX_PHOTOS ? "" : ""}`}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            cursor: enCours || nbPhotos >= MAX_PHOTOS ? "not-allowed" : "pointer",
            opacity: enCours || nbPhotos >= MAX_PHOTOS ? 0.6 : 1,
          }}
        >
          <ImagePlus size={16} aria-hidden="true" />
          {enCours ? "Envoi en cours..." : nbPhotos >= MAX_PHOTOS ? "Limite atteinte (8/8)" : "Ajouter une photo"}
        </label>
      </div>
    </div>
  );
}
