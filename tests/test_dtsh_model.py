# Copyright (c) 2023 Christophe Dufaza <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the dtsh.model module."""

# Relax pylint a bit for unit tests.
# pylint: disable=protected-access
# pylint: disable=pointless-statement
# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=too-many-statements

import os
import sys
from collections.abc import Sequence
from typing import Any

import pytest

from dtsh.model import (
    DTNode,
    DTNodeCriteria,
    DTNodeCriterion,
    DTNodeInterrupt,
    DTNodeRegister,
    DTNodeSorter,
    DTPath,
    DTVendor,
)

from .dtsh_uthelpers import DTShTests


def test_dtpath_split() -> None:
    assert DTPath.split("a") == ["a"]
    assert DTPath.split("a/b/c") == ["a", "b", "c"]
    # "/" always represent the first node name of a path name.
    assert DTPath.split("/") == ["/"]
    assert DTPath.split("/x") == ["/", "x"]
    assert DTPath.split("/x/y/z") == ["/", "x", "y", "z"]
    # Removed trailing empty node name.
    assert DTPath.split("/a/") == ["/", "a"]
    assert DTPath.split("") == []


def test_dtpath_join() -> None:
    assert DTPath.join("/", "a", "b") == "/a/b"
    assert DTPath.join("/a", "b") == "/a/b"
    assert DTPath.join("a/", "b") == "a/b"
    # Path is NOT normalized.
    assert DTPath.join("a", ".") == "a/."
    assert DTPath.join("a", "b/") == "a/b/"
    assert DTPath.join("a", "") == "a/"
    # Joining an absolute path will reset the join chain.
    assert DTPath.join("/a", "b", "/x", "y") == "/x/y"


def test_dtpath_normpath() -> None:
    # Remove redundant trailing ".".
    assert DTPath.normpath("/.") == "/"
    # Remove redundant "/".
    assert DTPath.normpath("a/b/") == "a/b"
    assert DTPath.normpath("a//b") == "a/b"
    # Remove redundant "." and "..".
    assert DTPath.normpath("a/foo/../b") == "a/b"
    assert DTPath.normpath("a/./b") == "a/b"
    # Root is its own parent.
    assert DTPath.normpath("/../a") == "/a"
    # Normalize empty paths.
    assert DTPath.normpath("") == "."


def test_dtpath_abspath() -> None:
    assert DTPath.abspath("") == "/"
    assert DTPath.abspath("/") == "/"
    assert DTPath.abspath("a") == "/a"
    assert DTPath.abspath("a/b") == "/a/b"
    # Path is normalized.
    assert DTPath.abspath("a/.") == "/a"
    assert DTPath.abspath("../a") == "/a"
    # Joined path starting with "/" will reset the join chain to itself.
    assert DTPath.abspath("a", "/foo") == "/foo/a"
    # Preserve absolute paths regardless of the "current working node".
    assert DTPath.abspath("/a/b", "/x") == "/a/b"

    with pytest.raises(ValueError):
        # Current working branch must be represented by an absolute path.
        DTPath.abspath("a", "relative/path")


def test_dtpath_relpath() -> None:
    # Relative paths from "/".
    assert DTPath.relpath("/") == "."
    assert DTPath.relpath("/a") == "a"
    # Relative paths from "/a".
    assert DTPath.relpath("/a", "/a") == "."
    assert DTPath.relpath("/a/b/c", "/a") == "b/c"

    with pytest.raises(ValueError):
        # Expect absolute path parameter..
        DTPath.relpath("a/b")
    with pytest.raises(ValueError):
        # Current working branch must be represented by an absolute path.
        DTPath.relpath("/a/b", "relative/path")


def test_dtpath_dirname() -> None:
    assert DTPath.dirname("/a") == "/"
    assert DTPath.dirname("/a/b/c") == "/a/b"
    assert DTPath.dirname("a/b") == "a"
    # The root node is its own parent.
    assert DTPath.dirname("/") == "/"
    # A trailing '/' is interpreted as an empty trailing node name.
    assert DTPath.dirname("./") == "."
    assert DTPath.dirname("/a/") == "/a"
    # Returns "." when path does not contain any "/".
    assert DTPath.dirname("") == "."
    assert DTPath.dirname("a") == "."
    assert DTPath.dirname(".") == "."
    assert DTPath.dirname("..") == "."


