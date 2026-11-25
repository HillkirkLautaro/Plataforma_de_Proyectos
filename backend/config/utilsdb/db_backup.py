"""Persistencia y sincronización de respaldos de catálogos externos en MySQL."""

import json
from flask import current_app
from config.db import get_db_connection

_DDL_BACKUP_TABLE = """
    CREATE TABLE IF NOT EXISTS api_profesor_backup (
        recurso VARCHAR(100) PRIMARY KEY,
        datos JSON NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB
"""

_tabla_verificada = False


def _asegurar_tabla_backup(cursor):
    """Crea la tabla de respaldo automáticamente si aún no existe."""
    global _tabla_verificada
    if _tabla_verificada:
        return
    cursor.execute(_DDL_BACKUP_TABLE)
    _tabla_verificada = True


def sincronizar_backup_bd(recurso: str, datos) -> bool:
    """Sobrescribe atómicamente el respaldo de un recurso en MySQL.

    Refleja exactamente el estado actual de la API externa: altas, modificaciones
    y eliminaciones (incluyendo listas vacías).
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        _asegurar_tabla_backup(cursor)
        query = """
            INSERT INTO api_profesor_backup (recurso, datos)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE
                datos = VALUES(datos),
                updated_at = CURRENT_TIMESTAMP
        """
        cursor.execute(query, (recurso, json.dumps(datos, ensure_ascii=False)))
        conn.commit()
        return True
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        current_app.logger.exception(
            "No se pudo sincronizar el backup en BD para el recurso '%s'", recurso
        )
        return False
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def leer_backup_bd(recurso: str):
    """Recupera el último respaldo guardado en MySQL para el recurso, o None si no existe."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        _asegurar_tabla_backup(cursor)
        cursor.execute(
            "SELECT datos FROM api_profesor_backup WHERE recurso = %s",
            (recurso,),
        )
        fila = cursor.fetchone()
        if fila is not None and fila["datos"] is not None:
            # Dependiendo del driver de MySQL, 'datos' puede venir como str o ya parseado.
            return json.loads(fila["datos"]) if isinstance(fila["datos"], str) else fila["datos"]
        return None
    except Exception:
        current_app.logger.exception(
            "No se pudo leer el backup en BD para el recurso '%s'", recurso
        )
        return None
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


# Alias de compatibilidad con imports existentes
_guardar_backup_bd = sincronizar_backup_bd
_leer_backup_bd = leer_backup_bd



# Alias de compatibilidad con imports existentes
_guardar_backup_bd = sincronizar_backup_bd
_leer_backup_bd = leer_backup_bd