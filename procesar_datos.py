name: 📊 Actualizar Dashboard

# Se ejecuta automáticamente cuando subes el Excel
on:
  push:
    paths:
      - 'data/**.xlsx'
      - 'data/**.xls'
  workflow_dispatch:   # también permite ejecutarlo manualmente desde GitHub

jobs:
  procesar:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: 📥 Descargar repositorio
        uses: actions/checkout@v4

      - name: 🐍 Configurar Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: 📦 Instalar dependencias
        run: pip install pandas openpyxl

      - name: ⚙️ Procesar Excel → data.json
        run: python scripts/procesar_datos.py

      - name: 📤 Subir data.json al repositorio
        run: |
          git config user.name  "GitHub Actions"
          git config user.email "actions@github.com"
          git add data.json
          git diff --staged --quiet || git commit -m "📊 Datos actualizados $(date +'%d/%m/%Y %H:%M')"
          git push
