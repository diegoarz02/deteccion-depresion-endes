"""Tests del agente: catálogo de recursos, detección de crisis y guardarraíles.

Aquí no se prueba que el agente escriba bien, sino que **no pueda** hacer daño:
que no invente un teléfono, que no diagnostique y que, ante una señal de crisis,
la respuesta salga de una plantilla revisada y no de un modelo generativo.

Ejecutar con::

    pytest tests/test_agente.py -v
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "agente"))

import guardrails  # noqa: E402
import recursos  # noqa: E402

# ─────────────────────────────────────────────────────────────────────
# Catálogo de recursos
# ─────────────────────────────────────────────────────────────────────


def test_catalogo_declara_cuando_fue_verificado():
    """Un catálogo de teléfonos de ayuda sin fecha de verificación caduca en silencio."""
    c = recursos.catalogo()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", c["_verificado_el"])


def test_todo_recurso_tiene_lo_minimo_para_ser_util():
    """Sin nombre ni descripción, un recurso no orienta a nadie."""
    for r in recursos.catalogo()["recursos"]:
        assert r["nombre"].strip()
        assert r["descripcion"].strip()
        assert r["id"].strip()


def test_los_telefonos_del_catalogo_son_numeros_peruanos():
    """Líneas cortas del Estado o números con formato nacional, nada más."""
    for t in recursos.telefonos_validos():
        limpio = re.sub(r"[\s\-()]", "", t)
        assert re.fullmatch(r"(\+?51)?\d{3,9}", limpio), t


def test_las_urls_del_catalogo_son_de_dominios_del_estado():
    """Un recurso oficial no puede vivir en un dominio cualquiera."""
    for u in recursos.urls_validas():
        assert re.search(r"\.gob\.pe(/|$)", u), u


def test_seleccionar_nunca_devuelve_lista_vacia():
    """Aunque la situación no encaje con ninguna etiqueta, debe quedar algo que ofrecer."""
    assert recursos.seleccionar([])
    assert recursos.seleccionar(["situacion_que_no_existe"])


def test_seleccionar_respeta_el_maximo():
    """Una lista larga de teléfonos no ayuda: abruma."""
    assert len(recursos.seleccionar(["crisis", "general"], maximo=2)) <= 2


def test_formatear_solo_emite_contactos_del_catalogo():
    """El texto que llega al usuario no puede contener un número que no esté verificado."""
    texto = recursos.formatear(recursos.catalogo()["recursos"])
    for t in re.findall(r"\b\d{3,9}\b", texto):
        assert any(t in v.replace(" ", "") for v in recursos.telefonos_validos()), t


# ─────────────────────────────────────────────────────────────────────
# Detección de crisis
# ─────────────────────────────────────────────────────────────────────


def test_item_sensible_activa_la_crisis():
    """Cualquier respuesta distinta de «para nada» en el ítem 9 basta."""
    assert recursos.detectar_crisis(perfil={"item_autolesion": 1})["hay_crisis"]


def test_item_sensible_en_cero_no_la_activa():
    """No se puede disparar con todo el mundo: perdería sentido."""
    assert not recursos.detectar_crisis(perfil={"item_autolesion": 0})["hay_crisis"]


def test_puntaje_severo_activa_la_crisis():
    """PHQ-9 de 20 o más es rango severo."""
    assert recursos.detectar_crisis(perfil={"phq9_score": 20})["hay_crisis"]
    assert not recursos.detectar_crisis(perfil={"phq9_score": 19})["hay_crisis"]


@pytest.mark.parametrize("frase", [
    "ya no quiero seguir viviendo",
    "a veces pienso en quitarme la vida",
    "SIENTO GANAS DE HACERME DAÑO",
    "creo que quiero morirme",
    "estoy pensando en cortarme",
])
def test_senales_en_texto_activan_la_crisis(frase):
    """Se busca con generosidad: un falso negativo cuesta mucho más que uno positivo."""
    assert recursos.detectar_crisis(texto=frase)["hay_crisis"], frase


@pytest.mark.parametrize("frase", [
    "me siento cansada últimamente",
    "quiero saber si tengo riesgo de depresión",
    "mi vecino murió el año pasado",
])
def test_texto_ordinario_no_activa_la_crisis(frase):
    """Hablar de tristeza o de una muerte ajena no es una crisis."""
    assert not recursos.detectar_crisis(texto=frase)["hay_crisis"], frase


def test_deteccion_tolera_valores_basura():
    """La detección corre antes de validar: no puede caerse con un dato mal formado."""
    for basura in ({"item_autolesion": "no sé"}, {"phq9_score": None}, {"phq9_score": ""}):
        assert recursos.detectar_crisis(perfil=basura)["hay_crisis"] is False


def test_la_respuesta_de_crisis_no_pasa_por_ningun_modelo():
    """El texto es fijo y trae recursos reales del catálogo."""
    texto, recs = recursos.respuesta_crisis()
    assert texto.strip()
    assert recs
    assert all(r["id"] in recursos.identificadores_validos() for r in recs)


def test_la_respuesta_de_crisis_no_describe_metodos():
    """Una respuesta de crisis no menciona el cómo. Nunca."""
    texto, _ = recursos.respuesta_crisis()
    for prohibido in ["pastilla", "dosis", "cuchill", "veneno", "arma", "altura"]:
        assert prohibido not in texto.lower()


# ─────────────────────────────────────────────────────────────────────
# Guardarraíles
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("texto", [
    "Usted tiene depresión moderada.",
    "Le recomiendo tomar sertralina 50 mg al día.",
    "Es seguro que no desarrollará ningún trastorno.",
])
def test_se_bloquea_lo_que_no_debe_decir_un_modelo(texto):
    """Diagnóstico, receta y certeza absoluta: las tres se detienen."""
    assert guardrails.verificar(texto)["veredicto"] != "aprobado", texto


def test_un_telefono_inventado_bloquea_la_respuesta():
    """El modelo no escribe contactos; si aparece uno fuera del catálogo, no sale."""
    r = guardrails.verificar("Puedes llamar al 0800 12345 para recibir ayuda.")
    assert r["veredicto"] == "bloqueado"
    assert "contacto" in r["motivo"].lower()


def test_una_url_inventada_bloquea_la_respuesta():
    """Igual que los teléfonos: solo salen enlaces verificados."""
    r = guardrails.verificar("Más información en https://ayuda-depresion.example.com")
    assert r["veredicto"] == "bloqueado"


def test_un_telefono_del_catalogo_no_bloquea():
    """El guardarraíl distingue el contacto verificado del inventado.

    Si bloqueara ambos, el sistema no podría emitir su propia respuesta de crisis.
    """
    texto, recs = recursos.respuesta_crisis()
    completo = texto + "\n\n" + recursos.formatear(recs)
    assert guardrails.verificar(completo)["veredicto"] != "bloqueado"


def test_el_lenguaje_poblacional_correcto_se_aprueba():
    """La formulación que sí queremos no puede quedar bloqueada por exceso de celo."""
    texto = ("De cada cien personas con este perfil, alrededor de veinte presentarían "
             "sintomatología depresiva moderada o grave según el PHQ-9. Es una estimación "
             "poblacional con fines académicos, no un diagnóstico.")
    assert guardrails.verificar(texto)["veredicto"] == "aprobado"


def test_limpiar_no_deja_pasar_lo_que_verificar_rechaza():
    """Si limpiar deja el texto listo, verificar debe darlo por bueno."""
    sucio = "Usted tiene depresión. Llame al 0800 99999."
    assert guardrails.verificar(guardrails.limpiar(sucio))["veredicto"] != "aprobado"
