#! /usr/bin/env python3

"""
Host-side RPC API 与运行环境管理模块。

该模块实现了面向宿主机的 RPC 接口 `HostApi`，用于：
- 编译并生成 Jailhouse cell 二进制
- 枚举与读取系统中的 PCI 设备信息
- 启动/停止 Jailhouse 管理与对 guest 的生命周期操作（load/create/start/stop 等）
- 在本地运行 Linux guest（组合 kernel, dtb, ramdisk）
- 管理 UART 转发服务并返回宿主机/guest 的运行状态

实现细节说明：
- `HostApi` 继承 `RPCApi` 并实现了 RPC 暴露的各种方法。所有方法仅在 docstring 中说明用途，
    具体行为由现有实现保持不变。

注意：本模块依赖 Linux 环境下的 `/sys` 访问、`psutil`、以及项目内的 `Jailhouse` 工具。
"""

from typing import Optional, Union
from server import RPCServer
from api import RPCApi
import os
import logging
from pci_device import PCIDevice
import psutil
import time
from jailhouse import Jailhouse, TempFile
import subprocess

mypath = os.path.split(os.path.realpath(__file__))[0]

cc      = 'gcc'
objcopy = 'objcopy'
jailhouse_src = os.path.join(mypath, "jailhouse")
jailhouse_bin = os.path.join(mypath, "jailhouse_bin")

inc_dirs = [
    os.path.join(jailhouse_src, "hypervisor/arch/arm64/include"),
    os.path.join(jailhouse_src, "hypervisor/include"),
    os.path.join(jailhouse_src, "include")
]

cflags = "-Werror -Wall -Wextra -D__LINUX_COMPILER_TYPES_H"


