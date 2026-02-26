"""
DTB (Device Tree Blob) 解析与构建工具。

该模块提供对二进制 DTB(blob) 的解析与修改能力，包含：
- 解析 DTB 头部（`DTBHeader`）
- 处理保留映射（`DTBReserveMap`）
- 管理字符串表（`DTBStrings`）
- 表示属性（`DTBProperty`）和节点（`DTBNode`）并支持解析/创建
- 将修改后的结构重新打包回 DTB（二进制 blob）（`DTB`）

主要类:
- `DTBHeader`: DTB 头部解析与序列化。
- `DTBReserveMap`: DTB 保留内存映射区域处理。
- `DTBStrings`: DTB 字符串表管理（添加/查找）。
- `DTBProperty`: 表示 DT 节点属性并提供解析/构建方法。
- `DTBNode`: 表示 DT 节点，支持查找、添加子节点和属性修改。
- `DTB`: 顶级封装类，解析整个 DTB 并支持读/写属性。

使用说明（摘要）:
- 解析：使用 `DTB(blob)` 创建实例，随后可通过 `get_prop`/`set_prop` 读取或修改属性。
- 序列化：调用 `DTB.get()` 返回修改后的 DTB 二进制数据。

注：本模块以 big-endian (`>` 格式) 解析 DTB 字段，且假定 DTB 版本兼容范围为 17。
"""

import struct

class DTBHeader:
    """
    DTB 头部解析与序列化类。

    解析给定 blob 中的 DTB 头部字段，并可将头部信息重新打包为二进制。

    Args:
        blob (bytes): 包含 DTB 头部的二进制数据（至少 40 字节）。

    属性:
        header_blob (bytes): 原始头部二进制数据。
        total_size, off_dt_struct, off_dt_strings, off_mem_rsvmap, version,
        last_comp_version, boot_cpuid_phys, size_dt_strings, size_dt_struct: 头部字段。
    """

    def __init__(self, blob):
        (self.total_size, self.off_dt_struct, self.off_dt_strings,
         self.off_mem_rsvmap, self.version, self.last_comp_version,
         self.boot_cpuid_phys, self.size_dt_strings, self.size_dt_struct) = \
            struct.unpack_from('>4x9I', blob)
        if self.version < 17 or self.last_comp_version > 17:
            print('Unsupported DTB version %d' % self.version)
            exit(1)
        self.header_blob = blob

    def get(self):
        """
        将头部字段序列化为二进制 DTB 头部。

        Returns:
            bytes: 序列化后的 40 字节 DTB 头部。
        """
        return struct.pack('>10I', 0xd00dfeed, self.total_size,
                           self.off_dt_struct, self.off_dt_strings,
                           self.off_mem_rsvmap, self.version,
                           self.last_comp_version, self.boot_cpuid_phys,
                           self.size_dt_strings, self.size_dt_struct)


class DTBReserveMap:
    """
    DTB 保留内存映射（reserve map）处理类。

    该结构用于描述在设备树中保留的物理内存区域。

    Args:
        blob (bytes): 从头部偏移处读取的保留映射数据。
    """

    def __init__(self, blob):
        self.blob = blob[0:16]
        pos = 0
        while struct.unpack_from('>8xQ', self.blob[pos:pos+16]) != (0,):
            self.blob += blob[pos+16:pos+32]
            pos += 16


class DTBStrings:
    """
    DTB 字符串表管理类。

    提供向字符串表追加字符串并通过偏移读取字符串的能力。

    Args:
        blob (bytes): 字符串表二进制。
    """

    def __init__(self, blob):
        self.blob = blob

    def add(self, string):
        """
        向字符串表追加一个以 NUL 结尾的字符串。

        Args:
            string (str): 要追加的字符串。

        Returns:
            int: 新字符串在字符串表中的偏移量。
        """
        offset = len(self.blob)
        self.blob += string.encode() + b'\0'
        return offset

    def get(self, off):
        """
        根据偏移从字符串表中读取字符串（以 NUL 终止）。

        Args:
            off (int): 字符串在字符串表中的偏移量。

        Returns:
            str: 对应的字符串（不包含终止 NUL）。
        """
        strings = str(self.blob.decode())
        return strings[off:].split('\0', 1)[0]


