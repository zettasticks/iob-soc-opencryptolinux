#!/usr/bin/env python3
import os
import sys
import shutil
import math

from mk_configuration import update_define
from verilog_tools import inplace_change
from iob_soc_opencryptolinux_create_periphs_tmp import create_periphs_tmp

from iob_soc import iob_soc
from iob_vexriscv import iob_vexriscv
from iob_uart16550 import iob_uart16550
from iob_uart import iob_uart
from iob_spi_master import iob_spi_master
from axil2iob import axil2iob
from iob_reset_sync import iob_reset_sync
from iob_ram_sp import iob_ram_sp


class iob_soc_opencryptolinux(iob_soc):
    name = "iob_soc_opencryptolinux"
    version = "V0.70"
    flows = "pc-emul emb sim doc fpga"
    setup_dir = os.path.dirname(__file__)

    @classmethod
    def _create_instances(cls):
        super()._create_instances()
        # Verilog modules instances if we have them in the setup list (they may not be in the list if a subclass decided to remove them).
        if iob_vexriscv in cls.submodule_list:
            cls.cpu = iob_vexriscv("cpu_0")
        # Instantiate OpenCryptoLinux peripherals
        if iob_uart16550 in cls.submodule_list:
            cls.peripherals.append(iob_uart16550("UART0", "Default UART interface"))
        if iob_spi_master in cls.submodule_list:
            cls.peripherals.append(iob_spi_master("SPI0", "SPI master peripheral"))

        # Add custom N_SLAVES and N_SLAVES_W
        cls.confs += [
            {
                "name": "N_SLAVES",
                "type": "M",
                "val": str(
                    len(cls.peripherals) + 3
                ),  # + 3 for internal BOOT_CTR, PLIC and CLINT
                "min": "NA",
                "max": "NA",
                "descr": "Number of peripherals",
            },
            {
                "name": "N_SLAVES_W",
                "type": "M",
                "val": str(
                    math.ceil(
                        math.log(
                            len(cls.peripherals)
                            + 3,  # + 3 for internal BOOT_CTR, PLIC and CLINT
                            2,
                        )
                    )
                ),
                "min": "NA",
                "max": "NA",
                "descr": "Peripheral bus width",
            },
        ]

    @classmethod
    def _create_submodules_list(cls, extra_submodules=[]):
        """Create submodules list with dependencies of this module"""
        super()._create_submodules_list(
            [
                {"interface": "peripheral_axi_wire"},
                {"interface": "intmem_axi_wire"},
                {"interface": "dBus_axi_wire"},
                {"interface": "iBus_axi_wire"},
                {"interface": "dBus_axi_m_port"},
                {"interface": "iBus_axi_m_port"},
                {"interface": "dBus_axi_m_portmap"},
                {"interface": "iBus_axi_m_portmap"},
                iob_vexriscv,
                iob_uart16550,
                axil2iob,
                iob_reset_sync,
                iob_ram_sp,
                # iob_spi_master,
                (iob_uart, {"purpose": "simulation"}),
            ]
            + extra_submodules
        )
        # Remove picorv32 and uart from iob-soc
        i = 0
        while i < len(cls.submodule_list):
            if type(cls.submodule_list[i]) == type and cls.submodule_list[i].name in [
                "iob_picorv32",
                "iob_uart",
                "iob_cache",
            ]:
                cls.submodule_list.pop(i)
                continue
            i += 1

    @classmethod
    def _post_setup(cls):
        super()._post_setup()
        dst = f"{cls.build_dir}/software/src"
        src = f"{__class__.setup_dir}/submodules/OS/software/OS_build"
        files = os.listdir(src)
        for fname in files:
            src_file = os.path.join(src, fname)
            if os.path.isfile(src_file):
                shutil.copy2(src_file, dst)

        # Copy terminalMode script to scripts build directory
        dst = f"{cls.build_dir}/scripts"
        src_file = f"{__class__.setup_dir}/submodules/IOBSOC/submodules/LIB/scripts/terminalMode.py"
        shutil.copy2(src_file, dst)
        src_file = f"{__class__.setup_dir}/scripts/check_if_run_linux.py"
        shutil.copy2(src_file, dst)

        # Override periphs_tmp.h of iob-soc with one specific for opencryptolinux
        create_periphs_tmp(
            cls.name,
            next(i["val"] for i in cls.confs if i["name"] == "ADDR_W"),
            cls.peripherals,
            f"{cls.build_dir}/software/{cls.name}_periphs.h",
        )

    @classmethod
    def _setup_confs(cls, extra_confs=[]):
        # Append confs or override them if they exist
        super()._setup_confs(
            [
                {
                    "name": "RUN_LINUX",
                    "type": "M",
                    "val": False,
                    "min": "0",
                    "max": "1",
                    "descr": "Used to select running linux.",
                },
                {
                    "name": "INIT_MEM",
                    "type": "M",
                    "val": False,
                    "min": "0",
                    "max": "1",
                    "descr": "Used to select running linux.",
                },
                {
                    "name": "USE_EXTMEM",
                    "type": "M",
                    "val": True,
                    "min": "0",
                    "max": "1",
                    "descr": "Always use external memory in the SoC.",
                },
                {
                    "name": "N_CORES",
                    "type": "P",
                    "val": "1",
                    "min": "1",
                    "max": "32",
                    "descr": "Number of CPU cores used in the SoC.",
                },
                {
                    "name": "BOOTROM_ADDR_W",
                    "type": "P",
                    "val": "15",
                    "min": "1",
                    "max": "32",
                    "descr": "Boot ROM address width",
                },
                {
                    "name": "SRAM_ADDR_W",
                    "type": "P",
                    "val": "15",
                    "min": "1",
                    "max": "32",
                    "descr": "SRAM address width",
                },
                {
                    "name": "MEM_ADDR_W",
                    "type": "P",
                    "val": "26",
                    "min": "1",
                    "max": "32",
                    "descr": "Memory bus address width",
                },
                {
                    "name": "OS_ADDR_W",
                    "type": "M",
                    "val": "25",
                    "min": "1",
                    "max": "32",
                    "descr": "Memory bus address width",
                },
                # INTERRUPTS ARCHITECTURE
                {
                    "name": "N_SOURCES",
                    "type": "P",
                    "val": "32",
                    "min": "1",
                    "max": "32",
                    "descr": "Number of peripherals that can generate an external interrupt to be interpreted by the PLIC.",
                },
                {
                    "name": "N_TARGETS",
                    "type": "P",
                    "val": "2",
                    "min": "1",
                    "max": "32",
                    "descr": "Number of HARTs in the SoC.",
                },
            ]
            + extra_confs
        )

        # Remove unnecessary confs of IOb-SoC
        i = 0
        while i < len(cls.confs):
            if cls.confs[i]["name"] in ["USE_MUL_DIV", "USE_COMPRESSED"]:
                cls.confs.pop(i)
                continue
            i += 1

    # Method that runs the setup process of this class
    @classmethod
    def _setup_portmap(cls):
        if iob_uart16550 in cls.submodule_list:
            cls.peripheral_portmap += [
                # Map interrupt port to internal wire
                (
                    {
                        "corename": "UART0",
                        "if_name": "interrupt",
                        "port": "interrupt_o",
                        "bits": [],
                    },
                    {"corename": "internal", "if_name": "uart", "port": "", "bits": []},
                ),
                # Map other rs232 ports to external interface (system IO)
                (
                    {
                        "corename": "UART0",
                        "if_name": "rs232",
                        "port": "txd_o",
                        "bits": [],
                    },
                    {"corename": "external", "if_name": "uart", "port": "", "bits": []},
                ),
                (
                    {
                        "corename": "UART0",
                        "if_name": "rs232",
                        "port": "rxd_i",
                        "bits": [],
                    },
                    {"corename": "external", "if_name": "uart", "port": "", "bits": []},
                ),
                (
                    {
                        "corename": "UART0",
                        "if_name": "rs232",
                        "port": "cts_i",
                        "bits": [],
                    },
                    {"corename": "external", "if_name": "uart", "port": "", "bits": []},
                ),
                (
                    {
                        "corename": "UART0",
                        "if_name": "rs232",
                        "port": "rts_o",
                        "bits": [],
                    },
                    {"corename": "external", "if_name": "uart", "port": "", "bits": []},
                ),
            ]

    @classmethod
    def _custom_setup(cls):
        super()._custom_setup()
        # Add the following arguments:
        # "RUN_LINUX": if should setup with init_mem or not
        for arg in sys.argv[1:]:
            if arg == "RUN_LINUX":
                update_define(cls.confs, "RUN_LINUX", True)