def test_dtpath_basename() -> None:
    assert DTPath.basename("/a") == "a"
    assert DTPath.basename("a") == "a"
    assert DTPath.basename("a/b") == "b"
    assert DTPath.basename("/a/b") == "b"
    assert DTPath.basename("/*") == "*"
    assert DTPath.basename("a/b*") == "b*"
    # A trailing '/' is interpreted as an empty trailing node name.
    assert DTPath.basename("/") == ""
    assert DTPath.basename("a/") == ""
    # By convention.
    assert DTPath.basename("") == ""
    assert DTPath.basename(".") == "."
    assert DTPath.basename("..") == ".."


def test_dtvendor() -> None:
    vendor = DTVendor("prefix", "vendor")
    assert vendor.prefix == "prefix"
    assert vendor.name == "vendor"

    # Only the prefix is relevant for identity and equality.
    assert len({vendor, DTVendor("prefix", "")}) == 1
    assert len({vendor, DTVendor("other", "")}) == 2
    assert DTVendor("prefix", "") == vendor
    assert vendor != DTVendor("other", "")

    # Order relationship is also by prefix.
    assert vendor < DTVendor("z", "")
    with pytest.raises(TypeError):
        vendor < ""


def test_dtbinding() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    dt_partitions = dtmodel["/soc/flash-controller@4001e000/flash@0/partitions"]
    dt_partition0 = dt_partitions.get_child("partition@0")
    dt_partition1 = dt_partitions.get_child("partition@c000")
    dt_bme680 = dtmodel["/soc/i2c@40003000/bme680@76"]

    assert not dt_partitions.binding
    assert dt_partition0.binding
    assert dt_partition0.binding.cb_depth == 0
    assert dt_partition0.binding.compatible == "zephyr,mapped-partition"
    assert dt_partition1.binding
    assert dt_partition1.binding.cb_depth == 0
    assert dt_partition1.binding.compatible == "zephyr,mapped-partition"

    assert dt_bme680.binding
    assert dt_bme680.binding.cb_depth == 0
    assert dt_bme680.binding.compatible == "bosch,bme680"

    # Identity.
    # Nodes "partition@0" and "partition@c000" are specified by the same
    # child-binding of "partitions".
    assert len({dt_partition0.binding, dt_partition1.binding}) == 1
    # Bindings for "partition@0" and "partitions" are defined in the same
    # YAML file, but the former is a child-binding of the later.
    assert len({dt_partitions.binding, dt_partition0.binding}) == 2
    # Then ,obviously.
    assert len({dt_partitions.binding, dt_partition0.binding, dt_bme680.binding}) == 3

    assert dtmodel.get_compatible_binding("bosch,bme680", "i2c") is dt_bme680.binding
    assert dtmodel.get_compatible_binding("fixed-partitions") is dt_partitions.binding

    # Equality
    assert dt_partition0.binding == dt_partition0.binding
    assert dt_partition1.binding == dt_partition0.binding
    assert dt_bme680.binding != dt_partition0.binding

    # Default order.
    assert dt_bme680.binding < dt_partition0.binding
    with pytest.raises(TypeError):
        dt_partition0.binding < ""


def test_dtbinding_buses() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    dt_i2c = dtmodel["/soc/i2c@40003000"]
    dt_bme680_i2c = dt_i2c.get_child("bme680@76")
    dt_spi = dtmodel["/soc/spi@40004000"]
    dt_bme680_spi = dt_spi.get_child("bme680@0")

    assert dt_i2c.binding
    assert dt_spi.binding
    assert dt_bme680_i2c.binding
    assert dt_bme680_spi.binding
    assert dt_i2c.binding.buses == ["i2c"]
    assert dt_spi.binding.buses == ["spi"]

    assert dt_bme680_i2c.binding.on_bus == "i2c"
    assert os.path.basename(dt_bme680_i2c.binding.path) == "bosch,bme680-i2c.yaml"
    assert not dt_bme680_i2c.binding.buses

    assert dt_bme680_spi.binding.on_bus == "spi"
    assert os.path.basename(dt_bme680_spi.binding.path) == "bosch,bme680-spi.yaml"
    assert not dt_bme680_spi.binding.buses


def test_dtbinding_includes() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    dt_bme680 = dtmodel["/soc/i2c@40003000/bme680@76"]
    assert dt_bme680.binding

    assert sorted(["sensor-device.yaml", "i2c-device.yaml"]) == sorted(
        [os.path.basename(path) for path in dt_bme680.binding.includes]
    )


