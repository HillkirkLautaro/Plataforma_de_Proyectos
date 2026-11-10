from werkzeug.security import generate_password_hash, check_password_hash
from config.db import get_db_connection

class Usuario:
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

    @staticmethod
    def verificar_password(password_hash, password_plano):
        return check_password_hash(password_hash, password_plano)
