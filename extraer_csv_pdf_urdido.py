"""
extraer_csv_pdf.py
Extrae los CSVs del dashboard de Urdido desde los PDFs generados por SISGO.

Uso:
    python extraer_csv_pdf.py
"""

import pdfplumber
import re
import csv
import sys
from pathlib import Path

# ══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════
PDFS_DIR   = Path("./pdfs")
SALIDA_DIR = Path("./data")
SALIDA_DIR.mkdir(exist_ok=True)

MAQUINAS = ['URDIDORA # 01', 'URDIDORA # 02', 'URDIDORA # 03', 'URDIDORA # 04']

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════
def fecha_del_nombre(nombre):
    """Extrae la fecha YYYYMMDD de 'produccion_20260921.pdf'."""
    m = re.search(r'(\d{8})', nombre)
    return m.group(1) if m else None


def limpiar(valor):
    """Normaliza celdas: quita saltos de línea, espacios extra."""
    if valor is None:
        return ''
    return str(valor).replace('\n', ' ').strip()


def detectar_maquina(texto):
    """Si el texto contiene 'URDIDORA # XX', devuelve la máquina."""
    m = re.search(r'URDIDORA\s*#\s*(\d+)', texto)
    if m:
        return f'URDIDORA # {int(m.group(1)):02d}'
    return None


def parsear_numero(s):
    """Convierte string tipo '18.000,00' o '3000.0' a float."""
    s = limpiar(s)
    if not s:
        return 0.0
    # Formato europeo: 18.000,00 → 18000.00
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return 0.0


# ══════════════════════════════════════════════════════════════
# EXTRACCIÓN DE PRODUCCIÓN
# ══════════════════════════════════════════════════════════════
def parsear_fila_produccion(fila, maquina_actual):
    """Convierte una fila de tabla a dict, o None si no aplica."""
    if not fila or len(fila) < 8:
        return None
    celda0 = limpiar(fila[0])
    # La primera celda debe ser un número (item)
    if not celda0.isdigit():
        return None
    return {
        'orden': int(celda0),
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
    }


def extraer_produccion(pdf_path):
    """Extrae todas las filas de producción del PDF."""
    filas = []
    maquina_actual = None

    with pdfplumber.open(pdf_path) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text() or ''
            maq_en_pagina = detectar_maquina(texto)
            if maq_en_pagina:
                maquina_actual = maq_en_pagina

            # Iterar todas las tablas de la página
            for tabla in (pagina.extract_tables() or []):
                if not tabla or len(tabla) < 2:
                    continue
                # ¿Es tabla de producción? Su cabecera debe contener 'Codigo'
                cabecera = ' '.join(limpiar(c).lower() for c in (tabla[0] or []))
                if 'codigo' not in cabecera:
                    continue

                for fila in tabla[1:]:
                    parsed = parsear_fila_produccion(fila, maquina_actual)
                    if parsed:
                        filas.append(parsed)

    return filas


# ══════════════════════════════════════════════════════════════
# EXTRACCIÓN DE ROTURAS (desde el PDF de producción)
# ══════════════════════════════════════════════════════════════
def extraer_roturas(pdf_path):
    """
    Extrae las roturas por máquina del PDF de producción.
    Busca la sección 'Roturas por Maquinas' y parsea cada bloque.
    Devuelve lista de dicts {maquina, tipo_rotura, cantidad}.
    """
    roturas = []
    maquina_actual = None

    with pdfplumber.open(pdf_path) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text() or ''
            lineas = texto.split('\n')

            modo_roturas = False
            for linea in lineas:
                linea_limpia = linea.strip()

                # Detectar inicio de la sección
                if 'Roturas por Maquinas' in linea_limpia:
                    modo_roturas = True
                    continue

                if not modo_roturas:
                    continue

                # Detectar cambio de máquina
                maq = detectar_maquina(linea_limpia)
                if maq:
                    maquina_actual = maq
                    continue

                # Ignorar cabeceras y filas vacías
                if not linea_limpia or 'Item' in linea_limpia or 'Codigo' in linea_limpia:
                    continue
                if 'Paro sin Roturas' in linea_limpia:
                    continue

                # Intentar parsear línea tipo: "1   27   Interferencia entre hilos   9"
                # o "1   1 Moña   8"
                m = re.match(
                    r'^\s*(\d+)\s+(\d+)?\s*([A-Za-zÁÉÍÓÚáéíóúñÑüÜ()\s]+?)\s+(\d+)\s*$',
                    linea_limpia
                )
                if m and maquina_actual:
                    tipo = m.group(3).strip()
                    cant = int(m.group(4))
                    # Filtrar "Hilos sueltos" si quieres (el dashboard ya lo hace)
                    roturas.append({
                        'maquina': maquina_actual,
                        'tipo_rotura': tipo,
                        'cantidad': cant,
                    })

    return roturas