def test_dtbinding_child_binding() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    dt_leds = dtmodel["/leds"]
    dt_led0 = dt_leds.get_child("led_0")
    dt_led1 = dt_leds.get_child("led_1")
    assert dt_leds.binding
    assert dt_leds.binding.cb_depth == 0
    assert dt_leds.binding.child_binding

    assert dt_led0.binding
    assert dt_led0.binding.cb_depth == 1
    assert not dt_led0.binding.child_binding
    assert dt_led0.binding == dt_leds.binding.child_binding

    assert dt_led1.binding
    assert dt_led1.binding.cb_depth == 1
    assert not dt_led1.binding.child_binding
    assert dt_led1.binding == dt_leds.binding.child_binding


def test_dtinterrupt() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    dt_i2c0 = dtmodel["/soc/i2c@40003000"]
    edtirq_i2c0 = dt_i2c0._edtnode.interrupts[0]
    dt_gpiote = dtmodel["/soc/gpiote@40006000"]
    edtirq_gpiote = dt_gpiote._edtnode.interrupts[0]

    irq_i2c0 = DTNodeInterrupt(edtirq_i2c0, dt_i2c0)
    assert irq_i2c0.number == 3
    assert irq_i2c0.priority == 1
    assert irq_i2c0.name == "IRQ_i2c0"
    assert dt_i2c0 == irq_i2c0.emitter
    assert irq_i2c0.controller is dtmodel[edtirq_i2c0.controller.path]

    irq_gpiote = DTNodeInterrupt(edtirq_gpiote, dt_gpiote)
    assert irq_gpiote.number == 6
    assert irq_gpiote.priority == 5
    assert dt_gpiote == irq_gpiote.emitter
    assert irq_gpiote.controller is dtmodel[edtirq_gpiote.controller.path]

    # Identity.
    assert len({irq_i2c0, DTNodeInterrupt(edtirq_i2c0, dt_i2c0)}) == 1
    assert len({irq_i2c0, DTNodeInterrupt(edtirq_gpiote, dt_gpiote)}) == 2

    # Equality.
    assert DTNodeInterrupt(edtirq_i2c0, dt_i2c0) == irq_i2c0
    assert DTNodeInterrupt(edtirq_gpiote, dt_gpiote) == irq_gpiote
    assert irq_gpiote != irq_i2c0

    # Default order.
    assert irq_i2c0 < irq_gpiote
    with pytest.raises(TypeError):
        irq_i2c0 < ""


def test_dtregister() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    dt_qspi = dtmodel["/soc/qspi@40029000"]
    edtreg_qspi = dt_qspi._edtnode.regs[0]

    reg_qspi = DTNodeRegister(edtreg_qspi)
    assert reg_qspi.address == 0x40029000
    assert reg_qspi.size == 0x1000
    assert reg_qspi.address + reg_qspi.size - 1 == reg_qspi.tail
    assert reg_qspi.name == "qspi"

    edtreg_bme680 = dtmodel["/soc/i2c@40003000/bme680@76"]._edtnode.regs[0]
    reg_bme680 = DTNodeRegister(edtreg_bme680)
    assert reg_bme680.address == 0x76
    assert reg_bme680.size == 0
    assert reg_bme680.address == reg_bme680.tail

    # Neither identity nor equality.
    assert len({reg_qspi, DTNodeRegister(edtreg_qspi)}) == 2
    assert DTNodeRegister(edtreg_qspi) != reg_qspi

    # Default order.
    # Meaningless, but 0x76 < 0x40029000 nonetheless
    assert reg_bme680 < reg_qspi
    with pytest.raises(TypeError):
        reg_bme680 < ""


def test_dtnode() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    edt = dtmodel._edt

    # Identity.
    assert len({dtmodel["/soc"], dtmodel["/soc"]}) == 1
    assert len({dtmodel["/soc"], dtmodel["/cpus"]}) == 2

    # Equality.
    assert dtmodel["/soc"] == dtmodel["/soc"]
    assert dtmodel["/soc"] != dtmodel["/cpus"]

    # Default order.
    assert dtmodel["/cpus"] < dtmodel["/soc"]

    # Test some known values.
    dt_button0 = dtmodel["/buttons/button_0"]
    assert dt_button0.label == "Push button switch 0"
    assert dt_button0.labels == ["button0"]
    assert edt.get_node(dt_button0.path).description
    assert edt.get_node(dt_button0.path).description == dt_button0.description
    assert sorted(["led0", "mcuboot-led0"]) == sorted(dtmodel["/leds/led_0"].aliases)
    assert dtmodel["/soc/random@4000d000"].chosen == ["zephyr,entropy"]
    assert DTVendor("nordic", "Nordic Semiconductor") == dtmodel["/soc/egu@40014000"].vendor
    assert dtmodel["/soc/i2c@40003000/bme680@76"].on_bus == "i2c"


