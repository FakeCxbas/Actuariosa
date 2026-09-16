"""
Tablas y Coeficientes Actuariales para Ecuador
Base legal:
- Código del Trabajo (Art. 218: Coeficientes de renta vitalicia).
- Resolución CI. 141 (Registro Oficial 650, 2002) del IESS: Tablas biométricas y tasa técnica (4% anual).
- Acuerdo Ministerial MDT-2018-0118 y MDT-2016-0099.
- Resolución No. 07-2021 de la Corte Nacional de Justicia (Jurisprudencia vinculante sobre topes).
"""
from __future__ import annotations

# Coeficientes oficiales de renta vitalicia del Código del Trabajo (Artículo 218)
# Coeficiente según la edad cumplida a la fecha de jubilación
COEFICIENTES_CODIGO_TRABAJO: dict[int, float] = {
    40: 0.0531, 41: 0.0540, 42: 0.0550, 43: 0.0560, 44: 0.0571,
    45: 0.0582, 46: 0.0594, 47: 0.0607, 48: 0.0620, 49: 0.0634,
    50: 0.0649, 51: 0.0665, 52: 0.0682, 53: 0.0700, 54: 0.0719,
    55: 0.0739, 56: 0.0761, 57: 0.0784, 58: 0.0808, 59: 0.0834,
    60: 0.0862, 61: 0.0892, 62: 0.0924, 63: 0.0958, 64: 0.0995,
    65: 0.1035, 66: 0.1078, 67: 0.1125, 68: 0.1176, 69: 0.1231,
    70: 0.1291, 71: 0.1356, 72: 0.1428, 73: 0.1507, 74: 0.1594,
    75: 0.1690, 76: 0.1797, 77: 0.1916, 78: 0.2049, 79: 0.2198,
    80: 0.2366, 81: 0.2555, 82: 0.2769, 83: 0.3012, 84: 0.3289,
    85: 0.3606, 86: 0.3970, 87: 0.4391, 88: 0.4881, 89: 0.5456,
    90: 0.6138, 91: 0.6954, 92: 0.7941, 93: 0.9149, 94: 1.0648,
    95: 1.2541,
}

def obtener_coeficiente_ct(edad: int) -> float:
    """Retorna el coeficiente del Código del Trabajo para la edad dada."""
    if edad < 40:
        return COEFICIENTES_CODIGO_TRABAJO[40]
    if edad > 95:
        return COEFICIENTES_CODIGO_TRABAJO[95]
    return COEFICIENTES_CODIGO_TRABAJO[edad]


# Anualidad vitalicia anticipada estimada según tablas de mortalidad IESS (Res. CI. 141)
# a_ddot(x) a tasa técnica de descuento del 4% anual
ANUALIDADES_VITALICIAS_4_PORCIENTO: dict[int, float] = {
    40: 17.58, 41: 17.31, 42: 17.03, 43: 16.74, 44: 16.44,
    45: 16.13, 46: 15.81, 47: 15.48, 48: 15.14, 49: 14.79,
    50: 14.43, 51: 14.06, 52: 13.68, 53: 13.29, 54: 12.89,
    55: 12.48, 56: 12.06, 57: 11.63, 58: 11.19, 59: 10.74,
    60: 10.29, 61: 9.83,  62: 9.37,  63: 8.90,  64: 8.44,
    65: 7.97,  66: 7.51,  67: 7.05,  68: 6.60,  69: 6.16,
    70: 5.72,  71: 5.30,  72: 4.89,  73: 4.49,  74: 4.11,
    75: 3.75,  76: 3.41,  77: 3.09,  78: 2.79,  79: 2.51,
    80: 2.25,  85: 1.28,  90: 0.67,  95: 0.31
}

def obtener_anualidad_vitalicia(edad: int) -> float:
    """Retorna la anualidad vitalicia anticipada ä_x para la edad dada."""
    if edad in ANUALIDADES_VITALICIAS_4_PORCIENTO:
        return ANUALIDADES_VITALICIAS_4_PORCIENTO[edad]
    if edad < 40:
        return ANUALIDADES_VITALICIAS_4_PORCIENTO[40]
    if edad > 95:
        return ANUALIDADES_VITALICIAS_4_PORCIENTO[95]
    # Interpolación lineal simple entre edades
    edades = sorted(ANUALIDADES_VITALICIAS_4_PORCIENTO.keys())
    for i in range(len(edades) - 1):
        e1, e2 = edades[i], edades[i+1]
        if e1 <= edad <= e2:
            a1, a2 = ANUALIDADES_VITALICIAS_4_PORCIENTO[e1], ANUALIDADES_VITALICIAS_4_PORCIENTO[e2]
            return a1 + (a2 - a1) * (edad - e1) / (e2 - e1)
    return 8.0

# Tasas estimadas de rotación de personal (turnover) por edad y permanencia
def tasa_rotacion_anual(antiguedad_anios: float, edad: int) -> float:
    """
    Tasa estimada de probabilidad de separación voluntaria / despido.
    A mayor antigüedad y edad, la rotación decrece sensiblemente.
    """
    if antiguedad_anios >= 20:
        return 0.010  # 1.0% para personas con derecho o casi derecho a jubilación
    elif antiguedad_anios >= 15:
        return 0.020  # 2.0%
    elif antiguedad_anios >= 10:
        return 0.035  # 3.5%
    elif antiguedad_anios >= 5:
        return 0.050  # 5.0%
    else:
        return 0.080  # 8.0% en personal de reciente ingreso
