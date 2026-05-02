from typing import TYPE_CHECKING, Optional

from InquirerPy import inquirer
from InquirerPy.prompts import FuzzyPrompt  # pyright: ignore[reportPrivateImportUsage]
from rich.console import Console

from ..base import BaseSelector

if TYPE_CHECKING:
    from ....core.config import AppConfig

console = Console()

from ..base import BaseSelector


class InquirerSelector(BaseSelector):
    def __init__(self, config: Optional["AppConfig"] = None):
        self.config = config

    def _print_header(self, header: Optional[str] = None):
        if self.config and self.config.fzf.show_header_ascii_art:
            header_color = self.config.fzf.header_color.split(",")
            color_str = f"rgb({header_color[0]},{header_color[1]},{header_color[2]})"
            console.print(self.config.fzf.header_ascii_art, style=color_str, highlight=False)
            print()  # Vertical spacing after logo

        if header:
            console.print(f"[bold cyan]{header}[/bold cyan]")

    def choose(self, prompt, choices, *, preview=None, header=None):
        self._print_header(header)
        return FuzzyPrompt(
            message=prompt,
            choices=choices,
            height="100%",
            border=False,
            validate=lambda result: result in choices,
            wrap_around=True,
            keybindings={
                "answer": [{"key": "enter"}, {"key": "right"}],
            },
        ).execute()

    def confirm(self, prompt, *, default=False):
        self._print_header()
        return inquirer.confirm(
            message=prompt,
            default=default,
            keybindings={
                "answer": [{"key": "enter"}, {"key": "right"}],
            },
        ).execute()

    def ask(self, prompt, *, default=None):
        self._print_header()
        return inquirer.text(
            message=prompt,
            default=default or "",
            keybindings={
                "answer": [{"key": "enter"}, {"key": "right"}],
            },
        ).execute()

    def choose_multiple(
        self, prompt: str, choices: list[str], preview: str | None = None
    ) -> list[str]:
        self._print_header()
        return FuzzyPrompt(
            message=prompt,
            choices=choices,
            height="100%",
            multiselect=True,
            border=False,
            wrap_around=True,
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
        self._print_header(header)
        
        # InquirerPy doesn't have a native dynamic search/reload like fzf,
        # so we fallback to a static fuzzy selection of initial results if provided,
        # or we just provide the fuzzy prompt.
        return FuzzyPrompt(
            message=prompt,
            choices=initial_results or [],
            height="100%",
            border=False,
            wrap_around=True,
            keybindings={
                "answer": [{"key": "enter"}, {"key": "right"}],
            },
        ).execute()


if __name__ == "__main__":
    selector = InquirerSelector()
    choice = selector.ask("Hello dev :)")
    print(choice)
    choice = selector.confirm("Hello dev :)")
    print(choice)
    choice = selector.choose_multiple("What comes first", ["a", "b"])
    print(choice)
    choice = selector.choose("What comes first", ["a", "b"])
    print(choice)
