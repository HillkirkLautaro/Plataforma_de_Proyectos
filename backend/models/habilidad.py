from config.db import get_db_connection

class Habilidad:
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
