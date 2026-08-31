"""Regresión logística: versión con diseño complejo y versión sin ponderar.

La inferencia principal usa el diseño muestral (pesos, conglomerados y
estratos). La versión sin ponderar se reporta como sensibilidad, y sirve además
de base para el modelo predictivo, donde los pesos no aplican.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

log = logging.getLogger(__name__)

Z95 = 1.959963984540054


# ─────────────────────────────────────────────────────────────────────
# Matriz de diseño
# ─────────────────────────────────────────────────────────────────────


#: Número máximo de valores distintos para tratar una variable numérica como
#: categórica. Por encima se considera continua y entra como tal.
MAX_CATEGORIAS = 12


def es_categorica(s: pd.Series, maximo: int = MAX_CATEGORIAS) -> bool:
    """Decide si una variable debe entrar al modelo como categórica.

    Texto y ``category`` siempre lo son. Una numérica lo es solo si tiene pocos
    valores distintos: sin este límite, una continua como el IMC generaría
    decenas de miles de columnas indicadoras y el ajuste no terminaría nunca.
    """
    if s.dtype == object or isinstance(s.dtype, pd.CategoricalDtype):
        return True
    return s.dtype.kind in "biu" and s.nunique(dropna=True) <= maximo


def matriz_diseno(
    df: pd.DataFrame, predictores: list[str], referencias: dict[str, str] | None = None
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Construye la matriz de diseño con dummies y categorías de referencia fijas.

    Fijar la referencia importa para interpretar: el OR de "Superior" frente a
    "Primaria o menos" no es el mismo número que el inverso.

    Las variables binarias (0/1) y las continuas entran tal cual; solo las
    categóricas se expanden en indicadoras, dejando fuera la de referencia.

    Returns
    -------
    tuple
        La matriz de diseño y el mapa de nombre de columna -> etiqueta legible.
    """
    referencias = referencias or {}
    piezas, etiquetas = [], {}
    for v in predictores:
        s = df[v]
        # 0 == 0.0 == False y 1 == 1.0 == True, de modo que {0, 1} ya cubre
        # enteros, flotantes y booleanos.
        binaria = set(s.dropna().unique()) <= {0, 1}
        if binaria or not es_categorica(s):
            piezas.append(s.astype(float).rename(v))
            etiquetas[v] = v
            continue
        cats = [str(c) for c in (s.cat.categories if isinstance(s.dtype, pd.CategoricalDtype)
                                 else sorted(s.dropna().unique()))]
        cats = [c for c in cats if c in set(s.astype(str))]
        ref = referencias.get(v, cats[0])
        for c in cats:
            if c == ref:
                continue
            col = f"{v}__{c}"
            piezas.append(pd.Series((s.astype(str) == c).astype(float), name=col))
            etiquetas[col] = f"{v}: {c} (ref. {ref})"
    return pd.concat(piezas, axis=1), etiquetas


# ─────────────────────────────────────────────────────────────────────
# Ajuste
# ─────────────────────────────────────────────────────────────────────


def logistica(
    df: pd.DataFrame,
    desenlace: str,
    predictores: list[str],
    con_diseno: bool = True,
    referencias: dict[str, str] | None = None,
    donde=None,
) -> dict:
    """Ajusta una regresión logística, con o sin diseño muestral complejo.

    Con diseño se usa ``svy.GLM``, que implementa la pseudo-verosimilitud
    ponderada con varianza de Taylor y los **grados de libertad del diseño**
    (conglomerados menos estratos), no los del tamaño muestral. Los contrastes
    son t y F, como en ``svyglm`` de R.

    No se usa ``statsmodels`` con ``freq_weights`` y ``cov_type='cluster'``:
    esa combinación emite ``SpecificationWarning`` porque los pesos de
    frecuencia alteran los grados de libertad de forma incompatible con el
    estimador sándwich. Los coeficientes coinciden, pero la inferencia no.

    Parameters
    ----------
    df : pandas.DataFrame
    desenlace : str
        Variable binaria de resultado.
    predictores : list of str
    con_diseno : bool, default True
        Si se aplica el diseño muestral complejo.
    referencias : dict, optional
        Categoría de referencia por variable categórica.
    donde : optional
        Restricción de dominio (``svy.col(...) == ...``) para analizar una
        subpoblación conservando la estructura del diseño en la varianza.

    Returns
    -------
    dict
        El modelo ajustado, la tabla de OR y las métricas de ajuste.
    """
    if con_diseno:
        return _logistica_diseno(df, desenlace, predictores, referencias, donde)

    cols = [desenlace, *predictores]
    d = df[cols].dropna()
    X, etiquetas = matriz_diseno(d, predictores, referencias)
    X = sm.add_constant(X)
    y = d[desenlace].astype(float)
    ajuste = sm.GLM(y, X, family=sm.families.Binomial()).fit()
    return {
        "modelo": ajuste, "tabla_or": tabla_or(ajuste, etiquetas), "X": X, "y": y, "d": d,
        "n": len(d), "eventos": int(y.sum()), "epv": y.sum() / (X.shape[1] - 1),
        "etiquetas": etiquetas, "con_diseno": False,
    }


