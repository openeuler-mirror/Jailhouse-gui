import os
import logging
import platform
import subprocess
import tempfile
from typing import Union, Optional
from api import RPCApi
import shlex


class TempFile(object):
    def __init__(self) -> None:
        self._temp_files = list()

    def __del__(self):
        self.clean()

    def save(self, prefix: str, suffix: str, data: Optional[Union[str,bytes]] = None) -> Optional[str]:
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

    def __init__(self) -> None:
        pass

    @classmethod
    def run_command(cls, cmd) -> RPCApi.Result:
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
        if not os.path.exists(cls.jh_dev):
            return RPCApi.Result(True)

        cmd = f'{cls.jh_exe} disable'
        if not cls.run_command(cmd):
            return RPCApi.Result(False, "disable failed.")
        return RPCApi.Result(True)

    @classmethod
    def list_cell(cls) -> RPCApi.Result:
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
        if ramdisk_fn is None:
            cmd = f'{cls.jh_exe} cell linux -d {dtb_fn} {cell_fn} {kernel_fn} -c "{bootargs}"'
        else:
            cmd = f'{cls.jh_exe} cell linux -d {dtb_fn} -i {ramdisk_fn} {cell_fn} {kernel_fn} -c "{bootargs}"'

        return cls.run_command(cmd)



