from inspect import isclass, isfunction
import json
import os
from typing import Callable, Optional, List, Set, Any, Union
import logging
import toml
import blinker
import weakref
import abc
from result import Result, Ok, Err
from collections import OrderedDict
import traceback
import uuid
import itertools
import copy
import enum
import base64

# 资源结构
# Resource
#  ResourcePlatform
#    ResourceCPU
#    ResourceBoard
#  ResourceJailhouse
#    ResourceRootCell
#    ResourceComm
#    ResourcePCIDeviceList
#      ResourcePCIDevice*
#    ResourceGuestCellList
#      ResourceGuestCell
#        ResourceRunInfo


class ResourceBase: pass  # type: ignore
class Resource(ResourceBase): pass  # type: ignore
class ResourcePlatform(ResourceBase): pass  # type: ignore
class ResourceCPU(ResourceBase):  pass# type: ignore
class ResourceBoard(ResourceBase): pass  # type: ignore
class ResourceJailhouse(ResourceBase): pass  # type: ignore
class ResourceRootCell(ResourceBase): pass  # type: ignore
class ResourceGuestCellList(ResourceBase): pass  # type: ignore
class ResourceGuestCell(ResourceBase): pass  # type: ignore
class ResourceComm(ResourceBase): pass  # type: ignore

class ARMArch(enum.Enum):
    AArch32 = "AArch32"
    AArch64 = "AArch64"

class ResourceSignals:
    # 添加信号
    # 由parent发送， rsc=[添加的元素]
    add = blinker.Signal("add")
    # 删除信号
    # 由parent发送，rsc=[删除的元素]
    remove = blinker.Signal("remove")
    # 当前资源改变信号
    current_rsc = blinker.Signal("current_rsc")
    # 值改变信号，表示内部的值发生变化
    # 由发生变化的元素发送，part=["改变的内容"]
    value_changed = blinker.Signal("value_changed")
    # 当Resource第一次发生修改时发送
    # 由发送变化的Resource对象发送
    modified = blinker.Signal('modified')


class DictHelper(object):
    logger = logging.getLogger("DictHelper")

    class Item(object):
        def __init__(self, keys, types,
                     _get: Callable[[object, ], Result],
                     _set: Callable[[object, Any], bool],
                     _require=True) -> None:
            self.keys = keys
            self.types = types
            self.get = _get
            self.set = _set
            self.require = _require

    KB = 1024
    MB = 1024*1024
    GB = 1024*1024*1024

    def __init__(self) -> None:
        pass

    @classmethod
    def common_set(cls, name: str):
        def _setattr(obj, value) -> bool:
            if not hasattr(obj, name):
                cls.logger.error(f"not attr {name} in object {obj}")
                return False
            if isfunction(getattr(obj, name)):
                cls.logger.error(f"attr {name} in object {obj} is function")
                return False
            setattr(obj, name, value)
            return True
        return _setattr

    @classmethod
    def common_get(cls, name: str):
        def _getattr(obj: object) -> Result:
            if not hasattr(obj, name):
                cls.logger.error(f"attr {name} not found in {obj}")
                return Err(f"attr {name} not found in {obj}")
            if isfunction(getattr(obj, name)):
                cls.logger.error(f"attr {name} in object {obj} is function")
                return Err(f"attr {name} in object {obj} is function")
            return Ok(getattr(obj, name))
        return _getattr

    @classmethod
    def common_getset(cls, name: str):
        return DictHelper.common_get(name), DictHelper.common_set(name)

    @classmethod
    def size_get(cls, name: str):
        def _getattr(obj: object) -> Result[Any, str]:
            if not hasattr(obj, name):
                cls.logger.error(f"attr {name} not found in {obj}")
                return Err(f"attr {name} not found in {obj}")
            if isfunction(getattr(obj, name)):
                cls.logger.error(f"attr {name} in object {obj} is function")
                return Err(f"attr {name} in object {obj} is function")
            size = getattr(obj, name)
            if size == 0:
                return Ok(size)
            if size%cls.GB == 0:
                return Ok(f"{size//cls.GB}GB")
            if size%cls.MB == 0:
                return Ok(f"{size//cls.MB}MB")
            if size%cls.KB == 0:
                return Ok(f"{size//cls.KB}KB")
            return Ok(size)
        return _getattr

    @classmethod
    def size_set(cls, name: str):
        def _setattr(obj, value) -> bool:
            if not hasattr(obj, name):
                cls.logger.error(f"not attr {name} in object {obj}")
                return False
            if isfunction(getattr(obj, name)):
                cls.logger.error(f"attr {name} in object {obj} is function")
                return False
            if isinstance(value, str):
                try:
                    if value.endswith('GB'):
                        value = int(value[0:-2])*cls.GB
                    elif value.endswith('MB'):
                        value = int(value[0:-2])*cls.MB
                    elif value.endswith('KB'):
                        value = int(value[0:-2])*cls.KB
                    else:
                        cls.logger.error("invalid size value")
                        return False
                except:
                    cls.logger.error("invalid size value")
                    return False
            if not isinstance(value, int):
                cls.logger.error("type error")
                return False
            setattr(obj, name, value)
            return True
        return _setattr

    @classmethod
    def size_getset(cls, name: str):
        return DictHelper.size_get(name), DictHelper.size_set(name)

    @classmethod
    def from_dict(cls, items: List[Item], obj: object, value: dict) -> bool:
        """
        从字典加载数据
        """
        for item in items:
            keys = item.keys
            if isinstance(keys, str):
                keys = keys.split('.')

            if not isinstance(keys, (list, tuple)):
                cls.logger.error("items error {keys}")
                return False

            v = value
            for key in keys:
                if not isinstance(v, dict):
                    cls.logger.error(f"[{key}] not a dict")
                    traceback.print_stack()
                    return False
                v = v.get(key)

            if v is None and not item.require:
                cls.logger.debug(f"{keys} not found, ignore")
                continue

            if isclass(item.types) and issubclass(item.types, enum.Enum):
                # 字符串转枚举值
                enum_type = item.types
                enum_value = None
                for name in enum_type.__members__:
                    if v.upper() == name.upper():
                        enum_value = enum_type.__members__[name]
                        break
                if enum_value is None:
                    cls.logger.error(f'unknown enum value {v} for type {enum_type}')
                    return False
                v = enum_value

            if not isinstance(v, item.types):
                cls.logger.error(f'[{item.keys}]({v}) type error expect {item.types} but {type(v)}: {value}')
                return False

            ret = item.set(obj, v)
            if not ret:
                return ret

        return True

    @classmethod
    def to_dict(cls, items, obj) -> Optional[dict]:
        value = OrderedDict()
        for item in items:
            v: Result = item.get(obj)
            if v.is_err():
                return None
            v = v.value
            if not isinstance(v, item.types):
                cls.logger.error(f"[{item.keys}] type error, expect {item.types} but {type(v)}")
                return None

            if isinstance(v, enum.Enum):
                # 枚举转为字符串
                v = v.name

            keys = item.keys
            if isinstance(keys, str):
                keys = keys.split('.')

            if not isinstance(keys, (list, tuple)):
                cls.logger.error("items error")
                return None

            sub_dict = value
            for key in keys[0:-1]:
                if key not in sub_dict:
                    sub_dict[key] = OrderedDict()
                sub_dict = sub_dict[key]
            sub_dict[keys[-1]] = v

        return value


class MemRegion(object):
    """
    通用的mem region
    """
    items = [
        DictHelper.Item("addr", int, *DictHelper.common_getset("_addr")),
        DictHelper.Item("size", (str, int), *DictHelper.size_getset("_size")),
    ]

    def __init__(self, addr=0, size=0) -> None:
        super().__init__()
        assert(isinstance(addr, int) and isinstance(size, int))
        self._addr = addr
        self._size = size

    def addr(self) -> int:
        return self._addr

    def size(self) -> int:
        return self._size

    def set_addr(self, addr: int):
        assert(isinstance(addr, int))
        self._addr = addr

    def set_size(self, size: int):
        self._size = size

    def end(self) -> int:
        return self._addr+self._size

    def from_dict(self, value: dict) -> bool:
        return DictHelper.from_dict(self.items, self, value)

    def to_dict(self) -> Optional[dict]:
        return DictHelper.to_dict(self.items, self)

    def is_overlap(self, other) -> bool:
        u_min = min(self._addr, other._addr)
        u_max = max(self._addr+self._size, other._addr+other._size)
        return u_max-u_min < self._size+other._size

    @staticmethod
    def list_overlap(regions: list) -> bool:
        """
        检查region列表是否重叠
        """
        for pair in itertools.combinations(regions, 2):
            if pair[0].is_overlap(pair[1]):
                return False
        return True

    @staticmethod
    def list_merge(regions: list) -> list:
        regions = sorted(regions, key=lambda x: x.addr())
        temp = None
        new_regions = list()
        for mem in regions:
            if temp is None:
                temp = mem
                continue
            if mem.addr() >= temp.addr() and mem.addr() < (temp.addr()+temp.size()):
                size = max((temp.size(), mem.addr()+mem.size()-temp.addr))
                temp = MemRegion(temp.addr(), size)
            else:
                new_regions.append(temp)
                temp = None
        if temp is not None:
            new_regions.append(temp)
        return new_regions

    def __repr__(self) -> str:
        return f"{self._size:x}@{self._addr:x}"