def _logistica_diseno(df, desenlace, predictores, referencias, donde) -> dict:
    """Ajusta la logística con diseño complejo usando ``svy.GLM``."""
    import svy

    from .encuesta import crear_diseno

    referencias = referencias or {}
    cols = [desenlace, *predictores]
    d = df[[*cols, "peso", "conglomerado", "estrato"]].dropna(subset=cols)
    muestra = crear_diseno(d, cols)

    x_svy, etiquetas = [], {}
    for v in predictores:
        s = d[v]
        # Mismo criterio que en matriz_diseno: una continua con miles de valores
        # distintos NO es categórica. Sin este límite, `svy.Cat` recibiría un
        # nivel por cada valor de altitud o IMC y el ajuste no terminaría nunca.
        binaria = set(s.dropna().unique()) <= {0, 1}
        es_cat = not binaria and es_categorica(s)
        if es_cat:
            ref = referencias.get(v)
            x_svy.append(svy.Cat(v, ref=ref) if ref else svy.Cat(v))
            for c in sorted({str(c) for c in s.dropna().unique()} - {str(ref)}):
                etiquetas[f"{v}_{c}"] = f"{v}: {c} (ref. {ref})"
        else:
            x_svy.append(v)
            etiquetas[v] = v

    g = muestra.glm.fit(y=desenlace, x=x_svy, family="binomial", link="logit",
                        where=donde, drop_nulls=True)
    st = g.stats
    filas = []
    for c in g.coefs:
        if c.term == "_intercept_":
            intercepto = float(c.est)
            continue
        filas.append({
            "termino": c.term, "etiqueta": etiquetas.get(c.term, c.term),
            "coeficiente": float(c.est), "ee": float(c.se),
            "or": float(np.exp(c.est)),
            "ic_inf": float(np.exp(c.lci)), "ic_sup": float(np.exp(c.uci)),
            "z": float(c.wald.value), "p": float(c.wald.p_value),
            "gl_diseno": int(c.wald.df),
        })
    tabla = pd.DataFrame(filas)
    tabla["significativo"] = tabla.p < 0.05
    tabla["or_formato"] = tabla.apply(
        lambda r: f"{r['or']:.2f} ({r.ic_inf:.2f} – {r.ic_sup:.2f})", axis=1)

    # Probabilidades predichas para ROC y calibración
    d_usada = d.dropna(subset=cols)
    X, _ = matriz_diseno(d_usada, predictores, referencias)
    coefs = {r.termino: r.coeficiente for _, r in tabla.iterrows()}
    lineal = np.full(len(d_usada), intercepto, dtype=float)
    for col in X.columns:
        # svy nombra las dummies como "variable_categoria"; la matriz local usa "__"
        clave = col.replace("__", "_")
        if clave in coefs:
            lineal += coefs[clave] * X[col].to_numpy(dtype=float)
    p_pred = 1 / (1 + np.exp(-lineal))
    y = d_usada[desenlace].astype(float)

    return {
        "modelo": g, "tabla_or": tabla, "X": X, "y": y, "d": d_usada,
        "intercepto": intercepto, "p_pred": p_pred,
        "n": int(st.n), "eventos": int(y.sum()),
        "epv": y.sum() / len(tabla),
        "gl_diseno": int(st.wald.df_den),
        "wald_global": {"F": float(st.wald.value), "gl_num": float(st.wald.df_num),
                        "gl_den": float(st.wald.df_den), "p": float(st.wald.p_value)},
        "aic": float(st.aic), "r2": float(st.r_squared),
        "etiquetas": etiquetas, "con_diseno": True,
    }


