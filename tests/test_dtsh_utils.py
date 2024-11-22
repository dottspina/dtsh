# Copyright (c) 2024 Christophe Dufaza <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the dtsh.dts utils."""

# Relax pylint a bit for unit tests.
# pylint: disable=protected-access
# pylint: disable=missing-function-docstring

from pathlib import Path

import pytest

from dtsh.utils import CMakeCache, YAMLFile, YAMLFilesystem

from .dtsh_uthelpers import DTShTests


def test_cmakecache_init() -> None:
    with DTShTests.from_res():
        assert 4 == len(CMakeCache("CMakeCache.txt"))

    # Opening a non existing file should not fault.
    assert CMakeCache.open("notafile") is None

    # Opening an invalid CMakeCache file will not fault,
    # and answer an empty cache instead (lines do not match expected format).
    with DTShTests.from_res():
        cache = CMakeCache.open("zephyr.dts")
        assert cache is not None
        assert 0 == len(cache)


def test_cmakecache_getstr() -> None:
    with DTShTests.from_res():
        cache = CMakeCache("CMakeCache.txt")
    assert "foobar" == cache.getstr("DTSH_TEST_STRING")
    assert cache.getstr("NOT_AN_ENTRY") is None


def test_cmakecache_getstrs() -> None:
    with DTShTests.from_res():
        cache = CMakeCache("CMakeCache.txt")
    assert ["foo", "bar"] == cache.getstrs("DTSH_TEST_STRING_LIST")
    assert [] == cache.getstrs("NOT_AN_ENTRY")


def test_cmakecache_getbool() -> None:
    with DTShTests.from_res():
        cmake_cache = CMakeCache("CMakeCache.txt")
    assert cmake_cache.getbool("DTSH_TEST_BOOL_TRUE")
    assert not cmake_cache.getbool("DTSH_TEST_BOOL_FALSE")
    assert not cmake_cache.getbool("NOT_AN_ENTRY")


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

    assert 7 == len(yamlfs.name2path)
    assert (
        DTShTests.get_resource_path("yaml", "i2c-device.yaml")
        == yamlfs.name2path["i2c-device.yaml"]
    )

    with pytest.raises(KeyError):
        _ = yamlfs.name2path["notafile"]


def test_dtshdts_yamlfs_find_path() -> None:
    with DTShTests.from_res():
        yamlfs = YAMLFilesystem(["yaml"])

    assert DTShTests.get_resource_path(
        "yaml", "sensor-device.yaml"
    ) == yamlfs.find_path("sensor-device.yaml")


def test_dtshdts_yamlfs_find_file() -> None:
    with DTShTests.from_res():
        yamlfs = YAMLFilesystem(["yaml"])

    yaml = yamlfs.find_file("sensor-device.yaml")
    assert yaml
    assert DTShTests.get_resource_path("yaml", "sensor-device.yaml") == str(
        yaml.path.absolute()
    )


def test_yamlfile() -> None:
    yaml = YAMLFile(DTShTests.get_resource_path("yaml", "i2c-device.yaml"))

    # Lazy initialzation.
    assert yaml._content is None
    assert yaml._raw is None
    assert not yaml._depth2included
    assert yaml.content.startswith("# Copyright (c) 2017, Linaro Limited")
    assert yaml.content.endswith("i2c bus")
    assert "i2c" == yaml.raw["on-bus"]
    assert ["base.yaml", "power.yaml"] == yaml.includes

    # Fail-safe
    yaml = YAMLFile("notafile")
    assert "" == yaml.content
    assert {} == yaml.raw
    assert not yaml.includes


def test_included_at_depth() -> None:
    with DTShTests.from_res():
        fyaml = YAMLFile(Path("yaml") / "included_at_depth.yaml")
        assert fyaml.raw

    assert ["inc1.yaml", "inc2.yaml", "inc3.yaml"] == fyaml.includes
    assert ["inc1.yaml"] == fyaml.included_at_depth(0)
    assert ["inc2.yaml"] == fyaml.included_at_depth(1)
    assert ["inc3.yaml"] == fyaml.included_at_depth(2)
