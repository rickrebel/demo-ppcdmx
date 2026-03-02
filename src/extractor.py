"""
Extractor de tablas del Presupuesto Participativo CDMX.

Usa Claude (Anthropic Vision API) para extraer datos estructurados
de fotografías de tablas.
"""

import base64
import csv
import io
import os
import sys
from pathlib import Path

import anthropic
import pandas as pd
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# Prompt base para la extracción
EXTRACTION_PROMPT = """Analiza la imagen de esta página del reporte oficial
"PPD Presupuesto Participativo para las Delegaciones" de la Ciudad de México
(Cuenta Pública CDMX).

El documento tiene:
- Encabezado: logo CDMX + "CUENTA PÚBLICA DE LA CIUDAD DE MÉXICO" + año (si visible)
- Título: "PPD PRESUPUESTO PARTICIPATIVO PARA LAS DELEGACIONES"
- Línea: "Unidad Responsable del Gasto: [código] [nombre delegación/alcaldía]"
- Tabla con columnas: COLONIA O PUEBLO ORIGINARIO, PROYECTO, DESCRIPCIÓN,
  AVANCE DEL PROYECTO (%), y columnas de presupuesto (APROBADO, MODIFICADO,
  EJERCIDO, PAR. %)
- Número de página en la esquina inferior derecha

Extrae todos los datos usando la herramienta extract_table.

Reglas:
- Celdas vacías → null. Valores numéricos cero → "0" o "0.00".
- Preserva números con su formato original (no conviertas ni redondees montos).
- Celdas combinadas: repite el valor en cada fila correspondiente.
- El año aparece en el encabezado junto al logo (ej. "2015").
- El número de página está en la esquina inferior derecha.
"""

# Schema de la herramienta para extracción estructurada (tool_use)
EXTRACT_TOOL = {
    "name": "extract_table",
    "description": (
        "Extrae una página del reporte PPD Presupuesto Participativo CDMX. "
        "Captura la tabla completa y los metadatos del encabezado del documento."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "columnas": {
                "type": "array",
                "description": "Nombres de columnas tal como aparecen en el encabezado de la tabla.",
                "items": {"type": "string"},
            },
            "filas": {
                "type": "array",
                "description": (
                    "Filas de datos. Cada fila es un array en el mismo orden que 'columnas'. "
                    "Usa null para celdas vacías. Repite valores de celdas combinadas."
                ),
                "items": {
                    "type": "array",
                    "items": {"type": ["string", "null"]},
                },
            },
            "alcaldia": {
                "type": ["string", "null"],
                "description": (
                    "Nombre de la delegación/alcaldía extraído de la línea "
                    "'Unidad Responsable del Gasto'. Ej: 'IZTAPALAPA', 'TLÁHUAC'."
                ),
            },
            "unidad_responsable": {
                "type": ["string", "null"],
                "description": (
                    "Texto completo de 'Unidad Responsable del Gasto: …', "
                    "incluyendo el código. Ej: '02 CD 24 IZTAPALAPA'."
                ),
            },
            "anio": {
                "type": ["string", "null"],
                "description": "Año visible en el encabezado del documento. Ej: '2015', '2018'.",
            },
            "pagina": {
                "type": ["string", "null"],
                "description": "Número de página en la esquina inferior derecha. Ej: '104', '059'.",
            },
            "notas": {
                "type": ["string", "null"],
                "description": "Texto relevante del documento fuera de la tabla y los campos anteriores.",
            },
        },
        "required": ["columnas", "filas", "alcaldia", "unidad_responsable", "anio", "pagina", "notas"],
    },
}


