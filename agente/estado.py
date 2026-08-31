"""Estado compartido del grafo del agente."""

from __future__ import annotations

from typing import TypedDict


class EstadoAgente(TypedDict, total=False):
    """Estado que fluye entre los nodos del grafo.

    Attributes
    ----------
    entrada_usuario : str
        Consulta libre o descripción del caso.
    perfil : dict or None
        Variables del caso: edad, sexo, región, exposiciones.
    prediccion : dict or None
        Probabilidad, categoría de riesgo y factores contribuyentes.
    contexto_epidemiologico : list of str
        Hallazgos recuperados de ``resultados/`` que sitúan el perfil.
    borrador : str or None
        Interpretación redactada, aún sin verificar.
    veredicto_seguridad : str or None
        ``"aprobado"``, ``"reescribir"`` o ``"bloqueado"``.
    motivo_rechazo : str or None
        Por qué el guardrail rechazó el borrador.
    intentos : int
        Contador para no reescribir indefinidamente.
    modo : str
        ``"llm"`` si se usó un modelo de lenguaje, ``"degradado"`` si no.
    salida_final : str or None
        Texto listo para mostrar, con disclaimer y línea de ayuda.
    hay_crisis : bool
        Si la detección determinista encontró señales de crisis.
    motivos_crisis : list of str
        Qué disparó la detección.
    recursos_ofrecidos : list of str
        Identificadores del catálogo verificado, nunca texto libre del modelo.
    recursos_texto : str
        Los recursos ya formateados por el código.
    trazas : list of dict
        Registro por nodo: nombre, duración y resumen.
    """

    entrada_usuario: str
    perfil: dict | None
    prediccion: dict | None
    contexto_epidemiologico: list[str]
    #: Tasa realmente observada en la ENDES para perfiles
    #: parecidos. Encabeza la respuesta cuando existe: es un
    #: recuento, no un pronóstico.
    tasa_observada: dict | None
    borrador: str | None
    veredicto_seguridad: str | None
    motivo_rechazo: str | None
    intentos: int
    modo: str
    salida_final: str | None
    trazas: list[dict]
    hay_crisis: bool
    motivos_crisis: list[str]
    recursos_ofrecidos: list[str]
    recursos_texto: str