def test_dtnodes() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    edt = dtmodel._edt

    for node in dtmodel.walk():
        edtnode = edt.get_node(node.path)
        assert edtnode == node._edtnode
        assert edtnode.path == node.path
        assert edtnode.name == node.name
        assert edtnode.unit_addr == node.unit_addr
        assert edtnode.status == node.status
        assert (edtnode.status == "okay") == node.enabled
        assert edtnode.label == node.label
        assert edtnode.aliases == node.aliases
        assert edtnode.labels == node.labels
        assert edtnode.compats == node.compatibles
        assert edtnode.matching_compat == node.compatible
        assert edtnode.binding_path == node.binding_path
        assert edtnode.dep_ordinal == node.dep_ordinal
        assert node.buses == edtnode.buses
        assert (edtnode._binding.on_bus if edtnode._binding else None) == node.on_bus

        if node.binding:
            assert node.binding.path == edtnode.binding_path
            assert node.binding.compatible == edtnode.matching_compat

        assert [child.path for child in node.children] == [
            child.path for _, child in edtnode.children.items()
        ]

        assert sorted([req.path for req in edtnode.required_by]) == sorted(
            [req.path for req in node.required_by]
        )
        assert sorted([req.path for req in edtnode.depends_on]) == sorted(
            [req.path for req in node.depends_on]
        )

        if edtnode.parent:
            assert node.parent._edtnode.path == edtnode.parent.path
        else:
            assert edtnode.path == "/"
            # dtsh: root is its own parent
            assert dtmodel.root == node
            assert dtmodel.root == node.parent


def test_dtnode_binding() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()

    # Binding for compatible value.
    dt_partition0 = dtmodel["/soc/flash-controller@4001e000/flash@0/partitions/partition@0"]
    assert dt_partition0.binding
    assert dt_partition0.binding.compatible == "zephyr,mapped-partition"

    # Child-binding without compatible value.
    dt_leds = dtmodel["/leds"]
    assert dt_leds.binding
    dt_led0 = dt_leds.get_child("led_0")
    assert dt_led0.binding
    assert not dt_led0.binding.compatible
    assert dt_leds.binding.child_binding == dt_led0.binding

    # Node without binding (e.g. "/", "/chosen", "/aliases", "/soc", "/cpus").
    assert not dtmodel["/soc"].binding


def test_dtnode_get_child() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    assert dtmodel.root.get_child("soc")
    assert dtmodel["/soc"].get_child("random@4000d000")

    with pytest.raises(KeyError):
        dtmodel.root.get_child("notachild")


def test_dtnode_vendor() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    dt_bme680 = dtmodel["/soc/i2c@40003000/bme680@76"]
    # Only vendor prefixes are relevant.
    assert DTVendor("bosch", "") == dt_bme680.vendor
    # Only the manufacturer is relevant.
    assert dtmodel.get_vendor("bosch,any") == dt_bme680.vendor


def test_dtnode_buses() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    dt_i2c = dtmodel["/soc/i2c@40003000"]
    dt_bme680_i2c = dt_i2c.get_child("bme680@76")
    dt_spi = dtmodel["/soc/spi@40004000"]
    dt_bme680_spi = dt_spi.get_child("bme680@0")

    assert dt_i2c.buses == ["i2c"]
    assert dt_spi.buses == ["spi"]

    assert dt_bme680_i2c.on_bus == "i2c"
    assert dt_i2c == dt_bme680_i2c.on_bus_device

    assert dt_bme680_spi.on_bus == "spi"
    assert dt_spi == dt_bme680_spi.on_bus_device


def test_dtnode_registers() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    dt_qspi = dtmodel["/soc/qspi@40029000"]
    reg_qspi = dt_qspi.registers[0]

    assert reg_qspi.address == 0x40029000
    assert reg_qspi.size == 0x1000
    assert reg_qspi.address + reg_qspi.size - 1 == reg_qspi.tail
    assert reg_qspi.name == "qspi"


