"""YAML utility functions for the Arazzo generator."""

import re

import yaml


def fix_output_references(yaml_str: str) -> str:
    """Fix any broken output references in the YAML string.

    Args:
        yaml_str: The YAML string to fix

    Returns:
        The fixed YAML string
    """
    # Apply a direct text-based fix for any broken references
    fixed_yaml = ""
    concat_next = False

    for line in yaml_str.splitlines():
        # If we flagged the previous line for concatenation
        if concat_next:
            # Merge with previous line
            fixed_yaml = fixed_yaml[:-1]  # Remove the newline
            fixed_yaml += " " + line.strip() + "\n"
            concat_next = False
            continue

        # Check if this line might continue on the next line
        if "$steps." in line and ".outputs." in line and line.strip().endswith(".outputs."):
            # This line ends with ".outputs." and likely continues
            concat_next = True

        fixed_yaml += line + "\n"

    # Now let's apply one more regex-based fix for any remaining broken references
    pattern = r"(\$steps\.[A-Za-z0-9_\-]+\.outputs\.[A-Za-z0-9_\-]+)\s*\n\s+([A-Za-z0-9_\-]+)"
    fixed_yaml = re.sub(pattern, r"\1 \2", fixed_yaml)

    return fixed_yaml


class NoWrapSafeDumper(yaml.SafeDumper):
    """Custom YAML dumper that preserves long strings."""

    def represent_scalar(self, tag, value, style=None):
        """Override scalar representation to ensure references stay on one line."""
        if isinstance(value, str) and "$steps." in value and ".outputs." in value:
            style = '"'  # Use double quotes for output references
        return super().represent_scalar(tag, value, style=style)
