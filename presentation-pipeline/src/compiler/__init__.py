"""Compiler infrastructure — normalizer, compiler bridge, repair guidance."""

from src.compiler.normalizer import normalize_xml
from src.compiler.compiler_client import compile_xml, validate_xml, CompilerError
from src.compiler.repair_guidance import build_error_guidance, error_signatures, is_stalled

__all__ = [
    "normalize_xml",
    "compile_xml",
    "validate_xml",
    "CompilerError",
    "build_error_guidance",
    "error_signatures",
    "is_stalled",
]
