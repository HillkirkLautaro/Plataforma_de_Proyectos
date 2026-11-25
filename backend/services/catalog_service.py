"""Sincronización, caché, respaldo en MySQL y validación de catálogos externos."""

import os
import requests
from cachetools import TTLCache
from flask import current_app
from werkzeug.exceptions import (
    BadGateway,
    GatewayTimeout,
    InternalServerError,
    TooManyRequests,
    Unauthorized,
)

from config.utilsdb.db_backup import leer_backup_bd, sincronizar_backup_bd

MENSAJE_CATALOGO_NO_DISPONIBLE = (
    "El catálogo de tecnologías y lenguajes no está disponible en este momento. "
    "Intenta nuevamente en unos minutos."
)
MENSAJE_CATALOGO_SATURADO = (
    "El catálogo de tecnologías y lenguajes está recibiendo muchas solicitudes en este momento. "
    "Intenta nuevamente en unos minutos."
)
MENSAJE_CATALOGO_TIMEOUT = (
    "El catálogo de tecnologías y lenguajes tardó demasiado en responder. "
    "Intenta nuevamente en unos minutos."
)

CATALOG_CACHE_TTL = int(os.environ.get("CATALOG_CACHE_TTL", "300"))
cache = TTLCache(maxsize=10, ttl=CATALOG_CACHE_TTL)


class CatalogUnavailable(Exception):
    """El catálogo remoto y su respaldo no pudieron confirmar la validez del ID."""


def invalidar_cache_catalogo(recurso: str | None = None):
    """Limpia la caché en memoria para un recurso específico o para todos."""
    if recurso is None:
        cache.clear()
    else:
        cache.pop(recurso, None)


def extraer_lista_catalogo(datos, recurso: str) -> list:
    """Extrae la lista de elementos desde la respuesta directa o envuelta en diccionario."""
    if isinstance(datos, list):
        return datos
    if isinstance(datos, dict):
        for clave in ("data", recurso, "results", "items"):
            if isinstance(datos.get(clave), list):
                return datos[clave]
        return next((v for v in datos.values() if isinstance(v, list)), [])
    return []


