"""Fábrica del tracker, tolerante a oclusiones.

Un `lost_track_buffer` más largo mantiene vivo un track cuando la persona
desaparece unos frames (pasa detrás de un estante) y lo reconecta con el MISMO id
al reaparecer, en vez de contar a alguien nuevo. El valor sale de la calibración
de la cámara. ByteTrack es numpy puro: se prueba sin el modelo.
"""
import supervision as sv


def crear_tracker(fps, lost_track_buffer=30, track_activation_threshold=0.25,
                  minimum_matching_threshold=0.8, minimum_consecutive_frames=2):
    """`minimum_consecutive_frames=2` es la diferencia entre contar personas y
    contar parpadeos: con 1 (el default de supervision) una deteccion aislada
    —un reflejo, media persona en el borde— nace ya confirmada y suma un
    visitante. Medido el 6-sep-2026: con 1, el mismo video daba 42 visitantes a
    2 FPS y 120 a 6 FPS.

    ponytail: 2 es el minimo que descarta el ruido de un frame. Subirlo a 3
    limpia mas pero se come a quien solo aparece un instante en el encuadre;
    tocarlo con el reporte de precision delante, no a ojo.
    """
    return sv.ByteTrack(
        frame_rate=int(round(fps)) or 1,
        lost_track_buffer=lost_track_buffer,
        track_activation_threshold=track_activation_threshold,
        minimum_matching_threshold=minimum_matching_threshold,
        minimum_consecutive_frames=minimum_consecutive_frames,
    )
