import { useRef, useState, type CSSProperties, type ReactNode } from "react";

/**
 * Enveloppe une carte avec une bascule 3D réactive à la position du curseur —
 * profondeur discrète (max 8°), jamais un gadget qui distrait du contenu.
 * Respecte prefers-reduced-motion (désactivé si l'utilisateur le demande).
 */
export function Tilt3D({
  children,
  className = "",
  style,
  maxTilt = 7,
  glare = false,
}: {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  maxTilt?: number;
  glare?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [transform, setTransform] = useState("perspective(1200px) rotateX(0deg) rotateY(0deg)");
  const [glarePos, setGlarePos] = useState({ x: 50, y: 50, opacity: 0 });
  const reducedMotion =
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const onMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (reducedMotion || !ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width;
    const py = (e.clientY - rect.top) / rect.height;
    const rotateY = (px - 0.5) * maxTilt * 2;
    const rotateX = (0.5 - py) * maxTilt * 2;
    setTransform(`perspective(1200px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`);
    if (glare) setGlarePos({ x: px * 100, y: py * 100, opacity: 0.14 });
  };

  const onMouseLeave = () => {
    setTransform("perspective(1200px) rotateX(0deg) rotateY(0deg)");
    if (glare) setGlarePos((g) => ({ ...g, opacity: 0 }));
  };

  return (
    <div
      ref={ref}
      className={`card-3d ${className}`}
      data-tilted={transform.includes("0deg) rotateY(0deg)") ? "false" : "true"}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
      style={{ transform, position: "relative", ...style }}
    >
      {children}
      {glare && (
        <div
          aria-hidden="true"
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "inherit",
            pointerEvents: "none",
            background: `radial-gradient(circle at ${glarePos.x}% ${glarePos.y}%, rgba(255,255,255,${glarePos.opacity}), transparent 60%)`,
            transition: "opacity 200ms ease",
          }}
        />
      )}
    </div>
  );
}
