"""
pipeline_unificado.py
Un solo clic para: Extraer de SISGO + Convertir PDFs a CSVs en la carpeta data/
"""
import os
import re
import csv
import time
import requests
import pdfplumber
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pathlib import Path

# ==========================================
# 1. CONFIGURACIÓN Y FECHAS AUTOMÁTICAS
# ==========================================
load_dotenv()
USUARIO = os.getenv('USUARIO')
PASSWORD = os.getenv('PASSWORD')

if not USUARIO or not PASSWORD:
    print("❌ ERROR: Faltan credenciales. Revisa tu archivo .env")
    exit(1)

# Fechas dinámicas: Primer día del mes actual hasta AYER
hoy = datetime.now()
ayer = hoy - timedelta(days=1)
inicio_mes = ayer.replace(day=1)

FECHA_INICIO = inicio_mes.strftime("%Y%m%d")
FECHA_FIN = ayer.strftime("%Y%mDD") # Corregido a %Y%m%d
FECHA_FIN = ayer.strftime("%Y%m%d")

BASE_URL = "http://172.30.1.13/SISGO"
URDIDO_URL = f"{BASE_URL}/produccion/urdido.php"
DATA_RAW = Path("data/raw")
DATA_SALIDA = Path("data")
DATA_SALIDA.mkdir(exist_ok=True)

CARPETA_RAW_ACTUAL = DATA_RAW / f"urdido_completo_{FECHA_INICIO}_{FECHA_FIN}"
CARPETA_RAW_ACTUAL.mkdir(parents=True, exist_ok=True)

MAQUINAS = ['URDIDORA # 01', 'URDIDORA # 02', 'URDIDORA # 03', 'URDIDORA # 04']
auth = HTTPBasicAuth(USUARIO, PASSWORD)
session = requests.Session()

print("="*60)
print(f"🚀 PIPELINE UNIFICADO URDIDO")
print(f"📅 Rango automático: {FECHA_INICIO} al {FECHA_FIN}")
print(f"📁 Destino CSV finales: {DATA_SALIDA.resolve()}")
print("="*60)

# ==========================================
# 2. FUNCIONES DE EXTRACCIÓN (De tu script original)
# ==========================================
def generar_fechas(inicio, fin):
    inicio_dt = datetime.strptime(inicio, "%Y%m%d")
    fin_dt = datetime.strptime(fin, "%Y%m%d")
    fechas = []
    current = inicio_dt
    while current <= fin_dt:
        fechas.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    return fechas

def descargar_pdf(fecha, tipo_informe):
    urls = {
        'produccion': f"{BASE_URL}/produccion/urdido_informe_produccion.php?fecha={fecha}",
        'tiempos_perdidos': f"{BASE_URL}/produccion/urdido_informe_tiempos_perdidos.php?fecha={fecha}",
        'inventario': f"{BASE_URL}/produccion/urdido_informe_inventario.php?fecha={fecha}"
    }
    try:
        response = session.get(urls[tipo_informe], auth=auth, timeout=30)
        if response.status_code == 200 and response.content[:4] == b'%PDF':
            return response.content
    except:
        pass
    return None

def extraer_urdido_csv(fecha):
    url = f"{URDIDO_URL}?fecha={fecha}"
    try:
        response = session.get(url, auth=auth, timeout=30)
        response.encoding = 'windows-1252'
        if response.status_code != 200: return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        tabla = soup.find('table', {'bgcolor': '#0066CC'})
        if not tabla: return []
        
        filas = tabla.find_all('tr')
        header_index = -1
        for idx, fila in enumerate(filas):
            if '#' in fila.get_text(strip=True) and 'ID' in fila.get_text(strip=True):
                header_index = idx
                break
        
        if header_index == -1: return []
        
        columnas = [celda.get_text(strip=True) for celda in filas[header_index].find_all('td') if celda.get_text(strip=True)]
        datos = []
        for fila in filas[header_index + 1:]:
            celdas = fila.find_all('td')
            if len(celdas) >= 10 and celdas[0].get_text(strip=True).isdigit():
                registro = {'fecha': fecha}
                for i, nombre in enumerate(columnas):
                    registro[nombre] = celdas[i].get_text(strip=True) if i < len(celdas) else ''
                datos.append(registro)
        return datos
    except Exception as e:
        print(f"   ❌ Error CSV {fecha}: {e}")
        return []

