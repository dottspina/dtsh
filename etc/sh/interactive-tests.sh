# Copyright (c) 2022 Chris Duf <chris@openmarl.org>
#
# SPDX-License-Identifier: Apache-2.0

# Helper for starting dtsh with various test configurations.

thisfile=$(readlink -f "$0")
thisdir=$(dirname "$thisfile")
DTSH_HOME=$(readlink -f "$thisdir/../..")
unset thisfile
unset thisdir

arg_zephyr_base="$1"
arg_zephyr_sdk="$2"

if [ -n "$arg_zephyr_base" ]; then
    TEST_ZEPHYR_BASE="$arg_zephyr_base"
    TEST_WEST_BASE=$(realpath -m "$arg_zephyr_base/..")
else
    TEST_WEST_BASE=$(realpath -m /mnt/platform/zephyr-rtos/workspaces/zephyr-sandbox)
    TEST_ZEPHYR_BASE="$TEST_WEST_BASE/zephyr"
fi
if [ -n "$arg_zephyr_sdk" ]; then
    TEST_ZEPHYR_SDK_DIR=$(realpath -m "$arg_zephyr_sdk")
else
    TEST_ZEPHYR_SDK_DIR=$(realpath -m /mnt/platform/zephyr-rtos/SDKs/zephyr-sdk-0.15)
fi
unset arg_zephyr_base
unset arg_zephyr_sdk


TEST_GCCARM10_DIR=$(realpath -m /mnt/platform/gcc-arm/gcc-arm-none-eabi-10)
TEST_GCCARM11_DIR=$(realpath -m /mnt/platform/gcc-arm/gcc-arm-none-eabi-11)

TEST_DIR="$DTSH_HOME/tmp-tests"

TEST_DTS_EDTLIB="$DTSH_HOME/tests/test.dts"
TEST_BINDINGS_EDTLIB="$DTSH_HOME/tests/bindings"

TEST_PROJECT_SENSOR="$TEST_ZEPHYR_BASE/samples/sensor/bme680"
TEST_PROJECT_CAN="$TEST_ZEPHYR_BASE/samples/drivers/can"
TEST_PROJECT_COAP="$TEST_ZEPHYR_BASE/samples/net/sockets/coap_client"
TEST_PROJECT_USB="$TEST_ZEPHYR_BASE/samples/subsys/usb/testusb"
TEST_PROJECT_BLE="$TEST_ZEPHYR_BASE/samples/bluetooth/eddystone"

TEST_BOARD_NRF52='nrf52840dk_nrf52840'
TEST_BOARD_F407GZ='black_f407zg_pro'
#FIXME: Link to documentation is broken for mimxrt1170_evk_cm7,
# which has the same documentation page as mimxrt1170_evk.
TEST_BOARD_NXP='mimxrt1170_evk_cm7'
TEST_BOARD_NANO='arduino_nano_33_ble'


. "$DTSH_HOME/etc/sh/zef"
. "$DTSH_HOME/etc/sh/dtsh"


test_run_yn() {
    echo -n 'Run test [yN]: '
    read yes_no
    case "$yes_no" in
        y|Y)
            return 1
            ;;
        *)
            ;;
    esac
    return 0
}


test_build_zephyr_project() {
    echo '==== Build Zephyr project'
    local arg_project="$1"
    local arg_board="$2"
    if [ -n "$arg_project" ]; then
        arg_project=$(realpath -m "$arg_project")
    else
        echo 'What project ?'
        zef_abort
    fi
    local previous_pwd=$(pwd)
    echo "*** Build Zephyr project: $arg_project"
    cd "$TEST_DIR" || zef_abort
    zef_open "$TEST_WEST_BASE" "$TEST_ZEPHYR_SDK_DIR" || zef_abort
    west build -b "$arg_board" "$arg_project" || zef_abort
    zef_close || zef_abort
    echo
    cd "$previous_pwd" || zef_abort
}


