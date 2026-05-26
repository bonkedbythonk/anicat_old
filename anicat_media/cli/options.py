from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional, get_args, get_origin

import click
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from ..core.config.model import OtherConfig

TYPE_MAP = {
    str: click.STRING,
    int: click.INT,
    bool: click.BOOL,
    float: click.FLOAT,
    Path: click.Path(),
}


class ConfigOption(click.Option):
    """
    Custom click option that allows for more flexible handling of Pydantic models.
    This is used to ensure that options can be generated dynamically from Pydantic models.
    """

    model_name: Optional[str]
    field_name: Optional[str]

    def __init__(self, *args, **kwargs):
        self.model_name = kwargs.pop("model_name", None)
        self.field_name = kwargs.pop("field_name", None)
        super().__init__(*args, **kwargs)


def options_from_model(model: type[BaseModel], parent_name: str = "") -> Callable:
    """
    A decorator factory that generates click.option decorators from a Pydantic model.

    This function introspects a Pydantic model and creates a stack of decorators
    that can be applied to a click command function, ensuring the CLI options
    always match the configuration model.

    Args:
        model: The Pydantic BaseModel class to generate options from.
    Returns:
        A decorator that applies the generated options to a function.
    """
    decorators = []

    is_external_tool = issubclass(model, OtherConfig)
    model_name = model.__name__.lower().replace("config", "")

    # Introspect the model's fields
    for field_name, field_info in model.model_fields.items():
        if isinstance(field_info.annotation, type) and issubclass(
            field_info.annotation, BaseModel
        ):
            nested_decorators = options_from_model(field_info.annotation, field_name)
            nested_decorator_list = getattr(nested_decorators, "decorators", [])
            decorators.extend(nested_decorator_list)
            continue

        if parent_name:
            cli_name = f"--{parent_name}-{field_name.replace('_', '-')}"
        elif is_external_tool:
            cli_name = f"--{model_name}-{field_name.replace('_', '-')}"
        else:
            cli_name = f"--{field_name.replace('_', '-')}"
        kwargs = {
            "type": _get_click_type(field_info),
            "help": field_info.description or "",
            "hidden": True,
        }

        if (
            field_info.annotation is not None
            and isinstance(field_info.annotation, type)
            and issubclass(field_info.annotation, Enum)
        ):
            kwargs["default"] = field_info.default.value
        elif field_info.annotation is bool:
            if field_info.default is not PydanticUndefined:
                kwargs["default"] = field_info.default
                kwargs["show_default"] = True
            if parent_name:
                cli_name = (
                    f"{cli_name}/--no-{parent_name}-{field_name.replace('_', '-')}"
                )
            elif is_external_tool:
                cli_name = (
                    f"{cli_name}/--no-{model_name}-{field_name.replace('_', '-')}"
                )
            else:
                cli_name = f"{cli_name}/--no-{field_name.replace('_', '-')}"
        elif field_info.default is not PydanticUndefined:
            kwargs["default"] = field_info.default
            kwargs["show_default"] = True

        decorators.append(
            click.option(
                cli_name,
                cls=ConfigOption,
                model_name=model_name,
                field_name=field_name,
                **kwargs,
            )
        )

    for field_name, computed_field_info in model.model_computed_fields.items():
        if parent_name:
            cli_name = f"--{parent_name}-{field_name.replace('_', '-')}"
        elif is_external_tool:
            cli_name = f"--{model_name}-{field_name.replace('_', '-')}"
        else:
            cli_name = f"--{field_name.replace('_', '-')}"

        kwargs = {
            "type": TYPE_MAP[computed_field_info.return_type],
            "help": computed_field_info.description or "",
            "hidden": True,
        }

        decorators.append(
            click.option(
                cli_name,
                cls=ConfigOption,
                model_name=model_name,
                field_name=field_name,
                **kwargs,
            )
        )

    def decorator(f: Callable) -> Callable:
        # Apply the decorators in reverse order to the function
        for deco in reversed(decorators):
            f = deco(f)
        return f

    # Store the list of decorators as an attribute for nested calls
    setattr(decorator, "decorators", decorators)
    return decorator


def _get_click_type(field_info: FieldInfo) -> Any:
    """Maps a Pydantic field's type to a corresponding click type."""
    field_type = field_info.annotation

    # check if type is enum
    if (
        field_type is not None
        and isinstance(field_type, type)
        and issubclass(field_type, Enum)
    ):
        # Get the string values of the enum members
        enum_choices = [member.value for member in field_type]
        return click.Choice(enum_choices)

    # Check if the type is a Literal
    if (
        field_type is not None
        and hasattr(field_type, "__origin__")
        and get_origin(field_type) is Literal
    ):
        args = get_args(field_type)
        if args:
            return click.Choice(args)

    # Check for examples in field_info - use as choices
    if hasattr(field_info, "examples") and field_info.examples:
        return click.Choice(field_info.examples)

    # Check for numeric constraints and create click.Range
    if field_type in (int, float):
        constraints = {}

        # Extract constraints from field_info.metadata
        if hasattr(field_info, "metadata") and field_info.metadata:
            for constraint in field_info.metadata:
                constraint_type = type(constraint).__name__

                if constraint_type == "Ge" and hasattr(constraint, "ge"):
                    constraints["min"] = constraint.ge
                elif constraint_type == "Le" and hasattr(constraint, "le"):
                    constraints["max"] = constraint.le
                elif constraint_type == "Gt" and hasattr(constraint, "gt"):
                    # gt means strictly greater than, so min should be gt + 1 for int
                    if field_type is int:
                        constraints["min"] = constraint.gt + 1
                    else:
                        # For float, we can't easily handle strict inequality in click.Range
                        constraints["min"] = constraint.gt
                elif constraint_type == "Lt" and hasattr(constraint, "lt"):
                    # lt means strictly less than, so max should be lt - 1 for int
                    if field_type is int:
                        constraints["max"] = constraint.lt - 1
                    else:
                        # For float, we can't easily handle strict inequality in click.Range
                        constraints["max"] = constraint.lt

        # Create click.Range if we have constraints
        if constraints:
            range_kwargs = {}
            if "min" in constraints:
                range_kwargs["min"] = constraints["min"]
            if "max" in constraints:
                range_kwargs["max"] = constraints["max"]

            if range_kwargs:
                if field_type is int:
                    return click.IntRange(**range_kwargs)
                else:
                    return click.FloatRange(**range_kwargs)

    return TYPE_MAP.get(
        field_type, click.STRING
    )  # Default to STRING if type is not found