def test_dtnode_walk() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    edt = dtmodel._edt

    # All nodes.
    assert len(edt.nodes) == len(list(dtmodel.root.walk())) == dtmodel.size
    # Enabled nodes.
    assert len([node for node in edt.nodes if node.status == "okay"]) == len(
        list(dtmodel.root.walk(enabled_only=True))
    )

    # flash-controller@4001e000
    # └── flash@0
    #   └── partitions
    #       ├── partitions/partition@0
    #       ├── partitions/partition@c000
    #       ├── partitions/partition@82000
    #       └── partitions/partition@f8000
    dt_flash_ctrl = dtmodel["/soc/flash-controller@4001e000"]
    assert [node.name for node in dt_flash_ctrl.walk()] == [
        "flash-controller@4001e000",
        "flash@0",
        "partitions",
        "partition@0",
        "partition@c000",
        "partition@82000",
        "partition@f8000",
    ]

    # Child nodes in reverse order.
    assert [node.name for node in dt_flash_ctrl.walk(reverse=True)] == [
        "flash-controller@4001e000",
        "flash@0",
        "partitions",
        "partition@f8000",
        "partition@82000",
        "partition@c000",
        "partition@0",
    ]

    # Fixed depth.
    assert [node.name for node in dt_flash_ctrl.walk(fixed_depth=2)] == [
        "flash-controller@4001e000",
        "flash@0",
        "partitions",
    ]


def test_dtnode_walk_order_by() -> None:
    dtmodel = DTShTests.get_sample_dtmodel(force_reload=True)
    edt = dtmodel._edt

    # Save initial children ordering (DTS order)
    unsorted = list(node for node in dtmodel.root.walk())

    # Walk the whole devicetree, sorting children by path name.
    natural_order = DTNodeSorter()
    assert sorted([edtnode.path for edtnode in edt.nodes]) == [
        node.path for node in dtmodel.root.walk(order_by=natural_order)
    ]

    # Assert we didn't mess with children ordering in the model.
    assert unsorted == list(node for node in dtmodel.root.walk())


def test_dtnode_rwalk() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    dt_partitions = dtmodel["/soc/flash-controller@4001e000/flash@0/partitions"]
    dt_partition0 = dt_partitions.get_child("partition@0")

    assert list(
        reversed(
            [
                "/",
                "soc",
                "flash-controller@4001e000",
                "flash@0",
                "partitions",
                "partition@0",
            ]
        )
    ) == [node.name for node in dt_partition0.rwalk()]


def test_dtnode_find() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()

    class FindPwmNodes(DTNodeCriterion):
        def match(self, node: DTNode) -> bool:
            return node.name.find("pwm") != -1

    assert [node.name for node in dtmodel if node.name.find("pwm") != -1] == [
        node.name for node in dtmodel.root.find(FindPwmNodes())
    ]

    assert sorted([node.path for node in dtmodel if node.name.find("pwm") != -1]) == [
        node.path for node in dtmodel.root.find(FindPwmNodes(), order_by=DTNodeSorter())
    ]

    # An empty criterion list should match all nodes, like in POSIX find.
    assert dtmodel.size == len(dtmodel.root.find(DTNodeCriteria()))


def test_dtmodel_init() -> None:
    dtmodel = DTShTests.get_sample_dtmodel(force_reload=True)
    edt = dtmodel._edt

    assert edt.dts_path == dtmodel.dts.path
    assert dtmodel.root.name == "/"
    assert dtmodel.root.unit_name == "/"
    assert len(edt.nodes) == dtmodel.size == len(dtmodel)
    assert edt.bindings_dirs == dtmodel.dts.bindings_search_path
    # By convention, root is its own parent.
    assert dtmodel.root.parent is dtmodel.root

    # edtlib.EDT -> DTModel isomorphic ?
    N = 0
    for node in dtmodel.root.walk():
        N += 1
        edtnode = edt.get_node(node.path)
        assert node._edtnode is edtnode

        binding = node.binding
        if binding:
            edtbinding = edtnode._binding

            if binding.compatible:
                assert binding._edtbinding is edtbinding
                assert node.compatible == binding.compatible
                assert edtnode.matching_compat == binding.compatible
                assert binding == dtmodel.get_compatible_binding(binding.compatible, node.on_bus)
            else:
                assert not edtnode.matching_compat
                # This SHOULD be a child-binding without compat string.
                assert edtnode.parent
                assert edtnode.parent._binding
                assert edtnode.parent._binding.child_binding is edtbinding
                assert binding.cb_depth > 0
                assert not node.compatible
                assert node.parent.binding
                assert binding == node.parent.binding.child_binding

            if binding.child_binding:
                assert binding.child_binding
                assert binding.child_binding.cb_depth > 0
                for child in node.children:
                    assert binding.child_binding == child.binding

        if node.on_bus:
            assert node.binding
            assert node.on_bus == node.binding.on_bus
            assert node._edtnode.on_buses

        if node.buses:
            assert node.binding
            assert node.buses == node.binding.buses
            assert len(node._edtnode.buses) == len(node.buses)

        for irq in node.interrupts:
            # EDT model hypothesis.
            assert irq.number != sys.maxsize
            assert irq.priority != sys.maxsize

        for reg in edtnode.regs:
            # EDT model hypothesis.
            assert reg.addr is not None

        assert len(node._edtnode.interrupts) == len(node.interrupts)
        assert len(node._edtnode.regs) == len(node.registers)

        # Preserve children order.
        assert [edt_child.path for edt_child in node._edtnode.children.values()] == [
            child.path for child in node.children
        ]

        if node.path == "/":
            # Consume EDT root node: contrary to dtsh (and according to DTSpec),
            # EDT does not assume root is its own parent.
            continue
        assert node.parent._edtnode is edt.get_node(node.path).parent

    assert dtmodel.size == N