OF_DT_BEGIN_NODE = 0x00000001
OF_DT_END_NODE = 0x00000002
OF_DT_PROP = 0x00000003
OF_DT_END = 0x00000009


class DTBProperty:
    """
    表示 DT 节点属性（property）。

    提供从二进制解析属性和将属性序列化回二进制的工具。
    """

    def __init__(self, name_off, value, strings):
        self.name_off = name_off
        self.name = strings.get(self.name_off)
        self.data = value

    @staticmethod
    def parse(blob, strings):
        """
        从给定的二进制块解析属性。

        Args:
            blob (bytes): 属性区域的二进制数据（从属性头开始）。
            strings (DTBStrings): 字符串表实例，用于解析属性名偏移。

        Returns:
            tuple: (DTBProperty, int) - 解析得到的属性对象及其占用的字节长度。
        """
        (datasize, name_off) = struct.unpack_from('>II', blob)
        data = blob[8:8+datasize]
        prop = DTBProperty(name_off, data, strings)
        length = 8 + (datasize + 3) & ~3
        return (prop, length)

    @staticmethod
    def create(name, value, strings):
        """
        创建一个新的 DTBProperty 实例并向字符串表添加名字。

        Args:
            name (str): 属性名。
            value (bytes): 属性值二进制。
            strings (DTBStrings): 字符串表实例。

        Returns:
            DTBProperty: 新创建的属性对象。
        """
        return DTBProperty(strings.add(name), value, strings)

    def set_value(self, value):
        """设置属性的新值（原地替换）。"""
        self.data = value

    def get(self):
        """
        将属性序列化为 DTB 中的二进制表示（包括填充对齐）。

        Returns:
            bytes: 序列化后的属性二进制。
        """
        datasize = len(self.data)
        blob = struct.pack('>III', OF_DT_PROP, datasize, self.name_off)
        blob += self.data
        if datasize & 3 != 0:
            blob += bytearray(4 - datasize & 3)
        return blob


class DTBNode:
    def __init__(self, name, children, properties, strings):
        """
        表示 DT 节点（node）。

        Args:
            name (str): 节点名。
            children (list): 子节点列表。
            properties (list): 属性列表（DTBProperty 实例）。
            strings (DTBStrings): 字符串表实例。
        """
        self.name = name
        self.children = children
        self.properties = properties
        self.strings = strings

    @staticmethod
    def parse(blob, strings):
        """
        从二进制结构解析一个节点（包括其子节点和属性）。

        Args:
            blob (bytes): 从节点起始处的二进制数据（不含 begin token）。
            strings (DTBStrings): 字符串表实例。

        Returns:
            tuple: (DTBNode, int) - 解析得到的节点对象及其占用的字节长度。
        """
        name = unpack_cstring(blob)
        # next field is word-aligned
        length = ((len(name) + 1) + 3) & ~3

        children = []
        properties = []

        while True:
            (token,) = struct.unpack_from('>I', blob[length:])
            length += 4
            if token == OF_DT_BEGIN_NODE:
                (child, child_length) = DTBNode.parse(blob[length:], strings)
                length += child_length
                children.append(child)
            elif token == OF_DT_PROP:
                (prop, prop_length) = DTBProperty.parse(blob[length:], strings)
                length += prop_length
                properties.append(prop)
            elif token == OF_DT_END_NODE:
                break
            else:
                raise RuntimeError('Invalid DTB')

        return (DTBNode(name, children, properties, strings), length)

    def find(self, path):
        """
        在当前节点树中查找给定路径的节点。

        Args:
            path (str): 以 '/' 分隔的路径（相对于当前节点）。

        Returns:
            DTBNode | None: 找到的节点或 None。
        """
        if path == '':
            return self
        if path.find('/') >= 0:
            (childname, subpath) = path.split('/', 1)
        else:
            childname = path
            subpath = ''
        matches = [c for c in self.children if c.name == childname]
        if len(matches) > 1:
            raise RuntimeError('Invalid DTB')
        if not matches:
            return None
        else:
            return matches[0].find(subpath)

    def add_node(self, name):
        """向当前节点添加一个子节点并返回该子节点对象。"""
        child = DTBNode(name, [], [], self.strings)
        self.children.append(child)
        return child

    def get_prop(self, name):
        """根据属性名返回匹配的属性（若存在），否则返回 None。"""
        matches = [p for p in self.properties if p.name == name]
        if len(matches) > 1:
            raise RuntimeError('Invalid DTB')
        return matches[0] if matches else None

    def add_prop(self, name, value):
        """向当前节点添加一个属性（创建新的 DTBProperty）。"""
        prop = DTBProperty.create(name, value, self.strings)
        self.properties.append(prop)

    def get(self):
        """
        将当前节点及其子树序列化为 DTB 二进制片段。

        Returns:
            bytes: 节点及其子节点/属性的序列化二进制。
        """
        namelen = ((len(self.name) + 1) + 3) & ~3
        blob = struct.pack('>I%ds' % namelen, OF_DT_BEGIN_NODE,
                           self.name.encode())
        for prop in self.properties:
            blob += prop.get()
        for child in self.children:
            blob += child.get()
        return blob + struct.pack('>I', OF_DT_END_NODE)


