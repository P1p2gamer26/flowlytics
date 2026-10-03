# Videos de ejemplo

Tres grabaciones públicas de cámaras fijas en tiendas reales. El panel las reproduce en
bucle y el worker las analiza como si fueran cámaras en vivo.

| Archivo | Origen | Qué es |
|---|---|---|
| `tienda_usa.mp4` | [YouTube -1bRhYjw1qE](https://www.youtube.com/watch?v=-1bRhYjw1qE) | Tienda en EE. UU., cámara de esquina alta, 60 s, 1920×1080 |
| `tienda_iprox.mp4` | [YouTube KMJS66jBtVQ](https://www.youtube.com/watch?v=KMJS66jBtVQ) | Tienda pequeña con caja y pasillos, 111 s, 1270×720 |
| `super_caja.mp4` | [YouTube -8zyEwAa50Q](https://www.youtube.com/watch?v=-8zyEwAa50Q) | Caja de supermercado vista desde arriba, 299 s, 1920×1080 |

Para volver a bajarlos:

```bash
python -m yt_dlp -f "bv*[vcodec^=avc1][height<=720]/b[vcodec^=avc1]" \
  -o "demo/videos/cctv/%(id)s.%(ext)s" \
  "https://www.youtube.com/watch?v=-1bRhYjw1qE" \
  "https://www.youtube.com/watch?v=KMJS66jBtVQ" \
  "https://www.youtube.com/watch?v=-8zyEwAa50Q"
```

El filtro `vcodec^=avc1` importa: sin él YouTube entrega AV1, que muchos OpenCV no
decodifican, y el análisis falla sin decir por qué.