class HostApi(RPCApi):
    """宿主机 RPC 接口实现。

    该类实现 `RPCApi` 定义的接口以便通过 RPC 暴露宿主机能力给远端管理工具。
    方法大致分为：编译/生成 cell、管理 Jailhouse（enable/disable、cell 生命周期）、
    读取 PCI 设备、运行 guest Linux、以及启动/停止 UART 转发服务等。
    """

    def __init__(self):
        super().__init__()
        self._uart_server: Optional[subprocess.Popen] = None

    def hello(self, msg: str):
        """简单回显接口，用于检测 RPC 通道是否可用。

        Args:
            msg (str): 要回显的字符串。

        Returns:
            dict: 包含回显消息的 `RPCApi.Result` 格式字典。
        """
        return RPCApi.Result(True, result=msg).to_dict()

    def compile_cell(self, src_txt: str) -> dict:
        """将传入的 C 源文本编译为 Jailhouse cell 二进制并返回其字节内容。

        步骤：
        1. 将 `src_txt` 写入临时文件
        2. 使用 `gcc` 编译为目标文件
        3. 使用 `objcopy` 导出为二进制 cell 文件

        Args:
            src_txt (str): C 源代码文本。

        Returns:
            dict: `RPCApi.Result` 风格的结果，成功时 `result` 为 cell 的二进制字节。
        """
        # 保存到临时目录
        tf = TempFile()

        if not isinstance(src_txt, str):
            return RPCApi.Result.error("source type error").to_dict()

        src = tf.save("compile", ".c")
        obj = tf.save("compile", ".o")
        cell = tf.save("compile", ".cell")

        logging.info(f"save source to {src}")
        with open(src, "wt", encoding='utf8') as f:
            f.write(src_txt)

        logging.info("compile")
        cflags_list = [
            cflags,
            ' '.join(map(lambda x: f"-I{x}", inc_dirs))
        ]
        cmd = f"{cc} -c {' '.join(cflags_list)} {src} -o {obj}"
        print(cmd)
        result = Jailhouse.run_command(cmd)
        if not result:
            return result.to_dict()

        logging.info("objcopy")
        cmd = f"{objcopy} -O binary --remove-section=.note.gnu.property {obj} {cell}"
        result = Jailhouse.run_command(cmd)
        if not result:
            return result.to_dict()

        cell_data = None
        with open(cell, "rb") as f:
            cell_data = f.read()

        return RPCApi.Result(True, result=cell_data).to_dict()

    def pci_devices(self) -> dict:
        """枚举系统中的 PCI 设备并返回其序列化信息列表。

        Returns:
            dict: `RPCApi.Result` 风格的结果，`result` 为设备信息列表。
        """
        devices = list()
        pcis = PCIDevice.all_from_sysfs()
        for pci in pcis:
            devices.append(pci.to_dict())
        return RPCApi.Result(True, result=devices).to_dict()

    def jailhouse_enable(self, rootcell: bytes) -> dict:
        """启用 Jailhouse 并加载根 cell（rootcell 二进制）。"""
        logging.info(f"jailhouse enable")
        return Jailhouse.enable(rootcell).to_dict()

    def jailhouse_disable(self) -> dict:
        """禁用 Jailhouse（相当于卸载/停止管理程序）。"""
        logging.info(f"jailhouse disable")
        return Jailhouse.disable().to_dict()

    def list_cell(self) -> dict:
        """列出当前已注册的 Guest cells 信息。"""
        logging.info(f"list cell")
        return Jailhouse.list_cell().to_dict()

    def create_cell(self, cell: bytes) -> dict:
        """创建一个新的 cell（传入 cell 二进制）。"""
        logging.info(f"create cell")
        return Jailhouse.create_cell(cell).to_dict()

    def destroy_cell(self, name: str) -> dict:
        """销毁指定名称的 cell。"""
        logging.info(f"destroy cell {name}")
        return Jailhouse.destroy_cell(name).to_dict()

    def load_cell(self, name, addr, data) -> dict:
        """将 cell 二进制数据加载到指定名称的 cell 的地址空间。"""
        logging.info(f"load cell {name} {hex(addr)}")
        return Jailhouse.load_cell(name, addr, data).to_dict()

    def start_cell(self, name) -> dict:
        """启动指定名称的 cell。"""
        logging.info(f"start cell {name}")
        return Jailhouse.start_cell(name).to_dict()

    def stop_cell(self, name) -> dict:
        """停止指定名称的 cell。"""
        logging.info(f"stop cell {name}")
        return Jailhouse.stop_cell(name).to_dict()

    def get_status(self) -> dict:
        """返回宿主机及所有 guest cells 的运行状态汇总。

        返回数据包含 `timestamp`, `rootcell`（宿主机资源信息）和 `guestcells` 映射。
        """
        status = dict()
        rootcell = dict()
        guestcells = dict()
        rootcell['meminfo'] = psutil.virtual_memory()._asdict()
        rootcell['cputimes'] = psutil.cpu_times()._asdict()
        rootcell['cpuload'] = psutil.cpu_percent()
        rootcell['cpucount'] = psutil.cpu_count()

        for cell in Jailhouse.list_cell().result:
            guestcells[cell['name']] = cell

        status['timestamp'] = time.time()
        status['rootcell'] = rootcell
        status['guestcells'] = guestcells
        return RPCApi.Result(True, result=status).to_dict()

    def run_linux(self, cell: bytes, kernel: bytes, dtb: bytes, ramdisk: bytes, bootargs: str) -> dict():
        """在宿主机上组合并运行 guest Linux（使用给定的 cell、kernel、dtb、ramdisk）。

        Args:
            cell (bytes): cell 二进制数据。
            kernel (bytes): kernel 二进制数据。
            dtb (bytes): 设备树二进制。
            ramdisk (bytes): 可选的 ramdisk 二进制。
            bootargs (str): 内核启动参数。

        Returns:
            dict: `Jailhouse.run_linux` 的结果字典表示。
        """
        tf = TempFile()

        if not isinstance(cell, bytes):
            return RPCApi.Result.error("cell type error").to_dict()
        if not isinstance(kernel, bytes):
            return RPCApi.Result.error("kernel type error").to_dict()
        if not isinstance(dtb, bytes):
            return RPCApi.Result.error("dtb type error").to_dict()
        if not isinstance(bootargs, str):
            return RPCApi.Result.error("bootargs type error").to_dict()

        cell_fn    = None
        kernel_fn  = None
        dtb_fn     = None
        ramdisk_fn = None

        logging.info(f"save cell {len(cell)} bytes.")
        cell_fn = tf.save("runlinux", ".cell", cell)
        if cell_fn is None:
            logging.error("save cell failed.")
            return RPCApi.Result.error("save cell failed.").to_dict()

        logging.info(f"save kernel {len(kernel)} bytes.")
        kernel_fn = tf.save("runlinux", ".kernel", kernel)
        if kernel_fn is None:
            logging.error("save kernel failed.")
            return RPCApi.Result.error("save kernel failed.").to_dict()

        logging.info(f"save devicetree {len(dtb)} bytes")
        dtb_fn = tf.save("runlinux", ".dtb", dtb)
        if dtb_fn is None:
            logging.error("save dtb failed.")
            return RPCApi.Result.error("save dtb failed.").to_dict()

        if ramdisk:
            ramdisk_fn = tf.save("runlinux", ".ramdisk", ramdisk)
            if ramdisk_fn is None:
                logging.error("save ramdisk failed.")
                return RPCApi.Result.error("save ramdisk failed.").to_dict()

        result = Jailhouse.run_linux(cell_fn, kernel_fn, dtb_fn, ramdisk_fn, bootargs)
        if not result:
            logging.error(f"run linux failed: {result.message}.")
        return result.to_dict()

    def get_guest_status(self, idx) -> dict:
        """（占位）返回指定 guest 的状态信息。

        目前为开发占位实现，返回示例数据结构。
        """
        status = {
            "online": true,
            "mem_total": 50,
            "mem_used": 50,
            "cpu_load": 50 
        }
        return RPCApi.Result.success(status).to_dict()

    def start_uart_server(self, config: str) -> dict:
        """启动 UART 转发服务器进程，基于项目内的 `ivsm-p2p-tool` 可执行文件。

        Args:
            config (str): UART 服务的配置文本，将写入临时 jhr 文件供工具使用。

        Returns:
            dict: `RPCApi.Result` 结果表示，表明启动是否成功。
        """
        if self._uart_server is not None:
            self._uart_server.terminate()
            try:
                self._uart_server.wait(1)
            except:
                pass
            self._uart_server = None

        uart_tool = f'{mypath}/ivsm-p2p-tool'
        if not os.path.isfile(uart_tool):
            print("{uart_tool} not exist.")
            return RPCApi.Result.error("{uart_tool} not exist.").to_dict()

        jhr_path = '/tmp/uart_server_config.jhr'
        try:
            with open(jhr_path, "wt") as f:
                f.write(config)
        except:
            msg = f"open config failed."
            print(msg)
            return RPCApi.Result.error(msg).to_dict()

        self._uart_server = subprocess.Popen((uart_tool, 'uart-server', '--jhr', jhr_path))
        # 睡眠一小段时间，检查命令是否异常退出
        time.sleep(0.1)
        if self._uart_server.poll() is not None:
            msg = f'run uart-server failed.'
            print(msg)
            self._uart_server = None
            return RPCApi.Result.error(msg).to_dict()

        return RPCApi.Result.success("success").to_dict()

    def stop_uart_server(self) -> dict:
        """停止之前启动的 UART 服务器（若存在）。"""
        if self._uart_server:
            self._uart_server.terminate()
            self._uart_server = None
        return RPCApi.Result.success("success").to_dict()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    addr = "tcp://0.0.0.0:4240"
    s = RPCServer(addr, HostApi())
    logging.info(f"server running {addr}.")
    s.run()
