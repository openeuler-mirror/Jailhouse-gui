import os
import sys
from typing import Optional, Any, List
import pathlib
import json
import platform
import tempfile
import shutil

_KB = 1024
_MB = 1024*1024
_GB = 1024*1024*1024


def to_human_addr(value: int) -> str:
    return hex(value)


def to_human_size(value: int) -> str:
    if value == 0:
        return "0"
    if value%_GB == 0:
        return f'{value//_GB}*GB'
    if value%_MB == 0:
        return f'{value//_MB}*MB'
    if value%_KB == 0:
        return f'{value//_KB}*KB'
    return str(value)


def from_human_num(s) -> Optional[int]:
    _globals = {
        '__builtins__':None,
        'KB': 1024,
        'MB': 1024*1024,
        'GB': 1024*1024*1024,
    }
    try:
        value = eval(s, _globals)
        return int(value)
    except:
        return None


def get_template_path(name: str) -> str:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        meipass = getattr(sys, '_MEIPASS')
        return os.path.join(meipass, "template", name)
    return os.path.join("assets", "template", name)

def get_cpio() -> str:
    if platform.system() == "Windows":
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            meipass = getattr(sys, '_MEIPASS')
            return os.path.join(meipass, "tools", "win32", "cpio.exe")
        current = os.path.abspath(os.path.dirname(__file__))
        return os.path.join(current, "tools", "win32", "cpio.exe")

    return "cpio"


class CpioUtil():
    def __init__(self, filename) -> None:
        self._filename = filename
        self._temp_dir = tempfile.mkdtemp(prefix='jh_')
        self._temp_cpio = None

    def __del__(self):
        shutil.rmtree(self._temp_dir)
        self._temp_dir = None

    def append(self, name: str, data: bytes) -> bool:
        if self._temp_cpio is None:
            temp = os.path.join(self._temp_dir, "temp.cpio")
            try:
                shutil.copy(self._filename, temp)
            except:
                return False
            self._temp_cpio = temp

        cwd = os.getcwd()
        cpio_exe = get_cpio()
        path = os.path.join(self._temp_dir, name)
        print("path: ", path)

        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        try:
            with open(path, "wb") as f:
                f.write(data)
        except:
            return False
    
        os.chdir(self._temp_dir)
        cmd = f"echo {name} | {cpio_exe} -oA -H newc -F temp.cpio"
        print(cmd)
        status = os.system(cmd)
        os.chdir(cwd)
        if status != 0:
            return False
        return True

    def get_bytes(self) -> Optional[bytes]:
        fn = self._filename
        if self._temp_cpio:
            fn = self._temp_cpio
        
        try:
            with open(fn, "rb") as f:
                return f.read()
        except:
            return None

    def save_as(self, dst: str) -> bool:
        fn = self._filename
        if self._temp_cpio:
            fn = self._temp_cpio

        try:
            shutil.copy(fn, dst)
        except:
            return False
        return True


def profile_load() -> dict:
    fn = os.path.join(pathlib.Path.home(), ".resource_tool")
    try:
        with open(fn, 'rt', encoding='utf8') as f:
            profile = json.load(f)
            if isinstance(profile, dict):
                return profile
            return {}
    except:
        return {}


class Profile(object):

    profile = profile_load()

    @classmethod
    def profile_get(cls, name, def_value) -> Any:
        value = cls.profile.get(name)
        if isinstance(value, type(def_value)):
            return value
        return def_value

    @classmethod
    def profile_set(cls, name: str, value: Any):
        cls.profile[name] = value
        fn = os.path.join(pathlib.Path.home(), ".resource_tool")
        try:
            with open(fn, 'wt', encoding='utf8') as f:
                json.dump(cls.profile, f)
        except:

            pass

    class Item(object):
        def __init__(self, name, def_value) -> None:
            self._name = name
            self._value = Profile.profile_get(name, def_value)

        def get(self):
            return self._value

        def set(self, value):
            if not isinstance(value, type(self._value)):
                return
            self._value = value
            Profile.profile_set(self._name, self._value)


if __name__ == '__main__':
    # cmd = f"{get_cpio()} -t -H newc -F test.cpio"
    # print(cmd)
    # os.system(cmd)

    # test_cpio = os.path.join(os.getcwd(), "test.cpio")
    # x = CpioUtil(test_cpio)
    # x.append("AAA", b'AAA')
    # x.save_as("test.cpio")

    import fdt
    import pyfdt
    from pyfdt.pyfdt import FdtBlobParse
    from pyfdt.pyfdt import FdtFsParse

    dtb = open("F:/02_实施中项目/04_613虚拟化/99_临时文件/d2000-linux/d2000-guestos.dtb", "rb").read()
    #x = fdt.parse_dtb(dtb)
    dts = open("platform/d2000-guestos.dts", "rt").read()
    x = fdt.parse_dts(dts)
    print(x)

    FdtBlobParse(dts)


    print(x.to_dtb(version=17))
