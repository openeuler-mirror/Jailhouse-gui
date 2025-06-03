"""
工具函数与配置管理模块。

本模块提供了系统工具集成与配置管理功能，包括：
- 数值与人类可读格式的转换（地址、大小）
- Cpio文件操作工具
- 模板文件路径解析
- 跨平台工具路径获取
- 配置文件（.resource_tool）的加载与管理

主要函数:
- to_human_addr: 将数值转换为十六进制地址字符串
- to_human_size: 将字节数转换为带单位的可读字符串
- from_human_num: 将带单位的字符串转换为数值
- get_template_path: 获取模板文件路径（支持打包环境）
- get_cpio: 获取Cpio工具路径（区分Windows/Linux）

主要类:
- CpioUtil: Cpio文件操作工具类
- Profile: 配置文件管理类
"""

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
    """
    将数值转换为十六进制地址字符串。
    
    Args:
        value: 数值地址
    Returns:
        十六进制字符串（如"0x1234"）
    """
    return hex(value)


def to_human_size(value: int) -> str:
    """
    将字节数转换为带单位的可读字符串（GB/MB/KB）。
    
    Args:
        value: 字节数
    Returns:
        带单位的字符串（如"10*MB"）
    """
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
    """
    将带单位的字符串转换为数值（支持KB/MB/GB）。
    
    Args:
        s: 带单位的字符串（如"10*MB"）
    Returns:
        转换后的整数，失败返回None
    """
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
    """
    获取模板文件路径（支持PyInstaller打包环境）。
    
    Args:
        name: 模板文件名
    Returns:
        模板文件的绝对路径
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        meipass = getattr(sys, '_MEIPASS')
        return os.path.join(meipass, "template", name)
    return os.path.join("assets", "template", name)

def get_cpio() -> str:
    """
    获取Cpio工具路径（Windows系统使用内置版本，Linux使用系统命令）。
    
    Returns:
        Cpio工具的绝对路径或命令名
    """
    if platform.system() == "Windows":
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            meipass = getattr(sys, '_MEIPASS')
            return os.path.join(meipass, "tools", "win32", "cpio.exe")
        current = os.path.abspath(os.path.dirname(__file__))
        return os.path.join(current, "tools", "win32", "cpio.exe")

    return "cpio"


class CpioUtil():
    """
    Cpio文件操作工具类。
    
    提供Cpio文件的追加内容、读取字节数据及另存为功能，
    自动管理临时目录用于文件操作。
    
    属性:
        _filename: 目标Cpio文件名
        _temp_dir: 临时工作目录
        _temp_cpio: 临时Cpio文件路径
    """
    def __init__(self, filename) -> None:
        """
        初始化Cpio工具类。
        
        Args:
            filename: 目标Cpio文件名
        """
        self._filename = filename
        self._temp_dir = tempfile.mkdtemp(prefix='jh_')
        self._temp_cpio = None

    def __del__(self):
        """析构函数，清理临时目录"""
        shutil.rmtree(self._temp_dir)
        self._temp_dir = None

    def append(self, name: str, data: bytes) -> bool:
        """
        向Cpio文件追加内容。
        
        Args:
            name: 追加的文件名
            data: 文件内容字节数据
        Returns:
            操作成功与否
        """
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
        """
        获取Cpio文件的字节数据（包含临时修改）。
        
        Returns:
            文件字节数据，失败返回None
        """
        fn = self._filename
        if self._temp_cpio:
            fn = self._temp_cpio
        
        try:
            with open(fn, "rb") as f:
                return f.read()
        except:
            return None

        return None

    def save_as(self, dst: str) -> bool:
        """
        将修改后的Cpio文件另存为新文件。
        
        Args:
            dst: 目标文件路径
        Returns:
            操作成功与否
        """
        fn = self._filename
        if self._temp_cpio:
            fn = self._temp_cpio

        try:
            shutil.copy(fn, dst)
        except:
            return False
        return True


def profile_load() -> dict:
    """
    加载配置文件（~/.resource_tool）。
    
    Returns:
        配置字典，加载失败返回空字典
    """
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
    """
    配置文件管理类。
    
    提供配置项的读取、保存功能，配置存储于~/.resource_tool文件，
    支持类型校验和持久化存储。
    
    属性:
        profile: 全局配置字典
    """

    profile = profile_load()

    @classmethod
    def profile_get(cls, name, def_value) -> Any:
        """
        获取配置项值（带类型校验）。
        
        Args:
            name: 配置项名称
            def_value: 默认值（决定返回类型）
        Returns:
            配置项值，类型匹配失败返回默认值
        """
        value = cls.profile.get(name)
        if isinstance(value, type(def_value)):
            return value
        return def_value

    @classmethod
    def profile_set(cls, name: str, value: Any):
        """
        设置配置项值并保存到文件。
        
        Args:
            name: 配置项名称
            value: 配置项值
        """
        cls.profile[name] = value
        fn = os.path.join(pathlib.Path.home(), ".resource_tool")
        try:
            with open(fn, 'wt', encoding='utf8') as f:
                json.dump(cls.profile, f)
        except:

            pass

    class Item(object):
        """
        配置项封装类。
        
        用于将配置项绑定为对象属性，支持类型安全的读写操作。
        
        属性:
            _name: 配置项名称
            _value: 配置项值
        """
        def __init__(self, name, def_value) -> None:
            """
            初始化配置项。
            
            Args:
                name: 配置项名称
                def_value: 默认值（决定类型）
            """
            self._name = name
            self._value = Profile.profile_get(name, def_value)

        def get(self):
            """获取配置项值"""
            return self._value

        def set(self, value):
            """
            设置配置项值（带类型校验）。
            
            Args:
                value: 要设置的值
            """
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
