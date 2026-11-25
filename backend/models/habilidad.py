"""Persistencia SQL de habilidades del usuario (tecnologías y lenguajes)."""

import json
from pathlib import Path

from mysql.connector import IntegrityError
from config.db import get_db_connection


SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"

MYSQL_ERR_DUP_ENTRY = 1062


class HabilidadDuplicadaError(Exception):
    """La habilidad ya está asociada al perfil del usuario."""

_DDL_USUARIO_LENGUAJES = """
    CREATE TABLE IF NOT EXISTS usuario_lenguajes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario_id INT NOT NULL,
        lenguaje_id INT NOT NULL,
        nivel ENUM('básico', 'intermedio', 'avanzado') NOT NULL,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
        UNIQUE KEY uk_usuario_len (usuario_id, lenguaje_id)
    ) ENGINE=InnoDB
"""

_tabla_lenguajes_verificada = False

_TABLAS_HABILIDAD = {
    "tecnologia": ("usuario_habilidades", "tecnologia_id"),
    "lenguaje": ("usuario_lenguajes", "lenguaje_id"),
}


def asegurar_tabla_usuario_lenguajes(cursor):
    """Crea automáticamente la tabla usuario_lenguajes si aún no existe."""
    global _tabla_lenguajes_verificada
    if _tabla_lenguajes_verificada:
        return
    cursor.execute(_DDL_USUARIO_LENGUAJES)
    _tabla_lenguajes_verificada = True


class Habilidad:
    @classmethod
    def cargar_schemas(cls):
        cls.SCHEMA_CREAR = json.loads(
            (SCHEMAS_DIR / "habilidad.schema.json").read_text(encoding="utf-8")
        )
        cls.SCHEMA_ACTUALIZAR = json.loads(
            (SCHEMAS_DIR / "habilidad_actualizar.schema.json").read_text(encoding="utf-8")
        )
        cls.SCHEMA = cls.SCHEMA_CREAR

    @staticmethod
    def listar_usuario(usuario_id: int) -> dict:
        """Devuelve las tecnologías y lenguajes asociados a un usuario."""
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            asegurar_tabla_usuario_lenguajes(cursor)

            cursor.execute(
                "SELECT tecnologia_id AS id, nivel FROM usuario_habilidades WHERE usuario_id = %s ORDER BY id",
                (usuario_id,),
            )
            tecnologias = cursor.fetchall()

            cursor.execute(
                "SELECT lenguaje_id AS id, nivel FROM usuario_lenguajes WHERE usuario_id = %s ORDER BY id",
                (usuario_id,),
            )
            lenguajes = cursor.fetchall()

            return {"tecnologias": tecnologias, "lenguajes": lenguajes}
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()

    @staticmethod
    def crear(usuario_id: int, tipo: str, item_id: int, nivel: str) -> None:
        """Inserta una nueva tecnología o lenguaje en el perfil del usuario.

        Lanza HabilidadDuplicadaError si ya existe (restricción UNIQUE / MySQL 1062).
        """
        if tipo not in _TABLAS_HABILIDAD:
            raise ValueError("El tipo de habilidad debe ser 'tecnologia' o 'lenguaje'.")

        tabla, columna = _TABLAS_HABILIDAD[tipo]
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            if tipo == "lenguaje":
                asegurar_tabla_usuario_lenguajes(cursor)

            cursor.execute(
                f"INSERT INTO {tabla} (usuario_id, {columna}, nivel) VALUES (%s, %s, %s)",
                (usuario_id, item_id, nivel),
            )
            conn.commit()
        except IntegrityError as exc:
            if conn is not None:
                conn.rollback()
            if exc.errno == MYSQL_ERR_DUP_ENTRY:
                raise HabilidadDuplicadaError("La habilidad ya existe en el perfil.") from exc
            raise
        except Exception:
            if conn is not None:
                conn.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()

    @staticmethod
    def actualizar_nivel(usuario_id: int, tipo: str, item_id: int, nivel: str) -> bool:
        """Actualiza el nivel de una habilidad existente del usuario.

        Devuelve True si la habilidad existe (aunque el nivel no haya cambiado) y
        False si no se encuentra asociada al perfil del usuario.
        """
        if tipo not in _TABLAS_HABILIDAD:
            raise ValueError("El tipo de habilidad debe ser 'tecnologia' o 'lenguaje'.")

        tabla, columna = _TABLAS_HABILIDAD[tipo]
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            if tipo == "lenguaje":
                asegurar_tabla_usuario_lenguajes(cursor)

            cursor.execute(
                f"UPDATE {tabla} SET nivel = %s WHERE usuario_id = %s AND {columna} = %s",
                (nivel, usuario_id, item_id),
            )
            conn.commit()
            if cursor.rowcount > 0:
                return True

            # En MySQL rowcount es 0 tanto si no existe el registro como si el nivel era idéntico.
            cursor.execute(
                f"SELECT 1 FROM {tabla} WHERE usuario_id = %s AND {columna} = %s LIMIT 1",
                (usuario_id, item_id),
            )
            return cursor.fetchone() is not None
        except Exception:
            if conn is not None:
                conn.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()

    @staticmethod
    def eliminar(usuario_id: int, tipo: str, item_id: int) -> bool:
        """Elimina una tecnología o lenguaje del perfil del usuario autenticado."""
        if tipo not in _TABLAS_HABILIDAD:
            raise ValueError("El tipo de habilidad debe ser 'tecnologia' o 'lenguaje'.")

        tabla, columna = _TABLAS_HABILIDAD[tipo]
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            if tipo == "lenguaje":
                asegurar_tabla_usuario_lenguajes(cursor)

            cursor.execute(
                f"DELETE FROM {tabla} WHERE usuario_id = %s AND {columna} = %s",
                (usuario_id, item_id),
            )
            conn.commit()
            return cursor.rowcount == 1
        except Exception:
            if conn is not None:
                conn.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()

    @staticmethod
    def asociar(usuario_id, tecnologia_id, nivel):
        """Alias compatible para asociar una tecnología al usuario."""
        return Habilidad.crear(usuario_id, "tecnologia", tecnologia_id, nivel)


Habilidad.cargar_schemas()