# ==========================================
# 3. FUNCIONES DE CONVERSIÓN PDF A CSV (De tu script original)
# ==========================================
def limpiar(valor):
    return str(valor).replace('\n', ' ').strip() if valor is not None else ''

def detectar_maquina(texto):
    m = re.search(r'URDIDORA\s*#\s*(\d+)', texto)
    return f'URDIDORA # {int(m.group(1)):02d}' if m else None

def parsear_numero(s):
    s = limpiar(s)
    if not s: return 0.0
    if ',' in s and '.' in s: s = s.replace('.', '').replace(',', '.')
    elif ',' in s: s = s.replace(',', '.')
    try: return float(s)
    except ValueError: return 0.0

def extraer_y_guardar_produccion(pdf_path, fecha):
    filas = []
    maquina_actual = None
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text() or ''
                maq = detectar_maquina(texto)
                if maq: maquina_actual = maq
                
                for tabla in (pagina.extract_tables() or []):
                    if not tabla or len(tabla) < 2: continue
                    cabecera = ' '.join(limpiar(c).lower() for c in (tabla[0] or []))
                    if 'codigo' not in cabecera: continue
                    
                    for fila in tabla[1:]:
                        if not fila or len(fila) < 8 or not limpiar(fila[0]).isdigit(): continue
                        filas.append({
                            'orden': int(limpiar(fila[0])),
                            'id': limpiar(fila[1]),
                            'persona': limpiar(fila[2]),
                            'estilo': limpiar(fila[3]),
                            'titulo': limpiar(fila[4]),
                            'lote': limpiar(fila[5]),
                            'nro_madeja': limpiar(fila[6]),
                            'metros_producidos': limpiar(fila[7]),
                            'roturas': limpiar(fila[8]) if len(fila) > 8 else '0',
                            'irmm': limpiar(fila[9]) if len(fila) > 9 else '0',
                            'maquina': maquina_actual or 'GLOBAL',
                        })
        
        # Guardar CSV
        out = DATA_SALIDA / f'produccion_{fecha}.csv'
        cabecera = ['orden', 'id', 'nro', 'inicio', 'maquina', 'hora_inicio', 'turno', 'persona', 'estilo', 'hilo', 'titulo', 'lote', 'nro_madeja', 'metros_a_urdir', 'metros_producidos', 'fecha_fin', 'fecha_fin_hora', 'fecha', 'roturas', 'IRMM']
        with open(out, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(cabecera)
            for r in filas:
                w.writerow([r['orden'], r['id'], r['id'], '', r['maquina'], '', '', r['persona'], r['estilo'], '', r['titulo'], r['lote'], r['nro_madeja'], '', r['metros_producidos'], '', '', fecha, r['roturas'], r['irmm']])
        print(f"  ✅ produccion_{fecha}.csv ({len(filas)} filas)")
    except Exception as e:
        print(f"  ❌ Error procesando {pdf_path.name}: {e}")

def extraer_y_guardar_tiempos(pdf_path, fecha):
    resultados = []
    maquina_actual = None
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text() or ''
                for linea in texto.split('\n'):
                    linea_limpia = linea.strip()
                    maq = detectar_maquina(linea_limpia)
                    if maq: 
                        maquina_actual = maq
                        continue
                    
                    m = re.match(r'^\s*(\d+)\s+(\d+)\s+([A-Za-zÁÉÍÓÚáéíóúñÑüÜ().,\s\-]+?)\s+([\d.,]+)\s+([\d.,]+)\s*$', linea_limpia)
                    if m and maquina_actual:
                        resultados.append({
                            'fecha': fecha, 'maquina': maquina_actual, 'item': m.group(1),
                            'codigo': m.group(2), 'causa': m.group(3).strip(),
                            'hrs': m.group(4).replace(',', '.'), 'porcentaje': m.group(5).replace(',', '.')
                        })
        
        out = DATA_SALIDA / f'tiempos_perdidos_{fecha}.csv'
        with open(out, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['fecha', 'maquina', 'item', 'codigo', 'causa', 'hrs', 'porcentaje'])
            for r in resultados:
                w.writerow([r['fecha'], r['maquina'], r['item'], r['codigo'], r['causa'], r['hrs'], r['porcentaje']])
        print(f"  ✅ tiempos_perdidos_{fecha}.csv ({len(resultados)} filas)")
    except Exception as e:
        print(f"  ❌ Error procesando {pdf_path.name}: {e}")

# ==========================================
# 4. EJECUCIÓN DEL PIPELINE (EL FLUJO AUTOMÁTICO)
# ==========================================
def main():
    print("\n📥 PASO 1: Descargando datos de SISGO...")
    fechas = generar_fechas(FECHA_INICIO, FECHA_FIN)
    
    # 4.1 Descargar CSV crudo (para tu histórico local)
    print("  • Descargando CSV crudo consolidado...")
    todos_datos = []
    for fecha in fechas:
        datos = extraer_urdido_csv(fecha)
        todos_datos.extend(datos)
        time.sleep(0.3)
    
    if todos_datos:
        columnas_csv = ['fecha'] + [col for col in todos_datos[0].keys() if col != 'fecha']
        nombre_csv_crudo = CARPETA_RAW_ACTUAL / f'urdido_{FECHA_INICIO}_{FECHA_FIN}.csv'
        with open(nombre_csv_crudo, 'w', newline='', encoding='utf-8-sig') as archivo:
            writer = csv.DictWriter(archivo, fieldnames=columnas_csv, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(todos_datos)
        print(f"  ✅ CSV crudo guardado en: {nombre_csv_crudo}")

    # 4.2 Descargar PDFs
    print("  • Descargando PDFs...")
    informes = ['produccion', 'tiempos_perdidos', 'inventario']
    for tipo in informes:
        carpeta_pdf = CARPETA_RAW_ACTUAL / f"pdfs_{tipo}"
        carpeta_pdf.mkdir(exist_ok=True)
        for fecha in fechas:
            pdf_data = descargar_pdf(fecha, tipo)
            if pdf_data:
                with open(carpeta_pdf / f'{tipo}_{fecha}.pdf', 'wb') as f:
                    f.write(pdf_data)
            time.sleep(0.3)
    print("  ✅ Descarga de PDFs completada.")

    print("\n⚙️ PASO 2: Convirtiendo PDFs a CSVs finales...")
    # NOTA: Leemos DIRECTAMENTE de la carpeta raw, eliminando el paso intermedio de copiar.
    carpeta_prod = CARPETA_RAW_ACTUAL / "pdfs_produccion"
    for pdf in sorted(carpeta_prod.glob('produccion_*.pdf')):
        fecha = re.search(r'(\d{8})', pdf.name).group(1)
        print(f"  📄 Procesando {pdf.name}...")
        extraer_y_guardar_produccion(pdf, fecha)

    carpeta_tiempos = CARPETA_RAW_ACTUAL / "pdfs_tiempos_perdidos"
    for pdf in sorted(carpeta_tiempos.glob('tiempos_perdidos_*.pdf')):
        fecha = re.search(r'(\d{8})', pdf.name).group(1)
        print(f"  📄 Procesando {pdf.name}...")
        extraer_y_guardar_tiempos(pdf, fecha)

    print("\n" + "="*60)
    print("✨ ¡PROCESO COMPLETADO CON ÉXITO!")
    print(f"📁 Los archivos CSV finales están listos en: {DATA_SALIDA.resolve()}")
    print("👉 Ahora puedes subirlos manualmente a GitHub o hacer lo que necesites.")
    print("="*60)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Proceso interrumpido por el usuario.")
    except Exception as e:
        print(f"\n\n❌ ERROR CRÍTICO: {e}")