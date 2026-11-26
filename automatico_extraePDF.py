import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent
DESTINO = BASE_DIR / "PDFs"
DESTINO.mkdir(exist_ok=True)

contador = 0
for carpeta in BASE_DIR.iterdir():
    if carpeta.is_dir() and carpeta.name != "PDFs":
        for pdf in carpeta.rglob("*.pdf"):
            destino_archivo = DESTINO / pdf.name
            contador_nombre = 1
            while destino_archivo.exists():
                destino_archivo = DESTINO / f"{pdf.stem}_{contador_nombre}{pdf.suffix}"
                contador_nombre += 1
            shutil.copy2(pdf, destino_archivo)
            contador += 1
            print(f"✅ {pdf.name}")

print(f"\n🎉 {contador} PDFs copiados a 'PDFs'.")