def test_dtmodel_aliased_nodes() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    edt = dtmodel._edt

    assert [(alias, edtnode.path) for (alias, edtnode) in edt._dt.alias2node.items()] == [
        (alias, node.path) for alias, node in dtmodel.aliased_nodes.items()
    ]

    with pytest.raises(KeyError):
        dtmodel.aliased_nodes["notanalias"]


def test_dtmodel_chosen_nodes() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    edt = dtmodel._edt

    assert [(chosen, edtnode.path) for (chosen, edtnode) in edt.chosen_nodes.items()] == [
        (chosen, node.path) for chosen, node in dtmodel.chosen_nodes.items()
    ]

    with pytest.raises(KeyError):
        dtmodel.chosen_nodes["notachosen"]


def test_dtmodel_labeled_nodes() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    edt = dtmodel._edt

    labeled_nodes: list[tuple[str, DTNode]] = []
    for edtnode, labels in [(node_, node_.labels) for node_ in edt.nodes]:
        labeled_nodes.extend((label, dtmodel[edtnode.path]) for label in labels)

    assert labeled_nodes == list(dtmodel.labeled_nodes.items())

    with pytest.raises(KeyError):
        dtmodel.labeled_nodes["notalabel"]


def test_dtmodel_bus_protocols() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    edt = dtmodel._edt

    buses: set[str] = set()
    for edtnode in edt.nodes:
        buses.update(edtnode.buses)
    assert buses == set(dtmodel.bus_protocols)


def test_dtmodel_compatible_strings() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    edt = dtmodel._edt
    assert list(edt.compat2nodes.keys()) == dtmodel.compatible_strings


def test_dtmodel_vendors() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    edt = dtmodel._edt

    unique_vendors = set(edt.compat2vendor.values())
    assert len(unique_vendors) == len(dtmodel.vendors)
    assert sorted(unique_vendors) == sorted([vendor.name for vendor in dtmodel.vendors])


def test_dtmodel_get_compatible_binding() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    edt = dtmodel._edt

    binding = dtmodel.get_compatible_binding("bosch,bme680", "i2c")
    assert binding
    assert edt.get_node("/soc/i2c@40003000/bme680@76").binding_path == binding.path

    # Lazy-cache.
    assert binding is dtmodel.get_compatible_binding("bosch,bme680", "i2c")

    # When the binding does expect a bus of appearance,
    # get_compatible_binding() should fail with no bus parameter
    # or a non relevant bus parameter.
    assert dtmodel.get_compatible_binding("bosch,bme680") is None
    assert dtmodel.get_compatible_binding("bosch,bme680", "qspi") is None

    # But, when the binding does not expect a bus of appearance,
    # get_compatible_binding() should succeed even if a non relevant
    # bus parameter is given.
    assert dtmodel.get_compatible_binding("nordic,nrf-pwm")
    assert dtmodel.get_compatible_binding("nordic,nrf-pwm") == dtmodel.get_compatible_binding(
        "nordic,nrf-pwm", "i2c"
    )

    # get_compatible_binding() should never fault.
    assert dtmodel.get_compatible_binding("notavendor,notamodel") is None
    assert dtmodel.get_compatible_binding("notavendor") is None


def test_dtmodel_get_base_binding() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()

    # Core bindings without compatible strings.
    assert dtmodel.get_base_binding("base.yaml")
    assert dtmodel.get_base_binding("power.yaml")
    assert dtmodel.get_base_binding("sensor-device.yaml")
    assert dtmodel.get_base_binding("i2c-device.yaml")

    # get_base_binding() won't fail with even more specific bindings
    # that define compatible strings.
    assert dtmodel.get_base_binding("nordic,nrf-pinctrl.yaml")
    assert dtmodel.get_base_binding("bosch,bme680-i2c.yaml")

    with pytest.raises(KeyError):
        # Included bindings MUST exist.
        dtmodel.get_base_binding("notafile")

    # Lazy-cache.
    assert dtmodel.get_base_binding("base.yaml") is dtmodel.get_base_binding("base.yaml")