def tabla_or(ajuste, etiquetas: dict[str, str]) -> pd.DataFrame:
    """Convierte los coeficientes de un modelo logístico en OR con IC 95 %."""
    ic = ajuste.conf_int()
    filas = []
    for t in ajuste.params.index:
        if t == "const":
            continue
        filas.append({
            "termino": t, "etiqueta": etiquetas.get(t, t),
            "coeficiente": ajuste.params[t], "ee": ajuste.bse[t],
            "or": np.exp(ajuste.params[t]),
            "ic_inf": np.exp(ic.loc[t, 0]), "ic_sup": np.exp(ic.loc[t, 1]),
            "z": ajuste.tvalues[t], "p": ajuste.pvalues[t],
        })
    out = pd.DataFrame(filas)
    out["significativo"] = out.p < 0.05
    out["or_formato"] = out.apply(
        lambda r: f"{r['or']:.2f} ({r.ic_inf:.2f} – {r.ic_sup:.2f})", axis=1)
    return out


# ─────────────────────────────────────────────────────────────────────
# Bondad de ajuste, discriminación y calibración
# ─────────────────────────────────────────────────────────────────────


def hosmer_lemeshow(y: np.ndarray, p: np.ndarray, g: int = 10) -> dict:
    """Prueba de Hosmer-Lemeshow de bondad de ajuste.

    ⚠️ Con N ≈ 30 000 esta prueba rechaza casi siempre: detecta desviaciones
    irrelevantes en la práctica. Se reporta por convención, pero la calibración
    debe juzgarse con la curva y el Brier score, no con este valor p.
    """
    d = pd.DataFrame({"y": np.asarray(y), "p": np.asarray(p)})
    d["decil"] = pd.qcut(d.p, g, labels=False, duplicates="drop")
    obs = d.groupby("decil").y.sum()
    esp = d.groupby("decil").p.sum()
    n = d.groupby("decil").size()
    chi2 = (((obs - esp) ** 2) / (esp * (1 - esp / n))).sum()
    gl = len(obs) - 2
    p_val = float(stats.chi2.sf(chi2, gl))
    return {
        "chi2": float(chi2), "gl": gl, "p": p_val,
        "grupos": int(len(obs)),
        "veredicto": (
            "Ajuste adecuado" if p_val >= 0.05 else
            "Rechaza el ajuste, pero con N grande la prueba es hipersensible: "
            "juzgar la calibración por la curva y el Brier score"
        ),
    }


def discriminacion(y: np.ndarray, p: np.ndarray, n_boot: int = 400, semilla: int = 42) -> dict:
    """Calcula el AUC con intervalo de confianza por bootstrap."""
    from sklearn.metrics import roc_auc_score, roc_curve

    y, p = np.asarray(y), np.asarray(p)
    auc = roc_auc_score(y, p)
    rng = np.random.default_rng(semilla)
    aucs = []
    for _ in range(n_boot):
        i = rng.integers(0, len(y), len(y))
        if len(np.unique(y[i])) < 2:
            continue
        aucs.append(roc_auc_score(y[i], p[i]))
    li, ls = np.percentile(aucs, [2.5, 97.5])
    fpr, tpr, _ = roc_curve(y, p)
    return {"auc": auc, "ic_inf": li, "ic_sup": ls, "fpr": fpr, "tpr": tpr,
            "veredicto": _calidad_auc(auc)}


def _calidad_auc(auc: float) -> str:
    """Traduce el AUC a la escala cualitativa habitual."""
    if auc < 0.6:
        return "discriminación pobre"
    if auc < 0.7:
        return "discriminación aceptable"
    if auc < 0.8:
        return "discriminación buena"
    return "discriminación excelente"


