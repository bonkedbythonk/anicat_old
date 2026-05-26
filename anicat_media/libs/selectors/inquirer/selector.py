from typing import TYPE_CHECKING, Optional

from InquirerPy import inquirer
from InquirerPy.validator import EmptyInputValidator
from rich.console import Console
from rich.text import Text

from ..base import BaseSelector

if TYPE_CHECKING:
    from ....core.config import AppConfig

console = Console()


class InquirerSelector(BaseSelector):
    def __init__(self, config: Optional["AppConfig"] = None):
        self.config = config

    def _get_header_text(self, header: Optional[str] = None) -> str:
        """Constructs the header text including logo and update notification."""
        lines = []
        if self.config and self.config.fzf.show_header_ascii_art:
            header_color = self.config.fzf.header_color.split(",")
            color_str = f"rgb({header_color[0]},{header_color[1]},{header_color[2]})"
            lines.append(f"[{color_str}]{self.config.fzf.header_ascii_art}[/]")
            lines.append("")  # Spacing

        if header:
            lines.append(f"[bold cyan]{header}[/bold cyan]")

        return "\n".join(lines)

    def _render_header(self, header: Optional[str] = None):
        """Prints the header to the console."""
        header_text = self._get_header_text(header)
        if header_text:
            console.print(header_text)

    def _get_clean_prompt(self, prompt: str) -> str:
        """Handles prompts that might contain Rich markup."""
        if "[" in prompt and "]" in prompt:
            rich_text = Text.from_markup(prompt)
            if rich_text.plain != prompt:
                # If it has markup, print the styled version and return the plain version
                console.print(rich_text)
                return " -> "  # Simple indicator since the message was already printed
        return prompt

    def choose(self, prompt, choices, *, preview=None, header=None):
        self._render_header(header)
        prompt = self._get_clean_prompt(prompt)

        return inquirer.fuzzy(  # type: ignore
            message=prompt,
            choices=choices,
            border=False,
            validate=lambda result: result in choices,
            keybindings={
                "answer": [{"key": "enter"}, {"key": "right"}],
            },
        ).execute()

    def confirm(self, prompt, *, default=False):
        self._render_header()
        prompt = self._get_clean_prompt(prompt)
        return inquirer.confirm(  # type: ignore
            message=prompt,
            default=default,
            keybindings={
                "answer": [{"key": "enter"}, {"key": "right"}],
            },
        ).execute()

    def ask(self, prompt, *, default=None):
        self._render_header()
        prompt = self._get_clean_prompt(prompt)
        return inquirer.text(  # type: ignore
            message=prompt,
            default=default or "",
            validate=EmptyInputValidator("Input cannot be empty. Please try again."),
            keybindings={
                "answer": [{"key": "enter"}, {"key": "right"}],
            },
        ).execute()

    def choose_multiple(
        self, prompt: str, choices: list[str], preview: str | None = None
    ) -> list[str]:
        self._render_header()
        prompt = self._get_clean_prompt(prompt)
        return inquirer.fuzzy(  # type: ignore
            message=prompt,
            choices=choices,
            multiselect=True,
            border=False,
            keybindings={
                "answer": [{"key": "enter"}, {"key": "right"}],
            },
        ).execute()

    def search(
        self,
        prompt: str,
        search_command: str,
        *,
        preview: str | None = None,
        header: str | None = None,
        initial_query: str | None = None,
        initial_results: list[str] | None = None,
    ) -> str | None:
        self._render_header(header)

        return inquirer.fuzzy(  # type: ignore
            message=prompt,
            choices=initial_results or [],
            border=False,
            keybindings={
                "answer": [{"key": "enter"}, {"key": "right"}],
            },
        ).execute()


if __name__ == "__main__":
    import sys

    try:
        selector = InquirerSelector()
        choice = selector.choose("Test", ["a", "b"])
        print(choice)
    finally:
        # Ensure terminal is reset on exit
        sys.exit(0)
