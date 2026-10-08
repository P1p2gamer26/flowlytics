import { useEffect, useRef } from "react";
import { colorCelda } from "./MapaCalor";

export function CapaCalor({
  grid,
  cols,
  rows,
  ancho,
  alto,
  opacidad = 0.75
}: {
  grid: number[][];
  cols: number;
  rows: number;
  ancho: number;
  alto: number;
  opacidad?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = ancho;
    canvas.height = alto;

    const offscreen = document.createElement("canvas");
    offscreen.width = cols;
    offscreen.height = rows;
    const offCtx = offscreen.getContext("2d");
    if (!offCtx) return;

    const imageData = offCtx.createImageData(cols, rows);
    const data = imageData.data;

    // Raíz de valor/máximo: con una sola zona muy pisada el resto quedaba bajo el
    // umbral de transparencia y la capa parecía vacía.
    const max = Math.max(...grid.flat(), 1e-9);
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const valor = grid[r][c];
        const [r_, g, b, a] = colorCelda(Math.sqrt(valor / max));
        const i = (r * cols + c) * 4;
        data[i] = r_;
        data[i + 1] = g;
        data[i + 2] = b;
        data[i + 3] = a;
      }
    }

    offCtx.putImageData(imageData, 0, 0);

    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    // Desenfoque proporcional al lienzo (en píxeles del frame de referencia).
    ctx.filter = `blur(${Math.round(ancho / 70)}px)`;
    ctx.globalAlpha = opacidad;
    ctx.drawImage(offscreen, 0, 0, ancho, alto);
  }, [grid, cols, rows, ancho, alto, opacidad]);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none absolute inset-0 h-full w-full"
      aria-hidden="true"
      width={ancho}
      height={alto}
    />
  );
}