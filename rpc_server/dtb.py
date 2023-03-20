import struct

class DTBHeader:
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
        return struct.pack('>10I', 0xd00dfeed, self.total_size,
                           self.off_dt_struct, self.off_dt_strings,
                           self.off_mem_rsvmap, self.version,
                           self.last_comp_version, self.boot_cpuid_phys,
                           self.size_dt_strings, self.size_dt_struct)


class DTBReserveMap:
    def __init__(self, blob):
        self.blob = blob[0:16]
        pos = 0
        while struct.unpack_from('>8xQ', self.blob[pos:pos+16]) != (0,):
            self.blob += blob[pos+16:pos+32]
            pos += 16


class DTBStrings:
    def __init__(self, blob):
        self.blob = blob

    def add(self, string):
        offset = len(self.blob)
        self.blob += string.encode() + b'\0'
        return offset

    def get(self, off):
        strings = str(self.blob.decode())
        return strings[off:].split('\0', 1)[0]


OF_DT_BEGIN_NODE = 0x00000001
OF_DT_END_NODE = 0x00000002
OF_DT_PROP = 0x00000003
OF_DT_END = 0x00000009


class DTBProperty:
    def __init__(self, name_off, value, strings):
        self.name_off = name_off
        self.name = strings.get(self.name_off)
        self.data = value

    @staticmethod
    def parse(blob, strings):
        (datasize, name_off) = struct.unpack_from('>II', blob)
        data = blob[8:8+datasize]
        prop = DTBProperty(name_off, data, strings)
        length = 8 + (datasize + 3) & ~3
        return (prop, length)

    @staticmethod
    def create(name, value, strings):
        return DTBProperty(strings.add(name), value, strings)

    def set_value(self, value):
        self.data = value

    def get(self):
        datasize = len(self.data)
        blob = struct.pack('>III', OF_DT_PROP, datasize, self.name_off)
        blob += self.data
        if datasize & 3 != 0:
            blob += bytearray(4 - datasize & 3)
        return blob


class DTBNode:
    def __init__(self, name, children, properties, strings):
        self.name = name
        self.children = children
        self.properties = properties
        self.strings = strings

    @staticmethod
    def parse(blob, strings):
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
        child = DTBNode(name, [], [], self.strings)
        self.children.append(child)
        return child

    def get_prop(self, name):
        matches = [p for p in self.properties if p.name == name]
        if len(matches) > 1:
            raise RuntimeError('Invalid DTB')
        return matches[0] if matches else None

    def add_prop(self, name, value):
        prop = DTBProperty.create(name, value, self.strings)
        self.properties.append(prop)

    def get(self):
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
        node = self.root_node.find(path[path.find('/')+1:])
        if not node:
            raise RuntimeError('DTB is missing node %s' % path)
        prop = node.get_prop(name)
        return prop.data if prop else None

    def set_prop(self, path, name, value):
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
        nodes = self.root_node.get() + struct.pack('>I', OF_DT_END)
        self.header.off_mem_rsvmap = 40
        self.header.off_dt_struct = 40 + len(self.rsvmap.blob)
        self.header.size_dt_struct = len(nodes)
        self.header.off_dt_strings = self.header.off_dt_struct + len(nodes)
        self.header.size_dt_strings = len(self.strings.blob)
        self.header.total_size = self.header.off_dt_strings + \
            len(self.strings.blob)

        return self.header.get() + self.rsvmap.blob + nodes + self.strings.blob
