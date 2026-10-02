"""
Folder path validation and conversion utilities for CheckMK handlers
"""

import re
from typing import Any, Dict, List, Tuple


class FolderValidator:
    """Validates and converts folder paths between different formats"""

    # Valid folder name pattern (alphanumeric, underscore, hyphen)
    FOLDER_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

    # Path separator conversions
    SEPARATORS = {"unix": "/", "checkmk": "~"}  # Unix-style paths: /server/test  # CheckMK API format: ~server~test

    @classmethod
    def validate_and_convert_path(
        cls, folder_path: str, operation: str = "general"
    ) -> Tuple[bool, str, List[str], str]:
        """
        Validate folder path and convert to CheckMK API format

        Args:
            folder_path: Input folder path (can be "/server/test", "server/test", "~server~test")
            operation: Type of operation (create, delete, update, move, list)

        Returns:
            Tuple of (is_valid, converted_path, validation_errors, normalized_display_path)
        """
        validation_errors = []

        if not folder_path or not isinstance(folder_path, str):
            validation_errors.append("Folder path cannot be empty")
            return False, "", validation_errors, ""

        # Clean the input path and convert to lowercase for consistency
        folder_path = folder_path.strip().lower()

        # Handle root folder special case
        if folder_path in ["/", "~", ""]:
            return True, "~", [], "/"

        # Normalize the path format first
        normalized_path = cls._normalize_path_format(folder_path)
        display_path = cls._to_display_format(normalized_path)

        # Validate individual folder names
        folder_names = cls._extract_folder_names(normalized_path)

        for folder_name in folder_names:
            if not folder_name:  # Empty folder name
                validation_errors.append("Empty folder names are not allowed")
                continue

            if len(folder_name) > 50:  # CheckMK limitation
                validation_errors.append(f"Folder name '{folder_name}' exceeds 50 characters")

            if not cls.FOLDER_NAME_PATTERN.match(folder_name):
                validation_errors.append(
                    f"Invalid folder name '{folder_name}'. Use only letters, numbers, underscore, and hyphen."
                )

            # CheckMK reserved names
            if folder_name.lower() in ["main", "root", "system", "tmp", "temp"]:
                validation_errors.append(f"'{folder_name}' is a reserved folder name")

        # Convert to CheckMK API format
        checkmk_path = cls._to_checkmk_format(normalized_path)

        # Operation-specific validation
        operation_errors = cls._validate_operation_specific(folder_path, operation, folder_names)
        validation_errors.extend(operation_errors)

        is_valid = len(validation_errors) == 0
        return is_valid, checkmk_path, validation_errors, display_path

    @classmethod
    def _normalize_path_format(cls, path: str) -> str:
        """Convert any input format to a consistent internal format"""
        if not path or path in ["/", "~"]:
            return "/"

        # Remove leading/trailing separators and normalize
        path = path.strip("/~")

        # Convert CheckMK format to Unix format for internal processing
        if "~" in path:
            path = path.replace("~", "/")

        # Ensure single leading slash
        return "/" + path if path else "/"

    @classmethod
    def _to_checkmk_format(cls, normalized_path: str) -> str:
        """Convert normalized path to CheckMK API format"""
        if normalized_path == "/":
            return "~"

        # Remove leading slash and convert / to ~
        path = normalized_path.lstrip("/")
        return "~" + path.replace("/", "~") if path else "~"

    @classmethod
    def _to_display_format(cls, normalized_path: str) -> str:
        """Convert normalized path to user-friendly display format"""
        return normalized_path if normalized_path != "/" else "/ (root)"

    @classmethod
    def _extract_folder_names(cls, normalized_path: str) -> List[str]:
        """Extract individual folder names from normalized path"""
        if normalized_path == "/":
            return []
        return [name for name in normalized_path.strip("/").split("/") if name]

    @classmethod
    def _validate_operation_specific(cls, original_path: str, operation: str, folder_names: List[str]) -> List[str]:
        """Perform operation-specific validation"""
        errors = []

        if operation == "create":
            if len(folder_names) == 0:
                errors.append("Cannot create root folder")
            elif len(folder_names) > 5:  # Reasonable depth limit
                errors.append("Folder hierarchy too deep (maximum 5 levels)")

        elif operation == "delete":
            if len(folder_names) == 0:
                errors.append("Cannot delete root folder")

        elif operation == "move":
            if len(folder_names) == 0:
                errors.append("Cannot move root folder")

        return errors

    @classmethod
    def convert_for_api(cls, folder_path: str) -> str:
        """
        Quick conversion for existing code - just converts path format
        Use validate_and_convert_path() for full validation
        """
        if not folder_path or folder_path in ["/", "~"]:
            return "~"

        # Convert to lowercase for consistency
        folder_path = folder_path.lower()

        # Handle already converted paths
        if folder_path.startswith("~"):
            return folder_path

        # Convert Unix-style paths
        if folder_path.startswith("/"):
            path = folder_path[1:] if len(folder_path) > 1 else ""
            return "~" + path.replace("/", "~") if path else "~"
        else:
            # Path without leading separator
            return "~" + folder_path.replace("/", "~")

    @classmethod
    def get_parent_folder(cls, folder_path: str) -> str:
        """Get parent folder path in CheckMK format"""
        is_valid, checkmk_path, errors, display_path = cls.validate_and_convert_path(folder_path)
        if not is_valid or checkmk_path == "~":
            return "~"  # Root has no parent, return root

        # Split CheckMK path and remove last component
        parts = checkmk_path.split("~")
        if len(parts) <= 2:  # ["", "folder"] -> parent is root
            return "~"

        return "~".join(parts[:-1])  # Remove last folder

    @classmethod
    def format_validation_errors(cls, errors: List[str]) -> str:
        """Format validation errors for user display"""
        if not errors:
            return ""

        if len(errors) == 1:
            return f"❌ {errors[0]}"

        return "❌ **Folder Path Validation Errors:**\n" + "\n".join(f"• {error}" for error in errors)


def validate_folder_path(folder_path: str, operation: str = "general") -> Dict[str, Any]:
    """
    Convenience function for quick folder path validation

    Returns:
        Dict with keys: is_valid, checkmk_path, errors, display_path
    """
    is_valid, checkmk_path, errors, display_path = FolderValidator.validate_and_convert_path(folder_path, operation)

    return {
        "is_valid": is_valid,
        "checkmk_path": checkmk_path,
        "errors": errors,
        "display_path": display_path,
        "error_message": FolderValidator.format_validation_errors(errors),
    }
