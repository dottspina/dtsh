# Copyright (c) 2024 Christophe Dufaza <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Devicetree shell built-in "cat".

Print node content.

Unit tests and examples: tests/test_dtsh_builtin_cat.py
"""

from typing import Sequence, List, Optional

from dtsh.utils import YAMLFile
from dtsh.model import DTNode, DTNodeProperty
from dtsh.modelutils import DTSUtil
from dtsh.io import DTShOutput
from dtsh.shell import (
    DTSh,
    DTShCommand,
    DTShFlag,
    DTShCommandError,
    DTShUsageError,
)

from dtsh.shellutils import (
    DTShFlagPager,
    DTShParamDTPathX,
)
from dtsh.config import DTShConfig

from dtsh.rich.shellutils import DTShFlagLongList
from dtsh.rich.text import TextUtil
from dtsh.rich.theme import DTShTheme
from dtsh.rich.tui import HeadingsContentWriter, RenderableError
from dtsh.rich.modelview import (
    ViewPropertyValueTable,
    FormPropertySpec,
    ViewNodeBinding,
    ViewDescription,
    ViewYAMLFile,
)


_dtshconf: DTShConfig = DTShConfig.getinstance()


class CatFlagCompactYAML(DTShFlag):
    """Whether to hide the content of included YAML files.

    Only available when '-l' and 'A' or 'Y'.
    """

    BRIEF = "hide content of included YAML files"
    LONGNAME = "compact-yaml"


class DTShFlagAll(DTShFlag):
    """Concatenate and output all available information about a node a property.

    Ignored:
    - in POSIX-like output mode ("-l" is not set)
    - when "cat" operates on multiple properties
    """

    BRIEF = "show all info about node or property"
    SHORTNAME = "A"


class DTShFlagDescription(DTShFlag):
    """Output node or property full description from binding."""

    BRIEF = "description from bindings"
    SHORTNAME = "D"


class DTShFlagBindings(DTShFlag):
    """Output bindings of a node or property."""

    BRIEF = "bindings or property specification"
    SHORTNAME = "B"


class DTShFlagYamlFile(DTShFlag):
    """Output the YAML view of bindings (with extended includes)."""

    BRIEF = "YAML view of bindings"
    SHORTNAME = "Y"


class DTShBuiltinCat(DTShCommand):
    """Devicetree shell built-in "cat".

    Concatenate and output info about a node and its properties.

    If the user does not explicitly select what to cat
    with command flags, will output all node property values.

    Otherwise:
    - POSIX-like output: '-A' is ignored, will output one of '-D', '-B', or '-Y'
    - rich output: will output options among '-DBY', or all if '-A'

    """

    def __init__(self) -> None:
        super().__init__(
            "cat",
            "concat and output info about a node and its properties",
            [
                DTShFlagDescription(),
                DTShFlagYamlFile(),
                DTShFlagBindings(),
                DTShFlagAll(),
                DTShFlagLongList(),
                CatFlagCompactYAML(),
                DTShFlagPager(),
            ],
            DTShParamDTPathX(),
        )

    def parse_argv(self, argv: Sequence[str]) -> None:
        """Overrides DTShCommand.parse_argv()."""
        super().parse_argv(argv)
        # Preconditions for compact mode.
        if self.with_flag(CatFlagCompactYAML):
            if not (
                self.with_flag(DTShFlagYamlFile) or self.with_flag(DTShFlagAll)
            ):
                raise DTShUsageError(
                    self, "option '--compact-yaml' requires '-Y' or '-A"
                )

        # Precondition for POSIX-like output only.
        if not self._with_longfmt():
            if self._nfmtspecs() > 1:
                raise DTShUsageError(
                    self, "more than one option among '-DBY' requires '-l'"
                )

        # Precondition for both POSIX-like and rich outputs.
        if self.with_param(DTShParamDTPathX).is_globexpr():
            if self.with_flag(DTShFlagAll) or self._nfmtspecs():
                raise DTShUsageError(
                    self,
                    "globbing properties, options '-DBYA' not allowed",
                )

    def execute(self, argv: Sequence[str], sh: DTSh, out: DTShOutput) -> None:
        """Overrides DTShCommand.execute()."""
        super().execute(argv, sh, out)

        parm_xpath = self.with_param(DTShParamDTPathX)
        parm_dtnode: DTNode
        parm_dtprops: Optional[List[DTNodeProperty]]
        # Command will fail here if the xpath parameter is invalid
        # (node or property not found).
        parm_dtnode, parm_dtprops = parm_xpath.xsplit(self, sh)

        # Setup pager after we could fail.
        if self.with_flag(DTShFlagPager):
            out.pager_enter()

        if parm_dtprops is not None:
            # The command is invoked with either:
            # - PROP resolved to a single property name
            # - PROP globbing expression matching zero,
            #   one or more properties

            if parm_xpath.is_globexpr():
                # Globbing: we may have zero, one or more matching properties.
                # Concatenate and output property values.
                self.cat_dtproperties(parm_dtprops, parm_dtnode, out)
            else:
                # If not globbing, we have exactly one property name.
                # Concatenate and output info about this property.
                self.cat_dtproperty(parm_dtprops[0], parm_dtnode, out)

        else:
            # The command is invoked for node at PATH.
            # Concatenate and output info about node.
            self.cat_dtnode(parm_dtnode, out)

        if self.with_flag(DTShFlagPager):
            out.pager_exit()

    def cat_dtnode(self, node: DTNode, out: DTShOutput) -> None:
        """The command is invoked with a DT node as parameter.

        Args:
            dtnode: The node to cat information about.
            out: Where to cat.
        """
        if self._with_longfmt():
            self._out_dtnode_rich(node, out)
        else:
            self._out_dtnode_raw(node, out)

    def cat_dtproperty(
        self, dtprop: DTNodeProperty, node: DTNode, out: DTShOutput
    ) -> None:
        """The command is invoked with a single DT property as parameter.

        Args:
            dtprop: The property parameter.
            out: Where to cat.
        """
        if self._with_longfmt():
            self._out_dtproperty_rich(dtprop, node, out)
        else:
            self._out_dtproperty_raw(dtprop, out)

    def cat_dtproperties(
        self, dtprops: List[DTNodeProperty], node: DTNode, out: DTShOutput
    ) -> None:
        """The command is invoked with a PROP globbing expression.

        It will output property values.

        Args:
            dtprops: The possibly empty list of properties
              matching the PROP globbing expression.
            out: Where to cat.
        """
        # Ignore no match.
        if dtprops:
            if self._with_longfmt():
                self._out_dtproperties_rich(dtprops, node, out)
            else:
                self._out_dtproperties_raw(dtprops, out)

    def _out_dtnode_rich(self, node: DTNode, out: DTShOutput) -> None:
        show_all = self.with_flag(DTShFlagAll)
        if not (show_all or self._nfmtspecs()):
            # If the user hasn't explicitly selected what to cat,
            # just dump all node property values, if any.
            dtprops = node.all_dtproperties()
            if dtprops:
                self._out_dtproperties_rich(dtprops, node, out)
            return

        # Otherwise, concatenate and output selected sections.
        sections: List[HeadingsContentWriter.Section] = []
        if show_all or self.with_flag(DTShFlagDescription):
            sections.append(
                HeadingsContentWriter.Section(
                    "description", ViewDescription(node.description)
                )
            )
        if show_all:
            # Show property values only when '-A' is set.
            dtprops = node.all_dtproperties()
            sections.append(
                HeadingsContentWriter.Section(
                    "Properties",
                    (
                        ViewPropertyValueTable(dtprops, node.dt)
                        if dtprops
                        else TextUtil.mk_apologies(
                            "This node does not set any property."
                        )
                    ),
                )
            )
        if show_all or self.with_flag(DTShFlagBindings):
            sections.append(
                HeadingsContentWriter.Section(
                    "Binding",
                    (
                        ViewNodeBinding(node)
                        if node.binding
                        else TextUtil.mk_apologies("This node has no binding.")
                    ),
                )
            )
        if show_all or self.with_flag(DTShFlagYamlFile):
            try:
                sections.append(
                    HeadingsContentWriter.Section(
                        "YAML",
                        (
                            ViewYAMLFile.create(
                                node.binding_path,
                                node.dt.dts.yamlfs,
                                style=DTShTheme.STYLE_YAML_BINDING,
                                compact=self.with_flag(CatFlagCompactYAML),
                            )
                            if node.binding_path
                            else TextUtil.mk_apologies(
                                "YAML binding unavailable."
                            )
                        ),
                    )
                )
            except RenderableError as e:
                e.warn_and_forward(self, "failed to open binding file", out)

        self._out_rich_sections(sections, out)

    def _out_dtnode_raw(self, node: DTNode, out: DTShOutput) -> None:
        if self.with_flag(DTShFlagDescription):
            if node.description:
                out.write(node.description)
        elif self.with_flag(DTShFlagYamlFile):
            if node.binding_path:
                yaml = YAMLFile(node.binding_path)
                out.write(yaml.content)
        elif self.with_flag(DTShFlagBindings):
            if node.binding_path:
                out.write(node.binding_path)
        else:
            # By default, dump property values.
            self._out_dtproperties_raw(node.all_dtproperties(), out)

    def _out_dtproperties_rich(
        self, dtprops: List[DTNodeProperty], node: DTNode, out: DTShOutput
    ) -> None:
        # Multiple properties: dump values in table view.
        view = ViewPropertyValueTable(dtprops, node.dt)
        view.left_indent(1)
        out.write(view)

    def _out_dtproperty_rich(
        self, dtprop: DTNodeProperty, node: DTNode, out: DTShOutput
    ) -> None:
        show_all = self.with_flag(DTShFlagAll)
        if not (show_all or self._nfmtspecs()):
            # If the user hasn't explicitly selected what to cat,
            # just dump property value.
            out.write(ViewPropertyValueTable([dtprop], node.dt))
            return

        # Otherwise, concatenate and output selected sections.
        sections: List[HeadingsContentWriter.Section] = []
        if show_all or self.with_flag(DTShFlagDescription):
            sections.append(
                HeadingsContentWriter.Section(
                    "description", ViewDescription(dtprop.description)
                )
            )
        if show_all or self.with_flag(DTShFlagBindings):
            sections.append(
                HeadingsContentWriter.Section(
                    "specification",
                    FormPropertySpec(dtprop.dtspec, node.dt),
                )
            )
        if show_all or self.with_flag(DTShFlagYamlFile):
            if dtprop.path == dtprop.node.binding_path:
                style = DTShTheme.STYLE_YAML_BINDING
            else:
                style = DTShTheme.STYLE_YAML_INCLUDE
            try:
                sections.append(
                    HeadingsContentWriter.Section(
                        "YAML",
                        (
                            ViewYAMLFile.create(
                                dtprop.path,
                                dtprop.node.dt.dts.yamlfs,
                                style=style,
                                compact=self.with_flag(CatFlagCompactYAML),
                            )
                            if dtprop.path
                            else TextUtil.mk_apologies(
                                "YAML specification unavailable."
                            )
                        ),
                    )
                )
            except RenderableError as e:
                e.warn_and_forward(
                    self, "failed to open specification file", out
                )

        self._out_rich_sections(sections, out)

    def _out_dtproperties_raw(
        self, dtprops: List[DTNodeProperty], out: DTShOutput
    ) -> None:
        for dtprop in dtprops:
            strval = DTSUtil.mk_property_value(dtprop)
            out.write(f"{dtprop.name}: {strval}")

    def _out_dtproperty_raw(
        self, dtprop: DTNodeProperty, out: DTShOutput
    ) -> None:
        # Precondition for POSIX-like output only.
        if self._nfmtspecs() > 1:
            raise DTShCommandError(
                self, "more than one option among '-DBY' requires '-l'"
            )

        if self.with_flag(DTShFlagDescription):
            if dtprop.description:
                out.write(dtprop.description)
        elif self.with_flag(DTShFlagYamlFile):
            if dtprop.path:
                yaml = YAMLFile(dtprop.path)
                out.write(yaml.content)
        elif self.with_flag(DTShFlagBindings):
            if dtprop.path:
                out.write(dtprop.path)
        else:
            # Default to property value.
            out.write(DTSUtil.mk_property_value(dtprop))

    def _with_longfmt(self) -> bool:
        # Should we use formatted output ?
        return (
            # "-l"
            self.with_flag(DTShFlagLongList)
            # "-A" implies "-l"
            or self.with_flag(DTShFlagAll)
        )

    def _nfmtspecs(self) -> int:
        # Number of output format specifier flags, among DTShFlagDescription,
        # DTShFlagYamlFile and DTShFlagBindings, set on the command line.
        # Each flag represents a headings in a rich output.
        # With POSIX-like output, only one is allowed.
        return sum(
            [
                self.with_flag(DTShFlagDescription),
                self.with_flag(DTShFlagBindings),
                self.with_flag(DTShFlagYamlFile),
            ]
        )

    def _out_rich_sections(
        self, sections: List[HeadingsContentWriter.Section], out: DTShOutput
    ) -> None:
        if len(sections) == 1:
            # If only on section, just write its content.
            out.write(sections[0].content)
        else:
            # Otherwise, use headings writer.
            hds_writer = HeadingsContentWriter()
            for section in sections:
                hds_writer.write_section(section, out)