def obtener_catalogo(recurso: str, forzar_recarga: bool = False):
    """Obtiene el catálogo desde caché TTL, API externa o respaldo persistente en MySQL.

    Flujo:
    - Si hay caché vigente y no se fuerza recarga, devuelve desde caché.
    - Al expirar el TTL (o con forzar_recarga=True), consulta la API externa:
      * 200 OK: actualiza caché y sobrescribe atómicamente el respaldo en MySQL
        (reflejando altas, modificaciones y eliminaciones).
      * 401: propaga el error sin ocultarlo detrás del respaldo.
      * Timeout / 429 / 5xx / error de red: intenta fallback desde el respaldo en MySQL
        (y actualiza caché); si no hay respaldo, intenta caché existente o propaga el error.
    """
    if not forzar_recarga and recurso in cache:
        return cache[recurso]

    profesor_url = os.environ.get("PROFESOR_API_URL", "").strip()
    access_key = os.environ.get("GRUPO_ACCESS_KEY", "").strip()

    if not profesor_url:
        current_app.logger.error("La variable de entorno PROFESOR_API_URL no está configurada.")
        raise InternalServerError(description=MENSAJE_CATALOGO_NO_DISPONIBLE)

    if not access_key:
        current_app.logger.error("La variable de entorno GRUPO_ACCESS_KEY no está configurada.")
        raise InternalServerError(description=MENSAJE_CATALOGO_NO_DISPONIBLE)

    headers = {
        "Grupo-Access-Key": access_key,
        "Content-Type": "application/json",
    }
    url = f"{profesor_url.rstrip('/')}/{recurso}"

    try:
        resp = requests.get(url, headers=headers, timeout=5)

        if resp.status_code == 200:
            try:
                datos = resp.json()
            except ValueError as exc:
                current_app.logger.error(
                    "La respuesta del catálogo '%s' no es un JSON válido: %s", recurso, exc
                )
                raise BadGateway(description=MENSAJE_CATALOGO_NO_DISPONIBLE) from exc

            cache[recurso] = datos
            sincronizar_backup_bd(recurso, datos)
            return datos

        if resp.status_code == 401:
            current_app.logger.error(
                "Grupo-Access-Key no autorizada o vencida al consultar '%s' (HTTP 401).", recurso
            )
            raise Unauthorized(description=MENSAJE_CATALOGO_NO_DISPONIBLE)

        if resp.status_code == 429:
            current_app.logger.warning(
                "La API externa limitó las solicitudes para '%s' (HTTP 429).", recurso
            )
            raise TooManyRequests(description=MENSAJE_CATALOGO_SATURADO)

        current_app.logger.warning(
            "La API externa respondió HTTP %s para '%s'.", resp.status_code, recurso
        )
        raise BadGateway(description=MENSAJE_CATALOGO_NO_DISPONIBLE)

    except Unauthorized:
        # Un 401 indica problema de credenciales propias; no debe ocultarse con caché/backup.
        raise

    except (TooManyRequests, BadGateway, requests.exceptions.Timeout, requests.exceptions.RequestException) as err:
        backup = leer_backup_bd(recurso)
        if backup is not None:
            current_app.logger.warning(
                "API externa no disponible para '%s'. Sirviendo desde backup en BD.", recurso
            )
            cache[recurso] = backup
            return backup

        if recurso in cache:
            current_app.logger.warning(
                "API externa no disponible y sin backup en BD para '%s'. Sirviendo desde caché en memoria.",
                recurso,
            )
            return cache[recurso]

        if isinstance(err, TooManyRequests):
            raise
        if isinstance(err, requests.exceptions.Timeout):
            current_app.logger.warning(
                "Tiempo de espera agotado al consultar el catálogo '%s'.", recurso
            )
            raise GatewayTimeout(description=MENSAJE_CATALOGO_TIMEOUT)
        if isinstance(err, requests.exceptions.RequestException):
            current_app.logger.warning(
                "Error de comunicación con la API externa para '%s': %s", recurso, err
            )
        raise BadGateway(description=MENSAJE_CATALOGO_NO_DISPONIBLE)


def validar_ids_catalogo(recurso: str, ids):
    """Valida que todos los IDs existan en la versión sincronizada del catálogo.

    Prioriza consultar la API externa (actualizando caché y backup en MySQL) para
    rechazar inmediatamente IDs eliminados, y hace fallback a backup/caché si la API cae.
    """
    if not ids:
        return

    try:
        datos = obtener_catalogo(recurso, forzar_recarga=True)
    except (BadGateway, GatewayTimeout, Unauthorized, TooManyRequests, InternalServerError) as exc:
        raise CatalogUnavailable(exc.description) from exc

    try:
        lista = extraer_lista_catalogo(datos, recurso)
        disponibles = {int(row["id"]) for row in lista if isinstance(row, dict) and "id" in row}
    except (ValueError, TypeError, KeyError) as exc:
        current_app.logger.error("Respuesta con formato inválido del catálogo '%s': %s", recurso, exc)
        raise CatalogUnavailable(MENSAJE_CATALOGO_NO_DISPONIBLE) from exc

    inexistentes = set(ids) - disponibles
    if inexistentes:
        current_app.logger.warning("IDs inexistentes en catálogo '%s': %s", recurso, sorted(inexistentes))
        if recurso == "tecnologias":
            raise ValueError("Algunas de las tecnologías seleccionadas no son válidas o ya no están disponibles.")
        if recurso == "lenguajes":
            raise ValueError("Algunos de los lenguajes seleccionados no son válidos o ya no están disponibles.")
        raise ValueError("Algunas de las opciones seleccionadas no son válidas o ya no están disponibles.")
