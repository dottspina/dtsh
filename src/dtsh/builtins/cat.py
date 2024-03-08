# Copyright (c) 2024 Christophe Dufaza <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Devicetree shell built-in "cat".

Print node content.

Unit tests and examples: tests/test_dtsh_builtin_cat.py
"""

from typing import Optional, Sequence, List


from dtsh.dts import YAMLFile
from dtsh.model import DTNode, DTNodeProperty
from dtsh.modelutils import DTSUtil
from dtsh.io import DTShOutput
from dtsh.shell import DTSh, DTShCommand, DTShFlag, DTShUsageError

from dtsh.shellutils import (
    DTShFlagPager,
    DTShParamDTPathX,
)
from dtsh.config import DTShConfig

from dtsh.rich.shellutils import DTShFlagLongList
from dtsh.rich.text import TextUtil
from dtsh.rich.modelview import (
    ViewPropertyValueTable,
    FormPropertySpec,
    ViewNodeBinding,
    ViewDescription,
    ViewYAML,
    HeadingsContentWriter,
)


_dtshconf: DTShConfig = DTShConfig.getinstance()


class DTShFlagAll(DTShFlag):
    """Flag to concatenate and output all available information
    about a node a property.


    Ignored:
    - in POSIX-like output mode ("-l" is not set)
    - when "cat" operates on multiple properties
    """

    BRIEF = "show all info about node or property"
    SHORTNAME = "A"


class DTShFlagDescription(DTShFlag):
    """Flag to output node or property full description from binding."""

    BRIEF = "description from bindings"
    SHORTNAME = "D"


class DTShFlagBindings(DTShFlag):
    """Flag to output bindings of a node or property."""

    BRIEF = "bindings or property specification"
    SHORTNAME = "B"


class DTShFlagYamlFile(DTShFlag):
    """Flag to output the YAML view (with extended includes)."""

    BRIEF = "YAML view of bindings"
    SHORTNAME = "Y"


class DTShBuiltinCat(DTShCommand):
    """Devicetree shell built-in "cat".

    This command can concatenate and output information about a node
    and its properties.

    If the user does not explicitly select what to cat with
    command flags, will output all node property values.

    Otherwise:
    - POSIX-like output: "A" is ignores, will output one of "D", "B", or "Y"
    - rich output: will output selected  "D", "B", and "Y, or all of the if "A"
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
                DTShFlagPager(),
            ],
            DTShParamDTPathX(),
        )

    def execute(self, argv: Sequence[str], sh: DTSh, out: DTShOutput) -> None:
        """Overrides DTShCommand.execute()."""
        super().execute(argv, sh, out)

        param_dtnode: DTNode
        param_dtprops: Optional[List[DTNodeProperty]]
        param_dtnode, param_dtprops = self.with_param(DTShParamDTPathX).xsplit(
            self, sh
        )

        if self.with_flag(DTShFlagPager):
            out.pager_enter()

        # Option "-A" implies "-l".
        with_longfmt = self.with_flag(DTShFlagLongList) or self.with_flag(
            DTShFlagAll
        )

        if param_dtprops:
            if with_longfmt:
                self._cat_dtproperties_rich(param_dtprops, out)
            else:
                self._cat_dtproperties_raw(param_dtprops, out)
        else:
            if with_longfmt:
                self._cat_dtnode_rich(param_dtnode, out)
            else:
                self._cat_dtnode_raw(param_dtnode, out)

        if self.with_flag(DTShFlagPager):
            out.pager_exit()

    def _cat_dtnode_rich(self, node: DTNode, out: DTShOutput) -> None:
        show_all = self.with_flag(DTShFlagAll)
        if not any(
            (
                show_all,
                self.with_flag(DTShFlagDescription),
                self.with_flag(DTShFlagYamlFile),
                self.with_flag(DTShFlagBindings),
            )
        ):
            # If the user hasn't explicitly selected what to cat,
            # just dump all node property values (or does nothing).
            dtprops = node.all_dtproperties()
            if dtprops:
                view = ViewPropertyValueTable(node.all_dtproperties())
                out.write(view)
            return

        # Otherwise, start by collecting selected sections.
        sections: List[HeadingsContentWriter.Section] = []
        if show_all or self.with_flag(DTShFlagDescription):
            sections.append(
                HeadingsContentWriter.Section(
                    "description", 1, ViewDescription(node.description)
                )
            )
        dtprops = node.all_dtproperties()
        if show_all:
            sections.append(
                HeadingsContentWriter.Section(
                    "Properties",
                    1,
                    ViewPropertyValueTable(dtprops)
                    if dtprops
                    else TextUtil.mk_apologies(
                        "This node does not set any property."
                    ),
                )
            )
        if show_all or self.with_flag(DTShFlagBindings):
            sections.append(
                HeadingsContentWriter.Section(
                    "Bindings", 1, ViewNodeBinding(node)
                )
            )
        if show_all or self.with_flag(DTShFlagYamlFile):
            yaml = YAMLFile(node.binding_path or "")
            yamlfs = node.dt.dts.yamlfs
            sections.append(
                HeadingsContentWriter.Section(
                    "YAML",
                    1,
                    ViewYAML(yaml, yamlfs, is_binding=True),
                )
            )

        if len(sections) > 1:
            # If more than one sections, use headings writer.
            hds_writer = HeadingsContentWriter()
            for section in sections:
                hds_writer.write_section(section, out)
        else:
            # Otherwise, just write section's content.
            out.write(sections[0].content)

    def _cat_dtnode_raw(self, node: DTNode, out: DTShOutput) -> None:
        nflags = sum(
            [
                self.with_flag(DTShFlagDescription),
                self.with_flag(DTShFlagYamlFile),
                self.with_flag(DTShFlagBindings),
            ]
        )
        if nflags > 1:
            raise DTShUsageError(
                self, "more than one option among '-DBY' requires '-l'"
            )

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
            self._cat_dtproperties_raw(node.all_dtproperties(), out)

    def _cat_dtproperties_rich(
        self, dtprops: List[DTNodeProperty], out: DTShOutput
    ) -> None:
        if len(dtprops) == 1:
            # Single property: dump value or selected "DBY".
            self._cat_dtproperty_rich(dtprops[0], out)
        elif dtprops:
            # Multiple properties: dump values in table view.
            view = ViewPropertyValueTable(dtprops)
            view.left_indent(1)
            out.write(view)

    def _cat_dtproperty_rich(
        self, dtprop: DTNodeProperty, out: DTShOutput
    ) -> None:
        show_all = self.with_flag(DTShFlagAll)
        if not any(
            (
                show_all,
                self.with_flag(DTShFlagDescription),
                self.with_flag(DTShFlagYamlFile),
                self.with_flag(DTShFlagBindings),
            )
        ):
            # If the user hasn't explicitly selected what to cat,
            # just dump property value.
            view = ViewPropertyValueTable([dtprop])
            out.write(view)
            return

        sections: List[HeadingsContentWriter.Section] = []
        if show_all or self.with_flag(DTShFlagDescription):
            sections.append(
                HeadingsContentWriter.Section(
                    "description", 1, ViewDescription(dtprop.description)
                )
            )
        if show_all or self.with_flag(DTShFlagBindings):
            sections.append(
                HeadingsContentWriter.Section(
                    "specification",
                    1,
                    FormPropertySpec(dtprop.dtspec),
                )
            )
        if show_all or self.with_flag(DTShFlagYamlFile):
            yaml = YAMLFile(dtprop.path or "")
            yamlfs = dtprop.node.dt.dts.yamlfs
            sections.append(
                HeadingsContentWriter.Section(
                    "YAML",
                    1,
                    ViewYAML(yaml, yamlfs, is_binding=True),
                )
            )

        if len(sections) > 1:
            hds_writer = HeadingsContentWriter()
            for section in sections:
                hds_writer.write_section(section, out)
        else:
            out.write(sections[0].content)

    def _cat_dtproperties_raw(
        self, dtprops: List[DTNodeProperty], out: DTShOutput
    ) -> None:
        if len(dtprops) == 1:
            dtprop = dtprops[0]
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
                out.write(DTSUtil.mk_property_value(dtprop))
        else:
            for dtprop in dtprops:
                strval = DTSUtil.mk_property_value(dtprop)
                out.write(f"{dtprop.name}: {strval}")
