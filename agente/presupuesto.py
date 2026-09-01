"""Tope diario de llamadas al modelo de lenguaje.

Por qué existe
--------------
``/interpretar`` es un endpoint **público y sin autenticación**, y el enlace se
reparte en clase. Cada llamada al modelo gasta unos 900 tokens de entrada y
hasta 600 de salida; el límite de peticiones son 60 por minuto **y por IP**, que
para un uso normal sobra y para un abuso no estorba: una sola IP sostenida
supera las tres mil llamadas por hora.

Sin un tope, un enlace público con un modelo de pago detrás es una factura
abierta. Con él, el peor caso está acotado y es conocido de antemano.

Cómo falla
----------
Al agotarse el presupuesto, ``hay_saldo()`` devuelve ``False`` y el agente cae
al **modo degradado**, que es la misma ruta que ya se usa cuando no hay clave:
plantillas deterministas construidas sobre las cifras reales. La aplicación
sigue funcionando igual, con menos variedad de estilo y ninguna interrupción.

Esa es la propiedad que hace aceptable el tope: agotarlo no rompe nada.

Limitación conocida
-------------------
El contador vive en memoria. Si el servicio se reinicia —y en el plan gratuito
de Render se duerme tras quince minutos sin visitas— el presupuesto vuelve a
empezar. Es una protección contra el abuso sostenido de una sesión, no una
contabilidad exacta.

Para un tope estricto haría falta un almacén compartido, que en este proyecto
sería más infraestructura que el problema que resuelve. Si algún día importa
llevar la cuenta al céntimo, el sitio donde cambiarlo es este archivo.
"""

from __future__ import annotations

import logging
import os
import threading
from datetime import date

log = logging.getLogger(__name__)

#: Llamadas al modelo permitidas por día. Con el coste aproximado de una
#: interpretación, doscientas acotan el gasto diario a algo asumible para un
#: trabajo de curso, y son muchas más de las que produce un uso real: en una
#: sustentación con treinta personas probando dos veces cada una se usan
#: sesenta.
LIMITE_DIARIO = int(os.getenv("LLM_LIMITE_DIARIO", "200"))

_candado = threading.Lock()
_dia = date.today()
_usadas = 0


def hay_saldo() -> bool:
    """Indica si queda presupuesto para llamar al modelo hoy."""
    _reiniciar_si_cambio_el_dia()
    return _usadas < LIMITE_DIARIO


def registrar_uso() -> None:
    """Anota una llamada consumida.

    Se llama **después** de que la petición al modelo haya salido, no antes: si
    contara los intentos fallidos, un proveedor caído agotaría el presupuesto
    del día sin haber redactado una sola respuesta.
    """
    global _usadas
    with _candado:
        _reiniciar_si_cambio_el_dia()
        _usadas += 1
        if _usadas == LIMITE_DIARIO:
            log.warning("Presupuesto diario del modelo agotado (%s llamadas). "
                        "El agente pasa a plantillas hasta mañana.", LIMITE_DIARIO)


def estado() -> dict:
    """Devuelve el consumo del día, para exponerlo en ``/health``."""
    _reiniciar_si_cambio_el_dia()
    return {"usadas": _usadas, "limite": LIMITE_DIARIO,
            "restantes": max(0, LIMITE_DIARIO - _usadas)}


def _reiniciar_si_cambio_el_dia() -> None:
    """Pone el contador a cero cuando cambia la fecha."""
    global _dia, _usadas
    hoy = date.today()
    if hoy != _dia:
        _dia, _usadas = hoy, 0