class MemRegionList(object):
    def __init__(self) -> None:
        self._regions: List[MemRegion] = list()

    def add(self, addr, size):
        self._regions.append(MemRegion(addr, size))

    def is_overlap(self, addr, size) -> bool:
        for region in self._regions:
            if region.is_overlap(MemRegion(addr, size)):
                return True
        return False

    def contains( self, m: MemRegion ) -> bool:
        # 检查是否包含内存区间
        for region in self._regions:
            if region.addr() <= m.addr() and m.addr()+m.size() <= region.addr()+region.size():
                return True
        return False


class MemMap(object):
    """
    通用的mem map
    """

    class Type(enum.Enum):
        NORMAL = "normal"
        RESOURCE_TABLE = "resource-table"

        @classmethod
        def names(cls):
            names = list()
            for n,e in cls.__members__.items():
                names.append(e.value)
            return names

        @classmethod
        def from_name(cls, name):
            for n,e in cls.__members__.items():
                if e.value == name:
                    return e
            return None

    items = [
        DictHelper.Item("phys", int, *DictHelper.common_getset("_phys")),
        DictHelper.Item("virt", int, *DictHelper.common_getset("_virt")),
        DictHelper.Item("size", (str, int), *DictHelper.size_getset("_size")),
        DictHelper.Item("comment", str, *DictHelper.common_getset("_comment"), False),
        DictHelper.Item("type", Type, *DictHelper.common_getset("_type"), False),
    ]

    def __init__(self, phys: int, virt: int, size: int, type=Type.NORMAL, comment='') -> None:
        super().__init__()
        self._phys = phys
        self._virt = virt
        self._size = size
        self._type = type
        self._comment = comment

    def phys(self) -> int:
        return self._phys

    def virt(self) -> int:
        return self._virt

    def size(self) -> int:
        return self._size

    def comment(self) -> str:
        return self._comment

    def type(self) -> Type:
        return self._type

    def from_dict(self, value: dict) -> bool:
        return DictHelper.from_dict(self.items, self, value)

    def to_dict(self) -> Optional[dict]:
        return DictHelper.to_dict(self.items, self)

    def is_overlap(self, other) -> bool:
        u_min = min(self._phys, other._phys)
        u_max = max(self._phys+self._size, other._phys+other._size)
        if u_max-u_min < self._size+other._size:
            return True
        u_min = min(self._virt, other._virt)
        u_max = max(self._virt+self._size, other._virt+other._size)
        if u_max-u_min < self._size+other._size:
            return True
        return False

    @staticmethod
    def list_overlap(maps: list) -> bool:
        """
        检查region列表是否重叠
        """
        for pair in itertools.combinations(maps, 2):
            if pair[0].is_overlap(pair[1]):
                return False
        return True

    def __repr__(self) -> str:
        return f"{self._size:x}@{self._phys}:{self._virt}"


class ResourceBase(metaclass=abc.ABCMeta):
    logger = logging.getLogger("ResourceBase")

    def __init__(self, parent) -> None:
        super().__init__()
        self._parent = None
        if parent is not None:
            self._parent = weakref.ref(parent)
        self._children = list()
        self._properities = dict()
        self._is_modified = False

    def is_modified(self, with_children=False):
        if self._is_modified:
            return True
        if not with_children:
            return self._is_modified

        for child in self._children:
            if child.is_modified(True):
                return True
        return False

    def parent(self) -> Optional[ResourceBase]:
        if self._parent is None:
            self.logger.error(f"{self} _parent is None")
            return None
        return self._parent()

    def index(self, child: ResourceBase) -> int:
        return self._children.index(child)

    def my_index(self) -> int:
        return self.parent().index(self)

    def ancestor(self, _type) -> Optional[ResourceBase]:
        if isinstance(self, _type):
            return self

        p: ResourceBase =  self.parent()
        while p is not None:
            if isinstance(p, _type):
                return p
            p = p.parent()
        return None

    def find(self, _type) -> Optional[ResourceBase]:
        root = self.ancestor(Resource)
        if root is None:
            return None

        def _find(o: ResourceBase, _type):
            if isinstance(o, _type):
                return o
            for c in o._children:
                x = _find(c, _type)
                if x is not None:
                    return x
        return _find(root, _type)

    def __len__(self):
        return len(self._children)

    def __getitem__(self, item):
        if item<0 or item>=len(self._children):
            return None
        return self._children[item]

    def set_prop(self, key, value):
        self._properities[key] = value

    def get_prop(self, key):
        return self._properities.get(key)

    def set_modified(self):
        self._is_modified = True
        ResourceSignals.modified.send(self)

    @classmethod
    def modified(cls, fun):
        def wrapper(*args):
            if len(args) == 0 or not isinstance(args[0], ResourceBase):
                return fun(*args)
            rsc = args[0]
            rsc._is_modified = True
            # cls.logger.debug(f"modified {fun}: {args}")
            ret = fun(*args)
            ResourceSignals.modified.send(rsc)
            return ret
        return wrapper

    @abc.abstractmethod
    def label(self) -> str:
        return ""

    @abc.abstractmethod
    def from_dict(self, value: dict) -> bool:
        pass

    @abc.abstractmethod
    def to_dict(self) -> Optional[dict]:
        pass


class CPUDevice(object):
    logger = logging.getLogger("CPUDevice")

    items = [
        DictHelper.Item("addr", int, *DictHelper.common_getset("_addr")),
        DictHelper.Item("size", int, *DictHelper.common_getset("_size")),
        DictHelper.Item("type", str, *DictHelper.common_getset("_type"), False),
    ]

    uart_types = (
        "pl011", "8250"
    )

    def __init__(self, name: str):
        super().__init__()
        self._name = name
        self._addr = 0
        self._size = 0
        self._irq = list()
        self._type = ""

    def name(self) -> str:
        return self._name

    def addr(self) -> int:
        return self._addr

    def size(self) -> int:
        return self._size

    def irq(self) -> List[int]:
        return self._irq

    def type(self) -> str:
        return self._type

    def from_dict(self, value: dict) -> bool:
        if not DictHelper.from_dict(self.items, self, value):
            return False

        self._irq.clear()
        irq = value.get("irq")
        if isinstance(irq, int):
            self._irq.append(irq)
        elif isinstance(irq, (tuple, list)):
            for v in irq:
                if not isinstance(v, int):
                    return False
                self._irq.append(v)

        # 对于串口设备，必须要指定串口类型
        if self._name.startswith("uart"):
            if self._type not in self.uart_types:
                self.logger.error(f"must specific type for uart device {self}.")
                return False
        return True

    def to_dict(self) -> Optional[dict]:
        value = DictHelper.to_dict(self.items, self)
        if value is None:
            ResourceCPU.logger.error(f"CPUDevice to dict faied.")
            return None
        value['irq'] = self._irq
        value['attr'] = self._type
        return value

    def __repr__(self) -> str:
        return f'{self._name}@{self._addr:x}'


class CPURegion(object):
    class Type(enum.Enum):
        MISC = "misc"
        DRAM = "dram"
        SRAM = "sram"
        PCI_ECAM = "pci_ecam"
        PCI_IO = "pci_io"
        PCI_MEM = "pci_mem"

    items = [
        DictHelper.Item("type", Type, *DictHelper.common_getset("_type"), False),
        DictHelper.Item("addr", int, *DictHelper.common_getset("_addr")),
        DictHelper.Item("size", (str, int), *DictHelper.size_getset("_size")),
    ]

    def __init__(self, name: str) -> None:
        self._name = name
        self._type = self.Type.MISC
        self._addr = 0
        self._size = 0

    def name(self):
        return self._name

    def type(self) -> Type:
        return self._type

    def attr(self) -> str:
        return ""

    def addr(self) -> int:
        return self._addr

    def size(self) -> int:
        return self._size

    def from_dict(self, value: dict) -> bool:
        if not DictHelper.from_dict(self.items, self, value):
            return False
        return True

    def to_dict(self) -> Optional[dict]:
        return DictHelper.to_dict(self.items, self)