# ══════════════════════════════════════════════════════════════
# EXTRACCIÓN DE TIEMPOS PERDIDOS
# ══════════════════════════════════════════════════════════════
def extraer_tiempos(pdf_path):
    """
    Extrae los tiempos perdidos del PDF.
    Formato de salida: {fecha, maquina, item, codigo, causa, hrs, porcentaje}.
    """
    resultados = []
    maquina_actual = None
    fecha = fecha_del_nombre(pdf_path.name)

    with pdfplumber.open(pdf_path) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text() or ''
            for linea in texto.split('\n'):
                linea_limpia = linea.strip()

                maq = detectar_maquina(linea_limpia)
                if maq:
                    maquina_actual = maq
                    continue

                # Intentar parsear línea de causa con horas
                # Ejemplo: "1  43  FALTA DE MATERIAL (HILO PARA URDIR)   1.83  22.88"
                m = re.match(
                    r'^\s*(\d+)\s+(\d+)\s+([A-Za-zÁÉÍÓÚáéíóúñÑüÜ().,\s\-]+?)\s+([\d.,]+)\s+([\d.,]+)\s*$',
                    linea_limpia
                )
                if m and maquina_actual:
                    resultados.append({
                        'fecha': fecha,
                        'maquina': maquina_actual,
                        'item': m.group(1),
                        'codigo': m.group(2),
                        'causa': m.group(3).strip(),
                        'hrs': m.group(4).replace(',', '.'),
                        'porcentaje': m.group(5).replace(',', '.'),
                    })

    return resultados


# ══════════════════════════════════════════════════════════════
# ESCRITURA DE CSVs
# ══════════════════════════════════════════════════════════════
def escribir_produccion(filas, fecha):
    out = SALIDA_DIR / f'produccion_{fecha}.csv'
    cabecera = [
        'orden', 'id', 'nro', 'inicio', 'maquina', 'hora_inicio', 'turno',
        'persona', 'estilo', 'hilo', 'titulo', 'lote', 'nro_madeja',
        'metros_a_urdir', 'metros_producidos', 'fecha_fin', 'fecha_fin_hora',
        'fecha', 'roturas', 'IRMM'
    ]
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(cabecera)
        for r in filas:
            w.writerow([
                r['orden'], r['id'], r['id'],       # nro = id
                '', r['maquina'], '', '',           # inicio, hora_inicio, turno vacíos
                r['persona'], r['estilo'], '',
                r['titulo'], r['lote'], r['nro_madeja'],
                '', r['metros_producidos'], '', '',
                fecha, r['roturas'], r['irmm'],
            ])
    print(f'  ✅ {out.name}: {len(filas)} filas')


def escribir_roturas(filas, fecha):
    out = SALIDA_DIR / f'roturas_{fecha}.csv'
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['maquina', 'tipo_rotura', 'cantidad', 'fecha'])
        for r in filas:
            w.writerow([r['maquina'], r['tipo_rotura'], r['cantidad'], fecha])
    print(f'  ✅ {out.name}: {len(filas)} filas')


def escribir_tiempos(filas, fecha):
    out = SALIDA_DIR / f'tiempos_perdidos_{fecha}.csv'
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['fecha', 'maquina', 'item', 'codigo', 'causa', 'hrs', 'porcentaje'])
        for r in filas:
            w.writerow([
                r['fecha'], r['maquina'], r['item'], r['codigo'],
                r['causa'], r['hrs'], r['porcentaje'],
            ])
    print(f'  ✅ {out.name}: {len(filas)} filas')


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def procesar_produccion():
    print('\n📦 PRODUCCIÓN')
    for pdf in sorted(PDFS_DIR.glob('produccion_*.pdf')):
        fecha = fecha_del_nombre(pdf.name)
        if not fecha:
            print(f'  ⚠️ {pdf.name}: sin fecha en el nombre')
            continue
        print(f'  📄 {pdf.name}')
        try:
            prod = extraer_produccion(pdf)
            escribir_produccion(prod, fecha)
            rot = extraer_roturas(pdf)
            escribir_roturas(rot, fecha)
        except Exception as e:
            print(f'  ❌ Error: {e}')


def procesar_tiempos():
    print('\n⏱️  TIEMPOS PERDIDOS')
    for pdf in sorted(PDFS_DIR.glob('tiempos_perdidos_*.pdf')):
        fecha = fecha_del_nombre(pdf.name)
        if not fecha:
            continue
        print(f'  📄 {pdf.name}')
        try:
            tp = extraer_tiempos(pdf)
            escribir_tiempos(tp, fecha)
        except Exception as e:
            print(f'  ❌ Error: {e}')


if __name__ == '__main__':
    print('🚀 Extractor de CSVs desde PDFs SISGO')
    print(f'   PDFs en: {PDFS_DIR.resolve()}')
    print(f'   CSVs en: {SALIDA_DIR.resolve()}')
    procesar_produccion()
    procesar_tiempos()
    print('\n✨ Listo.')