def test_dtmodel_get_vendor() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()

    vendor = dtmodel.get_vendor("nordic,nrf-swi")
    assert vendor
    assert vendor.name == "Nordic Semiconductor"
    assert vendor.prefix == "nordic"

    # get_vendor() should not fault.
    assert dtmodel.get_vendor("notapreifx,notavendor") is None
    assert dtmodel.get_vendor("nocomma") is None


def test_dtmodel_get_compatible_devices() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()

    dt_bme680_i2c = dtmodel["/soc/i2c@40003000/bme680@76"]
    dt_bme680_spi = dtmodel["/soc/spi@40004000/bme680@0"]

    assert [dt_bme680_i2c, dt_bme680_spi] == dtmodel.get_compatible_devices("bosch,bme680")


def test_dtmodel_walk() -> None:
    # This unit tests asserts the shortcut to DTModel.root.walk() honors
    # all supported parameters, test_dtnode_walk_xxx() for other
    # unit tests of the walk() API.
    dtmodel = DTShTests.get_sample_dtmodel()

    assert list(dtmodel.root.walk()) == list(dtmodel.walk())
    assert list(dtmodel.root.walk(enabled_only=True)) == list(dtmodel.walk(enabled_only=True))
    assert list(dtmodel.root.walk(fixed_depth=3)) == list(dtmodel.walk(fixed_depth=3))

    # Natural node order is by DT path name.
    order_by = DTNodeSorter()
    assert list(dtmodel.root.walk(order_by=order_by)) == list(dtmodel.walk(order_by=order_by))
    assert list(dtmodel.root.walk(order_by=order_by, reverse=True)) == list(
        dtmodel.walk(order_by=order_by, reverse=True)
    )


def test_dtmodel_find() -> None:
    # This unit tests asserts the shortcut to DTModel.root.find() honors
    # all supported parameters, test_dtnode_find() for other
    # unit tests of the find() API.
    dtmodel = DTShTests.get_sample_dtmodel()

    class Criterion(DTNodeCriterion):
        NODES = dtmodel["/soc"].children

        def match(self, node: DTNode) -> bool:
            return node in Criterion().NODES

    criterion = Criterion()
    assert list(dtmodel.root.find(criterion)) == list(dtmodel.find(criterion))
    assert list(dtmodel.root.find(criterion, enabled_only=True)) == list(
        dtmodel.find(criterion, enabled_only=True)
    )

    # Natural node order is by DT path name.
    order_by = DTNodeSorter()
    assert list(dtmodel.root.find(criterion, order_by=order_by)) == list(
        dtmodel.find(criterion, order_by=order_by)
    )
    assert list(dtmodel.root.find(criterion, order_by=order_by, reverse=True)) == list(
        dtmodel.find(criterion, order_by=order_by, reverse=True)
    )


def test_dtmodel_index_based() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()

    # Membership.
    assert "/soc" in dtmodel
    assert "notanode" not in dtmodel

    # Index-based access.
    assert dtmodel["/soc"]
    with pytest.raises(KeyError):
        dtmodel["notanode"]

    # Iterate on the model walking through the devicetree.
    assert list(node for node in dtmodel) == list(dtmodel.walk())


def test_dtnode_sorter() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()

    dt_flashctrl = dtmodel["/soc/flash-controller@4001e000"]
    dt_flash0 = dt_flashctrl.get_child("flash@0")
    dt_partitions = dt_flash0.get_child("partitions")
    sample_nodes = [
        dt_flashctrl,
        dt_flash0,
        dt_partitions,
        *dt_partitions.children,
    ]

    # Natural order (by path name).
    natural_order = DTNodeSorter()
    assert sorted(
        sample_nodes,
        key=lambda x: x.path,
    ) == natural_order.sort(sample_nodes)
    assert sorted(sample_nodes, key=lambda x: x.path, reverse=True) == natural_order.sort(
        sample_nodes, reverse=True
    )

    class OrderByUnitAddr(DTNodeSorter):
        """Oder by e.g. unit addresses."""

        def split_sortable_unsortable(
            self, nodes: Sequence[DTNode]
        ) -> tuple[list[DTNode], list[DTNode]]:
            return (
                [node for node in nodes if node.unit_addr is not None],
                [node for node in nodes if node.unit_addr is None],
            )

        def weight(self, node: DTNode) -> Any:
            return node.unit_addr

    order_by = OrderByUnitAddr()

    sorted_sortable = sorted(
        [
            dt_flash0,
            *dt_partitions.children,
        ],
        key=lambda x: x.unit_addr if x.unit_addr is not None else sys.maxsize,
    )

    assert [
        # Nodes sorted by unit address first.
        *sorted_sortable,
        # Nodes without unit address last, in unchanged relative order.
        dt_flashctrl,
        dt_partitions,
    ] == order_by.sort(sample_nodes)

    sorted_sortable.reverse()
    assert [
        # Nodes without unit address first, in reversed relative order.
        dt_partitions,
        dt_flashctrl,
        # Nodes with unit address last, in reverse order.
        *sorted_sortable,
    ] == order_by.sort(sample_nodes, reverse=True)


