# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Auto-completion with GNU readline for devicetree shells."""


from devicetree.edtlib import Node, Binding

from dtsh.dtsh import Dtsh, DtshCommand, DtshCommandOption, DtshAutocomp


class DevicetreeAutocomp(DtshAutocomp):
    """Devicetree shell commands auto-completion support with GNU readline.
    """

    _hints: list[str]
    _model: list | None

    def __init__(self, shell: Dtsh) -> None:
        """Initialize the completion engine.
        """
        self._dtsh = shell
        self._hints = list[str]()
        self._model = None

    @property
    def count(self) -> int:
        """Implements DtshAutocomp.count().
        """
        if self._model:
            return len(self._model)
        return 0

    @property
    def hints(self) -> list[str]:
        """Implements DtshAutocomp.hints().
        """
        return self._hints

    @property
    def model(self) -> list | None:
        """Implements DtshAutocomp.model().
        """
        return self._model

    def reset(self) -> None:
        """Implements DtshAutocomp.reset().
        """
        self._hints.clear()
        self._model = None

    def autocomplete(self,
                     cmdline: str,
                     prefix: str,
                     cursor: int = 0) -> list[str]:
        """Implements DtshAutocomp.autocomplete().
        """
        self.reset()
        cmdline_vstr = cmdline.lstrip().split()

        if len(cmdline_vstr) == 0:
            self._autocomp_empty_cmdline()
        elif prefix and (len(cmdline_vstr) == 1):
            self._autocomp_with_commands(prefix)
        else:
            cmd_name = cmdline_vstr[0]
            cmd = self._dtsh.builtin(cmd_name)
            if cmd:
                if prefix.startswith('-'):
                    self._autocomp_with_options(cmd, prefix)
                else:
                    self._autocomp_with_params(cmd, prefix)

        return self._hints

    def _autocomp_empty_cmdline(self) -> None:
        self._model = list[DtshCommand]()
        for cmd in self._dtsh.builtins:
            self._hints.append(cmd.name)
            self._model.append(cmd)

    def _autocomp_with_commands(self, prefix: str) -> None:
        self._model = list[DtshCommand]()
        for cmd in self._dtsh.builtins:
            if cmd.name.startswith(prefix) and (len(cmd.name) > len(prefix)):
                self._hints.append(cmd.name)
                self._model.append(cmd)

    def _autocomp_with_options(self, cmd: DtshCommand, prefix: str) -> None:
        self._model = list[DtshCommandOption]()
        for opt in cmd.autocomplete_option(prefix):
            self._model.append(opt)

        for opt in self._model:
            if opt.shortname and (not prefix.startswith('--')):
                self._hints.append(f'-{opt.shortname}')
        for opt in self._model:
            if opt.longname:
                self._hints.append(f'--{opt.longname}')

    def _autocomp_with_params(self, cmd:DtshCommand, prefix: str) -> None:
        model = cmd.autocomplete_param(prefix)
        if model:
            if isinstance(model[0], Node):
                self._model = list[Node]()
                for node in list[Node](model):
                    self._model.append(node)
                    self._hints.append(node.path)
            elif isinstance(model[0], Binding):
                self._model = list[Binding]()
                for binding in list[Binding](model):
                    self._model.append(binding)
                    self._hints.append(binding.compatible)
            else:
                # Fallback to string model.
                self._model = list[str]()
                for m in model:
                    completion = str(m)
                    self._model.append(completion)
                    self._hints.append(completion)
