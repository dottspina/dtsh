# Copyright (c) 2023 Christophe Dufaza <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Devicetree model helpers.

- Match node with text based criteria (implement DTNodeTextCriterion)
- Match node with integer based criteria (implement DTNodeIntCriterion)
- Sort nodes (implement DTNodeSorter)
- Arbitrary virtual devicetree (DTWalkableComb)

Unit tests and examples: tests/test_dtsh_modelutils.py
"""


from typing import (
    cast,
    Any,
    Union,
    Callable,
    Tuple,
    Set,
    List,
    Optional,
    Sequence,
    Iterator,
    Mapping,
)

import operator
import re
import sys

from dtsh.model import (
    DTWalkable,
    DTNode,
    DTNodeProperty,
    DTNodePHandleData,
    DTNodeSorter,
    DTNodeCriterion,
)


class DTNodeSortByAttr(DTNodeSorter):
    """Base for sorters that weight node attributes."""

    # The name of the dtsh.model.Node attribute this sorter is based on.
    _attname: str

    # Whether we should compare minimums or maximums when the attribute
    # value is a list.
    _reverse: bool = False

    def __init__(self, attname: str) -> None:
        """Initialize sorter.

        Args:
            attname: The Python attribute name.
        """
        self._attname = attname

    def split_sortable_unsortable(
        self, nodes: Sequence[DTNode]
    ) -> Tuple[List[DTNode], List[DTNode]]:
        """Overrides DTNodeSorter.split_sortable_unsortable().

        Returns:
            The tuple of (sortable, unsortable) where unsortable include
            nodes for which :
            - the attribute has no value
            - the attribute value is an empty lists: [] is less than
              any non empty list, which would not match
              the expected semantic (empty lists would appear first)
        """
        sortable = []
        unsortable = []
        for node in nodes:
            attr = getattr(node, self._attname)
            if (attr is not None) and (attr != []):
                sortable.append(node)
            else:
                unsortable.append(node)
        return (sortable, unsortable)

    def gravity(self, node: DTNode) -> Any:
        """Input of the weight function.

        This is typically the value of the attribute this sorter is based on,
        but subclasses may override this method to provide a more precise
        semantic: e.g. a sorter based on the node registers may either
        weight the register addresses or the register sizes.

        Args:
            node: The node to weight.

        Returns:
            The input for the weight function.
        """
        return getattr(node, self._attname)

    def weight(self, node: DTNode) -> Any:
        """Overrides DTNodeSorter.weight().

        The node weight is based on its gravity.

        If the gravity value is a list:

        - in ascending order: we expect to compare minimum,
          so the weight is min(gravity)
        - in descending order: we expect to compare maximum,
          so the weight is max(gravity)

        Returns:
            The node weight.
        """
        w = self.gravity(node)
        if isinstance(w, list):
            w = max(w) if self._reverse else min(w)
        return w

    def sort(
        self, nodes: Sequence[DTNode], reverse: bool = False
    ) -> List[DTNode]:
        """Overrides DTNodeSorter.sort()."""
        # Set the reverse flag that the weight function will rely on.
        self._reverse = reverse
        # Then sort nodes with the base DTNodeSorter implementation.
        return super().sort(nodes, reverse)


class DTNodeSortByPathName(DTNodeSortByAttr):
    """Sort nodes by path name."""

    def __init__(self) -> None:
        super().__init__("path")


class DTNodeSortByNodeName(DTNodeSortByAttr):
    """Sort nodes by node name."""

    def __init__(self) -> None:
        super().__init__("name")


class DTNodeSortByUnitName(DTNodeSortByAttr):
    """Sort nodes by unit-name."""

    def __init__(self) -> None:
        super().__init__("unit_name")


class DTNodeSortByUnitAddr(DTNodeSortByAttr):
    """Sort nodes by unit-address."""

    def __init__(self) -> None:
        super().__init__("unit_addr")


class DTNodeSortByCompatible(DTNodeSortByAttr):
    """Sort nodes by compatible strings."""

    def __init__(self) -> None:
        super().__init__("compatibles")


class DTNodeSortByBinding(DTNodeSortByAttr):
    """Sort nodes by binding (compatible value)."""

    def __init__(self) -> None:
        super().__init__("compatible")


class DTNodeSortByVendor(DTNodeSortByAttr):
    """Sort nodes by vendor name."""

    def __init__(self) -> None:
        super().__init__("vendor")

    def gravity(self, node: DTNode) -> Any:
        """Overrides DTNodeSortByAttrValue.weight().

        Returns:
            The vendor name.
        """
        # At this point, we know the device has a vendor.
        return [node.vendor.name]  # type: ignore


class DTNodeSortByDeviceLabel(DTNodeSortByAttr):
    """Sort nodes by device label."""

    def __init__(self) -> None:
        super().__init__("label")


class DTNodeSortByNodeLabel(DTNodeSortByAttr):
    """Sort nodes by DTS label."""

    def __init__(self) -> None:
        super().__init__("labels")


class DTNodeSortByAlias(DTNodeSortByAttr):
    """Sort nodes by alias."""

    def __init__(self) -> None:
        super().__init__("aliases")


class DTNodeSortByBus(DTNodeSortByAttr):
    """Sort nodes by supported bus protocols."""

    def __init__(self) -> None:
        super().__init__("buses")


class DTNodeSortByOnBus(DTNodeSortByAttr):
    """Sort nodes by bus of appearance."""

    def __init__(self) -> None:
        super().__init__("on_bus")


class DTNodeSortByDepOrdinal(DTNodeSortByAttr):
    """Sort nodes by dependency ordinal."""

    def __init__(self) -> None:
        super().__init__("dep_ordinal")


class DTNodeSortByIrqNumber(DTNodeSortByAttr):
    """Sort nodes by interrupt number."""

    def __init__(self) -> None:
        super().__init__("interrupts")

    def gravity(self, node: DTNode) -> Any:
        """Overrides DTNodeSortByAttrValue.weight().

        Returns:
            The interrupt numbers.
        """
        return [irq.number for irq in node.interrupts]


class DTNodeSortByIrqPriority(DTNodeSortByAttr):
    """Sort nodes by interrupt priority."""

    def __init__(self) -> None:
        super().__init__("interrupts")

    def gravity(self, node: DTNode) -> Any:
        """Overrides DTNodeSortByAttrValue.weight().

        Returns:
            The interrupt priorities.
        """
        return [
            irq.priority if irq.priority is not None else sys.maxsize
            for irq in node.interrupts
        ]


class DTNodeSortByRegAddr(DTNodeSortByAttr):
    """Sort nodes by register address."""

    def __init__(self) -> None:
        super().__init__("registers")

    def gravity(self, node: DTNode) -> Any:
        """Overrides DTNodeSortByAttrValue.weight().

        Returns:
            The register addresses.
        """
        return [reg.address for reg in node.registers]


class DTNodeSortByRegSize(DTNodeSortByAttr):
    """Sort nodes by register size."""

    def __init__(self) -> None:
        super().__init__("registers")

    def gravity(self, node: DTNode) -> Any:
        """Overrides DTNodeSortByAttrValue.weight().

        Returns:
            The register addresses.
        """
        return [reg.size for reg in node.registers]


class DTNodeSortByBindingDepth(DTNodeSortByAttr):
    """Sort nodes by child-binding depth."""

    def __init__(self) -> None:
        super().__init__("binding")

    def gravity(self, node: DTNode) -> Any:
        """Overrides DTNodeSortByAttrValue.weight().

        Returns:
            The interrupt priorities.
        """
        return node.binding.cb_depth if node.binding else None


class DTNodeTextCriterion(DTNodeCriterion):
    """Basis for text-based (pattern) criteria.

    A search pattern is matched to a node aspect that has
    a textual representation.

    This criterion may either match a Regular Expression
    or search for plain text.

    When the pattern is a strict RE, the criterion behaves as a RE-match,
    and any character in the pattern may be interpreted as special character:

    - in particular, "*" will represent a repetition qualifier,
      not a wild-card for any character: e.g. a pattern starting with "*"
      would be an invalid RE because there's nothing to repeat
    - parenthesis will group sub-expressions, as in "(image|storage).*"
    - brackets will mark the beginning ("[") and end ("]") of a character set

    When the pattern is not a strict RE, but contains at least one "*":

    - "*" is actually interpreted as a wild-card and not a repetition qualifier:
      here "*" is a valid expression that actually means "anything"
    - the criterion behaves as a RE-match: "*pattern" means ends with "pattern",
      "pattern*" starts with "pattern", and "*pattern*" contains "pattern"

    If the pattern is not  a strict RE, and does not contain any "*":

    - specials characters won't be interpreted (plain text search)
    - the criterion will behave as a RE-search
    """

    # The PATTERN argument from the command line.
    _pattern: str

    # The RE that implements this criterion.
    _re: re.Pattern[str]

    def __init__(
        self, pattern: str, re_strict: bool = False, ignore_case: bool = False
    ) -> None:
        """Initialize criterion.

        Args:
            pattern: The string pattern.
            re_strict: Whether to assume the pattern us a Regular Expression.
              Default is plain text search with wild-card substitution.
            ignore_case: Whether to ignore case.
              Default is case sensitive search.

        Raises:
            re.error: Malformed regular expression.
        """
        self._pattern = pattern
        if re_strict:
            self._re = self._init_strict_re(pattern, ignore_case)
        else:
            self._re = self._init_plain_text(pattern, ignore_case)

    @property
    def pattern(self) -> str:
        """The pattern string this criterion is built on."""
        return self._pattern

    def match(self, node: DTNode) -> bool:
        """Overrides DTNodeCriterion.match()."""
        return any(
            self._re.match(txt) is not None for txt in self.get_haystack(node)
        )

    def get_haystack(self, node: DTNode) -> Sequence[str]:
        """Get the textual representation of the haystack to search.

        The criterion is always False when the haystack is empty.

        Returns:
            The strings that this pattern may match.
        """
        del node
        return []

    def _init_strict_re(
        self, pattern: str, ignore_case: bool
    ) -> re.Pattern[str]:
        # RE strict mode, use pattern (e.g. from command string) as-is.
        return re.compile(pattern, flags=re.IGNORECASE if ignore_case else 0)

    def _init_plain_text(
        self, pattern: str, ignore_case: bool
    ) -> re.Pattern[str]:
        # Plain text search, escape all.
        pattern = re.escape(pattern)
        if r"\*" in pattern:
            # Convert wild-card to repeated printable.
            pattern = pattern.replace(r"\*", ".*")
            # Ensure starts/ends with semantic.
            pattern = f"^{pattern}$"
        else:
            # Convert RE-match to RE-search.
            pattern = f".*{pattern}.*"

        return re.compile(pattern, flags=re.IGNORECASE if ignore_case else 0)

    def __repr__(self) -> str:
        return self._re.pattern


class DTNodeWithPath(DTNodeTextCriterion):
    """Match path."""

    def get_haystack(self, node: DTNode) -> Sequence[str]:
        """Overrides DTNodeTextCriterion.get_haystack()."""
        return [node.path]


class DTNodeWithStatus(DTNodeTextCriterion):
    """Match status string."""

    def get_haystack(self, node: DTNode) -> Sequence[str]:
        """Overrides DTNodeTextCriterion.get_haystack()."""
        return [node.status]


class DTNodeWithName(DTNodeTextCriterion):
    """Match node name."""

    def get_haystack(self, node: DTNode) -> Sequence[str]:
        """Overrides DTNodeTextCriterion.get_haystack()."""
        return [node.name]


class DTNodeWithUnitName(DTNodeTextCriterion):
    """Match unit-name."""

    def get_haystack(self, node: DTNode) -> Sequence[str]:
        """Overrides DTNodeTextCriterion.get_haystack()."""
        return [node.unit_name]


class DTNodeWithCompatible(DTNodeTextCriterion):
    """Match compatible value."""

    def get_haystack(self, node: DTNode) -> Sequence[str]:
        """Overrides DTNodeTextCriterion.get_haystack()."""
        return node.compatibles


class DTNodeWithBinding(DTNodeTextCriterion):
    """Match binding compatible string.

    If the pattern is "*", will match any node with a binding,
    including bindings without compatible string.
    """

    def match(self, node: DTNode) -> bool:
        """Overrides DTNodeCriterion.match()."""
        if self.pattern == ".*":
            return node.binding is not None
        return super().match(node)

    def get_haystack(self, node: DTNode) -> Sequence[str]:
        """Overrides DTNodeTextCriterion.get_haystack()."""
        if not node.binding:
            return []

        haystack = []
        if node.binding.compatible:
            haystack.append(node.binding.compatible)

        headline = node.binding.get_headline()
        if headline:
            haystack.append(headline)

        return haystack


class DTNodeWithVendor(DTNodeTextCriterion):
    """Match vendor prefix or name."""

    def get_haystack(self, node: DTNode) -> Sequence[str]:
        """Overrides DTNodeTextCriterion.get_haystack()."""
        return [node.vendor.prefix, node.vendor.name] if node.vendor else []


class DTNodeWithDeviceLabel(DTNodeTextCriterion):
    """Match device label."""

    def get_haystack(self, node: DTNode) -> Sequence[str]:
        """Overrides DTNodeTextCriterion.get_haystack()."""
        return [node.label] if node.label else []


class DTNodeWithNodeLabel(DTNodeTextCriterion):
    """Match DTS labels."""

    def get_haystack(self, node: DTNode) -> Sequence[str]:
        """Overrides DTNodeTextCriterion.get_haystack()."""
        return node.labels


class DTNodeWithAlias(DTNodeTextCriterion):
    """Match aliases."""

    def get_haystack(self, node: DTNode) -> Sequence[str]:
        """Overrides DTNodeTextCriterion.get_haystack()."""
        return node.aliases


class DTNodeWithChosen(DTNodeTextCriterion):
    """Match chosen."""

    def get_haystack(self, node: DTNode) -> Sequence[str]:
        """Overrides DTNodeTextCriterion.get_haystack()."""
        return node.chosen


class DTNodeWithBus(DTNodeTextCriterion):
    """Match nodes with supported bus protocols."""

    def get_haystack(self, node: DTNode) -> Sequence[str]:
        """Overrides DTNodeTextCriterion.get_haystack()."""
        return node.buses


class DTNodeWithOnBus(DTNodeTextCriterion):
    """Match nodes with bus of appearance."""

    def get_haystack(self, node: DTNode) -> Sequence[str]:
        """Overrides DTNodeTextCriterion.get_haystack()."""
        return [node.on_bus] if node.on_bus else []


class DTNodeWithDescription(DTNodeTextCriterion):
    """Match node with description line by line."""

    def get_haystack(self, node: DTNode) -> Sequence[str]:
        """Overrides DTNodeTextCriterion.get_haystack()."""
        if not node.description:
            return []
        return node.description.splitlines()


class DTNodeAlsoKnownAs(DTNodeTextCriterion):
    """Match nodes with labels and aliases."""

    def get_haystack(self, node: DTNode) -> Sequence[str]:
        """Overrides DTNodeTextCriterion.get_haystack()."""
        aka = [
            *node.aliases,
            *node.labels,
        ]
        if node.label:
            aka.append(node.label)
        return aka


class DTNodeIntCriterion(DTNodeCriterion):
    """Basis for integer-based (expression) criteria."""

    OPERATORS: Mapping[str, Callable[[int, int], bool]] = {
        "<": operator.lt,
        ">": operator.gt,
        "=": operator.eq,
        ">=": operator.ge,
        "<=": operator.le,
        "!=": operator.ne,
    }

    _operator: Callable[[int, int], bool]
    _int: Optional[int]

    def __init__(
        self,
        criter_op: Optional[Callable[[int, int], bool]],
        criter_int: Optional[int],
    ) -> None:
        """Initialize criterion.

        Args:
            criter_op: The expression operator,
              one of DTNodeIntCriterion.OPERATORS.
              Defaults to equality.
            criter_int: The integer value the criterion expression should match.
              None means any integer value will match.
        """
        self._operator = criter_op or operator.eq
        self._int = criter_int

    def match(self, node: DTNode) -> bool:
        """Overrides DTNodeCriterion.match()."""
        return any(
            ((self._int is None) or self._operator(hay, self._int))
            for hay in self.get_haystack(node)
        )

    def get_haystack(self, node: DTNode) -> Sequence[int]:
        """Get the integer representation of the haystack to search.

        The criterion is always False when the haystack is empty.

        Returns:
            The integers that this expression may match.
        """
        del node
        return []


class DTNodeWithUnitAddr(DTNodeIntCriterion):
    """Match unit-address."""

    def get_haystack(self, node: DTNode) -> Sequence[int]:
        """Overrides DTNodeIntCriterion.get_haystack()."""
        return [node.unit_addr] if node.unit_addr is not None else []


class DTNodeWithIrqNumber(DTNodeIntCriterion):
    """Match IRQ number."""

    def get_haystack(self, node: DTNode) -> Sequence[int]:
        """Overrides DTNodeIntCriterion.get_haystack()."""
        return [irq.number for irq in node.interrupts]


class DTNodeWithIrqPriority(DTNodeIntCriterion):
    """Match IRQ priority."""

    def get_haystack(self, node: DTNode) -> Sequence[int]:
        """Overrides DTNodeIntCriterion.get_haystack()."""
        return [
            irq.priority for irq in node.interrupts if irq.priority is not None
        ]


class DTNodeWithRegAddr(DTNodeIntCriterion):
    """Match register address."""

    def get_haystack(self, node: DTNode) -> Sequence[int]:
        """Overrides DTNodeIntCriterion.get_haystack()."""
        return [reg.address for reg in node.registers]


class DTNodeWithRegSize(DTNodeIntCriterion):
    """Match register size."""

    def get_haystack(self, node: DTNode) -> Sequence[int]:
        """Overrides DTNodeIntCriterion.get_haystack()."""
        return [reg.size for reg in node.registers]


class DTNodeWithBindingDepth(DTNodeIntCriterion):
    """Match child-binding depth."""

    def get_haystack(self, node: DTNode) -> Sequence[int]:
        """Overrides DTNodeIntCriterion.get_haystack()."""
        return [node.binding.cb_depth] if node.binding else []


class DTNodeWithDepOrd(DTNodeIntCriterion):
    """Match dependency ordinal (aka DTS order)."""

    def get_haystack(self, node: DTNode) -> Sequence[int]:
        """Overrides DTNodeIntCriterion.get_haystack()."""
        return [node.dep_ordinal]


class DTWalkableComb(DTWalkable):
    """Walk an arbitrary subset of a devicetree.

    Permits to define a virtual devicetree as the minimal graph
    that will contain the paths from a given root to a selected
    set of leaves.

    The comb is the set of nodes this graph includes.
    """

    _root: DTNode
    _comb: Set[DTNode]

    def __init__(self, root: DTNode, leaves: Sequence[DTNode]) -> None:
        """Initialize the virtual devicetree.

        Args:
            root: Set the root node from where we'll later on
              walk the virtual devicetree.
            leaves: The leaf nodes of the virtual devicetree.
        """
        self._root = root
        self._comb: Set[DTNode] = set()
        for leaf in leaves:
            self._comb.update(list(leaf.rwalk()))

    @property
    def comb(self) -> Set[DTNode]:
        """All the nodes required to represent this virtual devicetree."""
        return self._comb

    def walk(
        self,
        /,
        order_by: Optional[DTNodeSorter] = None,
        reverse: bool = False,
        enabled_only: bool = False,
        fixed_depth: int = 0,
    ) -> Iterator[DTNode]:
        """Walk from the predefined root node through to all leaves.

        Overrides DTWalkable.walk().

        Args:
            enabled_only: Ignored, will always walk through to its leaves.
            fixed_depth: Ignored, will always walk through to its leaves.
        """
        return self._walk(self._root, order_by=order_by, reverse=reverse)

    def _walk(
        self,
        branch: Optional[DTNode] = None,
        /,
        order_by: Optional[DTNodeSorter] = None,
        reverse: bool = False,
    ) -> Iterator[DTNode]:
        if branch in self._comb:
            yield branch
            children = branch.children
            if children:
                if order_by:
                    children = order_by.sort(children, reverse=reverse)
                elif reverse:
                    # Reverse DTS-order.
                    children = list(reversed(children))
                for child in children:
                    yield from self._walk(
                        child, order_by=order_by, reverse=reverse
                    )


class DTSUtil:
    """Factory for string representations of DTS types."""

    @classmethod
    def mk_property_value(cls, prop: DTNodeProperty) -> str:
        """Make a string representation of a property value that resembles
        its DTS format.

        Args:
            prop: The DT property.

        Returns:
            The property value as it could appear in the DTS:
            - DT type "bool": true or false
            - DT type "int": e.g. < 0x01 >
            - DT type "array": e.g. < 0x2f >, < 0x01 >
            - DT type "string": e.g. "str"
            - DT type "string-array": e.g. "str1", "str2"
            - DT type "uint8-array": e.g. [ C2 28 17 ]
            - DT type "phandle": e.g. < &spi3_sleep >
            - DT type "phandles": e.g. < &spi3_sleep &spi3_default >
            - DT type "phandle-array": e.g. < &ctrl-1 0x01 0x02 >, < &ctrl-2 0x01 0x02 >
        """
        value: DTNodeProperty.ValueType = prop.value

        if isinstance(value, list):
            val0: Union[int, str, DTNode, DTNodePHandleData, None] = value[0]

            if isinstance(val0, int):
                # DTS "type: array".
                int_array: List[int] = cast(List[int], value)
                return cls.mk_array(int_array)

            if isinstance(val0, str):
                # DTS "type: string-array".
                str_array: List[str] = cast(List[str], value)
                return cls.mk_string_array(str_array)

            if isinstance(val0, DTNode):
                # DTS "type: phandles".
                phandles: List[DTNode] = cast(List[DTNode], value)
                return cls.mk_phandles(phandles)

            if isinstance(val0, DTNodePHandleData):
                # DTS "type: phandle-array".
                phandle_array: List[DTNodePHandleData] = cast(
                    List[DTNodePHandleData], value
                )
                return cls.mk_phandle_array(phandle_array)

        if isinstance(value, bool):
            # DTS "type: boolean".
            return cls.mk_boolean(value)
        if isinstance(value, int):
            # DTS "type: int".
            return cls.mk_int(value, as_cell=True)
        if isinstance(value, str):
            # DTS "type: string".
            return cls.mk_string(value)
        if isinstance(value, bytes):
            # DTS "type: uint8-array".
            return cls.mk_bytes(value)
        if isinstance(value, DTNode):
            # DTS "type: phandle".
            return cls.mk_phandle(value)

        # Answer empty string for properties with None value,
        # e.g. the "ranges" property of the /soc node, of type "compound".
        return ""

    @classmethod
    def mk_boolean(cls, value: bool) -> str:
        """Make DTS-like output for values of type "boolean".

        Args:
            value: The DT value.

        Returns:
            "true" or "false".
        """
        return str(value).lower()

    @classmethod
    def mk_int(cls, value: int, as_cell: bool) -> str:
        """Make DTS-like output for values of type "int".

        Args:
            value: The DT value.
            as_cell: Whether to put the value in a "<>" cell.

        Returns:
            An integer cell, e.g. "< 0x01 >"
        """
        # We'll format hex according to the required number of bytes.
        nbytes = 0
        x = value
        while x:
            x >>= 8
            nbytes += 1
        nbytes = nbytes or 1

        fmt = f"0x{{:0{2*nbytes}x}}"
        strval = fmt.format(value)

        if as_cell:
            strval = cls._mk_cell(strval)
        return strval

    @classmethod
    def mk_string(cls, value: str) -> str:
        """Make DTS-like output for values of type "string".

        Args:
            value: The DT value.

        Returns:
            A quoted string.
        """
        return f'"{value}"'

    @classmethod
    def mk_bytes(cls, value: bytes) -> str:
        """Make DTS-like output for values of type "uint8-array".

        Args:
            value: The DT value.

        Returns:
            An array of un-prefixed uppercase bytes, e.g. "[ C2 28 17 ]".
        """
        strbytes = " ".join(f"{b:02X}" for b in value)
        return f"[ {strbytes} ]"

    @classmethod
    def mk_phandle(cls, node: DTNode, as_cell: bool = True) -> str:
        """Make DTS-like output for values of type "phandle".

        Args:
            node: The DT value.
            as_cell: Whether to put the value in a "<>" cell.

        Returns:
            By default, a cell containing the handle, e.g. "< &spi3_sleep >".
        """
        # These usually have at least one DTS label.
        if node.labels:
            strhandle = f"&{node.labels[0]}"
        else:
            # Fallback to node's path.
            strhandle = node.path

        if as_cell:
            strhandle = cls._mk_cell(strhandle)
        return strhandle

    @classmethod
    def mk_array(cls, int_arr: List[int], as_cell: bool = True) -> str:
        """Make DTS-like output for values of type "array".

        Args:
            int_arr: The DT value.
            as_cell: Whether to put the array in a single "<>" cell instead
              of a comma separated list.

        Returns:
            A comma separated list of integer cells, e.g. "< 0x2f >, < 0x01 >"
            or the array as a single cell e.g. "< 0x2f 0x01 >".
        """
        if as_cell:
            # Array as single cell.
            strval = " ".join(cls.mk_int(val, as_cell=False) for val in int_arr)
            return cls._mk_cell(strval)

        # Comma separated list.
        return ", ".join(cls.mk_int(val, as_cell=True) for val in int_arr)

    @classmethod
    def mk_string_array(cls, str_arr: List[str]) -> str:
        """Make DTS-like output for values of type "string-array".

        Args:
            str_arr: The DT value.

        Returns:
            A comma separated list of quoted strings.
        """
        return ", ".join(cls.mk_string(val) for val in str_arr)

    @classmethod
    def mk_phandles(cls, phandles: List[DTNode]) -> str:
        """Make DTS-like output for values of type "phandles".

        Args:
            phandles: The DT value.

        Returns:
            A cell containing one or more phandles, e.g. "< &ctrl-1 &ctrl-2 >".
        """
        strval = " ".join(
            cls.mk_phandle(node, as_cell=False) for node in phandles
        )
        return cls._mk_cell(strval)

    @classmethod
    def mk_phandle_array(cls, phandle_array: List[DTNodePHandleData]) -> str:
        """Make DTS-like output for values of type "phandle-array".

        Args:
            phandle_array: The DT value.

        Returns:
            A comma separated list of phandle-array entries.
        """
        phdata_entries = [
            cls.mk_phandle_and_data(entry, as_cell=True)
            for entry in phandle_array
        ]
        return ", ".join(phdata_entries)

    @classmethod
    def mk_phandle_and_data(
        cls, phdata: DTNodePHandleData, as_cell: bool = True
    ) -> str:
        """Make DTS-like output for entries in a "phandle-array".

        Args:
            phdata: The DT value.

        Returns:
            By default, a cell containing the PHandle and its data,
            e.g. < &ctrl-1 0x01 0x10 >.
            Non-integer data values are converted to their default
            string representation.
        """
        data_values: List[str] = [
            cls.mk_int(data, as_cell=False)
            if isinstance(data, int)
            else str(data)
            for data in phdata.data.values()
        ]

        str_data = " ".join(val for val in data_values)
        str_phandle = cls.mk_phandle(phdata.phandle, as_cell=False)
        strval = f"{str_phandle} {str_data}"

        if as_cell:
            strval = cls._mk_cell(strval)
        return strval

    @classmethod
    def _mk_cell(cls, content: str) -> str:
        return f"< {content} >"
