# Copyright (c) 2024 Christophe Dufaza <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Devicetree shell built-in "board".

Print board information.

"""

from typing import Sequence


from dtsh.dts import YAMLFile, DTS, DTSFile
from dtsh.io import DTShOutput
from dtsh.shell import DTSh, DTShCommand, DTShFlag

from dtsh.shellutils import DTShFlagPager

from dtsh.config import DTShConfig

from dtsh.rich.shellutils import DTShFlagLongList
from dtsh.rich.text import TextUtil
from dtsh.rich.tui import RenderableError

from dtsh.rich.modelview import ViewYAMLFile, ViewDTSFile


_dtshconf: DTShConfig = DTShConfig.getinstance()


class DTShFlagBoardDTS(DTShFlag):
    """Output board file (DTS)."""

    BRIEF = "print board file (DTS)"
    LONGNAME = "board-file"


class DTShBuiltinBoard(DTShCommand):
    """Devicetree shell built-in "board".

    By default, print board description from YAML file.
    Print the board file (DTS) if "--board-file" is set.
    """

    def __init__(self) -> None:
        super().__init__(
            "board",
            "print board information",
            [
                DTShFlagBoardDTS(),
                DTShFlagLongList(),
                DTShFlagPager(),
            ],
            None,
        )

    def execute(self, argv: Sequence[str], sh: DTSh, out: DTShOutput) -> None:
        """Overrides DTShCommand.execute()."""
        super().execute(argv, sh, out)

        if self.with_flag(DTShFlagPager):
            out.pager_enter()

        # Show deprecation warning even in pager.
        self._warn_deprecated(out)

        if self.with_flag(DTShFlagLongList) or _dtshconf.pref_always_longfmt:
            if self.with_flag(DTShFlagBoardDTS):
                self._out_board_dts_rich(sh.dt.dts, out)
            else:
                self._out_board_yaml_rich(sh.dt.dts, out)
        else:
            if self.with_flag(DTShFlagBoardDTS):
                self._out_board_dts_raw(sh.dt.dts, out)
            else:
                self._out_board_yaml_raw(sh.dt.dts, out)

        if self.with_flag(DTShFlagPager):
            out.pager_exit()

    def _out_board_dts_rich(self, dts: DTS, out: DTShOutput) -> None:
        if dts.board_file:
            try:
                out.write(ViewDTSFile.create(dts.board_file))
            except RenderableError as e:
                e.warn_and_forward(self, "failed to open board file (DTS)", out)
        else:
            out.write(TextUtil.mk_apologies("Board file unavailable (DTS)."))

    def _out_board_yaml_rich(self, dts: DTS, out: DTShOutput) -> None:
        if dts.board_yaml:
            try:
                out.write(
                    ViewYAMLFile.create(
                        dts.board_yaml,
                        dts.yamlfs,
                        # Not really a binding file, but even less an included base YAML.
                        is_binding=True,
                        expand_includes=True,
                    )
                )
            except RenderableError as e:
                e.warn_and_forward(
                    self, "failed to open board file (YAML)", out
                )
        else:
            out.write(TextUtil.mk_apologies("Board file unavailable (YAML)."))

    def _out_board_dts_raw(self, dts: DTS, out: DTShOutput) -> None:
        if dts.board_file:
            out.write(DTSFile(dts.board_file).content)
        else:
            out.write("Board file unavailable (DTS).")

    def _out_board_yaml_raw(self, dts: DTS, out: DTShOutput) -> None:
        if dts.board_yaml:
            out.write(YAMLFile(dts.board_yaml).content)
        else:
            out.write("Board file unavailable (YAML).")

    def _warn_deprecated(self, out: DTShOutput) -> None:
        out.write(
            TextUtil.assemble(
                TextUtil.mk_warning("The "),
                TextUtil.bold(TextUtil.mk_warning("board")),
                TextUtil.mk_warning(" builtin is deprecated: please use the "),
                TextUtil.bold(TextUtil.mk_warning("uname")),
                TextUtil.mk_warning(" command instead."),
            )
        )
        out.write()
