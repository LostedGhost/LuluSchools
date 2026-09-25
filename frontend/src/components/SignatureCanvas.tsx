import { useRef, useState } from "react";
import { SecondaryButton } from "./ui";

interface SignatureCanvasProps {
  onSigner: (blob: Blob) => void;
  enCours?: boolean;
}

export function SignatureCanvas({ onSigner, enCours }: SignatureCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dessineRef = useRef(false);
  const [aDessine, setADessine] = useState(false);

  const position = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  };

  const demarrer = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;
    dessineRef.current = true;
    const { x, y } = position(e);
    ctx.beginPath();
    ctx.moveTo(x, y);
  };

  const dessiner = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!dessineRef.current) return;
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;
    const { x, y } = position(e);
    ctx.lineWidth = 2.5;
    ctx.lineCap = "round";
    ctx.strokeStyle = "#1e1b4b";
    ctx.lineTo(x, y);
    ctx.stroke();
    setADessine(true);
  };

  const arreter = () => {
    dessineRef.current = false;
  };

  const effacer = () => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    setADessine(false);
  };

  const valider = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.toBlob((blob) => {
      if (blob) onSigner(blob);
    }, "image/png");
  };

  return (
    <div>
      <canvas
        ref={canvasRef}
        width={500}
        height={200}
        className="touch-none rounded-lg border-2 border-dashed border-slate-300 bg-white"
        onPointerDown={demarrer}
        onPointerMove={dessiner}
        onPointerUp={arreter}
        onPointerLeave={arreter}
      />
      <div className="mt-3 flex gap-2">
        <SecondaryButton type="button" onClick={effacer}>
          Effacer
        </SecondaryButton>
        <button
          type="button"
          onClick={valider}
          disabled={!aDessine || enCours}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {enCours ? "Envoi..." : "Signer le contrat"}
        </button>
      </div>
    </div>
  );
}
