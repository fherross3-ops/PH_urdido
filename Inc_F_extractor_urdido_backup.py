#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXTRACTOR URDIDO - CSV + PDFs (3 tipos)
"""

import requests
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup
import csv
from datetime import datetime, timedelta
import time
import os
import re
from dotenv import load_dotenv

# ============================================
# CONFIGURACIÓN
# ============================================
load_dotenv()

USUARIO = os.getenv('USUARIO')
PASSWORD = os.getenv('PASSWORD')

if not USUARIO or not PASSWORD:
    raise ValueError("❌ Faltan credenciales. Revisa tu archivo .env")

FECHA_INICIO = "20261101"
FECHA_FIN = "20261124"
BASE_URL = "http://172.30.1.13/SISGO"
URDIDO_URL = f"{BASE_URL}/produccion/urdido.php"

# ============================================
# CARPETAS DE SALIDA
# ============================================
DATA_RAW = os.path.join('data', 'raw')
os.makedirs(DATA_RAW, exist_ok=True)

CARPETA_BASE = os.path.join(DATA_RAW, f'urdido_completo_{FECHA_INICIO}_{FECHA_FIN}')
os.makedirs(CARPETA_BASE, exist_ok=True)

DEBUG_DIR = os.path.join('debug_html')
os.makedirs(DEBUG_DIR, exist_ok=True)

# ============================================
# AUTENTICACIÓN Y SESIÓN
# ============================================
auth = HTTPBasicAuth(USUARIO, PASSWORD)
session = requests.Session()

print('🚀 EXTRACTOR URDIDO - CSV + PDFs')
print('='*70)
print(f'👤 Usuario: {USUARIO}')
print(f'📅 Rango: {FECHA_INICIO} - {FECHA_FIN}')
print(f'📁 Carpeta: {CARPETA_BASE}/')
print('='*70)

def generar_fechas(inicio, fin):
    inicio_dt = datetime.strptime(inicio, "%Y%m%d")
    fin_dt = datetime.strptime(fin, "%Y%m%d")
    fechas = []
    current = inicio_dt
    while current <= fin_dt:
        fechas.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    return fechas

def extraer_urdido_csv(fecha):
    """Extrae datos de la tabla Urdido para una fecha."""
    url = f"{URDIDO_URL}?fecha={fecha}"
    try:
        response = session.get(url, auth=auth, timeout=30)
        response.encoding = 'windows-1252'
        if response.status_code != 200:
            return []
        
        # Guardar HTML para depuración
        with open(os.path.join(DEBUG_DIR, f'urdido_{fecha}.html'), 'w', encoding='windows-1252') as f:
            f.write(response.text)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buscar la tabla principal (bgcolor #0066CC)
        tabla = soup.find('table', {'bgcolor': '#0066CC'})
        if not tabla:
            print(f"   ⚠️ No se encontró tabla para {fecha}")
            return []
        
        filas = tabla.find_all('tr')
        if len(filas) < 3:
            print(f"   ⚠️ Tabla sin suficientes filas para {fecha}")
            return []
        
        # Encontrar la fila de encabezados (la que contiene '#', 'ID', 'Nº', 'Inicio', etc.)
        header_row = None
        header_index = -1
        for idx, fila in enumerate(filas):
            texto = fila.get_text(strip=True)
            if '#' in texto and 'ID' in texto and 'Nº' in texto:
                header_row = fila
                header_index = idx
                break
        
        if not header_row:
            print(f"   ⚠️ No se encontró fila de encabezados para {fecha}")
            return []
        
        # Extraer nombres de columnas (desde la fila de encabezados)
        header_celdas = header_row.find_all('td')
        columnas = []
        for celda in header_celdas:
            nombre = celda.get_text(strip=True)
            if nombre:
                columnas.append(nombre)
        
        # Procesar filas de datos (después del encabezado)
        datos = []
        for fila in filas[header_index + 1:]:
            celdas = fila.find_all('td')
            if len(celdas) < 10:
                continue
            
            # Verificar si es una fila de datos (primera celda número)
            if not celdas[0].get_text(strip=True).isdigit():
                continue
            
            registro = {'fecha': fecha}
            for i, nombre in enumerate(columnas):
                if i < len(celdas):
                    registro[nombre] = celdas[i].get_text(strip=True)
                else:
                    registro[nombre] = ''
            datos.append(registro)
        
        return datos
    
    except Exception as e:
        print(f"   ❌ Error en {fecha}: {e}")
        return []

def descargar_pdf(fecha, tipo_informe):
    """Descarga un PDF de informe de Urdido."""
    urls = {
        'produccion': f"{BASE_URL}/produccion/urdido_informe_produccion.php?fecha={fecha}",
        'tiempos_perdidos': f"{BASE_URL}/produccion/urdido_informe_tiempos_perdidos.php?fecha={fecha}",
        'inventario': f"{BASE_URL}/produccion/urdido_informe_inventario.php?fecha={fecha}"
    }
    url = urls.get(tipo_informe)
    if not url:
        return None
    try:
        response = session.get(url, auth=auth, timeout=30)
        if response.status_code != 200:
            return None
        if response.content[:10].startswith(b'%PDF'):
            return response.content
        return None
    except:
        return None

# ============================================
# 1. EXTRACCIÓN CSV
# ============================================
print('\n📊 [1/2] Extrayendo datos de Urdido (CSV)...')
print('-'*70)

fechas = generar_fechas(FECHA_INICIO, FECHA_FIN)
total_fechas = len(fechas)
todos_datos = []

for idx, fecha in enumerate(fechas, 1):
    print(f'[{idx}/{total_fechas}] 📍 Procesando {fecha}...', end=' ')
    datos = extraer_urdido_csv(fecha)
    todos_datos.extend(datos)
    print(f'✅ {len(datos)} registros')
    time.sleep(0.5)

if todos_datos:
    # Obtener todas las columnas (excepto 'fecha')
    columnas_csv = ['fecha'] + [col for col in todos_datos[0].keys() if col != 'fecha']
    nombre_csv = os.path.join(CARPETA_BASE, f'urdido_{FECHA_INICIO}_{FECHA_FIN}.csv')
    with open(nombre_csv, 'w', newline='', encoding='utf-8-sig') as archivo:
        writer = csv.DictWriter(archivo, fieldnames=columnas_csv, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(todos_datos)
    print(f'\n✅ CSV guardado: {nombre_csv}')
    print(f'   📊 Total registros: {len(todos_datos)}')
else:
    print('\n⚠️ No se encontraron datos de Urdido')

# ============================================
# 2. DESCARGA DE PDFs
# ============================================
print('\n📄 [2/2] Descargando Informes (PDFs)...')
print('-'*70)

informes = [
    ('produccion', 'Informe Producción'),
    ('tiempos_perdidos', 'Tiempos Perdidos'),
    ('inventario', 'Informe Inventario')
]

for tipo, nombre in informes:
    carpeta_pdf = os.path.join(CARPETA_BASE, f'pdfs_{tipo}')
    os.makedirs(carpeta_pdf, exist_ok=True)
    descargados = 0
    for idx, fecha in enumerate(fechas, 1):
        print(f'   [{idx}/{total_fechas}] {fecha}...', end=' ')
        pdf_data = descargar_pdf(fecha, tipo)
        if pdf_data:
            nombre_pdf = os.path.join(carpeta_pdf, f'{tipo}_{fecha}.pdf')
            with open(nombre_pdf, 'wb') as f:
                f.write(pdf_data)
            descargados += 1
            print(f'✅ PDF ({len(pdf_data)//1024} KB)')
        else:
            print(f'⚠️ Sin datos')
        time.sleep(0.5)
    print(f'   ✅ Total {nombre}: {descargados} PDFs')

# ============================================
# RESUMEN FINAL
# ============================================
print('\n' + '='*70)
print('📊 RESUMEN FINAL - URDIDO')
print('='*70)
print(f'📁 Carpeta principal: {CARPETA_BASE}/')
print()
print(f'📊 Producción:')
print(f'   • CSV: urdido_{FECHA_INICIO}_{FECHA_FIN}.csv')
print(f'   • Registros: {len(todos_datos)}')
print()
print('📄 Informes (PDFs):')
for tipo, nombre in informes:
    carpeta = os.path.join(CARPETA_BASE, f'pdfs_{tipo}')
    if os.path.exists(carpeta):
        count = len([f for f in os.listdir(carpeta) if f.endswith('.pdf')])
        print(f'   • {nombre}: {count} PDFs')
print('='*70)
print('✨ ¡Proceso completado exitosamente!')
print(f'📁 Todos los archivos están en: {CARPETA_BASE}/')
print('='*70)