def test_dtnode_criteria() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()

    class CriterionMatchNone(DTNodeCriterion):
        def match(self, node: DTNode) -> bool:
            return False

    # Empty criteria match all.
    assert len(dtmodel) == len(dtmodel.find(DTNodeCriteria()))

    class CriterionMatchAll(DTNodeCriterion):
        def match(self, node: DTNode) -> bool:
            return True

    assert len(dtmodel) == len(dtmodel.find(CriterionMatchAll()))
    assert len(dtmodel.find(CriterionMatchNone())) == 0

    # Logical conjunction (default): fails on first non matched criterion.
    assert len(dtmodel.find(DTNodeCriteria([CriterionMatchNone(), CriterionMatchAll()]))) == 0

    # Logical disjunction: criteria will succeed on first match.
    assert len(dtmodel) == len(
        dtmodel.find(
            DTNodeCriteria(
                [CriterionMatchNone(), CriterionMatchAll()],
                ored_chain=True,
            ),
        )
    )

    # Logical negation.
    assert not dtmodel.find(DTNodeCriteria(negative_chain=True))
    assert not dtmodel.find(DTNodeCriteria([CriterionMatchAll()], negative_chain=True))


def test_dtnode_properties() -> None:
    dtmodel = DTShTests.get_sample_dtmodel()
    dt_qspi = dtmodel["/soc/qspi@40029000"]

    assert dt_qspi.has_dtproperty("interrupts")
    dtprop_irqs = dt_qspi.dtproperty("interrupts")
    assert dtprop_irqs
    assert dtprop_irqs.dttype == "array"
    assert isinstance(dtprop_irqs.value, list)
    assert dtprop_irqs.value == [0x29, 0x1]

    assert dt_qspi.has_dtproperty("pinctrl-0")
    dtprop_pinctrl0 = dt_qspi.dtproperty("pinctrl-0")
    assert dtprop_pinctrl0
    # NOTE: why isn't this a single phandle ?
    assert dtprop_pinctrl0.dttype == "phandles"
    assert isinstance(dtprop_pinctrl0.value, list)

    assert dt_qspi.has_dtproperty("pinctrl-names")
    dtprop_pinctrl_names = dt_qspi.dtproperty("pinctrl-names")
    assert dtprop_pinctrl_names
    assert dtprop_pinctrl_names.dttype == "string-array"
    assert dtprop_pinctrl_names.value == ["default", "sleep"]

    dt_mx25r64 = dt_qspi.get_child("mx25r6435f@0")
    assert dt_mx25r64.has_dtproperty("jedec-id")
    dtprop_jedec = dt_mx25r64.dtproperty("jedec-id")
    assert dtprop_jedec
    assert dtprop_jedec.dttype == "uint8-array"
    assert isinstance(dtprop_jedec.value, bytes)
    assert bytes([0xC2, 0x28, 0x17]) == dtprop_jedec.value

    assert dt_mx25r64.has_dtproperty("has-dpd")
    dtprop_dpd = dt_mx25r64.dtproperty("has-dpd")
    assert dtprop_dpd
    assert dtprop_dpd.dttype == "boolean"
    assert isinstance(dtprop_dpd.value, bool)
    assert dtprop_dpd.value is True

    assert not dt_qspi.has_dtproperty("not-a-property")
    with pytest.raises(KeyError):
        # Properties MUST exist.
        dt_qspi.dtproperty("not-a-property")

    assert [prop.name for prop in dtmodel.root.all_dtproperties()] == [
        # Although these are properties of the root node in the DTS,
        # they do not actually appear as properties via the edtlib API:
        # - "#address-cells",
        # - "#size-cells",
        # - "model",
        "compatible",
    ]
