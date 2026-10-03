from analytics.backups import elegir_para_borrar


def nombre(fecha):   # fecha: "YYYYMMDD" a medianoche
    return f"backup-{fecha}T000000.sql.gz"


def test_conserva_los_siete_diarios_mas_nuevos():
    dias = [nombre(f"202608{d:02d}") for d in range(1, 15)]   # 14 días seguidos
    borrar = elegir_para_borrar(dias, diarios=7, semanales=4)

    conservados = set(dias) - set(borrar)
    # los 7 más nuevos siempre se quedan
    assert set(dias[-7:]) <= conservados


def test_conserva_un_semanal_por_semana_hasta_el_tope():
    # ~8 semanas de respaldos diarios
    dias = [nombre(f"2026{6 + (d // 30):02d}{(d % 30) + 1:02d}") for d in range(56)]
    borrar = elegir_para_borrar(dias, diarios=7, semanales=4)
    conservados = set(dias) - set(borrar)

    # 7 diarios + a lo sumo 4 semanales
    assert 7 <= len(conservados) <= 11


def test_pocos_respaldos_no_se_borra_nada():
    dias = [nombre("20260810"), nombre("20260811"), nombre("20260812")]
    assert elegir_para_borrar(dias, diarios=7, semanales=4) == []
