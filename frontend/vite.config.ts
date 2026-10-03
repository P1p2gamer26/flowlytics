import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Django sirve el bundle desde /static/dashboard/app/
  base: "/static/dashboard/app/",
  build: {
    outDir: path.resolve(import.meta.dirname, "../dashboard/static/dashboard/app"),
    emptyOutDir: true,
    // Nombres fijos: sin hash no hace falta leer el manifest desde la plantilla.
    rollupOptions: {
      output: {
        entryFileNames: "app.js",
        chunkFileNames: "[name].js",
        assetFileNames: "app.[ext]",
      },
    },
  },
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "src") } },
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
});
