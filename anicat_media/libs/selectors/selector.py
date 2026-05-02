from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...core.config import AppConfig

from .base import BaseSelector

SELECTORS = ["fzf", "rofi", "default"]


class SelectorFactory:
    @staticmethod
    def create(config: "AppConfig") -> BaseSelector:
        """
        Factory to create a selector instance based on the configuration.
        """
        selector_name = config.general.selector

        if selector_name not in SELECTORS:
            raise ValueError(
                f"Unsupported selector: '{selector_name}'.Available selectors are: {SELECTORS}"
            )

        # Instantiate the class, passing the relevant config section
        if selector_name == "fzf":
            from .fzf import FzfSelector

            return FzfSelector(config.fzf)
        if selector_name == "rofi":
            from .rofi import RofiSelector

            return RofiSelector(config.rofi)

        from .inquirer import InquirerSelector

        return InquirerSelector(config)


# Simple alias for ease of use
create_selector = SelectorFactory.create
