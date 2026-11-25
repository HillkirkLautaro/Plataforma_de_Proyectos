"""Validación de JSON Schema con traducción de errores a mensajes claros en español."""

import re

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

NOMBRES_CAMPOS = {
    "username": "nombre de usuario",
    "email": "correo electrónico",
    "password": "contraseña",
    "nombre_completo": "nombre completo",
    "bio": "biografía",
    "nombre": "nombre del proyecto",
    "descripcion": "descripción",
    "etapa": "etapa",
    "fecha_inicio": "fecha de inicio",
    "fecha_fin": "fecha de finalización",
    "deadline": "fecha límite",
    "tecnologias": "tecnologías",
    "lenguajes": "lenguajes",
    "links": "enlaces",
    "tipo": "tipo",
    "url": "URL",
    "nivel": "nivel",
    "id": "identificador",
    "tecnologia_id": "tecnología",
}

CAMPOS_FECHA = {"fecha_inicio", "fecha_fin", "deadline"}


def _etiqueta_campo(nombre: str) -> str:
    return NOMBRES_CAMPOS.get(nombre, nombre.replace("_", " "))


def _obtener_campo_desde_path(path) -> tuple[str | None, str | None]:
    """Devuelve (clave_tecnica, etiqueta_amigable) del campo más específico en exc.path."""
    partes_texto = [p for p in path if isinstance(p, str)]
    if not partes_texto:
        return None, None
    clave = partes_texto[-1]
    return clave, _etiqueta_campo(clave)


def _extraer_campo_requerido(exc: ValidationError) -> str | None:
    if isinstance(exc.instance, dict) and isinstance(exc.validator_value, list):
        for prop in exc.validator_value:
            if prop not in exc.instance:
                return prop
    match = re.search(r"'([^']+)'", exc.message or "")
    return match.group(1) if match else None


def _traducir_any_of(exc: ValidationError, clave: str | None, etiqueta: str | None) -> str:
    # Caso login: requiere username o email
    if isinstance(exc.validator_value, list):
        requeridos = [
            sub.get("required", [])
            for sub in exc.validator_value
            if isinstance(sub, dict) and "required" in sub
        ]
        if ["username"] in requeridos and ["email"] in requeridos:
            return "Debes ingresar tu nombre de usuario o correo electrónico."

    # Caso fechas opcionales (date | null)
    if clave in CAMPOS_FECHA:
        return f"El formato ingresado en '{etiqueta}' no es válido. Usa el formato AAAA-MM-DD."

    if etiqueta:
        return f"El formato ingresado en '{etiqueta}' no es válido."
    return "El formato de los datos enviados no es correcto."


def _traducir_one_of(exc: ValidationError, clave: str | None, etiqueta: str | None) -> str:
    # Cuando una referencia de catálogo es un objeto con campos inválidos,
    # priorizamos el suberror específico del esquema de objeto.
    if exc.context and isinstance(exc.instance, dict):
        suberrores_objeto = [
            sub for sub in exc.context
            if sub.validator != "type" or sub.path
        ]
        if suberrores_objeto:
            return traducir_error_validacion(suberrores_objeto[0])

    if exc.context and isinstance(exc.instance, int) and not isinstance(exc.instance, bool):
        suberrores_entero = [
            sub for sub in exc.context
            if sub.validator == "minimum"
        ]
        if suberrores_entero:
            return traducir_error_validacion(suberrores_entero[0])

    if etiqueta:
        return f"El formato de los datos enviados en '{etiqueta}' no es correcto."
    return "El formato de los datos enviados no es correcto."


def traducir_error_validacion(exc: ValidationError) -> str:
    """Convierte un ValidationError de jsonschema en un mensaje claro en español."""
    validator = exc.validator
    limite = exc.validator_value
    clave, etiqueta = _obtener_campo_desde_path(exc.path)

    if validator == "required":
        campo_faltante = _extraer_campo_requerido(exc)
        if campo_faltante:
            return f"Falta completar el campo obligatorio: {_etiqueta_campo(campo_faltante)}."
        return "Falta completar un campo obligatorio."

    if validator == "minLength":
        unidad = "carácter" if limite == 1 else "caracteres"
        if etiqueta:
            return f"El campo '{etiqueta}' debe tener al menos {limite} {unidad}."
        return f"El texto ingresado debe tener al menos {limite} {unidad}."

    if validator == "maxLength":
        if etiqueta:
            return f"El campo '{etiqueta}' no puede superar los {limite} caracteres."
        return f"El texto ingresado no puede superar los {limite} caracteres."

    if validator in ("pattern", "format"):
        if clave == "email" or limite == "email":
            return "El formato del correo electrónico no es válido."
        if clave in CAMPOS_FECHA or limite == "date":
            campo = etiqueta or "fecha"
            return f"El formato ingresado en '{campo}' no es válido. Usa el formato AAAA-MM-DD."
        if clave == "url" or limite == "uri":
            return "El formato ingresado en 'URL' no es válido. Debe comenzar con http:// o https://."
        if clave == "username":
            return "El formato ingresado en 'nombre de usuario' no es válido. Solo se permiten letras, números y los símbolos . _ -"
        if etiqueta:
            return f"El formato ingresado en '{etiqueta}' no es válido."
        return "El formato de los datos enviados no es válido."

    if validator == "enum":
        if etiqueta:
            return f"El valor seleccionado para '{etiqueta}' no es válido."
        return "El valor seleccionado no es válido."

    if validator == "additionalProperties":
        return "Se enviaron datos no permitidos en la solicitud."

    if validator == "type":
        if etiqueta:
            return f"El formato de los datos enviados en '{etiqueta}' no es correcto."
        return "El formato de los datos enviados no es correcto."

    if validator == "minProperties":
        return "Debes enviar al menos un campo para actualizar."

    if validator == "minItems":
        if clave == "tecnologias" and limite == 1:
            return "Debes seleccionar al menos una tecnología para el proyecto."
        if clave == "lenguajes" and limite == 1:
            return "Debes seleccionar al menos un lenguaje de programación para el proyecto."
        unidad = "elemento" if limite == 1 else "elementos"
        if etiqueta:
            return f"El campo '{etiqueta}' debe tener al menos {limite} {unidad}."
        return f"Debes incluir al menos {limite} {unidad}."

    if validator == "maxItems":
        if etiqueta:
            return f"El campo '{etiqueta}' no puede tener más de {limite} elementos."
        return f"No se pueden enviar más de {limite} elementos."

    if validator == "uniqueItems":
        if etiqueta:
            return f"No se permiten elementos repetidos en '{etiqueta}'."
        return "No se permiten elementos repetidos."

    if validator == "minimum":
        if etiqueta:
            return f"El campo '{etiqueta}' debe ser mayor o igual a {limite}."
        return f"El valor ingresado debe ser mayor o igual a {limite}."

    if validator == "maximum":
        if etiqueta:
            return f"El campo '{etiqueta}' no puede ser mayor a {limite}."
        return f"El valor ingresado no puede ser mayor a {limite}."

    if validator == "anyOf":
        return _traducir_any_of(exc, clave, etiqueta)

    if validator == "oneOf":
        return _traducir_one_of(exc, clave, etiqueta)

    return "Los datos enviados no son válidos. Revisa la información e intenta nuevamente."


def validar_schema(data, schema) -> str | None:
    """Valida data contra schema y devuelve un mensaje amigable en español si falla."""
    if data is None:
        return "No se recibieron datos válidos en la solicitud."
    try:
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(data)
    except ValidationError as exc:
        return traducir_error_validacion(exc)
    return None
