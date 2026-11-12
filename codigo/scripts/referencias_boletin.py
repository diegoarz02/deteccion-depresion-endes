"""Referencias del boletín: una sola fuente para las citas, la lista y el .bib.

Cada entrada se verificó abriéndola: los metadatos contra Crossref y PubMed, y el
contenido que se le atribuye contra el resumen publicado (o, en el caso de la
ficha técnica del INEI, contra el propio PDF). La nota ``verificado`` dice qué se
comprobó en cada una. Una referencia que no se pudo abrir no entra aquí.

El boletín cita con ``par()`` y ``nar()``; la lista final y el archivo
``docs/referencias.bib`` se generan solo con las que se citaron, de modo que no
puede quedar una cita sin referencia ni una referencia sin cita.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field


@dataclass
class Ref:
    """Una referencia, con su cita en línea y su ficha BibTeX."""

    clave: str
    autores_citados: str          # «Barros y Hirakata», «Basauri-Delgado et al.»
    anio: str
    apa: str                      # referencia completa en APA 7, con <em> para cursivas
    bib: str                      # entrada BibTeX
    verificado: str = ""
    usos: int = field(default=0, repr=False)


def _bib(tipo: str, clave: str, **campos: str) -> str:
    cuerpo = ",\n".join(f"  {k} = {{{v}}}" for k, v in campos.items())
    return f"@{tipo}{{{clave},\n{cuerpo}\n}}"


REFS: dict[str, Ref] = {}


def _alta(r: Ref) -> None:
    REFS[r.clave] = r


_alta(Ref(
    "barros2003", "Barros y Hirakata", "2003",
    "Barros, A. J. D., &amp; Hirakata, V. N. (2003). Alternatives for logistic regression in "
    "cross-sectional studies: An empirical comparison of models that directly estimate the "
    "prevalence ratio. <em>BMC Medical Research Methodology, 3</em>, Artículo 21. "
    '<a href="https://doi.org/10.1186/1471-2288-3-21">https://doi.org/10.1186/1471-2288-3-21</a>',
    _bib("article", "barros2003", author="Barros, Aluísio J. D. and Hirakata, Vânia N.",
         title="Alternatives for logistic regression in cross-sectional studies: An empirical "
               "comparison of models that directly estimate the prevalence ratio",
         journal="BMC Medical Research Methodology", year="2003", volume="3", number="21",
         doi="10.1186/1471-2288-3-21"),
    "Crossref y PubMed 14567763; el resumen dice que el OR puede sobrestimar la razón de "
    "prevalencias y que Poisson con varianza robusta la estima bien."))

_alta(Ref(
    "basauri2025", "Basauri-Delgado et al.", "2025",
    "Basauri-Delgado, M., Mesía-Guevara, J.-A., &amp; Saintila, J. (2025). Influence of "
    "sociodemographic, socioeconomic, and health factors on depression in the Peruvian "
    "population: A cross-sectional study. <em>Journal of Primary Care &amp; Community Health, "
    '16</em>. <a href="https://doi.org/10.1177/21501319251342090">'
    "https://doi.org/10.1177/21501319251342090</a>",
    _bib("article", "basauri2025",
         author="Basauri-Delgado, Miguel and Mesía-Guevara, José-Alfonso and Saintila, Jacksaint",
         title="Influence of sociodemographic, socioeconomic, and health factors on depression "
               "in the Peruvian population: A cross-sectional study",
         journal="Journal of Primary Care \\& Community Health", year="2025", volume="16",
         doi="10.1177/21501319251342090"),
    "PubMed 40878715; resumen con razones de prevalencia ajustadas para hipertensión, "
    "diabetes, tabaco, sexo y área rural."))

_alta(Ref(
    "basualdo2022", "Basualdo-Meléndez et al.", "2022",
    "Basualdo-Meléndez, G. W., Hernández-Vásquez, A., Barón-Lozada, F. A., &amp; "
    "Vargas-Fernández, R. (2022). Prevalence of depression and depressive symptoms at high "
    "altitudes: A systematic review and meta-analysis. <em>Journal of Affective Disorders, "
    '317</em>, 388-396. <a href="https://doi.org/10.1016/j.jad.2022.08.079">'
    "https://doi.org/10.1016/j.jad.2022.08.079</a>",
    _bib("article", "basualdo2022",
         author="Basualdo-Meléndez, Gianfranco W. and Hernández-Vásquez, Akram and "
                "Barón-Lozada, Francisco A. and Vargas-Fernández, Rodrigo",
         title="Prevalence of depression and depressive symptoms at high altitudes: A "
               "systematic review and meta-analysis",
         journal="Journal of Affective Disorders", year="2022", volume="317", pages="388--396",
         doi="10.1016/j.jad.2022.08.079"),
    "PubMed 36055536; prevalencia combinada de síntomas depresivos de 17,9 % con "
    "heterogeneidad muy alta (I² = 99 %)."))

_alta(Ref(
    "calderon2012", "Calderón et al.", "2012",
    "Calderón, M., Gálvez-Buccollini, J. A., Cueva, G., Ordóñez, C., Bromley, C., &amp; "
    "Fiestas, F. (2012). Validación de la versión peruana del PHQ-9 para el diagnóstico de "
    "depresión [Carta al editor]. <em>Revista Peruana de Medicina Experimental y Salud "
    'Pública, 29</em>(4), 578-579. <a href="https://doi.org/10.1590/S1726-46342012000400027">'
    "https://doi.org/10.1590/S1726-46342012000400027</a>",
    _bib("article", "calderon2012",
         author="Calderón, María and Gálvez-Buccollini, Juan Antonio and Cueva, Gloria and "
                "Ordóñez, Carlos and Bromley, Carlos and Fiestas, Fabián",
         title="Validación de la versión peruana del PHQ-9 para el diagnóstico de depresión",
         journal="Revista Peruana de Medicina Experimental y Salud Pública", year="2012",
         volume="29", number="4", pages="578--579", doi="10.1590/S1726-46342012000400027"),
    "Texto completo leído en SciELO Perú: validación por juicio de expertos (23 psiquiatras, "
    "3 psicólogos y 1 enfermera) como primer paso; anuncia una validación de criterio "
    "pendiente. No propone punto de corte. Menciona pocos psiquiatras, concentrados en Lima."))

_alta(Ref(
    "gbd2022", "GBD 2019 Mental Disorders Collaborators", "2022",
    "GBD 2019 Mental Disorders Collaborators. (2022). Global, regional, and national burden "
    "of 12 mental disorders in 204 countries and territories, 1990-2019: A systematic "
    "analysis for the Global Burden of Disease Study 2019. <em>The Lancet Psychiatry, "
    '9</em>(2), 137-150. <a href="https://doi.org/10.1016/S2215-0366(21)00395-3">'
    "https://doi.org/10.1016/S2215-0366(21)00395-3</a>",
    _bib("article", "gbd2022",
         author="{GBD 2019 Mental Disorders Collaborators}",
         title="Global, regional, and national burden of 12 mental disorders in 204 countries "
               "and territories, 1990--2019: A systematic analysis for the Global Burden of "
               "Disease Study 2019",
         journal="The Lancet Psychiatry", year="2022", volume="9", number="2",
         pages="137--150", doi="10.1016/S2215-0366(21)00395-3"),
    "PubMed 35026139; los trastornos mentales fueron el 14,6 % de los años vividos con "
    "discapacidad en 2019 y el 4,9 % de los DALY."))

_alta(Ref(
    "greenland1999", "Greenland et al.", "1999",
    "Greenland, S., Pearl, J., &amp; Robins, J. M. (1999). Causal diagrams for epidemiologic "
    "research. <em>Epidemiology, 10</em>(1), 37-48. "
    '<a href="https://doi.org/10.1097/00001648-199901000-00008">'
    "https://doi.org/10.1097/00001648-199901000-00008</a>",
    _bib("article", "greenland1999",
         author="Greenland, Sander and Pearl, Judea and Robins, James M.",
         title="Causal diagrams for epidemiologic research", journal="Epidemiology",
         year="1999", volume="10", number="1", pages="37--48",
         doi="10.1097/00001648-199901000-00008"),
    "Metadatos contra Crossref; no se abrió el texto completo."))

_alta(Ref(
    "hernan2004", "Hernán et al.", "2004",
    "Hernán, M. A., Hernández-Díaz, S., &amp; Robins, J. M. (2004). A structural approach to "
    "selection bias. <em>Epidemiology, 15</em>(5), 615-625. "
    '<a href="https://doi.org/10.1097/01.ede.0000135174.63482.43">'
    "https://doi.org/10.1097/01.ede.0000135174.63482.43</a>",
    _bib("article", "hernan2004",
         author="Hernán, Miguel A. and Hernández-Díaz, Sonia and Robins, James M.",
         title="A structural approach to selection bias", journal="Epidemiology", year="2004",
         volume="15", number="5", pages="615--625", doi="10.1097/01.ede.0000135174.63482.43"),
    "PubMed 15308962; distingue el sesgo de selección (condicionar sobre un efecto común) "
    "de la confusión (causas comunes)."))

_alta(Ref(
    "hill1965", "Hill", "1965",
    "Hill, A. B. (1965). The environment and disease: Association or causation? "
    "<em>Proceedings of the Royal Society of Medicine, 58</em>(5), 295-300. "
    '<a href="https://doi.org/10.1177/003591576505800503">'
    "https://doi.org/10.1177/003591576505800503</a>",
    _bib("article", "hill1965", author="Hill, Austin Bradford",
         title="The environment and disease: Association or causation?",
         journal="Proceedings of the Royal Society of Medicine", year="1965", volume="58",
         number="5", pages="295--300", doi="10.1177/003591576505800503"),
    "Metadatos contra Crossref; texto clásico, no se releyó completo."))

_alta(Ref(
    "inei2026", "INEI", "2026",
    "Instituto Nacional de Estadística e Informática. (2026). <em>Ficha técnica: Encuesta "
    "Demográfica y de Salud Familiar (ENDES) 2025</em> [Documento técnico]. INEI. "
    '<a href="https://proyectos.inei.gob.pe/microdatos/">'
    "https://proyectos.inei.gob.pe/microdatos/</a>",
    _bib("techreport", "inei2026",
         author="{Instituto Nacional de Estadística e Informática}",
         title="Ficha técnica: Encuesta Demográfica y de Salud Familiar (ENDES) 2025",
         institution="Instituto Nacional de Estadística e Informática", year="2026",
         url="https://proyectos.inei.gob.pe/microdatos/"),
    "PDF leído completo (22 páginas): universo, una persona de 15 años a más por hogar para el "
    "cuestionario de salud, cobertura de 36 750 de 36 760 viviendas, ajuste de ponderadores "
    "por no respuesta. El año 2026 se deduce del contenido (menciona la recuperación de "
    "conglomerados en enero y febrero de 2026); el PDF no trae fecha de edición."))

_alta(Ref(
    "kious2019", "Kious et al.", "2019",
    "Kious, B. M., Bakian, A., Zhao, J., Mickey, B., Guille, C., Renshaw, P., &amp; Sen, S. "
    "(2019). Altitude and risk of depression and anxiety: Findings from the Intern Health "
    "Study. <em>International Review of Psychiatry, 31</em>(7-8), 637-645. "
    '<a href="https://doi.org/10.1080/09540261.2019.1586324">'
    "https://doi.org/10.1080/09540261.2019.1586324</a>",
    _bib("article", "kious2019",
         author="Kious, Brent M. and Bakian, Amanda and Zhao, Joan and Mickey, Brian and "
                "Guille, Constance and Renshaw, Perry and Sen, Srijan",
         title="Altitude and risk of depression and anxiety: Findings from the Intern Health "
               "Study", journal="International Review of Psychiatry", year="2019",
         volume="31", number="7--8", pages="637--645", doi="10.1080/09540261.2019.1586324"),
    "PubMed 31084447; residentes médicos de EE. UU.; residir a más de 900 m se asoció con el "
    "puntaje PHQ-9 (OR 1,32; IC 95 % 1,001-1,75)."))

_alta(Ref(
    "kroenke2001", "Kroenke et al.", "2001",
    "Kroenke, K., Spitzer, R. L., &amp; Williams, J. B. W. (2001). The PHQ-9: Validity of a "
    "brief depression severity measure. <em>Journal of General Internal Medicine, 16</em>(9), "
    '606-613. <a href="https://doi.org/10.1046/j.1525-1497.2001.016009606.x">'
    "https://doi.org/10.1046/j.1525-1497.2001.016009606.x</a>",
    _bib("article", "kroenke2001",
         author="Kroenke, Kurt and Spitzer, Robert L. and Williams, Janet B. W.",
         title="The {PHQ-9}: Validity of a brief depression severity measure",
         journal="Journal of General Internal Medicine", year="2001", volume="16",
         number="9", pages="606--613", doi="10.1046/j.1525-1497.2001.016009606.x"),
    "PubMed 11556941; puntaje ≥ 10 con sensibilidad y especificidad de 88 % para depresión "
    "mayor; los cortes 5, 10, 15 y 20 son depresión leve, moderada, moderadamente grave y "
    "grave."))

_alta(Ref(
    "krumpal2013", "Krumpal", "2013",
    "Krumpal, I. (2013). Determinants of social desirability bias in sensitive surveys: A "
    "literature review. <em>Quality &amp; Quantity, 47</em>(4), 2025-2047. "
    '<a href="https://doi.org/10.1007/s11135-011-9640-9">'
    "https://doi.org/10.1007/s11135-011-9640-9</a>",
    _bib("article", "krumpal2013", author="Krumpal, Ivar",
         title="Determinants of social desirability bias in sensitive surveys: A literature "
               "review", journal="Quality \\& Quantity", year="2013", volume="47", number="4",
         pages="2025--2047", doi="10.1007/s11135-011-9640-9"),
    "Metadatos contra Crossref y título; el resumen no se pudo abrir (la editorial lo "
    "bloquea). Se cita solo para la existencia del sesgo de deseabilidad social en preguntas "
    "sensibles, que es lo que dice el título."))

_alta(Ref(
    "levis2019", "Levis et al.", "2019",
    "Levis, B., Benedetti, A., &amp; Thombs, B. D. (2019). Accuracy of Patient Health "
    "Questionnaire-9 (PHQ-9) for screening to detect major depression: Individual participant "
    "data meta-analysis. <em>BMJ, 365</em>, Artículo l1476. "
    '<a href="https://doi.org/10.1136/bmj.l1476">https://doi.org/10.1136/bmj.l1476</a>',
    _bib("article", "levis2019",
         author="Levis, Brooke and Benedetti, Andrea and Thombs, Brett D.",
         title="Accuracy of Patient Health Questionnaire-9 ({PHQ-9}) for screening to detect "
               "major depression: Individual participant data meta-analysis",
         journal="BMJ", year="2019", volume="365", pages="l1476", doi="10.1136/bmj.l1476"),
    "PubMed 30967483; con entrevistas semiestructuradas, el corte ≥ 10 maximiza sensibilidad "
    "(0,88) y especificidad (0,85)."))

_alta(Ref(
    "lumley2010", "Lumley", "2010",
    "Lumley, T. (2010). <em>Complex surveys: A guide to analysis using R</em>. Wiley. "
    '<a href="https://doi.org/10.1002/9780470580066">https://doi.org/10.1002/9780470580066</a>',
    _bib("book", "lumley2010", author="Lumley, Thomas",
         title="Complex Surveys: A Guide to Analysis Using {R}", publisher="Wiley",
         year="2010", doi="10.1002/9780470580066"),
    "Metadatos contra Crossref."))

_alta(Ref(
    "maldonado1993", "Maldonado y Greenland", "1993",
    "Maldonado, G., &amp; Greenland, S. (1993). Simulation study of confounder-selection "
    "strategies. <em>American Journal of Epidemiology, 138</em>(11), 923-936. "
    '<a href="https://doi.org/10.1093/oxfordjournals.aje.a116813">'
    "https://doi.org/10.1093/oxfordjournals.aje.a116813</a>",
    _bib("article", "maldonado1993", author="Maldonado, George and Greenland, Sander",
         title="Simulation study of confounder-selection strategies",
         journal="American Journal of Epidemiology", year="1993", volume="138", number="11",
         pages="923--936", doi="10.1093/oxfordjournals.aje.a116813"),
    "PubMed 8256780; el criterio de cambio en la estimación funcionó mejor con un punto de "
    "corte bajo, del 10 %."))

_alta(Ref(
    "manea2012", "Manea et al.", "2012",
    "Manea, L., Gilbody, S., &amp; McMillan, D. (2012). Optimal cut-off score for diagnosing "
    "depression with the Patient Health Questionnaire (PHQ-9): A meta-analysis. "
    "<em>Canadian Medical Association Journal, 184</em>(3), E191-E196. "
    '<a href="https://doi.org/10.1503/cmaj.110829">https://doi.org/10.1503/cmaj.110829</a>',
    _bib("article", "manea2012",
         author="Manea, Laura and Gilbody, Simon and McMillan, Dean",
         title="Optimal cut-off score for diagnosing depression with the Patient Health "
               "Questionnaire ({PHQ-9}): A meta-analysis",
         journal="Canadian Medical Association Journal", year="2012", volume="184",
         number="3", pages="E191--E196", doi="10.1503/cmaj.110829"),
    "PubMed 22184363; propiedades aceptables entre los cortes 8 y 11, sin diferencias "
    "sustanciales."))

_alta(Ref(
    "mann2003", "Mann", "2003",
    "Mann, C. J. (2003). Observational research methods. Research design II: Cohort, cross "
    "sectional, and case-control studies. <em>Emergency Medicine Journal, 20</em>(1), 54-60. "
    '<a href="https://doi.org/10.1136/emj.20.1.54">https://doi.org/10.1136/emj.20.1.54</a>',
    _bib("article", "mann2003", author="Mann, C. J.",
         title="Observational research methods. Research design {II}: Cohort, cross sectional, "
               "and case-control studies", journal="Emergency Medicine Journal", year="2003",
         volume="20", number="1", pages="54--60", doi="10.1136/emj.20.1.54"),
    "PubMed 12533370; los estudios transversales determinan prevalencia y no permiten "
    "distinguir causa y efecto."))

_alta(Ref(
    "mickey1989", "Mickey y Greenland", "1989",
    "Mickey, R. M., &amp; Greenland, S. (1989). The impact of confounder selection criteria "
    "on effect estimation. <em>American Journal of Epidemiology, 129</em>(1), 125-137. "
    '<a href="https://doi.org/10.1093/oxfordjournals.aje.a115101">'
    "https://doi.org/10.1093/oxfordjournals.aje.a115101</a>",
    _bib("article", "mickey1989", author="Mickey, Ruth M. and Greenland, Sander",
         title="The impact of confounder selection criteria on effect estimation",
         journal="American Journal of Epidemiology", year="1989", volume="129", number="1",
         pages="125--137", doi="10.1093/oxfordjournals.aje.a115101"),
    "PubMed 2910056; el criterio de cambio en la estimación tiende a ser superior en los "
    "casos dudosos."))

_alta(Ref(
    "miettinen1974", "Miettinen", "1974",
    "Miettinen, O. S. (1974). Proportion of disease caused or prevented by a given exposure, "
    "trait or intervention. <em>American Journal of Epidemiology, 99</em>(5), 325-332. "
    '<a href="https://doi.org/10.1093/oxfordjournals.aje.a121617">'
    "https://doi.org/10.1093/oxfordjournals.aje.a121617</a>",
    _bib("article", "miettinen1974", author="Miettinen, Olli S.",
         title="Proportion of disease caused or prevented by a given exposure, trait or "
               "intervention", journal="American Journal of Epidemiology", year="1974",
         volume="99", number="5", pages="325--332", doi="10.1093/oxfordjournals.aje.a121617"),
    "Metadatos contra Crossref y PubMed 4825599; el artículo no trae resumen."))

_alta(Ref(
    "morgenstern1995", "Morgenstern", "1995",
    "Morgenstern, H. (1995). Ecologic studies in epidemiology: Concepts, principles, and "
    "methods. <em>Annual Review of Public Health, 16</em>, 61-81. "
    '<a href="https://doi.org/10.1146/annurev.pu.16.050195.000425">'
    "https://doi.org/10.1146/annurev.pu.16.050195.000425</a>",
    _bib("article", "morgenstern1995", author="Morgenstern, Hal",
         title="Ecologic studies in epidemiology: Concepts, principles, and methods",
         journal="Annual Review of Public Health", year="1995", volume="16",
         pages="61--81", doi="10.1146/annurev.pu.16.050195.000425"),
    "PubMed 7639884; los estudios ecológicos comparan grupos y tienen problemas "
    "metodológicos que limitan la inferencia causal, entre ellos el sesgo ecológico."))

_alta(Ref(
    "oms2026", "Organización Mundial de la Salud", "2026",
    "Organización Mundial de la Salud. (2026, 11 de septiembre). <em>Trastorno depresivo "
    "(depresión)</em>. Recuperado el 11 de noviembre de 2026, de "
    '<a href="https://www.who.int/es/news-room/fact-sheets/detail/depression">'
    "https://www.who.int/es/news-room/fact-sheets/detail/depression</a>",
    _bib("misc", "oms2026", author="{Organización Mundial de la Salud}",
         title="Trastorno depresivo (depresión)", year="2026",
         url="https://www.who.int/es/news-room/fact-sheets/detail/depression",
         note="Consultado el 11 de noviembre de 2026"),
    "Página abierta el 11-nov-2026: 5,2 % de los adultos y unos 322 millones de personas con "
    "depresión; episodios de al menos dos semanas; causas sociales, psicológicas y biológicas; "
    "hay tratamientos eficaces; barreras: falta de inversión, de profesionales y estigma."))

_alta(Ref(
    "rao1984", "Rao y Scott", "1984",
    "Rao, J. N. K., &amp; Scott, A. J. (1984). On chi-squared tests for multiway contingency "
    "tables with cell proportions estimated from survey data. <em>The Annals of Statistics, "
    '12</em>(1), 46-60. <a href="https://doi.org/10.1214/aos/1176346391">'
    "https://doi.org/10.1214/aos/1176346391</a>",
    _bib("article", "rao1984", author="Rao, J. N. K. and Scott, A. J.",
         title="On chi-squared tests for multiway contingency tables with cell proportions "
               "estimated from survey data", journal="The Annals of Statistics",
         year="1984", volume="12", number="1", pages="46--60",
         doi="10.1214/aos/1176346391"),
    "Metadatos contra Crossref."))

_alta(Ref(
    "rao1988", "Rao y Wu", "1988",
    "Rao, J. N. K., &amp; Wu, C. F. J. (1988). Resampling inference with complex survey data. "
    "<em>Journal of the American Statistical Association, 83</em>(401), 231-241. "
    '<a href="https://doi.org/10.1080/01621459.1988.10478591">'
    "https://doi.org/10.1080/01621459.1988.10478591</a>",
    _bib("article", "rao1988", author="Rao, J. N. K. and Wu, C. F. J.",
         title="Resampling inference with complex survey data",
         journal="Journal of the American Statistical Association", year="1988",
         volume="83", number="401", pages="231--241",
         doi="10.1080/01621459.1988.10478591"),
    "Metadatos contra Crossref."))

_alta(Ref(
    "robinson2009", "Robinson", "1950/2009",
    "Robinson, W. S. (2009). Ecological correlations and the behavior of individuals. "
    "<em>International Journal of Epidemiology, 38</em>(2), 337-341. "
    '<a href="https://doi.org/10.1093/ije/dyn357">https://doi.org/10.1093/ije/dyn357</a> '
    "(Trabajo original publicado en 1950)",
    _bib("article", "robinson2009", author="Robinson, W. S.",
         title="Ecological correlations and the behavior of individuals",
         journal="International Journal of Epidemiology", year="2009", volume="38",
         number="2", pages="337--341", doi="10.1093/ije/dyn357",
         note="Trabajo original publicado en 1950"),
    "Metadatos contra Crossref y PubMed 19179346; reimpresión del artículo de 1950."))

_alta(Ref(
    "rockhill1998", "Rockhill et al.", "1998",
    "Rockhill, B., Newman, B., &amp; Weinberg, C. (1998). Use and misuse of population "
    "attributable fractions. <em>American Journal of Public Health, 88</em>(1), 15-19. "
    '<a href="https://doi.org/10.2105/AJPH.88.1.15">https://doi.org/10.2105/AJPH.88.1.15</a>',
    _bib("article", "rockhill1998",
         author="Rockhill, Beverly and Newman, Beth and Weinberg, Clarice",
         title="Use and misuse of population attributable fractions",
         journal="American Journal of Public Health", year="1998", volume="88", number="1",
         pages="15--19", doi="10.2105/AJPH.88.1.15"),
    "Metadatos contra Crossref y PubMed 9584027; el artículo no trae resumen."))

_alta(Ref(
    "toyama2017", "Toyama et al.", "2017",
    "Toyama, M., Castillo, H., Galea, J. T., Brandt, L. R., Mendoza, M., Herrera, V., "
    "Mitrani, M., &amp; Cutipé, Y. (2017). Peruvian mental health reform: A framework for "
    "scaling-up mental health services. <em>International Journal of Health Policy and "
    'Management, 6</em>(9), 501-508. <a href="https://doi.org/10.15171/ijhpm.2017.07">'
    "https://doi.org/10.15171/ijhpm.2017.07</a>",
    _bib("article", "toyama2017",
         author="Toyama, Mauricio and Castillo, Humberto and Galea, Jerome T. and "
                "Brandt, Lena R. and Mendoza, María and Herrera, Vanessa and "
                "Mitrani, Martha and Cutipé, Yuri",
         title="Peruvian mental health reform: A framework for scaling-up mental health "
               "services", journal="International Journal of Health Policy and Management",
         year="2017", volume="6", number="9", pages="501--508",
         doi="10.15171/ijhpm.2017.07"),
    "PubMed 28949462; la gran mayoría de quienes padecen trastornos mentales no accede a "
    "atención; la reforma enfrenta como desafío los entornos rurales aislados."))

_alta(Ref(
    "villarreal2019", "Villarreal-Zegarra et al.", "2019",
    "Villarreal-Zegarra, D., Copez-Lonzoy, A., Bernabé-Ortiz, A., Melendez-Torres, G. J., "
    "&amp; Bazo-Alvarez, J. C. (2019). Valid group comparisons can be made with the Patient "
    "Health Questionnaire (PHQ-9): A measurement invariance study across groups by "
    "demographic characteristics. <em>PLOS ONE, 14</em>(9), Artículo e0221717. "
    '<a href="https://doi.org/10.1371/journal.pone.0221717">'
    "https://doi.org/10.1371/journal.pone.0221717</a>",
    _bib("article", "villarreal2019",
         author="Villarreal-Zegarra, David and Copez-Lonzoy, Anthony and "
                "Bernabé-Ortiz, Antonio and Melendez-Torres, G. J. and Bazo-Alvarez, "
                "Juan Carlos",
         title="Valid group comparisons can be made with the Patient Health Questionnaire "
               "({PHQ-9}): A measurement invariance study across groups by demographic "
               "characteristics", journal="PLOS ONE", year="2019", volume="14", number="9",
         pages="e0221717", doi="10.1371/journal.pone.0221717"),
    "PubMed 31498796; datos del cuestionario de salud de la ENDES (n = 30 449), estructura "
    "unidimensional e invarianza de medición entre sexo, edad, educación, nivel "
    "socioeconómico, estado civil y área; alfa y omega de 0,87."))

_alta(Ref(
    "elm2007", "von Elm et al.", "2007",
    "von Elm, E., Altman, D. G., Egger, M., Pocock, S. J., Gøtzsche, P. C., &amp; "
    "Vandenbroucke, J. P. (2007). The Strengthening the Reporting of Observational Studies in "
    "Epidemiology (STROBE) statement: Guidelines for reporting observational studies. "
    '<em>The Lancet, 370</em>(9596), 1453-1457. <a href="https://doi.org/10.1016/S0140-6736(07)61602-X">'
    "https://doi.org/10.1016/S0140-6736(07)61602-X</a>",
    _bib("article", "elm2007",
         author="von Elm, Erik and Altman, Douglas G. and Egger, Matthias and Pocock, "
                "Stuart J. and Gøtzsche, Peter C. and Vandenbroucke, Jan P.",
         title="The Strengthening the Reporting of Observational Studies in Epidemiology "
               "({STROBE}) statement: Guidelines for reporting observational studies",
         journal="The Lancet", year="2007", volume="370", number="9596",
         pages="1453--1457", doi="10.1016/S0140-6736(07)61602-X"),
    "Metadatos contra Crossref; sitio strobe-statement.org abierto (200)."))

_alta(Ref(
    "zegarra2022", "Zegarra-Rodríguez et al.", "2022",
    "Zegarra-Rodríguez, C. A., Plasencia-Dueñas, N. R., &amp; Failoc-Rojas, V. E. (2022). "
    "Disparities in the prevalence of screened depression at different altitudes in Peru: A "
    "retrospective analysis of the ENDES 2019. <em>PLOS ONE, 17</em>(12), Artículo e0278947. "
    '<a href="https://doi.org/10.1371/journal.pone.0278947">'
    "https://doi.org/10.1371/journal.pone.0278947</a>",
    _bib("article", "zegarra2022",
         author="Zegarra-Rodríguez, Cynthia Alejandra and Plasencia-Dueñas, Nahún Raphael "
                "and Failoc-Rojas, Virgilio E.",
         title="Disparities in the prevalence of screened depression at different "
               "altitudes in Peru: A retrospective analysis of the {ENDES} 2019",
         journal="PLOS ONE", year="2022", volume="17", number="12", pages="e0278947",
         doi="10.1371/journal.pone.0278947"),
    "PubMed 36542597; ENDES 2019, 7,23 % y 7,12 % en 1 500-2 499 y ≥ 2 500 m; razones de "
    "prevalencia ajustadas de 1,38 (1,04-1,84) y 1,41 (1,20-1,66)."))

_alta(Ref(
    "zou2004", "Zou", "2004",
    "Zou, G. (2004). A modified Poisson regression approach to prospective studies with "
    "binary data. <em>American Journal of Epidemiology, 159</em>(7), 702-706. "
    '<a href="https://doi.org/10.1093/aje/kwh090">https://doi.org/10.1093/aje/kwh090</a>',
    _bib("article", "zou2004", author="Zou, Guangyong",
         title="A modified {Poisson} regression approach to prospective studies with binary "
               "data", journal="American Journal of Epidemiology", year="2004",
         volume="159", number="7", pages="702--706", doi="10.1093/aje/kwh090"),
    "PubMed 15033648; Poisson con varianza robusta para estimar el riesgo relativo "
    "directamente."))

# ───────────── Altitud: mecanismos y evidencia peruana ─────────────

_alta(Ref(
    "hernandez2022", "Hernández-Vásquez et al.", "2022",
    "Hernández-Vásquez, A., Vargas-Fernández, R., Rojas-Roque, C., &amp; Gamboa-Unsihuay, J. E. "
    "(2022). Association between altitude and depression in Peru: An 8-year pooled analysis of "
    "population-based surveys. <em>Journal of Affective Disorders, 299</em>, 536-544. "
    '<a href="https://doi.org/10.1016/j.jad.2021.12.059">https://doi.org/10.1016/j.jad.2021.12.059</a>',
    _bib("article", "hernandez2022",
         author="Hernández-Vásquez, Akram and Vargas-Fernández, Rodrigo and Rojas-Roque, "
                "Carlos and Gamboa-Unsihuay, Jesús Eduardo",
         title="Association between altitude and depression in Peru: An 8-year pooled analysis "
               "of population-based surveys", journal="Journal of Affective Disorders",
         year="2022", volume="299", pages="536--544", doi="10.1016/j.jad.2021.12.059"),
    "PubMed 34942223; ENDES 2013-2020, 215 409 participantes; cada 100 m de altitud se asoció "
    "con más puntaje depresivo tras ajustar (β = 0,01); limitación: no se conoce el tiempo de "
    "residencia en altura."))

_alta(Ref(
    "zaeh2016", "Zaeh et al.", "2016",
    "Zaeh, S., Miele, C. H., Putcha, N., Gilman, R. H., Miranda, J. J., Bernabe-Ortiz, A., Wise, "
    "R. A., &amp; Checkley, W. (2016). Chronic respiratory disease and high altitude are associated "
    "with depressive symptoms in four diverse settings. <em>The International Journal of "
    'Tuberculosis and Lung Disease, 20</em>(9), 1263-1269. <a href="https://doi.org/10.5588/ijtld.15.0794">'
    "https://doi.org/10.5588/ijtld.15.0794</a>",
    _bib("article", "zaeh2016",
         author="Zaeh, S. and Miele, C. H. and Putcha, N. and Gilman, R. H. and Miranda, J. J. "
                "and Bernabe-Ortiz, A. and Wise, R. A. and Checkley, W.",
         title="Chronic respiratory disease and high altitude are associated with depressive "
               "symptoms in four diverse settings",
         journal="The International Journal of Tuberculosis and Lung Disease", year="2016",
         volume="20", number="9", pages="1263--1269", doi="10.5588/ijtld.15.0794"),
    "PubMed 27510256; cuatro escenarios del Perú, 2 953 adultos; vivir en altura se asoció con "
    "mayores odds de síntomas depresivos (OR 1,64; IC 95 % 1,10-2,43)."))

_alta(Ref(
    "ishikawa2013", "Ishikawa et al.", "2013",
    "Ishikawa, M., Yamanaka, G., Nakajima, S., Suwa, K., Matsuda, A., Nakaoka, T., Okumiya, K., "
    "Matsubayashi, K., &amp; Otsuka, K. (2013). Association between high altitude and depression "
    "in the Himalayas and the Andes [Artículo en japonés]. <em>Nippon Ronen Igakkai Zasshi, "
    '50</em>(3), 330-334. <a href="https://doi.org/10.3143/geriatrics.50.330">'
    "https://doi.org/10.3143/geriatrics.50.330</a>",
    _bib("article", "ishikawa2013",
         author="Ishikawa, Motonao and Yamanaka, Gaku and Nakajima, Shun and Suwa, Kuniaki and "
                "Matsuda, Akiko and Nakaoka, Takashi and Okumiya, Kiyohito and "
                "Matsubayashi, Kozo and Otsuka, Kuniaki",
         title="Association between high altitude and depression in the Himalayas and the Andes",
         journal="Nippon Ronen Igakkai Zasshi", year="2013", volume="50", number="3",
         pages="330--334", doi="10.3143/geriatrics.50.330"),
    "PubMed 23979333 (resumen en inglés); adultos mayores de los Himalayas y los Andes: la "
    "prevalencia de depresión por entrevista fue baja (1,8 % a 2,9 %) pese a la altitud."))

_alta(Ref(
    "kious2018", "Kious et al.", "2018",
    "Kious, B. M., Kondo, D. G., &amp; Renshaw, P. F. (2018). Living high and feeling low: "
    "Altitude, suicide, and depression. <em>Harvard Review of Psychiatry, 26</em>(2), 43-56. "
    '<a href="https://doi.org/10.1097/HRP.0000000000000158">'
    "https://doi.org/10.1097/HRP.0000000000000158</a>",
    _bib("article", "kious2018",
         author="Kious, Brent M. and Kondo, Douglas G. and Renshaw, Perry F.",
         title="Living high and feeling low: Altitude, suicide, and depression",
         journal="Harvard Review of Psychiatry", year="2018", volume="26", number="2",
         pages="43--56", doi="10.1097/HRP.0000000000000158"),
    "PubMed 29517615; revisión: la hipoxia hipobárica crónica podría favorecer la depresión "
    "al alterar el metabolismo de la serotonina y la bioenergética cerebral; reconoce que las "
    "variaciones regionales sugieren aportes sociodemográficos y ambientales."))

_alta(Ref(
    "kanekar2018", "Kanekar et al.", "2018",
    "Kanekar, S., Sheth, C. S., Ombach, H. J., Olson, P. R., Bogdanova, O. V., Petersen, M., "
    "Renshaw, C. E., Sung, Y.-H., D’Anci, K. E., &amp; Renshaw, P. F. (2018). Hypobaric hypoxia "
    "exposure in rats differentially alters antidepressant efficacy of the selective serotonin "
    "reuptake inhibitors fluoxetine, paroxetine, escitalopram and sertraline. "
    "<em>Pharmacology Biochemistry and Behavior, 170</em>, 25-35. "
    '<a href="https://doi.org/10.1016/j.pbb.2018.05.002">https://doi.org/10.1016/j.pbb.2018.05.002</a>',
    _bib("article", "kanekar2018",
         author="Kanekar, Shami and Sheth, Chandni S. and Ombach, Hendrik J. and Olson, Paul R. "
                "and Bogdanova, Olena V. and Petersen, Matthew and Renshaw, Chloe E. and "
                "Sung, Young-Hoon and D'Anci, Kristen E. and Renshaw, Perry F.",
         title="Hypobaric hypoxia exposure in rats differentially alters antidepressant "
               "efficacy of the selective serotonin reuptake inhibitors fluoxetine, "
               "paroxetine, escitalopram and sertraline",
         journal="Pharmacology Biochemistry and Behavior", year="2018", volume="170",
         pages="25--35", doi="10.1016/j.pbb.2018.05.002"),
    "PubMed 29738811; modelo animal: la exposición a altitud reduce la serotonina cerebral y "
    "varios inhibidores de la recaptación pierden eficacia."))

_alta(Ref(
    "reno2018", "Reno et al.", "2018",
    "Reno, E., Brown, T. L., Betz, M. E., Allen, M. H., Hoffecker, L., Reitinger, J., Roach, R., "
    "&amp; Honigman, B. (2018). Suicide and high altitude: An integrative review. <em>High "
    'Altitude Medicine &amp; Biology, 19</em>(2), 99-108. <a href="https://doi.org/10.1089/ham.2016.0131">'
    "https://doi.org/10.1089/ham.2016.0131</a>",
    _bib("article", "reno2018",
         author="Reno, Elaine and Brown, Talia L. and Betz, Marian E. and Allen, Michael H. and "
                "Hoffecker, Lilian and Reitinger, Jeremy and Roach, Robert and Honigman, "
                "Benjamin",
         title="Suicide and high altitude: An integrative review",
         journal="High Altitude Medicine \\& Biology", year="2018", volume="19", number="2",
         pages="99--108", doi="10.1089/ham.2016.0131"),
    "PubMed 29161114; trata suicidio, no depresión. Los estudios agregados no bastan para "
    "estimar el efecto de la altitud en una persona y otros factores individuales "
    "probablemente pesan más."))

_alta(Ref(
    "kim2011", "Kim et al.", "2011",
    "Kim, N., Mickelson, J. B., Brenner, B. E., Haws, C. A., Yurgelun-Todd, D. A., &amp; Renshaw, "
    "P. F. (2011). Altitude, gun ownership, rural areas, and suicide. <em>American Journal of "
    'Psychiatry, 168</em>(1), 49-54. <a href="https://doi.org/10.1176/appi.ajp.2010.10020289">'
    "https://doi.org/10.1176/appi.ajp.2010.10020289</a>",
    _bib("article", "kim2011",
         author="Kim, Namkug and Mickelson, Jennie B. and Brenner, Barry E. and Haws, Charlotte "
                "A. and Yurgelun-Todd, Deborah A. and Renshaw, Perry F.",
         title="Altitude, gun ownership, rural areas, and suicide",
         journal="American Journal of Psychiatry", year="2011", volume="168", number="1",
         pages="49--54", doi="10.1176/appi.ajp.2010.10020289"),
    "PubMed 20843869; trata suicidio. Al considerar tenencia de armas y densidad de población, "
    "la altitud siguió asociándose de forma independiente."))

# ───────────── Evidencia por factor ─────────────

_alta(Ref(
    "salk2017", "Salk et al.", "2017",
    "Salk, R. H., Hyde, J. S., &amp; Abramson, L. Y. (2017). Gender differences in depression in "
    "representative national samples: Meta-analyses of diagnoses and symptoms. "
    "<em>Psychological Bulletin, 143</em>(8), 783-822. "
    '<a href="https://doi.org/10.1037/bul0000102">https://doi.org/10.1037/bul0000102</a>',
    _bib("article", "salk2017",
         author="Salk, Rachel H. and Hyde, Janet S. and Abramson, Lyn Y.",
         title="Gender differences in depression in representative national samples: "
               "Meta-analyses of diagnoses and symptoms", journal="Psychological Bulletin",
         year="2017", volume="143", number="8", pages="783--822", doi="10.1037/bul0000102"),
    "PubMed 28447828; más de 90 países; OR global de 1,95 (IC 95 % 1,88-2,03), máximo en la "
    "adolescencia (3,02 a los 13-15 años) y estable en la adultez."))

_alta(Ref(
    "devries2013", "Devries et al.", "2013",
    "Devries, K. M., Mak, J. Y. T., Bacchus, L. J., Child, J. C., Falder, G., Petzold, M., "
    "Astbury, J., &amp; Watts, C. H. (2013). Intimate partner violence and incident depressive "
    "symptoms and suicide attempts: A systematic review of longitudinal studies. <em>PLoS "
    'Medicine, 10</em>(5), Artículo e1001439. <a href="https://doi.org/10.1371/journal.pmed.1001439">'
    "https://doi.org/10.1371/journal.pmed.1001439</a>",
    _bib("article", "devries2013",
         author="Devries, Karen M. and Mak, Joelle Y. T. and Bacchus, Loraine J. and Child, "
                "Jennifer C. and Falder, Gail and Petzold, Max and Astbury, Jill and Watts, "
                "Charlotte H.",
         title="Intimate partner violence and incident depressive symptoms and suicide "
               "attempts: A systematic review of longitudinal studies",
         journal="PLoS Medicine", year="2013", volume="10", number="5", pages="e1001439",
         doi="10.1371/journal.pmed.1001439"),
    "PubMed 23671407; en mujeres, la violencia de pareja se asoció con síntomas depresivos "
    "incidentes (OR agrupado 1,97) y, en sentido inverso, los síntomas depresivos con violencia "
    "incidente (OR 1,93)."))

_alta(Ref(
    "boden2011", "Boden y Fergusson", "2011",
    "Boden, J. M., &amp; Fergusson, D. M. (2011). Alcohol and depression. <em>Addiction, "
    '106</em>(5), 906-914. <a href="https://doi.org/10.1111/j.1360-0443.2010.03351.x">'
    "https://doi.org/10.1111/j.1360-0443.2010.03351.x</a>",
    _bib("article", "boden2011", author="Boden, Joseph M. and Fergusson, David M.",
         title="Alcohol and depression", journal="Addiction", year="2011", volume="106",
         number="5", pages="906--914", doi="10.1111/j.1360-0443.2010.03351.x"),
    "PubMed 21382111; con trastorno por consumo de alcohol los riesgos de depresión se duplican "
    "(OR ajustado agrupado de 2,00 a 2,09) y la asociación más verosímil va del alcohol a la "
    "depresión."))

_alta(Ref(
    "mezuk2008", "Mezuk et al.", "2008",
    "Mezuk, B., Eaton, W. W., Albrecht, S., &amp; Golden, S. H. (2008). Depression and type 2 "
    "diabetes over the lifespan: A meta-analysis. <em>Diabetes Care, 31</em>(12), 2383-2390. "
    '<a href="https://doi.org/10.2337/dc08-0985">https://doi.org/10.2337/dc08-0985</a>',
    _bib("article", "mezuk2008",
         author="Mezuk, Briana and Eaton, William W. and Albrecht, Sandra and Golden, "
                "Sherita Hill",
         title="Depression and type 2 diabetes over the lifespan: A meta-analysis",
         journal="Diabetes Care", year="2008", volume="31", number="12", pages="2383--2390",
         doi="10.2337/dc08-0985"),
    "PubMed 19033418; relación bidireccional: la diabetes se asoció con depresión incidente "
    "(RR 1,15) y la depresión con diabetes incidente (RR 1,60)."))

_alta(Ref(
    "meng2012", "Meng et al.", "2012",
    "Meng, L., Chen, D., Yang, Y., Zheng, Y., &amp; Hui, R. (2012). Depression increases the risk "
    "of hypertension incidence: A meta-analysis of prospective cohort studies. <em>Journal of "
    'Hypertension, 30</em>(5), 842-851. <a href="https://doi.org/10.1097/HJH.0b013e32835080b7">'
    "https://doi.org/10.1097/HJH.0b013e32835080b7</a>",
    _bib("article", "meng2012",
         author="Meng, Lin and Chen, Dongmei and Yang, Yang and Zheng, Yang and Hui, Rutai",
         title="Depression increases the risk of hypertension incidence: A meta-analysis of "
               "prospective cohort studies", journal="Journal of Hypertension", year="2012",
         volume="30", number="5", pages="842--851", doi="10.1097/HJH.0b013e32835080b7"),
    "PubMed 22343537; nueve cohortes; la depresión aumentó la incidencia de hipertensión "
    "(riesgo relativo ajustado de 1,42; IC 95 % 1,09-1,86)."))

_alta(Ref(
    "luppino2010", "Luppino et al.", "2010",
    "Luppino, F. S., de Wit, L. M., Bouvy, P. F., Stijnen, T., Cuijpers, P., Penninx, B. W. J. H., "
    "&amp; Zitman, F. G. (2010). Overweight, obesity, and depression: A systematic review and "
    "meta-analysis of longitudinal studies. <em>Archives of General Psychiatry, 67</em>(3), "
    '220-229. <a href="https://doi.org/10.1001/archgenpsychiatry.2010.2">'
    "https://doi.org/10.1001/archgenpsychiatry.2010.2</a>",
    _bib("article", "luppino2010",
         author="Luppino, Floriana S. and de Wit, Leonore M. and Bouvy, Paul F. and Stijnen, "
                "Theo and Cuijpers, Pim and Penninx, Brenda W. J. H. and Zitman, Frans G.",
         title="Overweight, obesity, and depression: A systematic review and meta-analysis of "
               "longitudinal studies", journal="Archives of General Psychiatry", year="2010",
         volume="67", number="3", pages="220--229",
         doi="10.1001/archgenpsychiatry.2010.2"),
    "PubMed 20194822; relación recíproca: la obesidad se asoció con depresión incidente (OR 1,55) "
    "y la depresión con obesidad incidente (OR 1,58)."))

_alta(Ref(
    "fluharty2017", "Fluharty et al.", "2017",
    "Fluharty, M., Taylor, A. E., Grabski, M., &amp; Munafò, M. R. (2017). The association of "
    "cigarette smoking with depression and anxiety: A systematic review. <em>Nicotine &amp; "
    'Tobacco Research, 19</em>(1), 3-13. <a href="https://doi.org/10.1093/ntr/ntw140">'
    "https://doi.org/10.1093/ntr/ntw140</a>",
    _bib("article", "fluharty2017",
         author="Fluharty, Meg and Taylor, Amy E. and Grabski, Meryem and Munafò, Marcus R.",
         title="The association of cigarette smoking with depression and anxiety: A "
               "systematic review", journal="Nicotine \\& Tobacco Research", year="2017",
         volume="19", number="1", pages="3--13", doi="10.1093/ntr/ntw140"),
    "PubMed 27199385; 148 estudios longitudinales; asociaciones positivas en ambos sentidos y "
    "dirección poco consistente."))

_alta(Ref(
    "lorant2003", "Lorant et al.", "2003",
    "Lorant, V., Deliège, D., Eaton, W., Robert, A., Philippot, P., &amp; Ansseau, M. (2003). "
    "Socioeconomic inequalities in depression: A meta-analysis. <em>American Journal of "
    'Epidemiology, 157</em>(2), 98-112. <a href="https://doi.org/10.1093/aje/kwf182">'
    "https://doi.org/10.1093/aje/kwf182</a>",
    _bib("article", "lorant2003",
         author="Lorant, Vincent and Deliège, Denise and Eaton, William and Robert, Annie and "
                "Philippot, Pierre and Ansseau, Marc",
         title="Socioeconomic inequalities in depression: A meta-analysis",
         journal="American Journal of Epidemiology", year="2003", volume="157", number="2",
         pages="98--112", doi="10.1093/aje/kwf182"),
    "PubMed 12522017; el nivel socioeconómico bajo se asoció con más depresión (OR 1,81) y se "
    "observó una relación dosis-respuesta para educación e ingreso."))

_alta(Ref(
    "peen2010", "Peen et al.", "2010",
    "Peen, J., Schoevers, R. A., Beekman, A. T., &amp; Dekker, J. (2010). The current status of "
    "urban-rural differences in psychiatric disorders. <em>Acta Psychiatrica Scandinavica, "
    '121</em>(2), 84-93. <a href="https://doi.org/10.1111/j.1600-0447.2009.01438.x">'
    "https://doi.org/10.1111/j.1600-0447.2009.01438.x</a>",
    _bib("article", "peen2010",
         author="Peen, J. and Schoevers, R. A. and Beekman, A. T. and Dekker, J.",
         title="The current status of urban-rural differences in psychiatric disorders",
         journal="Acta Psychiatrica Scandinavica", year="2010", volume="121", number="2",
         pages="84--93", doi="10.1111/j.1600-0447.2009.01438.x"),
    "PubMed 19624573; 20 encuestas poblacionales; los trastornos del ánimo son algo más "
    "frecuentes en zonas urbanas, con poco efecto del ajuste por confusores."))

_alta(Ref(
    "jurek2005", "Jurek et al.", "2005",
    "Jurek, A. M., Greenland, S., Maldonado, G., &amp; Church, T. R. (2005). Proper interpretation "
    "of non-differential misclassification effects: Expectations vs observations. "
    "<em>International Journal of Epidemiology, 34</em>(3), 680-687. "
    '<a href="https://doi.org/10.1093/ije/dyi060">https://doi.org/10.1093/ije/dyi060</a>',
    _bib("article", "jurek2005",
         author="Jurek, Anne M. and Greenland, Sander and Maldonado, George and Church, "
                "Timothy R.",
         title="Proper interpretation of non-differential misclassification effects: "
               "Expectations vs observations",
         journal="International Journal of Epidemiology", year="2005", volume="34",
         number="3", pages="680--687", doi="10.1093/ije/dyi060"),
    "PubMed 15802377; la no diferencialidad del error de clasificación no garantiza por sí sola "
    "un sesgo hacia la nulidad, ni que la estimación observada sea una subestimación."))

#: Orden alfabético para la lista (APA 7 ordena por el apellido del primer autor).
_ORDEN = sorted(REFS, key=lambda k: html.unescape(REFS[k].apa).lower())

_citadas: list[str] = []


def _marca(clave: str) -> Ref:
    r = REFS[clave]
    r.usos += 1
    if clave not in _citadas:
        _citadas.append(clave)
    return r


def par(*claves: str) -> str:
    """Cita entre paréntesis: ``(Barros y Hirakata, 2003; Zou, 2004)``."""
    partes = []
    for c in claves:
        r = _marca(c)
        partes.append(f"{r.autores_citados}, {r.anio}")
    return "(" + "; ".join(partes) + ")"


def nar(clave: str) -> str:
    """Cita narrativa: ``Barros y Hirakata (2003)``."""
    r = _marca(clave)
    return f"{r.autores_citados} ({r.anio})"


def reiniciar() -> None:
    """Vacía el registro de citas antes de generar todas las páginas."""
    _citadas.clear()
    for r in REFS.values():
        r.usos = 0


def lista_html() -> str:
    """Lista APA 7 en HTML con solo las referencias citadas, por orden alfabético."""
    claves = [k for k in _ORDEN if k in _citadas]
    items = "".join(f"<li>{REFS[k].apa}</li>" for k in claves)
    return f'<ol class="referencias">{items}</ol>'


def bib_citadas() -> str:
    """Contenido del .bib con las mismas referencias que la lista del boletín."""
    claves = [k for k in _ORDEN if k in _citadas]
    return "\n\n".join(REFS[k].bib for k in claves) + "\n"


def verificaciones() -> str:
    """Qué se comprobó de cada referencia citada (para el informe interno)."""
    return "\n".join(f"- {REFS[k].apa.split('(')[0].strip()} ({REFS[k].anio}): "
                     f"{REFS[k].verificado}" for k in _ORDEN if k in _citadas)
