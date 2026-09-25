import { useState } from "react";
import { ChevronLeft, ChevronRight, ImageOff } from "lucide-react";

interface CarouselProps {
  images: { id: string; url: string }[];
  aspectRatio?: string;
  emptyLabel?: string;
}

/**
 * Carrousel d'images minimal, sans dépendance externe. Dégrade proprement
 * sur zéro image (icône + libellé plutôt qu'un cadre vide) et sur une seule
 * image (pas de flèches inutiles).
 */
export function Carousel({ images, aspectRatio = "16 / 10", emptyLabel = "Aucune photo disponible" }: CarouselProps) {
  const [index, setIndex] = useState(0);

  if (images.length === 0) {
    return (
      <div
        style={{
          aspectRatio,
          borderRadius: "var(--radius-md)",
          background: "var(--surface-2)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "8px",
          color: "var(--ink-faint)",
        }}
      >
        <ImageOff size={22} aria-hidden="true" />
        <span style={{ fontSize: "var(--text-xs)" }}>{emptyLabel}</span>
      </div>
    );
  }

  const goTo = (next: number) => setIndex((next + images.length) % images.length);

  return (
    <div style={{ position: "relative", borderRadius: "var(--radius-md)", overflow: "hidden", aspectRatio, background: "var(--surface-2)" }}>
      <img
        src={images[index].url}
        alt=""
        style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
      />
      {images.length > 1 && (
        <>
          <button
            type="button"
            onClick={() => goTo(index - 1)}
            aria-label="Photo précédente"
            style={{
              position: "absolute", left: "8px", top: "50%", transform: "translateY(-50%)",
              width: "30px", height: "30px", borderRadius: "50%", border: "none", cursor: "pointer",
              background: "rgba(11, 18, 14, 0.55)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
            }}
          >
            <ChevronLeft size={16} />
          </button>
          <button
            type="button"
            onClick={() => goTo(index + 1)}
            aria-label="Photo suivante"
            style={{
              position: "absolute", right: "8px", top: "50%", transform: "translateY(-50%)",
              width: "30px", height: "30px", borderRadius: "50%", border: "none", cursor: "pointer",
              background: "rgba(11, 18, 14, 0.55)", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
            }}
          >
            <ChevronRight size={16} />
          </button>
          <div style={{ position: "absolute", bottom: "8px", left: "50%", transform: "translateX(-50%)", display: "flex", gap: "5px" }}>
            {images.map((img, i) => (
              <button
                key={img.id}
                type="button"
                onClick={() => setIndex(i)}
                aria-label={`Aller à la photo ${i + 1}`}
                style={{
                  width: "6px", height: "6px", borderRadius: "50%", border: "none", cursor: "pointer", padding: 0,
                  background: i === index ? "#fff" : "rgba(255,255,255,0.5)",
                }}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
