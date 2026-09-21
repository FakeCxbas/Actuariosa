"""
estructurar_correos_csv.py
Organiza la carpeta 'Correos .csv' en dos grupos limpios y sencillos siguiendo
la convención de nombres natural del Drive:
 1. Correos 100% funcionales (las empresas activas de Supercias y corporativos)
 2. Otras listas y descartes (educativos, genéricos conservados, inactivas e histórico)
"""
import shutil
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    base_src = root / "resultados/depuracion_supercias_2026"
    drive_local = root / "resultados/Para_Google_Drive"
    
    # Limpiar destino local para estructura limpia
    shutil.rmtree(drive_local, ignore_errors=True)
    drive_local.mkdir(parents=True, exist_ok=True)

    dir_funcionales = drive_local / "Correos 100% funcionales"
    dir_otros = drive_local / "Otras listas y descartes"

    dir_funcionales.mkdir(parents=True, exist_ok=True)
    dir_otros.mkdir(parents=True, exist_ok=True)

    print("Organizando archivos en las dos carpetas principales...")

    # 1. Correos 100% funcionales
    shutil.copy2(base_src / "1_Correos_Supercias_Activas_con_RUC.csv",
                 dir_funcionales / "Empresas Supercias Activas con RUC.csv")
    shutil.copy2(base_src / "2_Correos_Negocios_Corporativos_Activos.csv",
                 dir_funcionales / "Correos Corporativos Empresas Activas.csv")
    shutil.copy2(base_src / "3_Correos_Negocios_Totales_Depurados_Solo_Correos.csv",
                 dir_funcionales / "Correos Negocios Totales (Solo Correos).csv")
    shutil.copy2(base_src / "3_Correos_Negocios_Totales_Depurados_Detallado.csv",
                 dir_funcionales / "Correos Negocios Totales (Detallado con Datos).csv")

    # 2. Otras listas y descartes
    shutil.copy2(base_src / "5_Correos_Instituciones_Educativas_Colegios.csv",
                 dir_otros / "Colegios e Instituciones Educativas.csv")
    shutil.copy2(base_src / "6_Correos_Otros_Genericos_Conservados.csv",
                 dir_otros / "Correos Genericos Historicos Conservados.csv")
    shutil.copy2(base_src / "4_Correos_Descartados_Disolucion_o_Inactivas.csv",
                 dir_otros / "Empresas Inactivas o Liquidacion Supercias.csv")

    # Histórico del 20 de septiembre
    path_20sep = root / "resultados/Para_Google_Drive/Correos aptos totales 20 septiembre 2026.csv"
    if not path_20sep.exists():
        path_20sep = base_src.parent / "Para_Google_Drive/4. Historico Bases/Correos_Aptos_Totales_20_Septiembre_2026.csv"
    if not path_20sep.exists():
        path_20sep = root / "resultados/consolidado_maestro/Correos aptos totales 20 septiembre 2026.csv"
    
    # Si no lo encuentra, buscarlo en resultados
    for p in root.glob("**/Correos aptos totales 20 septiembre 2026.csv"):
        path_20sep = p
        break

    if path_20sep and path_20sep.exists():
        shutil.copy2(path_20sep, dir_otros / "Correos aptos totales 20 septiembre 2026.csv")

    # Informes
    shutil.copy2(base_src / "Resumen_Depuracion_Supercias.json",
                 dir_otros / "Resumen Depuracion Supercias.json")
    
    # Documento de informe previo si existe
    doc_previo = root / "resultados/Para_Google_Drive/5. Informes y Metricas/Informe General Actual.docx"
    if doc_previo.exists():
        shutil.copy2(doc_previo, dir_otros / "Informe General Actual.docx")

    # Crear ZIP comprimido al día
    zip_dest = root / "resultados/Correos_Depurados_Google_Drive"
    shutil.make_archive(str(zip_dest), 'zip', str(drive_local))
    shutil.copy2(root / "resultados/Correos_Depurados_Google_Drive.zip",
                 drive_local / "Correos_Depurados_Google_Drive.zip")

    print(f"Estructura organizada completada en: {drive_local}")


if __name__ == "__main__":
    main()
