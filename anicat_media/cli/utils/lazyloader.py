import importlib

import click


class LazyGroup(click.Group):
    """Click Group that lazily imports subcommands only when needed."""

    def __init__(self, root: str, *args, lazy_subcommands=None, hidden_commands=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = root
        self.lazy_subcommands = lazy_subcommands or {}
        self._hidden_commands = set(hidden_commands or [])

    def list_commands(self, ctx):
        base = super().list_commands(ctx)
        lazy = sorted(self.lazy_subcommands.keys())
        return [c for c in base + lazy if c not in self._hidden_commands]

    def get_command(self, ctx, cmd_name):
        if cmd_name in self.lazy_subcommands:
            return self._lazy_load(cmd_name)
        return super().get_command(ctx, cmd_name)

    def _lazy_load(self, cmd_name: str):
        import_path = self.lazy_subcommands[cmd_name]
        modname, cmd_object_name = import_path.rsplit(".", 1)
        mod = importlib.import_module(f".{modname}", package=self.root)
        cmd_object = getattr(mod, cmd_object_name)
        if not isinstance(cmd_object, click.Command):
            raise ValueError(
                f"Lazy loading of {import_path} failed by returning "
                "a non-command object"
            )
        return cmd_object
