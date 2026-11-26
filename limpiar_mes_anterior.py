"""
limpiar_mes_anterior.py
Mueve los CSVs de meses anteriores desde data/ hacia data/historicos/YYYY-MM/
para mantener el repositorio de GitHub ligero y limpio.

IMPORTANTE: Este script NUNCA borra archivos. Solo los mueve a una carpeta local
que está en el .gitignore, por lo que no se subirán a GitHub.

Uso:
    python limpiar_mes_anterior.py
"""
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

# ==========================================
# CONFIGURACIÓN
# ==========================================
DATA_DIR = Path("data")
HISTORICOS_DIR = DATA_DIR / "historicos"

# Patrones de archivos CSV que maneja el dashboard
PATRONES_CSV = [
    "produccion_*.csv",
    "roturas_*.csv",
    "tiempos_perdidos_*.csv",
]

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================
def extraer_fecha(nombre_archivo):
    """Extrae la fecha YYYYMMDD del nombre del archivo."""
    m = re.search(r'(\d{8})', nombre_archivo)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y%m%d")
        except ValueError:
            return None
    return None

def obtener_mes_actual():
    """Devuelve el año y mes actuales."""
    hoy = datetime.now()
    return hoy.year, hoy.month

def es_archivo_csv_valido(archivo):
    """Verifica si el archivo es uno de los CSVs que maneja el dashboard."""
    nombre = archivo.name.lower()
    return (nombre.startswith("produccion_") or 
            nombre.startswith("roturas_") or 
            nombre.startswith("tiempos_perdidos_")) and nombre.endswith(".csv")

# ==========================================
# FUNCIÓN PRINCIPAL
# ==========================================
def limpiar_repositorio():
    print("=" * 70)
    print("🧹 LIMPIEZA DEL REPOSITORIO - VENTANA DESLIZANTE")
    print("=" * 70)
    
    # Verificar que exista la carpeta data/
    if not DATA_DIR.exists():
        print(f"❌ ERROR: No se encuentra la carpeta '{DATA_DIR}'")
        return False
    
    # Crear carpeta de históricos si no existe
    HISTORICOS_DIR.mkdir(exist_ok=True)
    
    año_actual, mes_actual = obtener_mes_actual()
    print(f"📅 Mes activo: {año_actual}-{mes_actual:02d}")
    print(f"📁 Carpeta de archivo: {HISTORICOS_DIR.resolve()}")
    print()
    
    # Escanear archivos en data/
    archivos_en_data = [f for f in DATA_DIR.iterdir() if f.is_file()]
    csv_validos = [f for f in archivos_en_data if es_archivo_csv_valido(f)]
    
    print(f"📊 Archivos CSV encontrados en data/: {len(csv_validos)}")
    
    # Clasificar archivos
    archivos_mes_actual = []
    archivos_meses_anteriores = []
    archivos_sin_fecha = []
    
    for archivo in csv_validos:
        fecha = extraer_fecha(archivo.name)
        if not fecha:
            archivos_sin_fecha.append(archivo)
            continue
        
        if fecha.year == año_actual and fecha.month == mes_actual:
            archivos_mes_actual.append(archivo)
        else:
            archivos_meses_anteriores.append((archivo, fecha))
    
    # Mostrar resumen de clasificación
    print(f"   ✅ Del mes activo ({año_actual}-{mes_actual:02d}): {len(archivos_mes_actual)} archivos")
    print(f"   📦 De meses anteriores: {len(archivos_meses_anteriores)} archivos")
    if archivos_sin_fecha:
        print(f"   ⚠️  Sin fecha en el nombre (no se tocarán): {len(archivos_sin_fecha)} archivos")
    print()
    
    # Si no hay nada que mover, terminar
    if not archivos_meses_anteriores:
        print("✨ No hay archivos de meses anteriores para mover. Repositorio ya está limpio.")
        print("=" * 70)
        return True
    
    # Mover archivos de meses anteriores
    print("📦 Moviendo archivos a carpeta de archivo...")
    movidos = 0
    errores = 0
    
    for archivo, fecha in sorted(archivos_meses_anteriores, key=lambda x: x[1]):
        # Crear subcarpeta para el mes (ej: historicos/2026-10/)
        mes_carpeta = HISTORICOS_DIR / f"{fecha.year}-{fecha.month:02d}"
        mes_carpeta.mkdir(exist_ok=True)
        
        destino = mes_carpeta / archivo.name
        
        # Seguridad: si el archivo ya existe en destino, no sobrescribir
        if destino.exists():
            print(f"   ⚠️  {archivo.name} ya existe en {mes_carpeta.name}. Se omite.")
            continue
        
        try:
            shutil.move(str(archivo), str(destino))
            movidos += 1
            print(f"   ✅ {archivo.name} → historicos/{fecha.year}-{fecha.month:02d}/")
        except Exception as e:
            errores += 1
            print(f"   ❌ Error moviendo {archivo.name}: {e}")
    
    # Resumen final
    print()
    print("=" * 70)
    print("📊 RESUMEN DE LIMPIEZA")
    print("=" * 70)
    print(f"   ✅ Archivos movidos: {movidos}")
    if errores:
        print(f"   ❌ Errores: {errores}")
    print(f"   📁 Archivos que quedan en data/: {len(archivos_mes_actual)}")
    print()
    print("💡 PRÓXIMO PASO:")
    print("   Ejecuta 'ejecutar.bat' para que Git detecte los archivos eliminados")
    print("   de data/ y los borre también de GitHub (conservándolos en tu PC).")
    print("=" * 70)
    
    return True

# ==========================================
# EJECUCIÓN
# ==========================================
if __name__ == '__main__':
    try:
        limpiar_repositorio()
    except KeyboardInterrupt:
        print("\n\n⚠️ Proceso interrumpido por el usuario.")
    except Exception as e:
        print(f"\n\n❌ ERROR INESPERADO: {e}")