class ResourceCPU(ResourceBase):
    logger = logging.getLogger('ResourceCPU')

    items = [
        DictHelper.Item("system.name", str, *DictHelper.common_getset("_name")),
        DictHelper.Item("system.cpu_count", int, *DictHelper.common_getset("_cpu_count")),
        DictHelper.Item("system.gic.version", int, *DictHelper.common_getset("_gic_version")),
        DictHelper.Item("system.gic.gicd_base", int, *DictHelper.common_getset("_gicd_base")),
        DictHelper.Item("system.gic.gicr_base", int, *DictHelper.common_getset("_gicr_base")),
        DictHelper.Item("system.gic.gicc_base", int, *DictHelper.common_getset("_gicc_base")),
        DictHelper.Item("system.gic.gich_base", int, *DictHelper.common_getset("_gich_base")),
        DictHelper.Item("system.gic.gicv_base", int, *DictHelper.common_getset("_gicv_base")),
    ]

    def __init__(self, parent):
        super().__init__(parent)

        self._name = ""
        self._cpu_count = 0

        self._gic_version = 3
        self._gicd_base = 0
        self._gicr_base = 0
        self._gicc_base = 0
        self._gich_base = 0
        self._gicv_base = 0

        self._devices: List[CPUDevice] = list()
        self._regions: List[CPURegion] = list()

    def name(self) -> str:
        return self._name

    def cpu_count(self):
        return self._cpu_count

    def gic_version(self) -> int:
        return self._gic_version

    def gicd_base(self) -> int:
        return self._gicd_base

    def gicr_base(self) -> int:
        return self._gicr_base

    def gicc_base(self) -> int:
        return self._gicc_base

    def gich_base(self) -> int:
        return self._gich_base

    def gicv_base(self) -> int:
        return self._gicv_base

    def regions(self) -> List[CPURegion]:
        return self._regions

    def devices(self) -> List[CPUDevice]:
        return self._devices

    def find_device(self, name: str) -> Optional[CPUDevice]:
        for dev in self._devices:
            if dev.name() == name:
                return dev
        return None

    def find_region(self, name: str) -> Optional[MemRegion]:
        for region in self._regions:
            if name == region.name():
                return MemRegion(region.addr(), region.size())
        return None

    def label(self) -> str:
        return "CPU"

    def from_dict(self, cpu: dict) -> bool:
        if not DictHelper.from_dict(self.items, self, cpu):
            self.logger.error("cpu from dict failed.")
            return False

        self._devices.clear()
        self._regions.clear()

        devices = cpu.get("devices")
        if not isinstance(devices, dict):
            self.logger.error("[devices] ont a dict")
            return False
        for k, v in devices.items():
            dev = CPUDevice(k)
            if not dev.from_dict(v):
                self.logger.error(f"cpudevice from dict failed {k}.")
                return False
            self._devices.append(dev)

        regions = cpu.get("regions")
        if not isinstance(regions, dict):
            self.logger.error("[regions] is not a dict")
            return False
        for k, v in regions.items():
            region = CPURegion(k)
            if not region.from_dict(v):
                self.logger.error("region from dict failed.")
                return False
            self._regions.append(region)
        return True

    def to_dict(self) -> Optional[dict]:
        cpu = DictHelper.to_dict(self.items, self)
        if cpu is None:
            return None

        regions = OrderedDict()
        for region in self._regions:
            v = region.to_dict()
            if v is None:
                self.logger.error("region to dict failed.")
                return None
            regions[region.name()] = v

        devices = OrderedDict()
        for dev in self._devices:
            v = dev.to_dict()
            if v is None:
                self.logger.error("mmio dev to dict failed.")
                return None
            devices[dev.name()] = v

        cpu['regions'] = regions
        cpu["devices"] = devices
        return cpu


class ResourceBoard(ResourceBase):
    logger = logging.getLogger('ResourceBoard')

    items = [
        DictHelper.Item("info.name", str, *DictHelper.common_getset("_name")),
        DictHelper.Item("info.model", str, *DictHelper.common_getset("model")),
        DictHelper.Item("info.vendor", str, *DictHelper.common_getset("vendor")),
    ]

    def __init__(self, parent):
        super().__init__(parent)

        self._name = ""
        self.model = ""
        self.vendor = ""
        self.devices = list()
        # None为默认值，表示选择所有CPU
        self._cpus: Optional[Set[int]] = None
        self._ram_regions: List[MemRegion] = list()

    def ram_regions(self) -> List[MemRegion]:
        return self._ram_regions

    def ram_region_list(self) -> MemRegionList:
        board_mem = MemRegionList()
        for mem in self._ram_regions:
            board_mem.add( mem.addr(), mem.size() )
        return board_mem

    def cpus(self) -> Set[int]:
        if self._cpus is None:
            cpu: ResourceCPU = self.find(ResourceCPU)
            return set([i for i in range(cpu.cpu_count())])
        return self._cpus

    @ResourceBase.modified
    def set_cpus(self, cpus: Set[int]):
        self._cpus = cpus

    def name(self):
        return self._name

    def label(self) -> str:
        return "Board"

    @ResourceBase.modified
    def set_ram_regions(self, regions: List[MemRegion]):
        self._ram_regions = regions

    def from_dict(self, board: dict) -> bool:
        if not DictHelper.from_dict(self.items, self, board):
            self.logger.error("board from dict failed.")
            return False

        devices = board['system'].get('devices')
        if not isinstance(devices, list):
            self.logger.error(f'[devices]({devices}) not found')
            return False
        self.devices.clear()
        for dev in devices:
            if not isinstance(dev, str):
                self.logger.error("type error")
                return False
            self.devices.append(dev)

        self._ram_regions.clear()
        ram_regions = board['system'].get("ram_regions")
        if not isinstance(ram_regions, list):
            self.logger.error(f'[ram_regions]({ram_regions}) not found.')
            return False
        for region in ram_regions:
            if not isinstance(region, dict):
                self.logger.error(f'ram_region({region} not a dict)')
                return False
            v = MemRegion()
            if not v.from_dict(region):
                self.logger.error(f'ram region form dict failed: {region}')
                return False
            self._ram_regions.append(v)

        cpus = board.get('cpus', None)
        if isinstance(cpus, list):
            self._cpus = set(cpus)

        return True

    def to_dict(self) -> Optional[dict]:
        board = DictHelper.to_dict(self.items, self)
        if board is None:
            return None

        if 'system' not in board:
            board['system'] = dict()
        board['system']['devices'] = self.devices
        ram_regions = list()
        for region in self._ram_regions:
            ram_regions.append(region.to_dict())
        board['system']['ram_regions'] = ram_regions

        if self._cpus is not None:
            board['cpus'] = list(self._cpus)

        return board


class ResourcePlatform(ResourceBase):
    def __init__(self, parent):
        super().__init__(parent)

        self._cpu = ResourceCPU(self)
        self._board = ResourceBoard(self)
        self._children.append(self._cpu)
        self._children.append(self._board)

    def cpu(self):
        return self._cpu

    def board(self):
        return self._board

    def label(self) -> str:
        return "硬件平台"

    @staticmethod
    def update_platform_cpu(old_value: dict) -> Optional[dict]:
        """
        由于配置内容版本更新，加载可能失败，该函数用于更新配置内容
        参数为旧的字典内容，返回新的字典内容
        """
        system = old_value.get('system')
        if not isinstance(system, dict):
            return None
        cpu_name = system.get("name")
        if not isinstance(cpu_name, str):
            return None

        cpu: PlatformMgr.CPU = PlatformMgr.get_instance().find_cpu(cpu_name)
        if cpu is None:
            logging.error(f"can not find cpu {cpu_name} from platform")
            return None
        return cpu.value

    def from_dict(self, value: dict) -> bool:
        cpu = value.get("cpu")
        if not isinstance(cpu, dict):
            self.logger.error("[cpu] not a dict")
            return False
        board = value.get("board")
        if not isinstance(board, dict):
            self.logger.error("[board] not a dict")
            return False

        # 如果加载失败，则使用平台配置
        if not self._cpu.from_dict(cpu):
            cpu = self.update_platform_cpu(cpu)
            if not self._cpu.from_dict(cpu):
                return False
            logging.info("update platform cpu.")
            self._cpu.set_modified()

        if not self._board.from_dict(board):
            return False
        return True

    def to_dict(self) -> Optional[dict]:
        platform = OrderedDict()
        cpu = self._cpu.to_dict()
        if cpu is None:
            self.logger.error(f"get cpu dict failed")
            return None
        platform['cpu'] = cpu

        board = self._board.to_dict()
        if board is None:
            self.logger.error(f"get board dict failed")
            return None
        platform['board'] = board

        return platform


