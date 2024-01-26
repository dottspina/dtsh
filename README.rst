====
dtsh
====

:Author: Chris Duf

**dtsh** is an interactive *shell-like* interface with a devicetree and
its bindings:

-  browse the devicetree through a familiar hierarchical file-system
   metaphor
-  retrieve nodes and bindings with accustomed command names and command
   line syntax
-  generate simple documentation artifacts by redirecting commands
   output to files (text, HTML, SVG)
-  common command line interface paradigms (auto-completion, history)
   and keybindings

::

   $ dtsh build/gzephyr/zephyr.dts
   dtsh (0.1.0a4): Shell-like interface to a devicetree
   Help: man dtsh
   How to exit: q, or quit, or exit, or press Ctrl-D

   /
   > tree -L 1 -l
   /
   ├──  chosen
   ├──  aliases
   ├──  soc
   ├──  pin-controller   The nRF pin controller is a singleton node responsible for controlling…
   ├──  entropy_bt_hci   Bluetooth module that uses Zephyr's Bluetooth Host Controller Interface as…
   ├──  cpus
   ├──  sw-pwm           nRFx S/W PWM
   ├──  leds             This allows you to define a group of LEDs. Each LED in the group is…
   ├──  pwmleds          PWM LEDs parent node
   ├──  buttons          GPIO KEYS parent node
   ├──  connector        GPIO pins exposed on Arduino Uno (R3) headers…
   └──  analog-connector ADC channels exposed on Arduino Uno (R3) headers…


This software was created as a Proof of Concept for a:

- simple tool that could assist newcomers to Zephyr in understanding
  what a devicetree is, and how bindings describe and constrain its content
- an on hand DTS file viewer
