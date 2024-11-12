# Copyright (c) 2023 Christophe Dufaza <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the dtsh.dts module."""

# Relax pylint a bit for unit tests.
# pylint: disable=protected-access
# pylint: disable=missing-function-docstring


import os

import pytest

from dtsh.dts import DTS, YAMLFilesystem, YAMLFile

from .dtsh_uthelpers import DTShTests


def test_dts_init() -> None:
    # Use case:
    # - CMake cache: not available
    # - OS environment: reset
    with DTShTests.mock_env(
        {
            "ZEPHYR_BASE": None,
        }
    ):
        with DTShTests.from_res():
            dts = DTS("zephyr.dts")

            # App. binary directory (aka build) is always set to
            # the parent of the directory that contains the DTS file
            # (aka build/zephyr/zephyr.dts file layout).
            app_bin_dir = os.path.dirname(os.path.dirname(dts.path))
            assert app_bin_dir == dts.app_binary_dir

            assert not dts.app_source_dir
            assert not dts.toolchain
            assert not dts.board
            assert not dts.fw_name
            assert not dts.fw_version

            # Default minimal bindings search path:
            # - though cleared in environment, ZEPHYR_BASE may be derived
            # from __file__ when distributed with Zephyr
            if dts.zephyr_base:
                expect_dirs = [os.path.join(dts.zephyr_base, "dts", "bindings")]
            else:
                expect_dirs = []
            assert expect_dirs == dts.bindings_search_path


def test_dts_init_from_os_env() -> None:
    # Use case:
    # - CMake cache: not available
    # - OS environment: ZEPHYR_BASE
    tmpenv = {
        "ZEPHYR_BASE": "dummy",
    }
    with DTShTests.mock_env(tmpenv):  # type: ignore
        with DTShTests.from_res():
            dts = DTS("zephyr.dts")

            # Parent of the directory that contains the DTS file.
            app_bin_dir = os.path.dirname(os.path.dirname(dts.path))
            assert app_bin_dir == dts.app_binary_dir

            # Possibly set only when a CMake cache is available.
            assert not dts.app_source_dir
            assert not dts.toolchain
            assert not dts.board
            assert not dts.fw_name
            assert not dts.fw_version

            # Retrieved from mock environment.
            assert dts.zephyr_base
            assert tmpenv["ZEPHYR_BASE"] == dts.zephyr_base
            assert (
                os.path.join(
                    dts.zephyr_base, "dts", "bindings", "vendor-prefixes.txt"
                )
                == dts.vendors_file
            )
            # Default minimal bindings search path.
            expect_dirs = [
                os.path.join(dts.zephyr_base, "dts", "bindings"),
            ]
            assert expect_dirs == dts.bindings_search_path


def test_dts_init_from_cmake_zephyr() -> None:
    # Use-case:
    # - CMake cache: res/Build_zephyr/CMakeCache.txt
    # - Environment: reset
    with DTShTests.mock_env(
        {
            "ZEPHYR_BASE": None,
        }
    ):
        dts = DTS(
            DTShTests.get_resource_path("Build_zephyr", "zephyr", "zephyr.dts")
        )

        assert dts.zephyr_base
        assert (
            os.path.join(
                dts.zephyr_base, "dts", "bindings", "vendor-prefixes.txt"
            )
            == dts.vendors_file
        )

        # Parent of the directory that contains the DTS file.
        app_bin_dir = os.path.dirname(os.path.dirname(dts.path))
        assert app_bin_dir == dts.app_binary_dir

        # Retrieved from the CMake cache.
        assert (
            os.path.join(
                DTShTests.ANON_ZEPHYR_BASE, "samples", "sensor", "bme680"
            )
            == dts.app_source_dir
        )

        assert dts.board
        assert not dts.board.shield
        assert DTShTests.BOARD == dts.board.target
        assert os.path.join(
            DTShTests.ANON_ZEPHYR_BASE,
            "boards",
            "arm",
            "nrf52840dk_nrf52840",
        ) == str(dts.board.board_dir)

        assert "bme680" == dts.fw_name
        assert DTShTests.ZEPHYR_VERSION == dts.fw_version
        assert DTShTests.ANON_ZEPHYR_BASE == dts.zephyr_base

        assert dts.toolchain
        assert "zephyr" == dts.toolchain.variant
        assert DTShTests.ANON_ZEPHYR_SDK == str(dts.toolchain.path)


