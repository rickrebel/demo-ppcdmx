# Extractor de Tablas PP CDMX

Extrae datos estructurados de fotografías de páginas del **Presupuesto Participativo
para las Delegaciones** (Cuenta Pública CDMX). Usa Anthropic Claude con `tool_use`
para garantizar salida JSON estructurada sin parsing frágil.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # añade tu ANTHROPIC_API_KEY
```

## Comandos

```bash
# Una imagen
python -m src.extractor "images/examples/iztapalapa 2015.png"

# Directorio completo → genera data/processed/consolidado.csv
python -m src.extractor images/examples/

# Tests (no requieren API key)
pytest tests/ -v

# Notebook interactivo
jupyter notebook notebooks/01_exploracion.ipynb
```

## Arquitectura

```
src/extractor.py       → TableExtractor: preproceso → base64 → tool_use → DataFrame
EXTRACT_TOOL           → schema JSON de los campos esperados
data/colonias/         → catálogo 726 colonias CDMX para validate_colonia()
data/processed/        → CSVs de salida
```

## Formato de documentos soportado

Páginas del reporte oficial **"PPD Presupuesto Participativo para las Delegaciones"**
(Cuenta Pública CDMX). Estructura consistente en todos los documentos:

| Columna en la tabla | Descripción |
|---------------------|-------------|
| COLONIA O PUEBLO ORIGINARIO | Nombre de la colonia o pueblo |
| PROYECTO | Nombre o código del proyecto |
| DESCRIPCIÓN | Descripción del proyecto |
| AVANCE DEL PROYECTO (%) | Porcentaje de avance |
| APROBADO $ | Presupuesto aprobado |
| MODIFICADO $ | Presupuesto modificado |
| EJERCIDO $ | Presupuesto ejercido |
| PAR. % | Porcentaje de ejecución |

## Schema de salida (`df.attrs`)

```python
df.attrs["alcaldia"]            # "IZTAPALAPA"
df.attrs["unidad_responsable"]  # "02 CD 24 IZTAPALAPA"
df.attrs["anio"]                # "2015"
df.attrs["pagina"]              # "104"
df.attrs["notas"]               # None o texto adicional
df.attrs["imagen_origen"]       # nombre del archivo
```
