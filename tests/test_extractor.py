"""Tests básicos del extractor de tablas PP CDMX."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# --------------------------------------------------------------------------- #
# Fixtures                                                                     #
# --------------------------------------------------------------------------- #

MOCK_API_RESPONSE = {
    "columnas": [
        "Colonia o Pueblo Originario", "Proyecto", "Descripción",
        "Avance (%)", "Aprobado $", "Modificado $", "Ejercido $", "Par. %",
    ],
    "filas": [
        ["Tepito", "OBRAS Y SERVICIOS", "Pintura de fachada",
         "100%", "715,861.00", "715,861.00", "715,861.00", "100%"],
        ["Morelos", "OBRAS Y SERVICIOS", "Banqueta segura",
         "100%", "715,861.00", "715,861.00", "715,861.00", "100%"],
    ],
    "alcaldia": "CUAUHTÉMOC",
    "unidad_responsable": "02 CD 06 CUAUHTÉMOC",
    "anio": "2015",
    "pagina": "104",
    "notas": None,
}

SAMPLE_IMAGE_PATH = "images/examples/sample.jpg"


@pytest.fixture
def mock_extractor():
    """TableExtractor con cliente Anthropic simulado."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
        from src.extractor import TableExtractor

        extractor = TableExtractor.__new__(TableExtractor)
        extractor.model = "claude-opus-4-6"

        # Cargar catálogo real de colonias si existe
        colonias_path = Path("data/colonias/colonias_cdmx.csv")
        if colonias_path.exists():
            import pandas as pd
            extractor.colonias_df = pd.read_csv(colonias_path)
        else:
            extractor.colonias_df = None

        # Mock del cliente Anthropic
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"          # Debe ser string literal, no MagicMock
        mock_tool_block.input = MOCK_API_RESPONSE  # Dict directo, igual que tool_block.input real
        mock_message.content = [mock_tool_block]
        mock_client.messages.create.return_value = mock_message
        extractor.client = mock_client

        return extractor


# --------------------------------------------------------------------------- #
# Tests de extracción                                                          #
# --------------------------------------------------------------------------- #

class TestExtraction:
    def test_extract_returns_dataframe(self, mock_extractor, tmp_path):
        """La extracción debe devolver un DataFrame no vacío."""
        # Crear imagen de prueba mínima (1x1 px blanca)
        from PIL import Image
        img = Image.new("RGB", (100, 100), color="white")
        img_path = tmp_path / "test.jpg"
        img.save(img_path)

        df = mock_extractor.extract(str(img_path))

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == MOCK_API_RESPONSE["columnas"]

    def test_extract_metadata_attached(self, mock_extractor, tmp_path):
        """Los metadatos deben quedar en df.attrs."""
        from PIL import Image
        img = Image.new("RGB", (100, 100), color="white")
        img_path = tmp_path / "test.jpg"
        img.save(img_path)

        df = mock_extractor.extract(str(img_path))

        assert df.attrs["alcaldia"] == "CUAUHTÉMOC"
        assert df.attrs["unidad_responsable"] == "02 CD 06 CUAUHTÉMOC"
        assert df.attrs["anio"] == "2015"
        assert df.attrs["pagina"] == "104"

    def test_extract_data_values(self, mock_extractor, tmp_path):
        """Los datos extraídos deben coincidir con la respuesta simulada."""
        from PIL import Image
        img = Image.new("RGB", (100, 100), color="white")
        img_path = tmp_path / "test.jpg"
        img.save(img_path)

        df = mock_extractor.extract(str(img_path))

        assert df.iloc[0]["Colonia o Pueblo Originario"] == "Tepito"
        assert df.iloc[0]["Aprobado $"] == "715,861.00"


# --------------------------------------------------------------------------- #
# Tests de validación de colonias                                              #
# --------------------------------------------------------------------------- #

class TestValidateColonia:
    def test_colonia_existente(self, mock_extractor):
        """Tepito debe existir en el catálogo bajo Cuauhtémoc."""
        if mock_extractor.colonias_df is None:
            pytest.skip("Catálogo de colonias no disponible")

        result = mock_extractor.validate_colonia("Tepito", "Cuauhtémoc")
        assert result["encontrado"] is True

    def test_colonia_inexistente(self, mock_extractor):
        """Una colonia inventada no debe aparecer en el catálogo."""
        if mock_extractor.colonias_df is None:
            pytest.skip("Catálogo de colonias no disponible")

        result = mock_extractor.validate_colonia("ColoniaQueNoExiste12345")
        assert result["encontrado"] is False

    def test_colonia_sin_alcaldia(self, mock_extractor):
        """La búsqueda sin alcaldía debe devolver todas las coincidencias."""
        if mock_extractor.colonias_df is None:
            pytest.skip("Catálogo de colonias no disponible")

        result = mock_extractor.validate_colonia("Centro")
        # "Centro" puede aparecer en varias alcaldías
        assert isinstance(result["coincidencias"], list)


# --------------------------------------------------------------------------- #
# Tests de guardado                                                            #
# --------------------------------------------------------------------------- #

class TestSaveCSV:
    def test_save_csv_creates_file(self, mock_extractor, tmp_path):
        """save_csv debe crear el archivo en el path indicado."""
        df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        output = tmp_path / "output.csv"

        mock_extractor.save_csv(df, str(output))

        assert output.exists()
        loaded = pd.read_csv(output)
        assert len(loaded) == 2

    def test_save_csv_creates_parent_dirs(self, mock_extractor, tmp_path):
        """save_csv debe crear directorios padres si no existen."""
        df = pd.DataFrame({"x": [1]})
        output = tmp_path / "a" / "b" / "c.csv"

        mock_extractor.save_csv(df, str(output))

        assert output.exists()