def _image_to_base64(image_path: str) -> tuple[str, str]:
    """Convierte una imagen a base64 y detecta su media type."""
    path = Path(image_path)
    suffix = path.suffix.lower()

    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }

    media_type = media_types.get(suffix, "image/jpeg")

    with open(image_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")

    return data, media_type


def _preprocess_image(image_path: str, max_size: int = 1568) -> str:
    """
    Redimensiona la imagen si es muy grande para reducir tokens.
    Devuelve la ruta de la imagen (original o temporal).
    """
    img = Image.open(image_path)
    w, h = img.size

    if max(w, h) <= max_size:
        return image_path

    # Redimensionar manteniendo proporción
    scale = max_size / max(w, h)
    new_w, new_h = int(w * scale), int(h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    tmp_path = Path(image_path).with_suffix(".tmp.jpg")
    img.save(tmp_path, "JPEG", quality=90)
    return str(tmp_path)


class TableExtractor:
    """Extrae tablas del Presupuesto Participativo CDMX de imágenes."""

    def __init__(self, model: str = "claude-opus-4-6"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "No se encontró ANTHROPIC_API_KEY. "
                "Configúrala en el entorno o en un archivo .env"
            )
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Cargar catálogo de colonias para validación
        colonias_path = Path(__file__).parent.parent / "data" / "colonias" / "colonias_cdmx.csv"
        if colonias_path.exists():
            self.colonias_df = pd.read_csv(colonias_path)
        else:
            self.colonias_df = None

    def extract(self, image_path: str) -> pd.DataFrame:
        """
        Extrae los datos de una imagen de tabla y los devuelve como DataFrame.

        Args:
            image_path: Ruta a la imagen (.jpg, .png, .webp)

        Returns:
            DataFrame con los datos extraídos.
            El DataFrame tiene atributos adicionales: .metadata con alcaldia, colonia, anio, notas.
        """
        processed_path = _preprocess_image(image_path)
        img_b64, media_type = _image_to_base64(processed_path)

        # Limpiar archivo temporal si se creó
        if processed_path != image_path:
            Path(processed_path).unlink(missing_ok=True)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            tools=[EXTRACT_TOOL],
            tool_choice={"type": "tool", "name": "extract_table"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": img_b64,
                            },
                        },
                        {"type": "text", "text": EXTRACTION_PROMPT},
                    ],
                }
            ],
        )

        tool_block = next((b for b in response.content if b.type == "tool_use"), None)
        if tool_block is None:
            raise ValueError(
                f"La API no devolvió un bloque tool_use. "
                f"stop_reason={response.stop_reason!r}, content={response.content!r}"
            )
        parsed = tool_block.input  # Ya es un dict; no requiere json.loads()

        columnas = parsed.get("columnas", [])
        filas = parsed.get("filas", [])

        df = pd.DataFrame(filas, columns=columnas if columnas else None)

        # Adjuntar metadatos como atributos del DataFrame
        df.attrs["alcaldia"]            = parsed.get("alcaldia")
        df.attrs["unidad_responsable"]  = parsed.get("unidad_responsable")
        df.attrs["anio"]                = parsed.get("anio")
        df.attrs["pagina"]              = parsed.get("pagina")
        df.attrs["notas"]               = parsed.get("notas")
        df.attrs["imagen_origen"]       = str(Path(image_path).name)

        return df

    def save_csv(self, df: pd.DataFrame, output_path: str) -> None:
        """Guarda el DataFrame extraído como CSV."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"Guardado: {out}")

    def validate_colonia(self, colonia: str, alcaldia: str = None) -> dict:
        """
        Valida si una colonia existe en el catálogo de la CDMX.

        Returns:
            dict con 'encontrado' (bool) y 'coincidencias' (list).
        """
        if self.colonias_df is None:
            return {"encontrado": False, "coincidencias": [], "error": "Catálogo no disponible"}

        mask = self.colonias_df["colonia"].str.lower() == colonia.lower()
        if alcaldia:
            mask &= self.colonias_df["alcaldia"].str.lower() == alcaldia.lower()

        coincidencias = self.colonias_df[mask].to_dict("records")
        return {"encontrado": bool(coincidencias), "coincidencias": coincidencias}

    def process_directory(self, images_dir: str, output_dir: str) -> pd.DataFrame:
        """
        Procesa todas las imágenes en un directorio y consolida los resultados.

        Args:
            images_dir: Directorio con imágenes.
            output_dir: Directorio donde guardar CSVs individuales.

        Returns:
            DataFrame consolidado con todos los datos extraídos.
        """
        images_dir = Path(images_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        extensions = {".jpg", ".jpeg", ".png", ".webp"}
        images = [p for p in images_dir.iterdir() if p.suffix.lower() in extensions]

        if not images:
            print(f"No se encontraron imágenes en {images_dir}")
            return pd.DataFrame()

        all_dfs = []
        for img_path in sorted(images):
            print(f"Procesando: {img_path.name}")
            try:
                df = self.extract(str(img_path))
                df["_imagen"] = img_path.name
                df["_alcaldia"] = df.attrs.get("alcaldia")
                df["_anio"] = df.attrs.get("anio")
                df["_pagina"] = df.attrs.get("pagina")

                csv_out = output_dir / img_path.with_suffix(".csv").name
                self.save_csv(df, str(csv_out))
                all_dfs.append(df)
            except Exception as e:
                print(f"  Error en {img_path.name}: {e}")

        if all_dfs:
            consolidated = pd.concat(all_dfs, ignore_index=True)
            self.save_csv(consolidated, str(output_dir / "consolidado.csv"))
            return consolidated

        return pd.DataFrame()


def main():
    """Punto de entrada CLI: python -m src.extractor <imagen>"""
    if len(sys.argv) < 2:
        print("Uso: python -m src.extractor <ruta_imagen>")
        print("     python -m src.extractor <directorio_imagenes>")
        sys.exit(1)

    target = Path(sys.argv[1])
    extractor = TableExtractor()

    if target.is_dir():
        df = extractor.process_directory(str(target), "data/processed")
        print(f"\nTotal de filas extraídas: {len(df)}")
    else:
        df = extractor.extract(str(target))
        print("\n--- Datos extraídos ---")
        print(df.to_string())
        print("\n--- Metadatos ---")
        for key in ("alcaldia", "unidad_responsable", "anio", "pagina", "notas"):
            print(f"  {key}: {df.attrs.get(key)}")

        output = Path("data/processed") / target.with_suffix(".csv").name
        extractor.save_csv(df, str(output))


if __name__ == "__main__":
    main()
