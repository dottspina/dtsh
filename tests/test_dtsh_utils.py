# Copyright (c) 2024 Christophe Dufaza <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the dtsh.dts utils."""

# Relax pylint a bit for unit tests.
# pylint: disable=protected-access
# pylint: disable=missing-function-docstring


from dtsh.utils import CMakeCache

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
