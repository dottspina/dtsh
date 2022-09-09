# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Auto-completion with GNU readline for devicetree shells."""

from collections import OrderedDict

from devicetree.edtlib import Node, Binding, Property

from dtsh.dtsh import Dtsh, DtshCommand, DtshAutocomp


class DevicetreeAutocomp(DtshAutocomp):
    """Devicetree shell commands auto-completion support with GNU readline.
    """

    # Maps completion state (strings) and model (objects).
    #
    _autocomp_state: OrderedDict[str, object]

    # Autocomp mode.
    #
    _mode: int

    def __init__(self, shell: Dtsh) -> None:
        """Initialize the completion engine.
        """
        self._dtsh = shell
        self._mode = DtshAutocomp.MODE_ANY
        self._autocomp_state = OrderedDict[str, object]()

    @property
    def count(self) -> int:
        """Implements DtshAutocomp.count().
        """
        return len(self._autocomp_state)

    @property
    def hints(self) -> list[str]:
        """Implements DtshAutocomp.hints().
        """
        return list(self._autocomp_state.keys())

    @property
    def model(self) -> list:
        """Implements DtshAutocomp.model().
        """
        return list(self._autocomp_state.values())

    @property
    def mode(self) -> int:
        """Implements DtshAutocomp.mode().
        """
        return self._mode

    def reset(self) -> None:
        """Implements DtshAutocomp.reset().
        """
        self._mode = DtshAutocomp.MODE_ANY
        self._autocomp_state.clear()

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

        return self.hints

    def _autocomp_empty_cmdline(self) -> None:
        self._mode = DtshAutocomp.MODE_DTSH_CMD
        for cmd in self._dtsh.builtins:
            self._autocomp_state[cmd.name] = cmd

    def _autocomp_with_commands(self, prefix: str) -> None:
        self._mode = DtshAutocomp.MODE_DTSH_CMD
        for cmd in self._dtsh.builtins:
            if cmd.name.startswith(prefix) and (len(cmd.name) > len(prefix)):
                self._autocomp_state[cmd.name] = cmd

    def _autocomp_with_options(self, cmd: DtshCommand, prefix: str) -> None:
        self._mode = DtshAutocomp.MODE_DTSH_OPT
        for opt in cmd.autocomplete_option(prefix):
            # When building the options hints for rl_completion_matches(),
            # we must answer the longest possible hints for the given prefix:
            # we'll use the option's long name when it does not have any short
            # name or the prefix starts with '--', its short name otherwise.
            # The syntactic characters '-' are included in the hints since
            # they're part of the prefix.
            if opt.shortname and (not prefix.startswith('--')):
                self._autocomp_state[f'-{opt.shortname}'] = opt
            elif opt.longname:
                self._autocomp_state[f'--{opt.longname}'] = opt

    def _autocomp_with_params(self, cmd:DtshCommand, prefix: str) -> None:
        self._mode, model = cmd.autocomplete_param(prefix)
        if self._mode == DtshAutocomp.MODE_DT_NODE:
            for node in list[Node](model):
                hint = node.path
                if node.children:
                    # Prepare auto-completion state for TABing
                    # the node's children enumeration.
                    # See readline_completions_hook(() in dtsh.session.
                    hint += '/'
                self._autocomp_state[hint] = node
        elif self._mode == DtshAutocomp.MODE_DT_PROP:
            for prop in list[Property](model):
                hint = f'{prop.node.path}${prop.name}'
                self._autocomp_state[hint] = prop
        elif self._mode == DtshAutocomp.MODE_DT_BINDING:
            for binding in list[Binding](model):
                self._autocomp_state[binding.compatible] = binding
        elif self._mode == DtshAutocomp.MODE_DTSH_CMD:
            for cmd in list[DtshCommand](model):
                self._autocomp_state[cmd.name] = cmd
        else:
            for completion in model:
                self._autocomp_state[str(completion)] = completion
