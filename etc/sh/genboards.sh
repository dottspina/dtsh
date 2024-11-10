#!/usr/bin/env sh
# SPDX-License-Identifier: Apache-2.0

genboard_svg() {
	board="$1"
	board_dir="$2"

	svg_dir=doc/img
	mkdir -p "$svg_dir"

	board_svg="$svg_dir/board.svg"

	dtsh -c "ls --format nKd / > $board_svg" \
		-c "tree --fixed-depth 3 --format naKd soc >> $board_svg" \
		-c "tree --format nKrC &flash0 >> $board_svg"

	# Equivalent to (but avoiding to create a new DTSh session
	# for each command):
	# dtsh -c "ls --format nKd / > $board_svg"
	# dtsh -c "ls --format naKd soc >> $board_svg"
	# dtsh -c "tree --format nKrC &flash0 >> $board_svg"
	#
	# But clearly not equivalent to the commands bellow
	# where the OS shell would simly concatenate ANSI outputs text:
	# dtsh -c "ls --format nKd /" > $board_svg
	# dtsh -c "ls --format naKd soc" >> $board_svg
	# dtsh -c "tree --format nKrC &flash0" >> $board_svg
}

genboard_html() {
	board="$1"
	board_dir="$2"

	html_dir=doc
	mkdir -p "$html_dir"

	board_html="$html_dir/board.html"

	dtsh -c "ls --format nKd / > $board_html" \
		-c "tree --fixed-depth 3 --format naKd soc >> $board_html" \
		-c "tree --format nKrC &flash0 >> $board_html"
}

# Would be nice to be able to build a covenient list with something
# like:
# 	west boards -f '{name_v2} {dir}' >/tmp/boards.txt
# May be based on name/qualifiers.
echo "native_sim boards/native/native_sim" >/tmp/boards.txt
{
	echo "nrf52840dk/nrf52840 boards/nordic/nrf52840dk"
	echo "arduino_nano_33_ble/nrf52840/sense boards/arduino/nano_33_ble"
	echo "stm32vl_disco/stm32f100xb boards/st/stm32vl_disco"
	echo "mt8195_adsp/mt8195_adsp boards/mediatek/mt8195_adsp"
	echo "intel_socfpga_agilex5_socdk/agilex5 boards/intel/socfpga/agilex5_socdk"
	echo "esp32s3_devkitm/esp32s3/procpu boards/espressif/esp32s3_devkitm"
	echo "qemu_cortex_m3/ti_lm3s6965 boards/qemu/cortex_m3"

	# Can't distinguish variants (e.g. finding the qualifiers in
	# some CMake cache variable).
	# Would overwrite the board above.
	# echo "native_sim/native/64 boards/native/native_sim"
	# echo "esp32s3_devkitm/esp32s3/appcpu boards/espressif/esp32s3_devkitm"

} >>/tmp/boards.txt

old_wd="$PWD"

cat /tmp/boards.txt | tr -d '\r' |
	while read -r board_name board_dir; do
		echo "==== $board_name $board_dir ===="
		mkdir -p "$board_dir"
		cd "$board_dir" || return
		west build -p -b "$board_name" "$ZEPHYR_BASE/samples/hello_world"

		genboard_svg "$board" "$board_dir"
		genboard_html "$board" "$board_dir"

		cd "$old_wd" || return
	done
