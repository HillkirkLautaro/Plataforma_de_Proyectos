import json
from pathlib import Path

from config.db import get_db_connection


SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"


class Habilidad:
    @classmethod
    def cargar_schemas(cls):
        cls.SCHEMA = json.loads(
            (SCHEMAS_DIR / "habilidad.schema.json").read_text(encoding="utf-8")
        )

    @staticmethod
    def asociar(usuario_id, tecnologia_id, nivel):
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO usuario_habilidades (usuario_id, tecnologia_id, nivel)
            VALUES (%s, %s, %s)
        """
        cursor.execute(query, (usuario_id, tecnologia_id, nivel))
        conn.commit()
        res_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return res_id


Habilidad.cargar_schemas()
