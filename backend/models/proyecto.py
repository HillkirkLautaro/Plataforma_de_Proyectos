"""Persistencia SQL de proyectos y relaciones con catálogos externos."""

from datetime import date, datetime
import json
from pathlib import Path

from config.db import get_db_connection


SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"


class Proyecto:
    ETAPAS = {"formulación", "modelado", "implementación", "testing", "producción", "mantenimiento"}
    ETAPAS_SIN_FECHA_FIN = {"formulación", "modelado"}
    CAMPOS = {"nombre", "descripcion", "etapa", "fecha_inicio", "fecha_fin", "deadline"}
    FECHA_MINIMA = date(1990, 1, 1)
    MAX_ANIOS_FUTURO = 10

    @classmethod
    def _fecha_maxima(cls) -> date:
        hoy = date.today()
        try:
            return hoy.replace(year=hoy.year + cls.MAX_ANIOS_FUTURO)
        except ValueError:
            # Manejo seguro de año bisiesto (29 de febrero)
            return hoy.replace(year=hoy.year + cls.MAX_ANIOS_FUTURO, day=28)

    @staticmethod
    def _parsear_fecha(valor, etiqueta: str) -> date | None:
        if valor is None:
            return None
        if isinstance(valor, datetime):
            return valor.date()
        if isinstance(valor, date):
            return valor
        if isinstance(valor, str):
            try:
                return date.fromisoformat(valor)
            except ValueError as exc:
                raise ValueError(
                    f"El formato ingresado en '{etiqueta}' no es válido. Usa el formato AAAA-MM-DD."
                ) from exc
        raise ValueError(f"El formato ingresado en '{etiqueta}' no es válido. Usa el formato AAAA-MM-DD.")

    @classmethod
    def validar_reglas_negocio(cls, datos: dict, proyecto_actual: dict | None = None, crear: bool = False):
        """Valida plausibilidad de fechas, coherencia de etapa y obligatoriedad de tecnologías y lenguajes."""
        # 1. Obligatoriedad de al menos una tecnología y un lenguaje
        if crear:
            sin_tec = not datos.get("tecnologias")
            sin_len = not datos.get("lenguajes")
            if sin_tec and sin_len:
                raise ValueError("El proyecto debe incluir al menos una tecnología y un lenguaje de programación.")
            if sin_tec:
                raise ValueError("Debes seleccionar al menos una tecnología para el proyecto.")
            if sin_len:
                raise ValueError("Debes seleccionar al menos un lenguaje de programación para el proyecto.")
        else:
            if "tecnologias" in datos and len(datos["tecnologias"]) < 1:
                raise ValueError("Debes seleccionar al menos una tecnología para el proyecto.")
            if "lenguajes" in datos and len(datos["lenguajes"]) < 1:
                raise ValueError("Debes seleccionar al menos un lenguaje de programación para el proyecto.")

        # 2. Resolver valores efectivos (en PUT parcial se combinan con lo guardado en BD)
        base = proyecto_actual or {}
        raw_inicio = datos["fecha_inicio"] if "fecha_inicio" in datos else base.get("fecha_inicio")
        raw_fin = datos["fecha_fin"] if "fecha_fin" in datos else base.get("fecha_fin")
        raw_deadline = datos["deadline"] if "deadline" in datos else base.get("deadline")
        etapa = datos["etapa"] if "etapa" in datos else base.get("etapa", "formulación")

        fecha_inicio = cls._parsear_fecha(raw_inicio, "fecha de inicio")
        fecha_fin = cls._parsear_fecha(raw_fin, "fecha de finalización")
        deadline = cls._parsear_fecha(raw_deadline, "fecha límite")

        # 3. Rango temporal plausible
        fecha_maxima = cls._fecha_maxima()
        for fecha, etiqueta in (
            (fecha_inicio, "fecha de inicio"),
            (fecha_fin, "fecha de finalización"),
            (deadline, "fecha límite"),
        ):
            if fecha is None:
                continue
            if fecha < cls.FECHA_MINIMA:
                raise ValueError(f"La {etiqueta} no puede ser anterior al 1 de enero de 1990.")
            if fecha > fecha_maxima:
                raise ValueError(
                    f"La {etiqueta} no puede superar los {cls.MAX_ANIOS_FUTURO} años a partir de hoy "
                    f"({fecha_maxima.isoformat()})."
                )

        # 4. Orden cronológico y coherencia con deadline
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise ValueError("La fecha de finalización no puede ser anterior a la fecha de inicio.")

        if fecha_inicio and deadline and deadline < fecha_inicio:
            raise ValueError("La fecha límite no puede ser anterior a la fecha de inicio.")

        # 5. Coherencia de fecha de finalización según la etapa
        if etapa in cls.ETAPAS_SIN_FECHA_FIN and fecha_fin is not None:
            raise ValueError(
                "No puedes asignar una fecha de finalización mientras el proyecto está en etapa de "
                "formulación o modelado."
            )

    @classmethod
    def cargar_schemas(cls):
        archivos_schema = {
            "proyecto": "proyecto.schema.json",
            "proyecto_crear": "proyecto_crear.schema.json",
            "proyecto_tecnologia": "proyecto_tecnologia.schema.json",
            "proyecto_lenguaje": "proyecto_lenguaje.schema.json",
            "proyecto_link": "proyecto_link.schema.json",
        }
        cls.SCHEMAS = {
            nombre: json.loads((SCHEMAS_DIR / archivo).read_text(encoding="utf-8"))
            for nombre, archivo in archivos_schema.items()
        }

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


Proyecto.cargar_schemas()
