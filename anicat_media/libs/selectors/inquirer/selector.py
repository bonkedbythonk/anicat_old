from InquirerPy.prompts import FuzzyPrompt  # pyright: ignore[reportPrivateImportUsage]
from rich.prompt import Confirm, Prompt

from ..base import BaseSelector


class InquirerSelector(BaseSelector):
    def choose(self, prompt, choices, *, preview=None, header=None):
        if header:
            print(f"[bold cyan]{header}[/bold cyan]")
        return FuzzyPrompt(
            message=prompt,
            choices=choices,
            height="100%",
            border=True,
            validate=lambda result: result in choices,
            wrap_around=True,
            keybindings={
                "answer": [{"key": "enter"}, {"key": "right"}],
                "accept": [{"key": "enter"}, {"key": "right"}],
            },
        ).execute()

    def confirm(self, prompt, *, default=False):
        return Confirm.ask(prompt, default=default)

    def ask(self, prompt, *, default=None):
        return Prompt.ask(prompt=prompt, default=default or None)

    def choose_multiple(
        self, prompt: str, choices: list[str], preview: str | None = None
    ) -> list[str]:
        return FuzzyPrompt(
            message=prompt,
            choices=choices,
            height="100%",
            multiselect=True,
            border=True,
            wrap_around=True,
            keybindings={
                "answer": [{"key": "enter"}, {"key": "right"}],
                "accept": [{"key": "enter"}, {"key": "right"}],
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
        if header:
            print(f"[bold cyan]{header}[/bold cyan]")
        
        # InquirerPy doesn't have a native dynamic search/reload like fzf,
        # so we fallback to a static fuzzy selection of initial results if provided,
        # or we just provide the fuzzy prompt.
        return FuzzyPrompt(
            message=prompt,
            choices=initial_results or [],
            height="100%",
            border=True,
            wrap_around=True,
            keybindings={
                "answer": [{"key": "enter"}, {"key": "right"}],
                "accept": [{"key": "enter"}, {"key": "right"}],
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