def calibracion(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> tuple[pd.DataFrame, dict]:
    """Calcula la curva de calibración y el Brier score con su descomposición."""
    d = pd.DataFrame({"y": np.asarray(y), "p": np.asarray(p)})
    d["bin"] = pd.qcut(d.p, n_bins, labels=False, duplicates="drop")
    curva = d.groupby("bin").agg(
        p_media=("p", "mean"), observado=("y", "mean"), n=("y", "size")).reset_index()
    brier = float(((d.p - d.y) ** 2).mean())
    base = float(d.y.mean())
    brier_ref = base * (1 - base)
    return curva, {
        "brier": brier, "brier_referencia": brier_ref,
        "skill_score": 1 - brier / brier_ref,
        "veredicto": (f"Brier {brier:.4f} frente a {brier_ref:.4f} del modelo nulo "
                      f"(mejora del {(1 - brier / brier_ref) * 100:.1f} %)"),
    }


def linealidad_logit(df: pd.DataFrame, desenlace: str, continua: str) -> dict:
    """Prueba de Box-Tidwell para la linealidad del logit de una continua.

    Añade el término ``x·ln(x)`` al modelo: si resulta significativo, la
    relación con el logit no es lineal y conviene usar splines o categorizar.
    """
    d = df[[desenlace, continua]].dropna()
    d = d[d[continua] > 0]
    X = pd.DataFrame({
        continua: d[continua].astype(float),
        f"{continua}_x_ln": d[continua] * np.log(d[continua]),
    })
    X = sm.add_constant(X)
    m = sm.GLM(d[desenlace].astype(float), X, family=sm.families.Binomial()).fit()
    p = float(m.pvalues[f"{continua}_x_ln"])
    return {
        "variable": continua, "p_box_tidwell": p, "lineal": p >= 0.05,
        "veredicto": ("El logit es lineal en esta variable" if p >= 0.05 else
                      "El logit NO es lineal: usar splines o categorizar"),
    }


def metricas_clasificacion(
    y: np.ndarray, p: np.ndarray, umbral: float | str | None = "cuantil"
) -> dict:
    """Calcula el panel completo de métricas para un problema desbalanceado.

    Con 6 % de eventos, la exactitud es engañosa: predecir "nadie tiene
    depresión" acierta el 94 %. Por eso las métricas principales son AUC-ROC y
    AUC-PR, que no dependen de ningún umbral.

    Parameters
    ----------
    y, p : numpy.ndarray
        Desenlace observado y probabilidad predicha.
    umbral : float or {"cuantil", "prevalencia"} or None, default "cuantil"
        Punto de corte para las métricas que sí dependen de él.

        ``"cuantil"`` marca como positivos al mismo porcentaje de casos que la
        prevalencia observada, tomando los de mayor puntuación. Es el operativo
        natural en tamizaje —"¿a cuántos puedo atender?"— y **el único válido
        cuando el modelo se entrenó con** ``class_weight`` **o**
        ``scale_pos_weight``: esas correcciones desplazan las probabilidades
        hacia el 0,5 y dejan de estar calibradas a la prevalencia real, de modo
        que un corte fijo en la prevalencia marcaría a casi todo el mundo como
        positivo y daría sensibilidad 1 con especificidad 0.

        ``"prevalencia"`` usa el valor de la prevalencia como corte absoluto,
        solo apropiado si el modelo está calibrado.
    """
    from sklearn.metrics import average_precision_score, confusion_matrix, f1_score, roc_auc_score

    y, p = np.asarray(y), np.asarray(p)
    prev = float(y.mean())
    if umbral == "cuantil" or umbral is None:
        umbral = float(np.quantile(p, 1 - prev))
    elif umbral == "prevalencia":
        umbral = prev
    pred = (p >= umbral).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "umbral": umbral,
        "criterio_umbral": "cuantil de la prevalencia" if abs(umbral - prev) > 1e-9 else "prevalencia",
        "auc_roc": roc_auc_score(y, p),
        "auc_pr": average_precision_score(y, p),
        "prevalencia": prev,
        "sensibilidad": tp / (tp + fn) if (tp + fn) else np.nan,
        "especificidad": tn / (tn + fp) if (tn + fp) else np.nan,
        "vpp": tp / (tp + fp) if (tp + fp) else np.nan,
        "vpn": tn / (tn + fn) if (tn + fn) else np.nan,
        "f1": f1_score(y, pred, zero_division=0),
        "exactitud": (tp + tn) / len(y),
        "exactitud_modelo_trivial": 1 - prev,
        "vp": int(tp), "vn": int(tn), "fp": int(fp), "fn": int(fn),
    }