class ResourceComm(ResourceBase):
    items = [
        DictHelper.Item("ivshmem_phys", int,  *DictHelper.common_getset("_ivshmem_phys")),
        DictHelper.Item("ivshmem_state_size", (int, str),  *DictHelper.common_getset("_ivshmem_state_size")),
        DictHelper.Item("ivshmem_rw_size", (int, str),  *DictHelper.common_getset("_ivshmem_rw_size")),
        DictHelper.Item("ivshmem_out_size", (int, str),  *DictHelper.common_getset("_ivshmem_out_size")),
    ]
    def __init__(self, parent) -> None:
        super().__init__(parent)

        self._ivshmem_phys = 0
        self._ivshmem_state_size = 0x1000
        self._ivshmem_rw_size = 0x1000
        self._ivshmem_out_size = 1024*1024

    def ivshmem_phys(self):
        return self._ivshmem_phys

    def ivshmem_state_size(self):
        return self._ivshmem_state_size

    def ivshmem_rw_size(self):
        return self._ivshmem_rw_size

    def ivshmem_out_size(self):
        return self._ivshmem_out_size

    @ResourceBase.modified
    def set_ivshmem_phys(self, v):
        self._ivshmem_phys = v

    @ResourceBase.modified
    def set_ivshmem_state_size(self, v):
        self._ivshmem_state_size = v

    @ResourceBase.modified
    def set_ivshmem_rw_size(self, v):
        self._ivshmem_rw_size = v

    @ResourceBase.modified
    def set_ivshmem_out_size(self, v):
        self._ivshmem_out_size = v

    def label(self) -> str:
        return "核间通信"

    def from_dict(self, value: dict) -> bool:
        if not DictHelper.from_dict(self.items, self, value):
            return False
        return True

    def to_dict(self) -> Optional[dict]:
        return DictHelper.to_dict(self.items, self)


class ResourceRootCell(ResourceBase):
    items = [
        DictHelper.Item("name",          str,  *DictHelper.common_getset("_name")),
        DictHelper.Item("debug_console", str,  *DictHelper.common_getset("_debug_console")),
        DictHelper.Item("vpci_irq_base", int,  *DictHelper.common_getset("_vpci_irq_base"), False),
    ]

    class PCIMMConfig(object):
        items = [
            DictHelper.Item("base_addr",       int,  *DictHelper.common_getset("base_addr")),
            DictHelper.Item("bus_count",    int,  *DictHelper.common_getset("bus_count")),
            DictHelper.Item("domain",     int,  *DictHelper.common_getset("domain")),
        ]

        def __init__(self, addr=0, bus_count=1, domain=1):
            self.base_addr = addr
            self.bus_count = bus_count
            self.domain = domain

        def to_dict(self) -> Optional[dict]:
            return DictHelper.to_dict(self.items, self)

        def from_dict(self, value: dict) -> bool:
            ok = DictHelper.from_dict(self.items, self, value)
            # FIXME 强制总线个数为1
            self.bus_count = 1
            return ok

    def __init__(self, parent):
        super().__init__(parent)
        self._name = ""
        self._debug_console = ""
        self._pci_mmconfig = self.PCIMMConfig()
        self._hypervisor = MemRegion(0,0)
        self._system_mem: List[MemRegion] = list()
        self._vpci_irq_base = 100

    @classmethod
    def check_name(cls, name: str) -> bool:
        if not isinstance(name, str):
            return False
        if len(name) == 0:
            return False
        if len(name) > 31:
            return False
        for c in name:
            if not (c.isalnum() or c=='-' or c=='_'):
                return False
        return True

    def name(self) -> str:
        return self._name

    def get_debug_console(self) -> str:
        return self._debug_console

    def vpci_irq_base(self):
        return self._vpci_irq_base

    @ResourceBase.modified
    def set_name(self, name: str) -> bool:
        if not self.check_name(name):
            return False
        self._name = name
        return True

    @ResourceBase.modified
    def set_vpci_irq_base(self, irq: int):
        self._vpci_irq_base = irq

    @ResourceBase.modified
    def set_debug_console(self, name: Optional[str]):
        self.logger.info(f"set debug console {name}")
        if name is None:
            name = ""
        self._debug_console = name

    def pci_mmconfig(self) -> PCIMMConfig:
        return self._pci_mmconfig

    @ResourceBase.modified
    def set_pci_mmconfig(self, cfg) -> bool:
        if not isinstance(cfg, self.PCIMMConfig):
            self.logger.error("type error")
            return False
        self._pci_mmconfig = cfg
        self.logger.info(f"set pci mmconfig {cfg.to_dict()}")
        return False

    def hypervisor(self) -> MemRegion:
        return self._hypervisor

    @ResourceBase.modified
    def set_hypervisor(self, hyp: MemRegion) -> bool:
        if not isinstance(hyp, MemRegion):
            return False
        self._hypervisor = hyp
        self.logger.info(f"set hypervisor {hyp.to_dict()}")
        return True

    def system_mem(self) -> List[MemRegion]:
        return self._system_mem

    @ResourceBase.modified
    def set_system_mem(self, regions: List[MemRegion]) -> bool:
        self._system_mem = regions
        return True

    def label(self) -> str:
        return "Root Cell"

    def from_dict(self, value: dict) -> bool:
        if not DictHelper.from_dict(self.items, self, value):
            self.logger.error("")
            return False

        if not self._pci_mmconfig.from_dict(value.get("pci_mmconfig")):
            self.logger.error("pci_mmconfig from dict failed.")
            return False
        if not self._hypervisor.from_dict(value.get("hypervisor")):
            self.logger.error("hypervisor from dict failed.")
            return False

        self._system_mem.clear()
        sys_mem = value.get("system_memory")
        if isinstance(sys_mem, (list, tuple)):
            for mem in sys_mem:
                region = MemRegion(0,0)
                if not region.from_dict(mem):
                    self.logger.error("invalid system mem")
                    continue
                self._system_mem.append(region)

        return True

    def to_dict(self) -> Optional[dict]:
        rootcell = DictHelper().to_dict(self.items, self)
        if rootcell is None:
            self.logger.error("root cell to dict failed.")
            return None

        pci_mmconfig = self._pci_mmconfig.to_dict()
        if pci_mmconfig is None:
            self.logger.error("pci_mmconfig to dict failed")
            return None

        hypervisor = self._hypervisor.to_dict()
        if hypervisor is None:
            self.logger.error("hypervisor to dict failed")
            return None

        sys_mem = list()
        for mem in self._system_mem:
            sys_mem.append(mem.to_dict())

        rootcell["pci_mmconfig"] = pci_mmconfig
        rootcell["hypervisor"] = hypervisor
        rootcell["system_memory"] = sys_mem

        return rootcell


class ImageInfo(object):
    items = [
        DictHelper.Item("enable",   bool, *DictHelper.common_getset("enable")),
        DictHelper.Item("name",     str, *DictHelper.common_getset("name")),
        DictHelper.Item("addr",     int, *DictHelper.common_getset("addr")),
        DictHelper.Item("filename", str, *DictHelper.common_getset("filename")),
    ]
    def __init__(self) -> None:
        self.enable = False
        self.name = ""
        self.addr = 0
        self.filename = ""

    def from_dict(self, value: dict) -> bool:
        return DictHelper.from_dict(self.items, self, value)

    def to_dict(self) -> Optional[dict]:
        return DictHelper.to_dict(self.items, self)

    def __str__(self) -> str:
        return f"{self.name} {self.addr:x}"

class OSRunInfoBase(object):
    """
    子类的名称必须为 <OS>+RunInfo
    """
    def __init__(self):
        pass

    @classmethod
    def get_os_names(cls):
        names = list()
        for subc in cls.__subclasses__():
            name: str = subc.__name__
            if name.endswith('RunInfo'):
                names.append(name[0:-7])
        return names

    @classmethod
    def get_subclass(cls, name):
        if not isinstance(name, str):
            return None
        name = name + "RunInfo"
        for subc in cls.__subclasses__():
            if name == subc.__name__:
                return subc
        return None

    @abc.abstractmethod
    def name(self, value: dict) -> bool:
        return ""

    @abc.abstractmethod
    def from_dict(self, value: dict) -> bool:
        self.__class__
        return False

    @abc.abstractmethod
    def to_dict(self) -> Optional[dict]:
        return None

