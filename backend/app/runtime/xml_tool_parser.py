"""XML-based tool argument parser.

This module provides functionality for parsing tool arguments from XML-like
input, with support for validation and error handling.
"""

try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 compatibility

from loguru import logger
from pydantic import BaseModel, Field

from app.runtime.tools.tool import Tool
from app.runtime.xml_parser import ToleranceXMLParser


class ToolArguments(BaseModel):
    """Model for storing and validating tool arguments."""

    arguments: dict[str, str] = Field(
        default_factory=dict, description="Dictionary mapping argument names to their values"
    )


class ToolParser:
    """Parser for extracting and validating tool arguments from XML input."""

    ARGUMENT_ALIASES: dict[str, tuple[str, ...]] = {
        "path": ("file_path", "filepath"),
        "file_path": ("path", "filepath"),
        "directory_path": ("path", "dir_path", "directory"),
    }

    def __init__(self: Self, tool: Tool) -> None:
        """Initialize the parser with a tool instance."""
        self.tool = tool
        self.xml_parser = ToleranceXMLParser()

    def parse(self: Self, xml_string: str) -> dict[str, str]:
        """Parse XML string and return validated tool arguments."""
        try:
            if not xml_string:
                error_msg = "Input text must be a non-empty string"
                logger.error(f"Error extracting XML elements: {error_msg}")
                raise ValueError(f"Error extracting XML elements: {error_msg}")

            if not xml_string.strip().startswith("<"):
                error_msg = "Failed to parse XML"
                logger.error(f"Error extracting XML elements: {error_msg}")
                raise ValueError(f"Error extracting XML elements: {error_msg}")

            elements = self.xml_parser.extract_elements(xml_string, preserve_cdata=True)
            logger.debug(f"Extracted elements from XML: {elements}")

            arguments = self.tool.get_non_injectable_arguments()
            normalized_elements = self._normalize_argument_aliases(elements, arguments)

            for arg in arguments:
                if arg.required and arg.name not in normalized_elements:
                    error_msg = f"argument {arg.name} not found"
                    logger.error(f"Error extracting XML elements: {error_msg}")
                    raise ValueError(f"Error extracting XML elements: {error_msg}")

            argument_dict = {arg.name: normalized_elements.get(arg.name, "") for arg in arguments}
            validated_args = ToolArguments(arguments=argument_dict)
            logger.debug(f"Successfully parsed arguments: {validated_args.arguments}")
            return validated_args.arguments

        except ValueError as e:
            if not str(e).startswith("Error extracting XML elements:"):
                error_msg = f"Error extracting XML elements: {str(e)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            raise

    def _normalize_argument_aliases(self, elements: dict[str, str], arguments: list) -> dict[str, str]:
        """Map common alias argument names to the tool's canonical schema."""
        normalized = dict(elements)
        for arg in arguments:
            if arg.name in normalized:
                continue
            for alias in self.ARGUMENT_ALIASES.get(arg.name, ()):
                if alias in elements:
                    normalized[arg.name] = elements[alias]
                    break
        return normalized
