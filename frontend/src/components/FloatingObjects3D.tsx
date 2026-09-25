import type { CSSProperties } from "react";

/**
 * Objets décoratifs en volume (CSS `transform-style: preserve-3d`), purement
 * décoratifs — `aria-hidden`, rien de ce qu'ils montrent n'est absent du texte
 * qui les accompagne. Voir la section "SCÈNE 3D" dans index.css pour les
 * classes `.diploma-card` / `.medal-3d`.
 */

export function DiplomaCard({ style, className = "" }: { style?: CSSProperties; className?: string }) {
  return (
    <div className={`obj-3d diploma-card ${className}`} style={style} aria-hidden="true">
      <div className="obj-face obj-face-front">
        <i />
        <i style={{ width: "80%" }} />
        <i style={{ width: "45%" }} />
        <span className="obj-seal" />
      </div>
      <div className="obj-face obj-face-side" />
      <div className="obj-face obj-face-bottom" />
    </div>
  );
}

export function FloatingMedal({ style, className = "" }: { style?: CSSProperties; className?: string }) {
  return (
    <div className={`obj-3d medal-3d ${className}`} style={style} aria-hidden="true">
      <div className="obj-face obj-face-back" />
      <div className="obj-face obj-face-front" />
    </div>
  );
}