class CommonOSRunInfo(OSRunInfoBase):
    items = [
        DictHelper.Item("reset_addr",   int, *DictHelper.common_getset("_reset_addr"), False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._images: List[ImageInfo] = list()
        # 在GuestCell中也包含reset_addr， 这里的值偏向与动态， GuestCell里的
        # reset_addr偏向与全局
        self._reset_addr = 0

    def name(self) -> str:
        return 'CommonOS'

    def reset_addr(self) -> int:
        return self._reset_addr

    def add_image(self, image: ImageInfo):
        self._images.append(image)

    def clear_image(self):
        self._images.clear()

    def set_reset_addr(self, addr: int) -> bool:
        if not isinstance(addr, int):
            return False
        self._reset_addr = addr

    def images(self) -> List[ImageInfo]:
        return self._images

    def from_dict(self, value: dict) -> bool:
        DictHelper.from_dict(self.items, self, value)
        images = value.get("images")
        if not isinstance(images, list):
            return True
        for image in images:
            image_info = ImageInfo()
            if image_info.from_dict(image):
                self._images.append(image_info)
        return True

    def to_dict(self) -> Optional[dict]:
        value = DictHelper.to_dict(self.items, self)
        images = list()
        for image in self._images:
            images.append(image.to_dict())
        value['images'] = images
        return value


class LinuxRunInfo(OSRunInfoBase):
    items = [
        DictHelper.Item("kernel",     str, *DictHelper.common_getset("kernel")),
        DictHelper.Item("devicetree", str, *DictHelper.common_getset("devicetree")),
        DictHelper.Item("ramdisk",    str, *DictHelper.common_getset("ramdisk")),
        DictHelper.Item("bootargs",   str, *DictHelper.common_getset("bootargs")),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.kernel = ""
        self.devicetree = ""
        self.ramdisk = ""
        self.bootargs = ""
        self.ramdisk_overlay = list()

    def name(self):
        return 'Linux'

    def from_dict(self, value: dict) -> bool:
        if not isinstance(value, (dict, OrderedDict)):
            return False
        ok = DictHelper.from_dict(self.items, self, value)
        if not ok:
            return False
        overlay = value.get("ramdisk_overlay")
        if isinstance(overlay, list):
            for item in overlay:
                if isinstance(item, str):
                    self.ramdisk_overlay.append(item)
        return True

    def to_dict(self) -> Optional[dict]:
        value = DictHelper.to_dict(self.items, self)
        value['ramdisk_overlay'] = self.ramdisk_overlay
        return value


class ResourceRunInfo(ResourceBase):
    def __init__(self, parent) -> None:
        super().__init__(parent)

        self._os_runinfo: OSRunInfoBase = CommonOSRunInfo()

    def label(self) -> str:
        return "runinfo"

    def os_runinfo(self) -> Optional[OSRunInfoBase]:
        return self._os_runinfo

    @ResourceBase.modified
    def set_os_runinfo(self, runinfo: OSRunInfoBase) -> bool:
        if not isinstance(runinfo, OSRunInfoBase):
            return False
        self._os_runinfo = copy.deepcopy(runinfo)
        return True

    def from_dict(self, value: dict) -> bool:
        if not isinstance(value, dict):
            return False

        os_type = value.get('os_type')
        os_runinfo = value.get('os_runinfo')
        if os_type is None or os_runinfo is None:
            return True
        if os_type not in OSRunInfoBase.get_os_names():
            self.logger.error(f"unsupport os type: {os_type}")
            return True

        self._os_runinfo = OSRunInfoBase.get_subclass(os_type)()
        self._os_runinfo.from_dict(os_runinfo)
        return True

    def to_dict(self) -> Optional[dict]:
        value = OrderedDict()
        if self._os_runinfo is not None:
            value['os_type'] = self._os_runinfo.name()
            value['os_runinfo'] = self._os_runinfo.to_dict()
        return value


class ResourceGuestCell(ResourceBase):
    items = [
        DictHelper.Item("unique_id",    str,     *DictHelper.common_getset("_unique_id")),
        DictHelper.Item("name",         str,     *DictHelper.common_getset("_name")),
        DictHelper.Item("arch",         ARMArch, *DictHelper.common_getset("_arch")),
        DictHelper.Item("virt_console", bool,    *DictHelper.common_getset("_virt_console")),
        DictHelper.Item("use_virt_cpuid", bool,    *DictHelper.common_getset("_use_virt_cpuid"), False),
        DictHelper.Item("ivshmem_virt_addr", int,*DictHelper.common_getset("_ivshmem_virt_addr")),
        DictHelper.Item("comm_region",  int,     *DictHelper.common_getset("_comm_region")),
        DictHelper.Item("console",      str,     *DictHelper.common_getset("_console"), False),
        DictHelper.Item("reset_addr",   int,     *DictHelper.common_getset("_reset_addr"), False),
    ]
    def __init__(self, parent):
        super().__init__(parent)
        self._unique_id = str(uuid.uuid1())
        self._name = ""
        self._arch = ARMArch.AArch64
        self._virt_console = True
        self._use_virt_cpuid = False
        self._ivshmem_virt_addr = 0
        self._comm_region = 0
        self._console = ''
        self._reset_addr = 0
        # 系统内存
        self._system_mem: List[MemMap] = list()
        # 其他内存映射
        self._memmaps: List[MemMap] = list()
        self._cpus: Set[int] = set()
        self._devices: List[str] = list()
        self._pci_devices: List[str] = list()

        self._runinfo = ResourceRunInfo(self)
        self._children.append(self._runinfo)

    @classmethod
    def check_name(cls, name: str) -> bool:
        if not isinstance(name, str):
            return False
        if len(name) == 0:
            return False
        if len(name) > 31:
            return False
        for c in name:
            if not (c.isalnum() or c=='-' or c=='_'):
                return False
        return True

    def unique_id(self) -> str:
        return self._unique_id

    def name(self) -> str:
        return self._name

    def arch(self) -> ARMArch:
        return self._arch

    def virt_console(self) -> bool:
        return self._virt_console

    def virt_cpuid(self) -> bool:
        return self._use_virt_cpuid

    def ivshmem_virt_addr(self) -> int:
        return self._ivshmem_virt_addr

    def comm_region(self) -> int:
        return self._comm_region

    def system_mem(self) -> List[MemMap]:
        return self._system_mem

    def memmaps(self) -> List[MemMap]:
        return self._memmaps

    def cpus(self) -> Set[int]:
        return self._cpus

    def devices(self) -> List[str]:
        return self._devices

    def pci_deivces(self) -> List[str]:
        return self._pci_devices

    def runinfo(self) -> ResourceRunInfo:
        return self._runinfo

    def console(self) -> str:
        return self._console

    def reset_addr(self) -> int:
        return self._reset_addr

    def system_mem_resource_table(self) -> Optional[MemMap]:
        for mem in self._system_mem:
            if mem.type() is MemMap.Type.RESOURCE_TABLE:
                return mem

    def system_mem_normal(self) -> List[MemMap]:
        mems = list()
        for mem in self._system_mem:
            if mem.type() is not MemMap.Type.RESOURCE_TABLE:
                mems.append(mem)
        return mems

    @ResourceBase.modified
    def set_name(self, name):
        self._name = name
        ResourceSignals.value_changed.send(self, part='name')

    @ResourceBase.modified
    def set_system_mem(self, regions: List[MemMap]) -> bool:
        if not isinstance(regions, (list, tuple)):
            return False
        if not all(map(lambda x: isinstance(x, MemMap), regions)):
            return False
        self._system_mem = regions
        return True

    @ResourceBase.modified
    def set_memmaps(self, mmaps: List[MemMap]) -> bool:
        if not isinstance(mmaps, (list, tuple)):
            return False
        if not all(map(lambda x: isinstance(x, MemMap), mmaps)):
            return False
        self._memmaps = mmaps
        return True

    @ResourceBase.modified
    def set_arch(self, arch: ARMArch):
        self._arch = arch

    @ResourceBase.modified
    def set_virt_console_enable(self, en: bool):
        self._virt_console = en

    @ResourceBase.modified
    def set_virt_cpuid_enable(self, en: bool):
        self._use_virt_cpuid = en

    @ResourceBase.modified
    def set_ivshmem_virt_addr(self, addr: int):
        self._ivshmem_virt_addr = addr

    @ResourceBase.modified
    def set_comm_region(self, addr:int):
        self._comm_region = addr

    @ResourceBase.modified
    def set_cpus(self, cpus: Set[int]):
        self._cpus = cpus

    @ResourceBase.modified
    def set_console(self, console: str) -> bool:
        if not isinstance(console, str):
            return False
        self._console = console.strip()
        return True

    @ResourceBase.modified
    def set_devices(self, devices: List[str]) -> bool:
        cpu: ResourceCPU = self.find(ResourceCPU)
        if cpu is None:
            self.logger.error("ResourceCPU not found.")
            return False

        device_names = list()
        for dev in cpu.devices():
            device_names.append(dev.name())

        for dev in devices:
            if dev not in device_names:
                self.logger.error(f"device {dev} not fount.")
                return False
        self._devices = devices
        return True

    @ResourceBase.modified
    def set_pci_devices(self, devices: List[str]) -> bool:
        self._pci_devices = devices
        return True

    @ResourceBase.modified
    def set_reset_addr(self, addr: int) -> bool:
        if not isinstance(addr, int):
            return False
        self._reset_addr = addr
        return True

    def label(self) -> str:
        return f"Guest Cell: {self._name}"

    def from_dict(self, value: dict) -> bool:
        if not DictHelper.from_dict(self.items, self, value):
            self.logger.error("from dict failed.")
            return False

        self._system_mem.clear()
        sys_mem = value.get("system_memory")
        if isinstance(sys_mem, (list, tuple)):
            for mem in sys_mem:
                mmap = MemMap(0, 0, 0)
                if not mmap.from_dict(mem):
                    self.logger.error("invalid system mem")
                    continue
                self._system_mem.append(mmap)
        else:
            self.logger.warn("system_memory not found.")

        self._memmaps.clear()
        memmaps = value.get("memmaps")
        if isinstance(memmaps, (list, tuple)):
            for mem in memmaps:
                mmap = MemMap(0, 0, 0)
                if not mmap.from_dict(mem):
                    self.logger.error(f"invalid memmap {mem}")
                    continue
                self._memmaps.append(mmap)
        else:
            self.logger.warn("memmaps not found.")

        cpus = value.get("cpus")
        if isinstance(cpus, list):
            if all(map(lambda x: isinstance(x,int), cpus)):
                self._cpus = set(cpus)
            else:
                self.logger.error("invalid cpus value.")
        else:
            self.logger.error("cpus not found.")

        devices = value.get("devices")
        if isinstance(devices, list):
            self._devices = devices

        pci_devices = value.get("pci_devices")
        if isinstance(devices, list):
            self._pci_devices = pci_devices

        runinfo = value.get("runinfo")
        if runinfo:
            if not self._runinfo.from_dict(runinfo):
                self.logger.error("runinfo from dict failed.")

        return True

    def to_dict(self) -> Optional[dict]:
        guestcell = DictHelper.to_dict(self.items, self)
        if guestcell is None:
            self.logger.error("to dict failed.")
            return None

        sys_mem = list()
        for mem in self._system_mem:
            sys_mem.append(mem.to_dict())

        memmaps = list()
        for mem in self._memmaps:
            memmaps.append(mem.to_dict())

        guestcell["system_memory"] = sys_mem
        guestcell["memmaps"] = memmaps
        guestcell["cpus"] = sorted(list(self._cpus))
        guestcell["devices"] = self._devices
        guestcell["pci_devices"] = self._pci_devices
        guestcell["runinfo"] = self._runinfo.to_dict()
        return guestcell

class ResourceGuestCellList(ResourceBase):
    logger = logging.getLogger("ResourceGuestCellList")

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self._cells: List[ResourceGuestCell] = list()

    def cell_count(self) -> int:
        return len(self._cells)

    def cell_at(self, idx: int) -> Optional[ResourceGuestCell]:
        if idx<0 or idx>len(self._cells):
            return None
        return self._cells[idx]

    @ResourceBase.modified
    def create_cell(self, name: str) -> Optional[ResourceGuestCell]:
        cell = ResourceGuestCell(self)
        self._cells.append(cell)
        self._children.append(cell)
        cell.set_name(name)

        ResourceSignals.add.send(self, rsc=cell)
        return cell

    @ResourceBase.modified
    def remove_cell(self, cell: Union[str, ResourceGuestCell]) -> bool:
        if isinstance(cell, str):
            cell = self.find_cell(cell)

        if not isinstance(cell, ResourceGuestCell):
            return False
        if cell not in self._cells:
            return False

        self._cells.remove(cell)
        self._children.remove(cell)
        ResourceSignals.remove.send(self, rsc=cell)
        return True

    def find_cell(self, name: str) -> Optional[ResourceGuestCell]:
        for cell in self._cells:
            if cell.name() == name:
                return cell
        return None

    def label(self) -> str:
        return "虚拟机"

    def from_dict(self, value: dict) -> bool:
        if not isinstance(value, dict):
            self.logger.error("not a dict")
            return False

        guest_cells = value.get("cells")
        self._cells.clear()
        if isinstance(guest_cells, list):
            for cell_dict in guest_cells:
                cell = ResourceGuestCell(self)
                if not cell.from_dict(cell_dict):
                    self.logger.error("guest cell form dict failed.")
                    continue
                self._cells.append(cell)
                self._children.append(cell)
        else:
            self.logger.warn("guest_cells not exist or not a list")

        return True

    def to_dict(self) -> Optional[dict]:
        value = OrderedDict()

        guest_cells = list()
        for cell in self._cells:
            cell_dict = cell.to_dict()
            if cell_dict is None:
                self.logger.error("guest to cell failed.")
                return None
            guest_cells.append(cell_dict)
        value['cells'] = guest_cells
        return value

    def __iter__(self):
        return iter(self._cells)

class ResourcePCIDevice(ResourceBase):
    logger = logging.getLogger("ResourcePCIDevice")

    class PCICap(object):
        items = [
            DictHelper.Item("cap",    int,  *DictHelper.common_getset("_id")),
            DictHelper.Item("start", int,  *DictHelper.common_getset("_start")),
            DictHelper.Item("len",   int,  *DictHelper.common_getset("_len")),
            DictHelper.Item("flags", str,  *DictHelper.common_getset("_flags")),
            DictHelper.Item("extended", bool,  *DictHelper.common_getset("_extended")),
        ]
        def __init__(self) -> None:
            self._id = 0
            self._start = 0
            self._len = 0
            self._flags = 0
            self._extended = False

        def id(self):
            return self._id

        def start(self):
            return self._start

        def len(self):
            return self._len

        def is_extended(self) -> bool:
            return self._extended

        def from_dict(self, value: dict) -> bool:
            return DictHelper.from_dict(self.items, self, value)

        def to_dict(self) -> Optional[dict]:
            return DictHelper.to_dict(self.items, self)

    class PCIBar(object):
        items = [
            DictHelper.Item("start", int,  *DictHelper.common_getset("_start")),
            DictHelper.Item("size",  int,  *DictHelper.common_getset("_size")),
            DictHelper.Item("mask",  int,  *DictHelper.common_getset("_mask")),
            DictHelper.Item("type",  str,  *DictHelper.common_getset("_type")),
        ]
        def __init__(self) -> None:
            self._start = 0
            self._size = 0
            self._mask = 0
            self._type = ""

        def start(self) -> int:
            return self._start

        def size(self) -> int:
            return self._size

        def mask(self) -> int:
            return self._mask

        def type(self) -> str:
            return self._type

        def from_dict(self, value: dict) -> bool:
            return DictHelper.from_dict(self.items, self, value)

        def to_dict(self) -> Optional[dict]:
            return DictHelper.to_dict(self.items, self)

    items = [
        DictHelper.Item("name",     str,  *DictHelper.common_getset("_name")),
        DictHelper.Item("path",     str,  *DictHelper.common_getset("_path")),
        DictHelper.Item("domain",   int,  *DictHelper.common_getset("_domain")),
        DictHelper.Item("bus",      int,  *DictHelper.common_getset("_bus")),
        DictHelper.Item("dev",   int,  *DictHelper.common_getset("_device")),
        DictHelper.Item("fun", int,  *DictHelper.common_getset("_function")),
    ]

    def __init__(self, parent):
        super().__init__(parent)

        self._name = ""
        self._path = ""
        self._domain = 0
        self._bus = 0
        self._device = 0
        self._function = 0
        self._bars = list()
        self._caps = list()

    def label(self) -> str:
        return os.path.basename(self._path)

    def from_dict(self, value: dict) -> bool:
        if not DictHelper.from_dict(self.items, self, value):
            self.logger.error("from dict failed.")
            return False

        caps = value.get("caps")
        if not isinstance(caps, list):
            self.logger.error("caps not fount.")
            return False
        for cap in caps:
            pcicap = self.PCICap()
            if not pcicap.from_dict(cap):
                self.logger.error("failed.")
                return False
            self._caps.append(pcicap)

        self._bars.clear()
        new_bars = list()
        bars = value.get("bars")
        if isinstance(bars, list) and len(bars)==6:
            for bar in bars:
                pcibar = self.PCIBar()
                if not pcibar.from_dict(bar):
                    self.logger.error("bars value error")
                    break
                new_bars.append(pcibar)
        else:
            self.logger.error("bars not found.")
        if len(new_bars) == 6:
            self._bars = new_bars

        return True

    def to_dict(self) -> Optional[dict]:
        value = DictHelper.to_dict(self.items, self)
        if value is None:
            return None

        caps = list()
        for cap in self._caps:
            caps.append(cap.to_dict())
        value['caps'] = caps

        bars = list()
        for bar in self._bars:
            bars.append(bar.to_dict())
        value['bars'] = bars

        return value

    def name(self):
        return self._name

    def path(self):
        return self._path

    def domain(self):
        return self._domain

    def bdf(self) -> tuple:
        return (self._bus, self._device, self._function)

    def bdf_value(self) -> int:
        return (self._bus<<8) + (self._device<<3) + self._function

    def caps(self) -> List[PCICap]:
        return self._caps

    def bars(self) -> List[PCIBar]:
        return self._bars


class ResourcePCIDeviceList(ResourceBase):
    logger = logging.getLogger("ResourcePCIDeviceList")
    def __init__(self, parent):
        super().__init__(parent)
        self._devices: List[ResourcePCIDevice] = list()

    @ResourceBase.modified
    def add_device(self, value: dict) -> Optional[ResourcePCIDevice]:
        """从字典添加一个设备
        """
        dev = ResourcePCIDevice(self)
        if not dev.from_dict(value):
            self.logger.error("invalid dict value")
            return None

        self._devices.append(dev)
        self._children.append(dev)
        ResourceSignals.add.send(self, rsc=dev)
        return dev

    @ResourceBase.modified
    def remove_device(self, path) -> bool:
        for dev in self._devices:
            if dev.path() == path:
                self._devices.remove(dev)
                return True
        return False

    @ResourceBase.modified
    def remove_all_device(self) -> None:
        for dev in self._devices:
            self._children.remove(dev)
        # TODO 对device做一次复制，使不被释放
        devices = list(self._devices)
        self._devices.clear()
        ResourceSignals.remove.send(self, devices=devices, count=len(devices))

    def find_device(self, path) -> Optional[ResourcePCIDevice]:
        for dev in self._devices:
            if dev.path() == path:
                return dev
        return None

    def device_count(self):
        return len(self._devices)

    def device_at(self, index: int) -> Optional[ResourcePCIDevice]:
        if index >= 0 and index < len(self._devices):
            return self._devices[index]
        return None

    def label(self) -> str:
        return "PCI设备"

    def from_dict(self, value: dict) -> bool:
        if not isinstance(value, dict):
            return False
        devices = value.get("devices")
        if isinstance(devices, (list, tuple)):
            for dev_dict in devices:
                dev = ResourcePCIDevice(self)
                if not dev.from_dict(dev_dict):
                    self.logger.error("PCI device from dict faied.")
                self._devices.append(dev)
                self._children.append(dev)

        return True

    def to_dict(self) -> Optional[dict]:
        value = OrderedDict()
        devices = list()
        for dev in self._devices:
            dev_dict = dev.to_dict()
            if dev_dict is None:
                self.logger.error("pci device to dict failed.")
                return None
            devices.append(dev_dict)
        value["devices"] = devices
        return value

class ResourceJailhouse(ResourceBase):

    def __init__(self, parent) -> None:
        super().__init__(parent)

        self._root_cell = ResourceRootCell(self)
        self._comm = ResourceComm(self)
        self._pci_devices = ResourcePCIDeviceList(self)
        self._guest_cells = ResourceGuestCellList(self)

        self._children.append(self._root_cell)
        self._children.append(self._comm)
        self._children.append(self._pci_devices)
        self._children.append(self._guest_cells)

    def rootcell(self) -> ResourceRootCell:
        return self._root_cell

    def ivshmem(self) -> ResourceComm:
        return self._comm

    def pci_devices(self) -> ResourcePCIDeviceList:
        return self._pci_devices

    def guestcells(self) -> ResourceGuestCellList:
        return self._guest_cells

    def label(self) -> str:
        return "虚拟机配置"

    def from_dict(self, value: dict) -> bool:
        if not isinstance(value, dict):
            self.logger.error("not a dict")
            return False

        rootcell = value.get("rootcell")
        if rootcell is None or not isinstance(rootcell, dict):
            self.logger.error("[rootcell] not found")
            return False
        if not self._root_cell.from_dict(rootcell):
            self.logger.error("rootcell from dict failed")
            return False

        comm = value.get('comm')
        if comm is None or not isinstance(comm, dict):
            self.logger.error("[comm] not found")
            return False
        if not self._comm.from_dict(comm):
            self.logger.error("comm from dict failed")
            return False

        guestcells = value.get("guestcells")
        if isinstance(guestcells, dict):
            if not self._guest_cells.from_dict(guestcells):
                self.logger.warn("guestcells from dict faied.")
        else:
            self.logger.warn("guestcells not found")

        pci_devices = value.get("pci_devices")
        if isinstance(pci_devices, dict):
            if not self._pci_devices.from_dict(pci_devices):
                self.logger.error("pci_device from dict faied")
                return False

        return True

    def to_dict(self) -> Optional[dict]:
        jh = OrderedDict()
        comm = self._comm.to_dict()
        if comm is None:
            self.logger.error("comm to dict faied.")
            return None
        rootcell = self._root_cell.to_dict()
        if rootcell is None:
            self.logger.error("rootcell to dict faied.")
            return None
        pci_deivces = self._pci_devices.to_dict()
        if pci_deivces is None:
            self.logger.error("pci_devices to dict faied.")
            return None

        guestcells = self._guest_cells.to_dict()
        if guestcells is None:
            self.logger.error("guestcell to dict faield.")
            return None

        jh['comm'] = comm
        jh['rootcell'] = rootcell
        jh['pci_devices'] = pci_deivces
        jh['guestcells'] = guestcells
        return jh


class Resource(ResourceBase):
    def __init__(self, name: str, parent):
        super().__init__(parent)

        self._platform = ResourcePlatform(self)
        self._jailhosue = ResourceJailhouse(self)

        self._name = name
        self._filename = None
        self._children.append(self._platform)
        self._children.append(self._jailhosue)

    def name(self) -> str:
        return self._name

    def platform(self) -> ResourcePlatform:
        return self._platform

    def jailhouse(self):
        return self._jailhosue

    def label(self) -> str:
        return self._name

    def filename(self) -> Optional[str]:
        return self._filename

    def set_filename(self, filename: str) -> bool:
        if not isinstance(filename, str) or len(filename.strip())==0:
            return False
        self._filename = filename
        return True

    def abs_path(self, path: str) -> str:
        """
        如果是绝对路径,直接返回,如果是相对路径,返回相对于jhr文件的绝对路径
        失败返回空字符串
        """
        if os.path.isabs(path):
            return path
        if self._filename is None:
            return ""
        dirname = os.path.dirname(self._filename)
        if len(dirname) == 0:
            return ""
        
        abspath = os.path.abspath(os.path.join(dirname, path))
        return abspath

    @ResourceBase.modified
    def set_name(self, name: str) -> bool:
        name = name.strip()
        if len(name) == 0:
            return False
        self._name = name
        return True

    def from_dict(self, value: dict) -> bool:
        if not isinstance(value, dict):
            self.logger.error(f"not a dict {value}")
            return False
        platform = value.get("platform")
        if not isinstance(platform, dict):
            self.logger.error("[platform] type error")
            return False
        if not self._platform.from_dict(platform):
            self.logger.error("platform from dict failed")
            return False

        jailhouse = value.get("jailhouse")
        if not isinstance(jailhouse, dict):
            return False
        if not self._jailhosue.from_dict(jailhouse):
            self.logger.error("jailhosue from dict failed")
            return False

        name = value.get("name")
        if isinstance(name, str):
            self._name = name

        return True

    def to_dict(self) -> Optional[dict]:
        rsc = OrderedDict()
        platform = self._platform.to_dict()
        if platform is None:
            self.logger.error(f"get platform dict failed")
            return None
        jailhosue = self._jailhosue.to_dict()
        if jailhosue is None:
            self.logger.error("get jailhouse dict failed.")
            return None

        rsc['name'] = self._name
        rsc['platform'] = platform
        rsc['jailhouse'] = jailhosue
        return rsc


class PlatformMgr(object):
    logger = logging.getLogger("platform")

    class CPU():
        def __init__(self):
            self.id = ''
            self.file = ''

            self.name = ''
            self.path = ''
            self.value = None
            self.guestos_dts = None

        def from_dict(self, value) -> bool:
            return DictHelper.from_dict(self.items, self, value)

    class Board(object):
        items = [
            DictHelper.Item("file", str, *DictHelper.common_getset("file")),
            DictHelper.Item("cpu", str, *DictHelper.common_getset("cpu_id")),
        ]
        def __init__(self):
            self.id = ''
            self.file = ''
            self.cpu_id = ''

            self.name = ''
            self.path = ''
            self.value = None
            self.cpu = None

        def from_dict(self, value) -> bool:
            return DictHelper.from_dict(self.items, self, value)

    instance = None

    @classmethod
    def get_instance(cls):
        if cls.instance is None:
            cls.instance = PlatformMgr()
        return cls.instance

    def __init__(self):
        super().__init__()
        self._path = ""
        self._cpus: List[self.CPU] = list()
        self._boards: List[self.Board] = list()

    def reset(self):
        self._cpus.clear()
        self._boards.clear()

    @classmethod
    def load_toml(cls, filename: str):
        try:
            index = toml.load(filename)
            return index
        except Exception as e:
            cls.logger.error(f"load toml {filename} failed {e}")
            return None

    def load(self, plt_path: str) -> bool:
        """
        加载平台资源文件
        :param index_toml: index.toml
        :return:
        """
        index_toml = os.path.join(plt_path, "index.toml")

        try:
            index = toml.load(index_toml)
        except Exception as e:
            self.logger.error(f"parse platform index file failed, {index_toml}")
            self.logger.error(str(e))
            return False

        if not isinstance(index, dict):
            self.logger.error("invalid index, not a dict.")
            return False

        cpus: List[self.CPU] = list()
        boards: List[self.Board] = list()

        index_cpus = index.get('cpus')
        if not isinstance(index_cpus, dict):
            self.logger.error("cpus not a dict")
            return False

        for cpu_id in index_cpus:
            filename = index_cpus[cpu_id]['file']
            self.logger.info(f"load cpu {filename}")
            guestos_dts = index_cpus[cpu_id].get('guestos-dts')
            if not isinstance(cpu_id, str) or not isinstance(filename, str):
                self.logger.error("cpu_id or file is not a string")
                continue

            cpu = self.CPU()
            cpu.id = cpu_id
            cpu.path = os.path.join(plt_path, filename)
            if not os.path.exists(cpu.path):
                self.logger.error(f"cpu toml {cpu.path} not exist.")
                continue

            cpu.value = self.load_toml(cpu.path)
            if not isinstance(cpu.value, dict):
                self.logger.error(f"cpu toml not a dict")
                continue

            if guestos_dts is not None:
                dts_path = os.path.join(plt_path, guestos_dts)
                if os.path.exists(dts_path):
                    with open(dts_path, "rt") as f:
                        cpu.guestos_dts = base64.b64encode(f.read())

            # 检查能否使用ResourceCPU加载
            rsc_cpu = ResourceCPU(None)
            if not rsc_cpu.from_dict(cpu.value):
                self.logger.error("cpu from dict failed.")
                continue
            cpu.name = rsc_cpu.name()
            cpus.append(cpu)

        index_boards = index.get("boards")
        if not isinstance(index_boards, dict):
            self.logger.error("boards not a dict")
            return False

        for board_id in index_boards:
            board_value = index_boards[board_id]
            board = self.Board()
            if not board.from_dict(board_value):
                self.logger.error("board from dict failed.")
                continue

            board.path = os.path.join(plt_path, board.file)
            board.value = self.load_toml(board.path)
            if not isinstance(board.value, dict):
                self.logger.error("board toml is not dict")
                continue

            # 检查是否能使用ResourceBoard加载
            rsc_board = ResourceBoard(None)
            if not rsc_board.from_dict(board.value):
                self.logger.error("board form dict failed.")
                continue

            for cpu in cpus:
                if cpu.id == board.cpu_id:
                    board.cpu = cpu
                    break
            if board.cpu is None:
                self.logger.error(f'{board.path} cpu not found.')
                continue

            board.name = rsc_board.name()
            board.id = board_id
            boards.append(board)

        self._path = plt_path
        self._cpus = cpus
        self._boards = boards
        return True

    def find_board(self, name: str) -> Optional[Board]:
        for board in self._boards:
            if board.name == name or board.id == name:
                return board
        return None

    def find_cpu(self, name: str) -> Optional[CPU]:
        for cpu in self._cpus:
            if cpu.name == name or cpu.id == name:
                return cpu
        return None

    def board_names(self) -> List[str]:
        return list(map(lambda x: x.name, self._boards))

    def cpu_names(self) -> List[str]:
        return list(map(lambda x: x.name, self._cpu))


class ResourceMgr(object):
    logger = logging.getLogger("ResourceMgr")

    instance = None

    def __init__(self):
        super().__init__()
        self._resources: List[Resource] = list()

        self._current: Optional[Resource] = None

    @classmethod
    def get_instance(cls):
        if cls.instance is None:
            cls.instance = ResourceMgr()
        return cls.instance

    def create(self, name: str, board_name: str) -> Optional[Resource]:
        pltmgr = PlatformMgr.get_instance()
        if pltmgr is None:
            self.logger.error("get PlatformMgr instance failed")
            return None

        board = pltmgr.find_board(board_name)
        if board is None:
            self.logger.error(f"board {name} not found")
            return None

        rsc = Resource(name, self)
        if not rsc.platform().cpu().from_dict(board.cpu.value):
            self.logger.error("cpu from dict failed.")
            return None
        if not rsc.platform().board().from_dict(board.value):
            self.logger.error("board from dict failed.")
            return None
        self._resources.append(rsc)
        ResourceSignals.add.send(self, rsc=rsc)
        return rsc

    def load(self, jhr: dict) -> Optional[Resource]:
        rsc = Resource("new", self)
        if not rsc.from_dict(jhr):
            self.logger.error("resource from dict failed.")
            return None

        self._resources.append(rsc)
        ResourceSignals.add.send(self, rsc=rsc)
        return rsc

    def open(self, filename) -> Optional[Resource]:
        value = None
        try:
            with open(filename, "rt", encoding='utf8') as f:
                value = json.load(f)
        except Exception as e:
            self.logger.error(f"open {filename} failed: {e}")
            return None

        rsc = self.load(value)
        if rsc is not None:
            rsc.set_filename(filename)
        return rsc

    @classmethod
    def save(cls, rsc: Resource, filename: str) -> bool:
        value = rsc.to_dict()
        if value is None:
            cls.logger.error("resource to dict failed")
            return False

        json_str = json.dumps(value, indent=4, ensure_ascii=False)

        try:
            with open(filename, "wt", encoding='utf-8') as f:
                f.write(json_str)
        except:
            cls.logger.error("save file failed.")

        return True

    def remove(self, rsc: Resource):
        if rsc in self._resources:
            self._resources.remove(rsc)

    def set_current(self, rsc: Resource) -> bool:
        if rsc not in self._resources:
            self.logger.error(f"{rsc} not in resource list.")
            return False
        if rsc is self._current:
            return True
        ResourceSignals.current_rsc.send(self, rsc=rsc)
        self._current = rsc
        return True

    def get_current(self) -> Optional[Resource]:
        return self._current

    def index(self, rsc: Resource):
        if rsc not in self._resources:
            return -1
        return self._resources.index(rsc)

    def __len__(self):
        return len(self._resources)

    def __getitem__(self, item):
        return self._resources[item]


import click
@click.group()
def cli():
    logging.basicConfig(level=logging.DEBUG)
    pltmgr = PlatformMgr.get_instance().load("platform")
    if pltmgr is None:
        logging.error("load index.toml failed")
        return False

@cli.command()
def test():
    import pprint
    import json

    rsc = ResourceMgr.get_instance().create("test", "hanwei_ft2004")
    if rsc is None:
        logging.error("create resource failed.")
        return False

    if not ResourceMgr.get_instance().save(rsc, "temp.jhr"):
        logging.error("save failed")
        return False

    new_rsc = ResourceMgr.get_instance().open("temp.jhr")
    if new_rsc is None:
        logging.error("open failed.")
        return False
    return True

@cli.group()
@click.argument("jhr")
@click.pass_context
def dump(ctx, jhr):
    ctx.ensure_object(dict)
    rsc = ResourceMgr.get_instance().open(jhr)
    if rsc is None:
        exit(1)
    ctx.obj['resource'] = rsc

@dump.command("list-cell")
@click.pass_context
def dump_list_cell(ctx):
    resource: Resource = ctx.obj['resource']
    guestcells: ResourceGuestCellList = resource.jailhouse().guestcells()
    for i in range(guestcells.cell_count()):
        print(guestcells.cell_at(i).name())

@dump.command("cell-resource")
@click.argument('name')
@click.pass_context
def dump_list_cell(ctx, name):
    resource: Resource = ctx.obj['resource']
    guestcells: ResourceGuestCellList = resource.jailhouse().guestcells()
    cell = guestcells.find_cell(name)
    if cell is None:
        print(f'cell {name} not found.')
    else:
        import pprint
        json_str = json.dumps(cell.to_dict(), indent=4, ensure_ascii=False)
        print(json_str)


if __name__ == '__main__':
    cli()
