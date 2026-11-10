"""Persistencia SQL de proyectos y relaciones con catálogos externos."""

from config.db import get_db_connection


class Proyecto:
    ETAPAS = {"formulación", "modelado", "implementación", "testing", "producción", "mantenimiento"}
    CAMPOS = {"nombre", "descripcion", "etapa", "fecha_inicio", "fecha_fin", "deadline"}

    @staticmethod
    def listar_usuario(usuario_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # Evita JSON_ARRAYAGG para compatibilidad con versiones antiguas de MySQL/MariaDB.
            cursor.execute("""SELECT id, nombre, descripcion, etapa, fecha_inicio,
                fecha_fin, deadline, created_at, updated_at
                FROM proyectos WHERE usuario_id=%s ORDER BY updated_at DESC""", (usuario_id,))
            proyectos = cursor.fetchall()
            if not proyectos:
                return proyectos

            proyecto_ids = [proyecto["id"] for proyecto in proyectos]
            placeholders = ",".join(["%s"] * len(proyecto_ids))
            cursor.execute(f"""SELECT proyecto_id, tecnologia_id, nivel FROM proyecto_tecnologias
                WHERE proyecto_id IN ({placeholders})""", tuple(proyecto_ids))
            tecnologias = {}
            for row in cursor.fetchall():
                tecnologias.setdefault(row["proyecto_id"], []).append(
                    {"id": row["tecnologia_id"], "nivel": row["nivel"]})

            cursor.execute(f"""SELECT proyecto_id, lenguaje_id, nivel FROM proyecto_lenguajes
                WHERE proyecto_id IN ({placeholders})""", tuple(proyecto_ids))
            lenguajes = {}
            for row in cursor.fetchall():
                lenguajes.setdefault(row["proyecto_id"], []).append(
                    {"id": row["lenguaje_id"], "nivel": row["nivel"]})

            for proyecto in proyectos:
                proyecto["tecnologias"] = tecnologias.get(proyecto["id"], [])
                proyecto["lenguajes"] = lenguajes.get(proyecto["id"], [])
            cursor.execute(f"""SELECT proyecto_id, tipo, url FROM proyecto_links
                WHERE proyecto_id IN ({placeholders}) ORDER BY id""", tuple(proyecto_ids))
            links = {}
            for row in cursor.fetchall():
                links.setdefault(row["proyecto_id"], []).append({"tipo": row["tipo"], "url": row["url"]})
            for proyecto in proyectos:
                proyecto["links"] = links.get(proyecto["id"], [])
            return proyectos
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def obtener(usuario_id, proyecto_id):
        return next((p for p in Proyecto.listar_usuario(usuario_id) if p["id"] == proyecto_id), None)

    @staticmethod
    def guardar(usuario_id, datos, proyecto_id=None):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            if proyecto_id is None:
                cursor.execute("""INSERT INTO proyectos
                    (usuario_id,nombre,descripcion,etapa,fecha_inicio,fecha_fin,deadline)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)""", (
                    usuario_id, datos["nombre"], datos.get("descripcion", ""), datos.get("etapa", "formulación"),
                    datos.get("fecha_inicio"), datos.get("fecha_fin"), datos.get("deadline")))
                proyecto_id = cursor.lastrowid
            else:
                # Bloqueo y comprobación de propiedad dentro de la misma transacción.
                # Se hace antes de actualizar campos o relaciones M:N, incluso si
                # el payload solo contiene tecnologías/lenguajes.
                cursor.execute("SELECT id FROM proyectos WHERE id=%s AND usuario_id=%s FOR UPDATE",
                               (proyecto_id, usuario_id))
                if cursor.fetchone() is None:
                    raise LookupError("Proyecto inexistente")
                cambios = {k: v for k, v in datos.items() if k in Proyecto.CAMPOS}
                if cambios:
                    sets = ", ".join(f"{campo}=%s" for campo in cambios)
                    cursor.execute(f"UPDATE proyectos SET {sets} WHERE id=%s AND usuario_id=%s",
                                   (*cambios.values(), proyecto_id, usuario_id))

            for campo, tabla, columna in (("tecnologias", "proyecto_tecnologias", "tecnologia_id"),
                                           ("lenguajes", "proyecto_lenguajes", "lenguaje_id")):
                if campo in datos:
                    cursor.execute(f"DELETE FROM {tabla} WHERE proyecto_id=%s", (proyecto_id,))
                    relaciones = datos[campo]
                    if relaciones:
                        cursor.executemany(
                            f"INSERT INTO {tabla} (proyecto_id,{columna},nivel) VALUES (%s,%s,%s)",
                            [(proyecto_id, item["id"], item["nivel"]) for item in relaciones],
                        )
            if "links" in datos:
                cursor.execute("DELETE FROM proyecto_links WHERE proyecto_id=%s", (proyecto_id,))
                if datos["links"]:
                    cursor.executemany(
                        "INSERT INTO proyecto_links (proyecto_id,tipo,url) VALUES (%s,%s,%s)",
                        [(proyecto_id, link["tipo"], link["url"]) for link in datos["links"]],
                    )
            conn.commit()
            return proyecto_id
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def eliminar(usuario_id, proyecto_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM proyectos WHERE id=%s AND usuario_id=%s", (proyecto_id, usuario_id))
            conn.commit()
            return cursor.rowcount == 1
        finally:
            cursor.close()
            conn.close()
