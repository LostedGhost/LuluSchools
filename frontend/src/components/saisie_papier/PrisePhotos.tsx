import { useEffect, useRef, useState } from "react";
import { Camera, FileText, Upload, X } from "lucide-react";
import { Btn } from "../ui";

/** Photos d'un document papier : appareil photo du téléphone/de la tablette (capture) ou
 * fichiers (photos, PDF de scanner). Aperçus retirables avant l'envoi. */
export function PrisePhotos({ fichiers, onChange, max = 8, unique = false, aide }: {
  fichiers: File[];
  onChange: (fichiers: File[]) => void;
  max?: number;
  unique?: boolean;
  aide?: string;
}) {
  const camera = useRef<HTMLInputElement>(null);
  const fichiersRef = useRef<HTMLInputElement>(null);
  const [apercus, setApercus] = useState<string[]>([]);

  useEffect(() => {
    const urls = fichiers.map((f) => (f.type.startsWith("image/") ? URL.createObjectURL(f) : ""));
    setApercus(urls);
    return () => urls.forEach((u) => u && URL.revokeObjectURL(u));
  }, [fichiers]);

  const ajouter = (liste: FileList | null) => {
    if (!liste) return;
    const nouveaux = Array.from(liste);
    onChange(unique ? nouveaux.slice(0, 1) : [...fichiers, ...nouveaux].slice(0, max));
  };

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        <Btn type="button" variant="primary" leftIcon={<Camera size={16} />} onClick={() => camera.current?.click()}
          disabled={!unique && fichiers.length >= max}>
          Prendre une photo
        </Btn>
        <Btn type="button" variant="outline" leftIcon={<Upload size={16} />} onClick={() => fichiersRef.current?.click()}
          disabled={!unique && fichiers.length >= max}>
          {unique ? "Choisir un fichier" : "Choisir des fichiers"}
        </Btn>
        <input ref={camera} type="file" accept="image/*" capture="environment" hidden
          onChange={(e) => { ajouter(e.target.files); e.target.value = ""; }} />
        <input ref={fichiersRef} type="file" accept="image/*,application/pdf" multiple={!unique} hidden
          onChange={(e) => { ajouter(e.target.files); e.target.value = ""; }} />
      </div>
      <p className="text-sm" style={{ color: "var(--ink-soft)", margin: "8px 0 0" }}>
        {aide ?? "Posez la feuille à plat, bien éclairée, et cadrez-la entière. Une photo par page."}
        {!unique && " Vous pouvez sélectionner plusieurs fichiers à la fois, ou prendre les photos l'une après l'autre."}
        {!unique && ` ${fichiers.length}/${max}.`}
      </p>
      {fichiers.length > 0 && (
        <ul className="flex flex-wrap gap-2" style={{ listStyle: "none", padding: 0, margin: "10px 0 0" }}>
          {fichiers.map((f, i) => (
            <li key={`${f.name}-${i}`} style={{ position: "relative", width: "84px" }}>
              {apercus[i] ? (
                <img src={apercus[i]} alt={`Page ${i + 1}`} style={{ width: "84px", height: "108px", objectFit: "cover", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)" }} />
              ) : (
                <div style={{ width: "84px", height: "108px", display: "flex", alignItems: "center", justifyContent: "center", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)", background: "var(--surface-2)" }}>
                  <FileText size={24} aria-hidden="true" />
                </div>
              )}
              <button type="button" onClick={() => onChange(fichiers.filter((_, j) => j !== i))} aria-label={`Retirer ${f.name}`}
                style={{ position: "absolute", top: "-8px", right: "-8px", width: "26px", height: "26px", borderRadius: "50%", border: "none", background: "var(--action)", color: "#fff", display: "inline-flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}>
                <X size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
