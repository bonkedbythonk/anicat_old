from enum import Enum
from pathlib import Path
from ...core.config import AppConfig


def generate_config_toml_from_app_model(config: AppConfig) -> str:
    """
    Generates a TOML string from an AppConfig object.

    This is a simple implementation to avoid external dependencies like tomli_w.
    """
    lines = [r"#/\_/\ ", r"#( o.o )", r"# > ^ <  [ a n i c a t ]", ""]

    for section_name, section_model in config:
        model_class = type(section_model)
        if not hasattr(model_class, "model_fields"):
            continue

        lines.append(f"[{section_name}]")

        for field_name in model_class.model_fields:
            field_value = getattr(section_model, field_name)

            # Special case for token in anilist section to ensure it's always written
            if (
                section_name == "anilist"
                and field_name == "token"
                and field_value is None
            ):
                field_value = ""

            if field_value is None:
                continue

            if isinstance(field_value, bool):
                value = str(field_value).lower()
            elif isinstance(field_value, (int, float)):
                value = str(field_value)
            elif isinstance(field_value, list):
                # Simple list formatting for TOML
                value = (
                    "["
                    + ", ".join(
                        f'"{v.value}"'
                        if isinstance(v, Enum)
                        else f'"{v}"'
                        if isinstance(v, str)
                        else str(v)
                        for v in field_value
                    )
                    + "]"
                )
            elif isinstance(field_value, Path):
                # Make path dynamic to user home if possible
                try:
                    home = Path.home()
                    if field_value.is_relative_to(home):
                        str_val = "~/" + str(field_value.relative_to(home))
                    else:
                        str_val = str(field_value)
                except (ValueError, RuntimeError):
                    str_val = str(field_value)

                str_val = str_val.replace("\\", "\\\\").replace('"', '\\"')
                value = f'"{str_val}"'
            elif isinstance(field_value, Enum):  # Enum
                value = f'"{field_value.value}"'
            else:
                str_val = str(field_value).replace("\\", "\\\\")
                if "\n" in str_val:
                    # Use multiline string for values with newlines
                    value = f'"""\n{str_val}"""'
                else:
                    str_val = str_val.replace('"', '\\"')
                    value = f'"{str_val}"'

            lines.append(f"{field_name} = {value}")
        lines.append("")

    return "\n".join(lines)
