import os
import logging
import platform
import subprocess
import tempfile
from typing import Union, Optional
from api import RPCApi
import shlex

"""
Jailhouse RPC helper module.

本模块为 RPC 层提供与本地 `jailhouse` 二进制及驱动交互的封装，
用于在宿主机上执行 jailhouse 的常见操作：加载/卸载驱动、
列举/创建/销毁/加载/启动/停止 guest cell，以及通过临时文件传递二进制数据。

主要类:
- TempFile: 管理临时文件的创建与清理。
- Jailhouse: 封装与 `jailhouse` 可执行文件的交互接口方法。

主要方法:
- `Jailhouse.run_command`: 在子进程中执行 shell 命令并返回 `RPCApi.Result`。
- `Jailhouse.enable/disable`: 启用或关闭 jailhouse hypervisor。
- `Jailhouse.list_cell/create_cell/destroy_cell/load_cell/start_cell/stop_cell`: 管理 cell 的生命周期。

注意: 本文件只包含与外部 `jailhouse` 工具的调用封装，
具体实现依赖系统环境和 `jailhouse` 可执行文件的可用性。
"""


class TempFile(object):
    """
    临时文件管理工具类。

    负责创建、保存和在需要时清理临时文件。典型用法是在需要将二进制
    或文本数据传递给外部命令时先写入临时文件，操作完成后统一删除。
    """

    def __init__(self) -> None:
        self._temp_files = list()

    def __del__(self):
        """析构函数，尝试清理残留的临时文件。"""
        self.clean()

    def save(self, prefix: str, suffix: str, data: Optional[Union[str,bytes]] = None) -> Optional[str]:
        """
        创建并保存临时文件。

        Args:
            prefix (str): 临时文件名前缀
            suffix (str): 临时文件名后缀
            data (str|bytes|None): 要写入临时文件的内容

        Returns:
            str|None: 成功返回临时文件路径，失败返回 None
        """
        temp = tempfile.mktemp(suffix, prefix)
        try:
            if isinstance(data, str):
                with open(temp, "wt") as f:
                    f.write(data)
            elif isinstance(data, bytes):
                with open(temp, "wb") as f:
                    f.write(data)
        except:
            logging.error(f"write file failed {temp}.")
            return None

        self._temp_files.append(temp)
        return temp

    def clean(self):
        """删除已记录的所有临时文件并清空内部记录。"""
        for fn in self._temp_files:
            os.unlink(fn)
        self._temp_files.clear()



mypath = os.path.split(os.path.realpath(__file__))[0]

cc      = 'gcc'
objcopy = 'objcopy'
jailhouse_src = os.path.join(mypath, "jailhouse")
jailhouse_bin = os.path.join(mypath, "jailhouse_bin")

if platform.machine() == 'x86_64':
    repo_root      = "../../613virt/"
    cc             = repo_root + "tools/gcc-7.3.1-64-gnu/bin/aarch64-linux-gnu-gcc"
    objcopy        = repo_root + "tools/gcc-7.3.1-64-gnu/bin/aarch64-linux-gnu-objcopy"

inc_dirs = [
    os.path.join(jailhouse_src, "hypervisor/arch/arm64/include"),
    os.path.join(jailhouse_src, "hypervisor/include"),
    os.path.join(jailhouse_src, "include")
]

cflags = "-Werror -Wall -Wextra -D__LINUX_COMPILER_TYPES_H"


