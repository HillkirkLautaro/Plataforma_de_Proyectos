import json
from pathlib import Path

from werkzeug.security import generate_password_hash, check_password_hash
from config.db import get_db_connection
from models.habilidad import asegurar_tabla_usuario_lenguajes


SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"


class Usuario:
    CAMPOS_PERFIL = {"nombre_completo", "bio"}

    @classmethod
    def cargar_schemas(cls):
        cls.SCHEMA_REGISTRO = json.loads(
            (SCHEMAS_DIR / "usuario.schema.json").read_text(encoding="utf-8")
        )
        cls.SCHEMA_LOGIN = json.loads(
            (SCHEMAS_DIR / "login.schema.json").read_text(encoding="utf-8")
        )
        cls.SCHEMA_PERFIL_PATCH = json.loads(
            (SCHEMAS_DIR / "perfil_actualizar.schema.json").read_text(encoding="utf-8")
        )
        cls.SCHEMA_PERFIL_PUT = json.loads(
            (SCHEMAS_DIR / "perfil_reemplazar.schema.json").read_text(encoding="utf-8")
        )
        cls.SCHEMA_PERFIL_ACTUALIZAR = cls.SCHEMA_PERFIL_PATCH

    def __init__(self, id=None, username="", email="", password_hash="", nombre_completo="", bio="", rol="usuario"):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.nombre_completo = nombre_completo
        self.bio = bio
        self.rol = rol

    @staticmethod
    def crear(username, email, password_plano, nombre_completo="", bio=""):
        conn = get_db_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            hashed = generate_password_hash(password_plano, method="scrypt")
            query = """
                INSERT INTO usuarios (username, email, password_hash, nombre_completo, bio)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (username, email, hashed, nombre_completo, bio))
            conn.commit()
            return cursor.lastrowid
        except Exception:
            conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @staticmethod
    def obtener_por_credencial(identificador):
        conn = get_db_connection()
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT id, username, email, password_hash, rol FROM usuarios
                WHERE email = %s OR username = %s
                LIMIT 1
            """
            cursor.execute(query, (identificador, identificador))
            return cursor.fetchone()
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @classmethod
    def listar_publicos(cls):
        """Obtiene el directorio público de desarrolladores con su conteo de proyectos."""
        conn = get_db_connection()
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT u.id, u.username, u.nombre_completo, u.bio,
                       COUNT(p.id) AS cantidad_proyectos
                FROM usuarios u
                LEFT JOIN proyectos p ON p.usuario_id = u.id
                GROUP BY u.id, u.username, u.nombre_completo, u.bio
                ORDER BY u.username
            """
            cursor.execute(query)
            return cursor.fetchall()
        finally:
            if cursor:
                cursor.close()
            conn.close()

    @classmethod
    def obtener_portafolio_publico(cls, usuario_id):
        """Obtiene los datos públicos del perfil y las habilidades de un usuario."""
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT id, username, nombre_completo, bio FROM usuarios WHERE id = %s",
                (usuario_id,)
            )
            perfil = cursor.fetchone()

            if not perfil:
                return None

            cursor.execute(
                "SELECT tecnologia_id, nivel FROM usuario_habilidades WHERE usuario_id = %s",
                (usuario_id,)
            )
            habilidades = cursor.fetchall()

            asegurar_tabla_usuario_lenguajes(cursor)
            cursor.execute(
                "SELECT lenguaje_id, nivel FROM usuario_lenguajes WHERE usuario_id = %s",
                (usuario_id,)
            )
            lenguajes = cursor.fetchall()

            return {
                "perfil": perfil,
                "habilidades": habilidades,
                "lenguajes": lenguajes,
            }
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()

    @staticmethod
    def obtener_perfil_privado(usuario_id: int):
        """Obtiene los datos privados del perfil del usuario autenticado."""
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT id, username, email, nombre_completo, bio FROM usuarios WHERE id = %s",
                (usuario_id,),
            )
            return cursor.fetchone()
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()

    @classmethod
    def actualizar_perfil(cls, usuario_id: int, datos: dict):
        """Actualiza nombre_completo y/o bio del usuario autenticado."""
        cambios = {k: v for k, v in datos.items() if k in cls.CAMPOS_PERFIL}
        if not cambios:
            return cls.obtener_perfil_privado(usuario_id)

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id FROM usuarios WHERE id = %s", (usuario_id,))
            if cursor.fetchone() is None:
                return None

            sets = ", ".join(f"{campo} = %s" for campo in cambios)
            cursor.execute(
                f"UPDATE usuarios SET {sets} WHERE id = %s",
                (*cambios.values(), usuario_id),
            )
            conn.commit()

            cursor.execute(
                "SELECT id, username, email, nombre_completo, bio FROM usuarios WHERE id = %s",
                (usuario_id,),
            )
            return cursor.fetchone()
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
    def verificar_password(password_hash, password_plano):
        return check_password_hash(password_hash, password_plano)


Usuario.cargar_schemas()