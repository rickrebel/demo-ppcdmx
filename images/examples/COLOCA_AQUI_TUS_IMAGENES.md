# Imágenes de ejemplo

Coloca aquí las fotografías de las tablas del Presupuesto Participativo CDMX.

## Convención de nombres sugerida

```
{alcaldia}_{colonia}_{anio}.jpg
```

Ejemplos:
- `iztapalapa_cabeza_de_juarez_2024.jpg`
- `coyoacan_del_carmen_2023.png`
- `cuauhtemoc_tepito_2024.jpg`

## Requisitos de las imágenes

- La tabla debe ser legible (no borrosa ni muy oscura)
- Preferiblemente encuadrada de frente
- Formatos aceptados: `.jpg`, `.jpeg`, `.png`, `.webp`
- Resolución mínima recomendada: 800 × 600 px

## Cómo probar

Una vez que tengas imágenes aquí, ejecuta en el notebook:

```python
from src.extractor import TableExtractor

extractor = TableExtractor()
resultado = extractor.extract("images/examples/tu_imagen.jpg")
print(resultado.to_string())
```

O desde la terminal:

```bash
python -m src.extractor images/examples/tu_imagen.jpg
```