class Jailhouse(object):
    jh_exe = os.path.join(jailhouse_bin, "jailhouse")
    jh_ko  = os.path.join(jailhouse_bin, "jailhouse.ko")
    jh_dev = '/dev/jailhouse'
    linux_loader = os.path.join(jailhouse_bin, "linux-loader.bin")

    tmep_files = list()

    """
    与本地 `jailhouse` 可执行文件交互的工具类。

    该类通过类方法提供对 jailhouse 的常用操作封装，便于在 RPC 层调用。
    """

    def __init__(self) -> None:
        pass

    @classmethod
    def run_command(cls, cmd) -> RPCApi.Result:
        """
        在子进程中执行命令并返回 `RPCApi.Result` 对象。

        Args:
            cmd (str): 要执行的 shell 命令字符串

        Returns:
            RPCApi.Result: 执行结果，`result` 字段包含 stdout 或错误信息
        """
        logging.debug(f"run command {cmd}")

        proc = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.wait()
        out, err = proc.communicate()
        code = proc.returncode

        if isinstance(out, bytes):
            out = out.decode()
        if isinstance(err, bytes):
            err = err.decode()

        if proc.returncode == 0:
            return RPCApi.Result(True, result=out)
        else:
            return RPCApi.Result(False, msg=out+'\n'+err)

    @classmethod
    def find_cell_id(cls, name: str) -> Optional[int]:
        """
        根据 cell 名称查找对应的 cell id。

        Args:
            name (str): cell 名称

        Returns:
            int|None: 找到返回 cell id，否则返回 None
        """
        celllist = cls.list_cell()
        if not celllist:
            return None
        celllist = celllist.result

        for cell in celllist:
            if cell['id'] == 0:
                continue
            if cell['name'] == name:
                return cell['id']
        return None

    @classmethod
    def enable(cls, rootcell: bytes) -> RPCApi.Result:
        """
        启用 jailhouse hypervisor，并使用给定的 rootcell 数据。

        Args:
            rootcell (bytes): rootcell 的二进制内容

        Returns:
            RPCApi.Result: 操作结果
        """
        tf = TempFile()
        if not os.path.exists(cls.jh_dev):
            # 加载驱动
            logging.info("install jailhouse ko")
            r = cls.run_command(f'insmod {cls.jh_ko}')
            if not r:
                return RPCApi.Result(False, msg="insmod failed")

        # 保存rootcell到文件
        temp_fn = tf.save("rootcell", ".cell", rootcell)
        if temp_fn is None:
            return RPCApi.Result(False, msg="save temp file failed.")

        cmd = f'{cls.jh_exe} enable {temp_fn}'
        r = cls.run_command(cmd)
        if not r:
            return RPCApi.Result(False, msg='jailhouse enable faild.')

        return RPCApi.Result(True)

    @classmethod
    def disable(cls) -> RPCApi.Result:
        """
        禁用 jailhouse（如果已启用则执行 disable 操作）。

        Returns:
            RPCApi.Result: 操作结果
        """
        if not os.path.exists(cls.jh_dev):
            return RPCApi.Result(True)

        cmd = f'{cls.jh_exe} disable'
        if not cls.run_command(cmd):
            return RPCApi.Result(False, "disable failed.")
        return RPCApi.Result(True)

    @classmethod
    def list_cell(cls) -> RPCApi.Result:
        """
        列出当前系统中的 cell 列表并解析为字典列表。

        Returns:
            RPCApi.Result: 成功时 `result` 字段为 cell 字典列表
        """
        cmd = f"{cls.jh_exe} cell list"
        r = cls.run_command(cmd)
        if not r:
            return r

        cells = list()
        lines = r.result.split('\n')

        for line in lines[1:]:
            s = line.strip().split()
            if len(s) < 4:
                continue
            cells.append({
                'id': int(s[0]),
                'name': s[1],
                'status': s[2],
                'cpus': s[3]
            })
        return RPCApi.Result(True, result=cells)

    @classmethod
    def create_cell(cls, cell: bytes) -> RPCApi.Result:
        """
        创建一个新的 cell，cell 内容以二进制形式传入并写入临时文件。

        Args:
            cell (bytes): cell 二进制内容

        Returns:
            RPCApi.Result: 操作结果
        """
        tf = TempFile()
        temp_fn = tf.save("create_cell", ".cell", cell)
        if temp_fn is None:
            return RPCApi.Result(False, msg="save temp file failed")

        cmd = f"{cls.jh_exe} cell create {temp_fn}"
        r = cls.run_command(cmd)
        if not r:
            return r

        return RPCApi.Result(True)

    @classmethod
    def destroy_cell(cls, name: str) -> RPCApi.Result:
        """
        销毁指定名称的 cell。

        Args:
            name (str): 要销毁的 cell 名称

        Returns:
            RPCApi.Result: 操作结果
        """
        cell_id = cls.find_cell_id(name)
        if cell_id is None:
            return RPCApi.Result(False, msg=f"cell {name} not found")

        cmd = f"{cls.jh_exe} cell destroy {cell_id}"
        r = cls.run_command(cmd)
        if not r:
            return r

        return RPCApi.Result(True)

    @classmethod
    def load_cell(cls, name, addr, data) -> RPCApi.Result:
        """
        将二进制镜像加载到指定 cell 的给定地址。

        Args:
            name (str): cell 名称
            addr (int): 加载地址
            data (bytes): 镜像数据

        Returns:
            RPCApi.Result: 操作结果
        """
        tf = TempFile()
        cell_id = cls.find_cell_id(name)
        if cell_id is None:
            return RPCApi.Result(False, msg=f"cell {name} not found")

        temp_fn = tf.save("load", ".bin", data)
        if temp_fn is None:
            return RPCApi.Result(False, msg="save temp file failed.")

        cmd = f"{cls.jh_exe} cell load {cell_id} {temp_fn} -a {hex(addr)}"
        r = cls.run_command(cmd)
        if not r:
            return r

        return RPCApi.Result(True)

    @classmethod
    def start_cell(cls, name) -> RPCApi.Result:
        """
        启动指定的 cell。

        Args:
            name (str): cell 名称

        Returns:
            RPCApi.Result: 操作结果
        """
        cell_id = cls.find_cell_id(name)
        if cell_id is None:
            return RPCApi.Result(False, msg=f"cell {name} not found")

        cmd = f"{cls.jh_exe} cell start {cell_id}"
        r = cls.run_command(cmd)
        if not r:
            return r

        return RPCApi.Result(True)

    @classmethod
    def stop_cell(cls, name) -> RPCApi.Result:
        """
        停止（关闭）指定的 cell。

        Args:
            name (str): cell 名称

        Returns:
            RPCApi.Result: 操作结果
        """
        cell_id = cls.find_cell_id(name)
        if cell_id is None:
            return RPCApi.Result(False, msg=f"cell {name} not found")

        cmd = f"{cls.jh_exe} cell shutdown {cell_id}"
        r = cls.run_command(cmd)
        if not r:
            return r

        return RPCApi.Result(True)

    @classmethod
    def run_linux(cls, cell_fn, kernel_fn, dtb_fn, ramdisk_fn, bootargs):
        """
        使用 jailhouse 的 linux 子命令在给定的 cell 中运行 Linux 引导流程。

        Args:
            cell_fn (str): cell 文件路径
            kernel_fn (str): kernel 二进制路径
            dtb_fn (str): dtb 文件路径
            ramdisk_fn (str|None): ramdisk 文件路径（可为 None）
            bootargs (str): kernel 命令行参数

        Returns:
            RPCApi.Result: 子进程命令执行结果
        """
        if ramdisk_fn is None:
            cmd = f'{cls.jh_exe} cell linux -d {dtb_fn} {cell_fn} {kernel_fn} -c "{bootargs}"'
        else:
            cmd = f'{cls.jh_exe} cell linux -d {dtb_fn} -i {ramdisk_fn} {cell_fn} {kernel_fn} -c "{bootargs}"'

        return cls.run_command(cmd)



