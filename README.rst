====
DTSh
====

:Author: Christophe Dufaza

Shell-like command line interface with Devicetree:

- browse a devicetree through a hierarchical file system metaphor
- search for devices, bindings, buses or interrupts with flexible criteria
- filter, sort and format commands output
- generate simple documentation artifacts (text, HTML, SVG) by redirecting the output
  of commands to files
- *rich* Textual User Interface, command line auto-completion, command history, user themes

::

   $ dtsh build/zephyr/zephyr.dts
   dtsh (0.2rc1): Shell-like interface with Devicetree
   How to exit: q, or quit, or exit, or press Ctrl-D

   /
   > cd /soc/flash-controller@4001e000

   /soc/flash-controller@4001e000
   > tree -l
                                 Description
                                 ─────────────────────────────────────────────────────────────────
   flash-controller@4001e000     Nordic NVMC (Non-Volatile Memory Controller)
   └── flash@0                   Flash node
       └── partitions            This binding is used to describe fixed partitions of a flash (or…
            ├── partition@0      Each child node of the fixed-partitions node represents…
            ├── partition@c000   Each child node of the fixed-partitions node represents…
            ├── partition@82000  Each child node of the fixed-partitions node represents…
            └── partition@f8000  Each child node of the fixed-partitions node represents…