def test_dts_init_from_cmake_gnuarm() -> None:
    # Use-case:
    # - CMake cache: res/Build_gnuarm/CMakeCache.txt
    # - Environment: reset
    with DTShTests.mock_env(
        {
            "ZEPHYR_BASE": None,
        }
    ):
        dts = DTS(
            DTShTests.get_resource_path("Build_gnuarm", "zephyr", "zephyr.dts")
        )

        assert dts.zephyr_base
        assert (
            os.path.join(
                dts.zephyr_base, "dts", "bindings", "vendor-prefixes.txt"
            )
            == dts.vendors_file
        )

        # Parent of the directory that contains the DTS file.
        app_bin_dir = os.path.dirname(os.path.dirname(dts.path))
        assert app_bin_dir == dts.app_binary_dir

        # Retrieved from the CMake cache.
        assert (
            os.path.join(
                DTShTests.ANON_ZEPHYR_BASE, "samples", "sensor", "bme680"
            )
            == dts.app_source_dir
        )

        assert dts.board
        assert os.path.join(
            DTShTests.ANON_ZEPHYR_BASE,
            "boards",
            "arm",
            "nrf52840dk_nrf52840",
        ) == str(dts.board.board_dir)

        assert DTShTests.BOARD == dts.board.target
        assert not dts.board.shield

        assert "bme680" == dts.fw_name
        assert DTShTests.ZEPHYR_VERSION == dts.fw_version
        assert DTShTests.ANON_ZEPHYR_BASE == dts.zephyr_base

        assert dts.toolchain
        assert "gnuarmemb" == dts.toolchain.variant
        assert DTShTests.ANON_GNUARMEMB == str(dts.toolchain.path)


def test_yamlfs_find_path() -> None:
    with DTShTests.from_res():
        yamlfs = YAMLFilesystem(["yaml"])

    assert yamlfs.find_path("notafile") is None

    for name, path in [
        ("power.yaml", DTShTests.get_resource_path("yaml", "power.yaml")),
        (
            "i2c-device.yaml",
            DTShTests.get_resource_path("yaml", "i2c-device.yaml"),
        ),
        (
            "sensor-device.yaml",
            DTShTests.get_resource_path("yaml", "sensor-device.yaml"),
        ),
    ]:
        assert path == yamlfs.find_path(name)


def test_yamlfs_find_file() -> None:
    with DTShTests.from_res():
        yamlfs = YAMLFilesystem(["yaml"])

    fyaml = yamlfs.find_file("i2c-device.yaml")
    assert fyaml
    assert DTShTests.get_resource_path("yaml", "i2c-device.yaml") == str(
        fyaml.path.absolute()
    )

    # Opening a non existing file should not fault.
    assert yamlfs.find_file("notafile") is None


def test_yamlfs_name2path() -> None:
    with DTShTests.from_res():
        yamlfs = YAMLFilesystem(["yaml"])

    assert {
        "i2c-device.yaml": DTShTests.get_resource_path(
            "yaml", "i2c-device.yaml"
        ),
        "power.yaml": DTShTests.get_resource_path("yaml", "power.yaml"),
        "sensor-device.yaml": DTShTests.get_resource_path(
            "yaml", "sensor-device.yaml"
        ),
    } == yamlfs.name2path

    with pytest.raises(KeyError):
        _ = yamlfs.name2path["notafile"]


def test_dtshdts_yamlfs_find_path() -> None:
    with DTShTests.from_res():
        dts = DTS("zephyr.dts", ["yaml"])

    assert DTShTests.get_resource_path(
        "yaml", "sensor-device.yaml"
    ) == dts.yamlfs.find_path("sensor-device.yaml")


def test_dtshdts_yamlfs_find_file() -> None:
    with DTShTests.from_res():
        dts = DTS("zephyr.dts", ["yaml"])

    yaml = dts.yamlfs.find_file("sensor-device.yaml")
    assert yaml
    assert DTShTests.get_resource_path("yaml", "sensor-device.yaml") == str(
        yaml.path.absolute()
    )


def test_yamlfile() -> None:
    yaml = YAMLFile(DTShTests.get_resource_path("yaml", "i2c-device.yaml"))

    # Lazy initialzation.
    assert yaml._content is None
    assert yaml._raw is None
    assert yaml._includes is None
    assert yaml.content.startswith("# Copyright (c) 2017, Linaro Limited")
    assert yaml.content.endswith("i2c bus")
    assert "i2c" == yaml.raw["on-bus"]
    assert ["base.yaml", "power.yaml"] == yaml.includes

    # Fail-safe
    yaml = YAMLFile("notafile")
    assert "" == yaml.content
    assert {} == yaml.raw
    assert [] == yaml.includes
