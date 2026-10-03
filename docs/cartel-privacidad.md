# Cartel de privacidad — Para pegar en la puerta del local

Local: Supermercado Piloto (primer local / primer piloto)
Sistema: Analítica de video — Cuenta personas, mide fila y aforo.
Fecha del primer análisis / primer día: 2026-09-29

---

Ley 1581 de 2012 — Protección de datos personales (habeas data colombiana).

Qué guarda este sistema:
- Posición de personas (puntos en el video) por 30 días (`retencion_dias`).
- Clips de 10 segundos solo cuando ocurre un evento (fila larga, caja desatendida, local lleno).
- Métricas agregadas (cuánta gente, cuánto tiempo) sin guardar video continuo.

Qué NO guarda:
- Video continuo del local.
- Caras ni nombres de personas.
- Datos que identifiquen a alguien entre días o entre cámaras.

Cómo se borra:
- Automáticamente cada 30 días (`manage.py purgar_posiciones`).
- Cada borrada deja un registro (`JobRun`) que se puede auditar.

Más información (y auditoría de borradas):
http://<IP-local>:8000/privacidad/

---

Este cartel es obligatorio según la ley de habeas data colombiana y debe ser visible desde la entrada del local.
