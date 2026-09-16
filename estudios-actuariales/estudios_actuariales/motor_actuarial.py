"""
Motor de Cálculo Actuarial para Beneficios a los Empleados (Ecuador - NIC 19 / NIIF)
- Jubilación Patronal (Código del Trabajo Art. 216 - 219)
- Bonificación por Desahucio (Código del Trabajo Art. 185)
- Método: Unidad de Crédito Proyectada (Projected Unit Credit Method - PUCM)
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
import math
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from tablas_actuariales import (
    obtener_coeficiente_ct,
    obtener_anualidad_vitalicia,
    tasa_rotacion_anual,
)


@dataclass
class EmpleadoCenso:
    cedula: str
    nombre: str
    sexo: str  # 'M' o 'F'
    fecha_nacimiento: date
    fecha_ingreso: date
    sueldo_mensual: float
    reserva_anterior_jubilacion: float = 0.0
    reserva_anterior_desahucio: float = 0.0
    observaciones: str = ""


@dataclass
class ParametrosActuariales:
    fecha_corte: date
    tasa_descuento: float = 0.04               # 4.0% tasa técnica oficial IESS (Res. CI. 141)
    tasa_incremento_salarial: float = 0.02      # 2.0% expectativa de inflación/crecimiento
    salario_basico_unificado: float = 460.00    # SBU vigente
    edad_jubilacion_hombres: int = 65
    edad_jubilacion_mujeres: int = 60
    anios_servicio_jubilacion: float = 25.0     # 25 años para jubilación patronal ordinaria
    tasa_impuesto_renta: float = 0.25           # 25% tarifa corporativa para impuesto diferido


@dataclass
class ResultadoEmpleado:
    cedula: str
    nombre: str
    sexo: str
    edad: float
    antiguedad: float
    sueldo_actual: float
    sueldo_proyectado: float
    anios_al_retiro: float
    edad_retiro: int

    # Jubilación Patronal
    pension_mensual_estimada: float
    obd_jubilacion: float                      # Obligación por Beneficios Definidos (Pasivo)
    costo_servicio_jubilacion: float           # Current Service Cost
    costo_interes_jubilacion: float            # Interest Cost
    ajuste_actuarial_jubilacion: float         # Variación neta respecto a reserva anterior
    con_derecho_adquirido_jubilacion: bool     # >= 25 años
    en_periodo_proporcional_jubilacion: bool   # 20 - 24 años

    # Desahucio
    beneficio_desahucio_acumulado: float       # 25% de última remuneración x años
    obd_desahucio: float                       # Pasivo por desahucio
    costo_servicio_desahucio: float
    costo_interes_desahucio: float
    ajuste_actuarial_desahucio: float

    # Totales del empleado
    obd_total: float
    costo_servicio_total: float


class CalculadoraActuarial:
    def __init__(self, parametros: ParametrosActuariales):
        self.params = parametros

    def calcular_empleado(self, emp: EmpleadoCenso) -> ResultadoEmpleado:
        dias_edad = (self.params.fecha_corte - emp.fecha_nacimiento).days
        edad = max(18.0, dias_edad / 365.25)

        dias_antiguedad = (self.params.fecha_corte - emp.fecha_ingreso).days
        antiguedad = max(0.0, dias_antiguedad / 365.25)

        # Edad normal de jubilación según sexo o por alcanzar 25 años de servicio
        edad_jubilar_genero = (
            self.params.edad_jubilacion_mujeres
            if emp.sexo.upper() == "F"
            else self.params.edad_jubilacion_hombres
        )

        faltante_servicio = max(0.0, self.params.anios_servicio_jubilacion - antiguedad)
        faltante_edad = max(0.0, float(edad_jubilar_genero) - edad)

        # Se jubila cuando cumpla los 25 años o la edad jubilar (lo que ocurra primero)
        anios_al_retiro = min(faltante_servicio, faltante_edad) if faltante_servicio > 0 else 0.0
        edad_retiro = int(round(edad + anios_al_retiro))
        if edad_retiro < 40:
            edad_retiro = 40

        # Proyección salarial al momento del retiro esperado
        g = self.params.tasa_incremento_salarial
        sueldo_proyectado = emp.sueldo_mensual * math.pow(1.0 + g, anios_al_retiro)

        # -------------------------------------------------------------
        # 1. CÁLCULO DE JUBILACIÓN PATRONAL (Art. 216 Código del Trabajo)
        # -------------------------------------------------------------
        # Haber individual legal: 5% del promedio anual x 25 años
        # HI = 0.05 * (sueldo_proyectado * 12) * 25
        haber_individual = 0.05 * (sueldo_proyectado * 12.0) * self.params.anios_servicio_jubilacion

        # Coeficiente del Código del Trabajo (Art. 218)
        coef_ct = obtener_coeficiente_ct(edad_retiro)

        # Pensión mensual patronal según Código del Trabajo
        # Pensión Anual = HI / Coeficiente
        pension_anual_bruta = haber_individual / coef_ct
        pension_mensual = pension_anual_bruta / 12.0

        # Reglas legales y jurisprudencia vinculante (Corte Nacional de Justicia Res. 07-2021)
        # Piso legal: $20.00 o $30.00 USD
        pension_mensual = max(30.0, pension_mensual)
        # Techo legal: no mayor al sueldo medio mensual del trabajador (sueldo_proyectado)
        pension_mensual = min(sueldo_proyectado, pension_mensual)

        # Pensión anual total considerando décima tercera y décima cuarta renta (Art. 216 num. 3)
        pension_anual_total = (pension_mensual * 13.0) + self.params.salario_basico_unificado

        # Valor Presente Actuarial del flujo vitalicio al momento de jubilarse
        anualidad_vitalicia = obtener_anualidad_vitalicia(edad_retiro)
        vp_en_retiro = pension_anual_total * anualidad_vitalicia

        # Factor de descuento financiero v^t
        i = self.params.tasa_descuento
        factor_descuento = math.pow(1.0 + i, -anios_al_retiro)

        # Factor de probabilidad de permanencia (supervivencia y retención)
        tasa_rot = tasa_rotacion_anual(antiguedad, int(edad))
        probabilidad_permanencia = math.pow(1.0 - tasa_rot, anios_al_retiro)

        # Valor Presente Actuarial de la Obligación Futura al corte actual
        vpa_futuro = vp_en_retiro * factor_descuento * probabilidad_permanencia

        # Prorrateo por Unidad de Crédito Proyectada (PUCM - NIC 19)
        derecho_adquirido = antiguedad >= self.params.anios_servicio_jubilacion
        periodo_proporcional = 20.0 <= antiguedad < self.params.anios_servicio_jubilacion

        if derecho_adquirido:
            # Derecho adquirido: pasivo al 100% de la obligación vitalicia
            obd_jubilacion = vpa_futuro
            costo_servicio_jub = 0.0
        elif antiguedad >= 20.0:
            # Proporcional de jubilación (Art. 216, inciso 7)
            fraccion = antiguedad / self.params.anios_servicio_jubilacion
            obd_jubilacion = vpa_futuro * fraccion
            costo_servicio_jub = vpa_futuro / self.params.anios_servicio_jubilacion
        else:
            # Menor a 20 años: provisión proporcional a los años de servicio transcurridos
            anios_totales_esperados = antiguedad + anios_al_retiro
            fraccion = (antiguedad / anios_totales_esperados) if anios_totales_esperados > 0 else 0.0
            obd_jubilacion = vpa_futuro * fraccion
            costo_servicio_jub = (vpa_futuro / anios_totales_esperados) if anios_totales_esperados > 0 else 0.0

        costo_interes_jub = emp.reserva_anterior_jubilacion * i
        ajuste_jubilacion = obd_jubilacion - emp.reserva_anterior_jubilacion

        # -------------------------------------------------------------
        # 2. CÁLCULO DE BONIFICACIÓN POR DESAHUCIO (Art. 185 Código del Trabajo)
        # -------------------------------------------------------------
        # 25% de la última remuneración mensual por cada año de servicio completo
        anios_completos = math.floor(antiguedad)
        beneficio_acumulado_desahucio = 0.25 * emp.sueldo_mensual * anios_completos

        # Enfoque PUCM para Desahucio:
        # Se proyecta al cese considerando probabilidad de rotación acumulada
        if anios_al_retiro > 0:
            anios_totales_desahucio = antiguedad + anios_al_retiro
            beneficio_proyectado_desahucio = 0.25 * sueldo_proyectado * anios_totales_desahucio
            obd_desahucio = beneficio_proyectado_desahucio * factor_descuento * (antiguedad / anios_totales_desahucio)
            costo_servicio_desahucio = (beneficio_proyectado_desahucio * factor_descuento) / anios_totales_desahucio
        else:
            obd_desahucio = beneficio_acumulado_desahucio
            costo_servicio_desahucio = 0.0

        # El pasivo no debe ser menor al beneficio acumulado devengado si saliera hoy
        obd_desahucio = max(beneficio_acumulado_desahucio * 0.90, obd_desahucio)

        costo_interes_desahucio = emp.reserva_anterior_desahucio * i
        ajuste_desahucio = obd_desahucio - emp.reserva_anterior_desahucio

        return ResultadoEmpleado(
            cedula=emp.cedula,
            nombre=emp.nombre,
            sexo=emp.sexo,
            edad=round(edad, 2),
            antiguedad=round(antiguedad, 2),
            sueldo_actual=round(emp.sueldo_mensual, 2),
            sueldo_proyectado=round(sueldo_proyectado, 2),
            anios_al_retiro=round(anios_al_retiro, 2),
            edad_retiro=edad_retiro,
            pension_mensual_estimada=round(pension_mensual, 2),
            obd_jubilacion=round(obd_jubilacion, 2),
            costo_servicio_jubilacion=round(costo_servicio_jub, 2),
            costo_interes_jubilacion=round(costo_interes_jub, 2),
            ajuste_actuarial_jubilacion=round(ajuste_jubilacion, 2),
            con_derecho_adquirido_jubilacion=derecho_adquirido,
            en_periodo_proporcional_jubilacion=periodo_proporcional,
            beneficio_desahucio_acumulado=round(beneficio_acumulado_desahucio, 2),
            obd_desahucio=round(obd_desahucio, 2),
            costo_servicio_desahucio=round(costo_servicio_desahucio, 2),
            costo_interes_desahucio=round(costo_interes_desahucio, 2),
            ajuste_actuarial_desahucio=round(ajuste_desahucio, 2),
            obd_total=round(obd_jubilacion + obd_desahucio, 2),
            costo_servicio_total=round(costo_servicio_jub + costo_servicio_desahucio, 2),
        )

    def ejecutar_estudio(self, censo: list[EmpleadoCenso], nombre_empresa: str) -> dict[str, Any]:
        resultados = [self.calcular_empleado(e) for e in censo]

        total_empleados = len(resultados)
        femenino = sum(1 for r in resultados if r.sexo.upper() == "F")
        masculino = sum(1 for r in resultados if r.sexo.upper() == "M")

        edad_promedio = sum(r.edad for r in resultados) / total_empleados if total_empleados else 0.0
        antiguedad_promedio = sum(r.antiguedad for r in resultados) / total_empleados if total_empleados else 0.0
        sueldo_promedio = sum(r.sueldo_actual for r in resultados) / total_empleados if total_empleados else 0.0

        total_obd_jubilacion = sum(r.obd_jubilacion for r in resultados)
        total_servicio_jubilacion = sum(r.costo_servicio_jubilacion for r in resultados)
        total_interes_jubilacion = sum(r.costo_interes_jubilacion for r in resultados)
        total_ajuste_jubilacion = sum(r.ajuste_actuarial_jubilacion for r in resultados)

        total_obd_desahucio = sum(r.obd_desahucio for r in resultados)
        total_servicio_desahucio = sum(r.costo_servicio_desahucio for r in resultados)
        total_interes_desahucio = sum(r.costo_interes_desahucio for r in resultados)
        total_ajuste_desahucio = sum(r.ajuste_actuarial_desahucio for r in resultados)

        # Segmentación legal de desahucio (< 20 años vs >= 20 años)
        desahucio_menor_20 = sum(r.obd_desahucio for r in resultados if r.antiguedad < 20.0)
        conteo_menor_20 = sum(1 for r in resultados if r.antiguedad < 20.0)

        desahucio_mayor_20 = sum(r.obd_desahucio for r in resultados if r.antiguedad >= 20.0)
        conteo_mayor_20 = sum(1 for r in resultados if r.antiguedad >= 20.0)

        total_obd_global = total_obd_jubilacion + total_obd_desahucio
        total_gasto_ejercicio = total_ajuste_jubilacion + total_ajuste_desahucio

        # Activo por impuesto diferido según Circular SRI No. NAC-DGECCGC23-00000006
        activo_impuesto_diferido = total_obd_global * self.params.tasa_impuesto_renta

        # Asiento contable propuesto
        asiento_contable = [
            {
                "cuenta": "Gastos Generales por Beneficios a Empleados (Gasto No Deducible)",
                "debe": round(total_obd_global, 2),
                "haber": 0.0,
                "nota": "Reconocimiento contable de la provisión acumulada del ejercicio (NIC 19)"
            },
            {
                "cuenta": "Provisión por Jubilación Patronal (Pasivo a Largo Plazo)",
                "debe": 0.0,
                "haber": round(total_obd_jubilacion, 2),
                "nota": "Obligación por beneficios definidos de jubilación patronal"
            },
            {
                "cuenta": "Provisión por Bonificación por Desahucio (Pasivo a Largo Plazo)",
                "debe": 0.0,
                "haber": round(total_obd_desahucio, 2),
                "nota": "Obligación acumulada por desahucio"
            },
            {
                "cuenta": "Activo por Impuestos Diferidos (25% según Circular SRI)",
                "debe": round(activo_impuesto_diferido, 2),
                "haber": 0.0,
                "nota": "Diferencia temporaria deducible en el momento del pago efectivo"
            },
            {
                "cuenta": "Ingreso por Impuesto a la Renta Diferido (Resultados)",
                "debe": 0.0,
                "haber": round(activo_impuesto_diferido, 2),
                "nota": "Efecto tributario diferido en resultados"
            }
        ]

        return {
            "empresa": nombre_empresa,
            "fecha_corte": self.params.fecha_corte.isoformat(),
            "parametros": {
                "tasa_descuento": self.params.tasa_descuento,
                "tasa_incremento_salarial": self.params.tasa_incremento_salarial,
                "salario_basico_unificado": self.params.salario_basico_unificado,
                "tasa_impuesto_renta": self.params.tasa_impuesto_renta,
            },
            "demografia": {
                "total_empleados": total_empleados,
                "mujeres": femenino,
                "hombres": masculino,
                "edad_promedio": round(edad_promedio, 2),
                "antiguedad_promedio": round(antiguedad_promedio, 2),
                "sueldo_promedio": round(sueldo_promedio, 2),
            },
            "resumen_jubilacion_patronal": {
                "obd_total": round(total_obd_jubilacion, 2),
                "costo_servicio_actual": round(total_servicio_jubilacion, 2),
                "costo_intereses": round(total_interes_jubilacion, 2),
                "ajuste_anual": round(total_ajuste_jubilacion, 2),
                "empleados_con_derecho_adquirido": sum(1 for r in resultados if r.con_derecho_adquirido_jubilacion),
                "empleados_en_periodo_proporcional": sum(1 for r in resultados if r.en_periodo_proporcional_jubilacion),
            },
            "resumen_desahucio": {
                "obd_total": round(total_obd_desahucio, 2),
                "costo_servicio_actual": round(total_servicio_desahucio, 2),
                "costo_intereses": round(total_interes_desahucio, 2),
                "ajuste_anual": round(total_ajuste_desahucio, 2),
                "tramo_menor_20_anios": {
                    "empleados": conteo_menor_20,
                    "monto": round(desahucio_menor_20, 2),
                },
                "tramo_mayor_o_igual_20_anios": {
                    "empleados": conteo_mayor_20,
                    "monto": round(desahucio_mayor_20, 2),
                },
            },
            "totales_estudio": {
                "obd_global_nic19": round(total_obd_global, 2),
                "gasto_anual_provision": round(total_gasto_ejercicio, 2),
                "activo_impuesto_diferido": round(activo_impuesto_diferido, 2),
            },
            "asiento_contable": asiento_contable,
            "detalle_empleados": [asdict(r) for r in resultados],
        }