class DTB:
    def __init__(self, blob):
        """
        解析整个 DTB blob，并构建头部、保留映射、字符串表与根节点树。

        Args:
            blob (bytes): 完整的 DTB 二进制数据。
        """
        self.header = DTBHeader(blob[0:40])

        self.rsvmap = DTBReserveMap(blob[self.header.off_mem_rsvmap:])

        end_idx = self.header.off_dt_strings + self.header.size_dt_strings
        self.strings = DTBStrings(blob[self.header.off_dt_strings:end_idx])

        start_idx = self.header.off_dt_struct
        end_idx = start_idx + self.header.size_dt_struct

        (begin_token,) = struct.unpack_from('>I', blob[start_idx:end_idx])
        if begin_token != OF_DT_BEGIN_NODE:
            raise RuntimeError('Invalid DTB')
        (self.root_node, length) = DTBNode.parse(blob[start_idx+4:end_idx],
                                                 self.strings)

    def get_prop(self, path, name):
        """
        获取指定节点路径的属性数据。

        Args:
            path (str): 节点路径（以根节点为起点，例如 '/root/sub'）。
            name (str): 属性名。

        Returns:
            bytes | None: 属性数据（若存在），否则返回 None。
        """
        node = self.root_node.find(path[path.find('/')+1:])
        if not node:
            raise RuntimeError('DTB is missing node %s' % path)
        prop = node.get_prop(name)
        return prop.data if prop else None

    def set_prop(self, path, name, value):
        """
        设置或添加指定节点路径下的属性。

        如果指定节点不存在则会创建相应子节点。

        Args:
            path (str): 节点路径（以根节点为起点）。
            name (str): 属性名。
            value (bytes): 属性数据。
        """
        subpath = path[path.find('/')+1:]
        node = self.root_node.find(subpath)
        if not node:
            (parent_path, new_node) = path.rsplit('/')
            parent = self.root_node.find(parent_path)
            node = parent.add_node(new_node)
        prop = node.get_prop(name)
        if prop:
            prop.set_value(value)
        else:
            node.add_prop(name, value)

    def get(self):
        """
        将当前内存中表示的 DT 节点树序列化回一个完整的 DTB 二进制 blob。

        Returns:
            bytes: 序列化后的 DTB 二进制数据。
        """
        nodes = self.root_node.get() + struct.pack('>I', OF_DT_END)
        self.header.off_mem_rsvmap = 40
        self.header.off_dt_struct = 40 + len(self.rsvmap.blob)
        self.header.size_dt_struct = len(nodes)
        self.header.off_dt_strings = self.header.off_dt_struct + len(nodes)
        self.header.size_dt_strings = len(self.strings.blob)
        self.header.total_size = self.header.off_dt_strings + \
            len(self.strings.blob)

        return self.header.get() + self.rsvmap.blob + nodes + self.strings.blob