run_unittests() {
    echo '==== Unit tests: run unit tests before interactive sessions ?'
    test_run_yn
    if [ "$?" = 0 ]; then
        return
    fi
    dtsh_unittests
    sleep 2
}


run_interactive_use_case1() {
    echo '==== UC1: DTS and bindings from edtlib unit tests'
    echo '     DTS: tests/test.dts'
    echo '     Bindings search path: tests/bindings'
    test_run_yn
    if [ "$?" = 0 ]; then
        return
    fi
    local test_venv="$TEST_DIR/.venv"
    echo '==== Setup test environment'
    dtsh_clean
    dtsh_venv "$test_venv"
    echo 'done.'
    echo
    "$VIRTUAL_ENV/bin/dtsh" "$TEST_DTS_EDTLIB" "$TEST_BINDINGS_EDTLIB" || zef_abort
    echo 'done.'
    echo
    echo '==== Dispose test environment'
    deactivate
    rm -r "$TEST_DIR"
    echo 'done.'
}


run_interactive_use_case2() {
    echo '==== UC2: DTS from Zephyr build, Zephyr bindings'
    echo '     Bindings search path: $ZEPHYR_BASE/dts/bindings'
    # Only ZEPHYR_BASE is set.
    echo '     Toolchain: unavailable'
    echo "     Application: $(basename "$TEST_PROJECT_SENSOR")"
    echo "     Board: $TEST_BOARD_NRF52"
    test_run_yn
    if [ "$?" = 0 ]; then
        return
    fi
    local test_venv="$TEST_DIR/.venv"
    if [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
    mkdir -p "$TEST_DIR"
    test_build_zephyr_project "$TEST_PROJECT_SENSOR" "$TEST_BOARD_NRF52"
    echo 'done.'
    echo
    echo '==== Setup test environment'
    dtsh_clean
    dtsh_venv "$test_venv"
    export ZEPHYR_BASE="$TEST_ZEPHYR_BASE"
    echo 'done.'
    echo
    "$VIRTUAL_ENV/bin/dtsh" "$TEST_DIR/build/zephyr/zephyr.dts" || zef_abort
    echo 'done.'
    echo
    echo '==== Dispose test environment'
    unset ZEPHYR_BASE
    deactivate
    rm -r "$TEST_DIR"
    echo 'done.'
}


run_interactive_use_case3() {
    echo '==== UC3: DTS from Zephyr build, Zephyr bindings'
    echo '     Bindings search path: $ZEPHYR_BASE/dts/bindings'
    echo '     Toolchain: Zephyr SDK'
    echo "     Application: $(basename "$TEST_PROJECT_SENSOR")"
    echo "     Board: $TEST_BOARD_NRF52"
    test_run_yn
    if [ "$?" = 0 ]; then
        return
    fi
    local test_venv="$TEST_DIR/.venv"
    if [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
    mkdir -p "$TEST_DIR"
    test_build_zephyr_project "$TEST_PROJECT_SENSOR" "$TEST_BOARD_NRF52"
    echo 'done.'
    echo
    echo '==== Setup test environment'
    dtsh_clean
    zef_open "$TEST_WEST_BASE" "$TEST_ZEPHYR_SDK_DIR" || zef_abort
    pip install "$DTSH_HOME" || zef_abort
    echo 'done.'
    echo
    "$VIRTUAL_ENV/bin/dtsh" "$TEST_DIR/build/zephyr/zephyr.dts" || zef_abort
    echo 'done.'
    echo
    echo '==== Dispose test environment'
    pip uninstall --yes dtsh || zef_abort
    zef_close || zef_abort
    rm -r "$TEST_DIR"
    echo 'done.'
}


run_interactive_use_case4() {
    echo '==== UC4: DTS from Zephyr build, Zephyr bindings'
    echo '     Bindings search path: $ZEPHYR_BASE/dts/bindings'
    echo '     Toolchain (dtsh): Zephyr SDK'
    echo "     Application: $(basename "$TEST_PROJECT_CAN")"
    echo "     Board: $TEST_BOARD_F407GZ"
    test_run_yn
    if [ "$?" = 0 ]; then
        return
    fi
    local test_venv="$TEST_DIR/.venv"
    if [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
    mkdir -p "$TEST_DIR"
    test_build_zephyr_project "$TEST_PROJECT_CAN" "$TEST_BOARD_F407GZ"
    echo 'done.'
    echo
    echo '==== Setup test environment'
    dtsh_clean
    zef_open "$TEST_WEST_BASE" "$TEST_ZEPHYR_SDK_DIR" || zef_abort
    pip install "$DTSH_HOME" || zef_abort
    echo 'done.'
    echo
    "$VIRTUAL_ENV/bin/dtsh" "$TEST_DIR/build/zephyr/zephyr.dts" || zef_abort
    echo 'done.'
    echo
    echo '==== Dispose test environment'
    pip uninstall --yes dtsh || zef_abort
    zef_close || zef_abort
    rm -r "$TEST_DIR"
    echo 'done.'
}


run_interactive_use_case5() {
    echo '==== UC5: DTS from Zephyr build, Zephyr bindings'
    echo '     Bindings search path: $ZEPHYR_BASE/dts/bindings'
    echo '     Toolchain (dtsh): Zephyr SDK'
    echo "     Application: $(basename "$TEST_PROJECT_COAP")"
    echo "     Board: $TEST_BOARD_NXP"
    test_run_yn
    if [ "$?" = 0 ]; then
        return
    fi
    local test_venv="$TEST_DIR/.venv"
    if [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
    mkdir -p "$TEST_DIR"
    test_build_zephyr_project "$TEST_PROJECT_COAP" "$TEST_BOARD_NXP"
    echo 'done.'
    echo
    echo '==== Setup test environment'
    dtsh_clean
    zef_open "$TEST_WEST_BASE" "$TEST_ZEPHYR_SDK_DIR" || zef_abort
    pip install "$DTSH_HOME" || zef_abort
    echo 'done.'
    echo
    "$VIRTUAL_ENV/bin/dtsh" "$TEST_DIR/build/zephyr/zephyr.dts" || zef_abort
    echo 'done.'
    echo
    echo '==== Dispose test environment'
    pip uninstall --yes dtsh || zef_abort
    zef_close || zef_abort
    rm -r "$TEST_DIR"
    echo 'done.'
}


run_interactive_use_case6() {
    echo '==== UC6: DTS from Zephyr build, Zephyr bindings'
    echo '     Bindings search path: $ZEPHYR_BASE/dts/bindings'
    echo '     Toolchain (dtsh): Zephyr SDK'
    echo "     Application: $(basename "$TEST_PROJECT_USB")"
    echo "     Board: $TEST_BOARD_NXP"
    test_run_yn
    if [ "$?" = 0 ]; then
        return
    fi
    local test_venv="$TEST_DIR/.venv"
    if [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
    mkdir -p "$TEST_DIR"
    test_build_zephyr_project "$TEST_PROJECT_USB" "$TEST_BOARD_NXP"
    echo 'done.'
    echo
    echo '==== Setup test environment'
    dtsh_clean
    zef_open "$TEST_WEST_BASE" "$TEST_ZEPHYR_SDK_DIR" || zef_abort
    pip install "$DTSH_HOME" || zef_abort
    echo 'done.'
    echo
    "$VIRTUAL_ENV/bin/dtsh" "$TEST_DIR/build/zephyr/zephyr.dts" || zef_abort
    echo 'done.'
    echo
    echo '==== Dispose test environment'
    pip uninstall --yes dtsh || zef_abort
    zef_close || zef_abort
    rm -r "$TEST_DIR"
    echo 'done.'
}


run_interactive_use_case7() {
    echo '==== UC7: DTS from Zephyr build, Zephyr bindings'
    echo '     Bindings search path: $ZEPHYR_BASE/dts/bindings'
    echo '     Toolchain (dtsh): Zephyr SDK'
    echo "     Application: $(basename "$TEST_PROJECT_BLE")"
    echo "     Board: $TEST_BOARD_NANO"
    test_run_yn
    if [ "$?" = 0 ]; then
        return
    fi
    local test_venv="$TEST_DIR/.venv"
    if [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
    mkdir -p "$TEST_DIR"
    test_build_zephyr_project "$TEST_PROJECT_BLE" "$TEST_BOARD_NANO"
    echo 'done.'
    echo
    echo '==== Setup test environment'
    dtsh_clean
    zef_open "$TEST_WEST_BASE" "$TEST_ZEPHYR_SDK_DIR" || zef_abort
    pip install "$DTSH_HOME" || zef_abort
    echo 'done.'
    echo
    "$VIRTUAL_ENV/bin/dtsh" "$TEST_DIR/build/zephyr/zephyr.dts" || zef_abort
    echo 'done.'
    echo
    echo '==== Dispose test environment'
    pip uninstall --yes dtsh || zef_abort
    zef_close || zef_abort
    rm -r "$TEST_DIR"
    echo 'done.'
}


run_interactive_use_case8() {
    echo '==== UC8: DTS from Zephyr build, Zephyr bindings'
    echo '     Bindings search path: $ZEPHYR_BASE/dts/bindings'
    echo '     Toolchain: GCC Arm 10'
    echo "     Application: $(basename "$TEST_PROJECT_SENSOR")"
    echo "     Board: $TEST_BOARD_NRF52"
    test_run_yn
    if [ "$?" = 0 ]; then
        return
    fi
    local test_venv="$TEST_DIR/.venv"
    if [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
    mkdir -p "$TEST_DIR"
    test_build_zephyr_project "$TEST_PROJECT_SENSOR" "$TEST_BOARD_NRF52"
    echo 'done.'
    echo
    echo '==== Setup test environment'
    dtsh_clean
    zef_open "$TEST_WEST_BASE" "$TEST_GCCARM10_DIR" || zef_abort
    pip install "$DTSH_HOME" || zef_abort
    echo 'done.'
    echo
    "$VIRTUAL_ENV/bin/dtsh" "$TEST_DIR/build/zephyr/zephyr.dts" || zef_abort
    echo 'done.'
    echo
    echo '==== Dispose test environment'
    pip uninstall --yes dtsh || zef_abort
    zef_close || zef_abort
    rm -r "$TEST_DIR"
    echo 'done.'
}


run_interactive_use_case9() {
    echo '==== UC9: DTS from Zephyr build, Zephyr bindings'
    echo '     Bindings search path: $ZEPHYR_BASE/dts/bindings'
    echo '     Toolchain: GCC Arm 11'
    echo "     Application: $(basename "$TEST_PROJECT_SENSOR")"
    echo "     Board: $TEST_BOARD_NRF52"
    test_run_yn
    if [ "$?" = 0 ]; then
        return
    fi
    local test_venv="$TEST_DIR/.venv"
    if [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
    mkdir -p "$TEST_DIR"
    test_build_zephyr_project "$TEST_PROJECT_SENSOR" "$TEST_BOARD_NRF52"
    echo 'done.'
    echo
    echo '==== Setup test environment'
    dtsh_clean
    zef_open "$TEST_WEST_BASE" "$TEST_GCCARM11_DIR" || zef_abort
    pip install "$DTSH_HOME" || zef_abort
    echo 'done.'
    echo
    "$VIRTUAL_ENV/bin/dtsh" "$TEST_DIR/build/zephyr/zephyr.dts" || zef_abort
    echo 'done.'
    echo
    echo '==== Dispose test environment'
    pip uninstall --yes dtsh || zef_abort
    zef_close || zef_abort
    rm -r "$TEST_DIR"
    echo 'done.'
}


clear
run_unittests
clear
run_interactive_use_case1
clear
run_interactive_use_case2
clear
run_interactive_use_case3
clear
run_interactive_use_case4
clear
run_interactive_use_case5
clear
run_interactive_use_case6
clear
run_interactive_use_case7
clear
run_interactive_use_case8
clear
run_interactive_use_case9
