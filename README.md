# Extractor de Tablas — Presupuesto Participativo CDMX

Herramienta para extraer datos de **imágenes de tablas** del Presupuesto Participativo (PP) de la Ciudad de México. Las tablas contienen información de proyectos por colonia y alcaldía.

## Estructura del proyecto

```
demo-ppcdmx/
├── data/
│   ├── colonias/
│   │   └── colonias_cdmx.csv        # Catálogo de colonias por alcaldía
│   └── processed/                   # Datos extraídos (salida)
├── images/
│   └── examples/                    # Imágenes de ejemplo para pruebas
│       └── COLOCA_AQUI_TUS_IMAGENES.md
├── src/
│   ├── __init__.py
│   └── extractor.py                 # Lógica de extracción de tablas
├── notebooks/
│   └── 01_exploracion.ipynb         # Notebook de exploración y pruebas
├── tests/
│   └── test_extractor.py
├── requirements.txt
└── README.md
```

## Configuración

### 1. Crear entorno virtual e instalar dependencias

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

### 2. Configurar API key de Anthropic (para extracción con visión)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

O crear un archivo `.env` en la raíz:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Uso básico

```python
from src.extractor import TableExtractor

extractor = TableExtractor()

# Extraer datos de una imagen
resultado = extractor.extract("images/examples/mi_tabla.jpg")
print(resultado)

# Guardar resultado como CSV
extractor.save_csv(resultado, "data/processed/mi_tabla.csv")
```

### Ejecutar desde línea de comandos

```bash
python -m src.extractor images/examples/mi_tabla.jpg
```

## Imágenes de ejemplo

Coloca las imágenes de tablas del Presupuesto Participativo en:

```
images/examples/
```

Formatos soportados: `.jpg`, `.jpeg`, `.png`, `.webp`

Ver instrucciones detalladas en [`images/examples/COLOCA_AQUI_TUS_IMAGENES.md`](images/examples/COLOCA_AQUI_TUS_IMAGENES.md).

## Datos de colonias

El archivo [`data/colonias/colonias_cdmx.csv`](data/colonias/colonias_cdmx.csv) contiene el catálogo de colonias y alcaldías de la CDMX compilado a partir del [Portal de Datos Abiertos de la CDMX](https://datos.cdmx.gob.mx/dataset/catalogo-de-colonias-datos-abiertos).

Para actualizar con el dataset oficial más reciente:

```bash
python scripts/descargar_colonias.py
```

## Contexto: Presupuesto Participativo CDMX

El Presupuesto Participativo (PP) es un mecanismo de democracia directa que permite a los habitantes de la CDMX decidir en qué se invierten recursos públicos a nivel de colonia. Las tablas fotografiadas contienen:

- Nombre del proyecto
- Colonia y alcaldía
- Monto asignado
- Categoría del proyecto
- Año del ejercicio
- Votos obtenidos (en su caso)

## Flujo de trabajo

```
Fotografía de tabla PP
        ↓
  Preprocesamiento
  (ajuste de imagen)
        ↓
  Claude Vision API
  (extracción de datos)
        ↓
  Validación con
  catálogo de colonias
        ↓
  CSV procesado
  en data/processed/
```
