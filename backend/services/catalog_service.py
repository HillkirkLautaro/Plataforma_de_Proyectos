"""Validación estricta de IDs contra los catálogos de la API del profesor."""

import os
import requests
from flask import current_app


class CatalogUnavailable(Exception):
    """El catálogo remoto no pudo confirmar la validez del ID."""


def validar_ids_catalogo(recurso, ids):
    if not ids:
        return
    base = os.environ.get("PROFESOR_API_URL", "").rstrip("/")
    key = os.environ.get("GRUPO_ACCESS_KEY", "")
    if not base or not key:
        raise CatalogUnavailable("La integración con el catálogo no está configurada")
    try:
        response = requests.get(f"{base}/{recurso}", headers={"Grupo-Access-Key": key}, timeout=5)
    except requests.RequestException as exc:
        raise CatalogUnavailable("No se pudo consultar el catálogo del profesor") from exc
    if response.status_code == 401:
        raise CatalogUnavailable("La clave de acceso al catálogo fue rechazada")
    if response.status_code == 429:
        raise CatalogUnavailable("El catálogo del profesor limitó las solicitudes; reintentá más tarde")
    if response.status_code != 200:
        raise CatalogUnavailable("El catálogo del profesor no está disponible")
    try:
        body = response.json()
        if isinstance(body, dict):
            body = body.get("data", body.get(recurso, body.get("results", [])))
        disponibles = {int(row["id"]) for row in body if isinstance(row, dict) and "id" in row}
    except (ValueError, TypeError, KeyError) as exc:
        raise CatalogUnavailable("La respuesta del catálogo tiene un formato inválido") from exc
    inexistentes = set(ids) - disponibles
    if inexistentes:
        raise ValueError(f"IDs inexistentes en catálogo {recurso}: {sorted(inexistentes)}")
