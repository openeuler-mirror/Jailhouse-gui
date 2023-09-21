import os
import struct
import enum
import glob
from typing import List
from io import BytesIO, StringIO
from collections import OrderedDict


class PCICapFlag(enum.Enum):
    NONE = ''
    RW = 'rw'
    RD = 'r'


class PCICapID(enum.Enum):
    NULL                    = 0x00
    PM                      = 0x01
    AGP                     = 0x02
    VPD                     = 0x03
    SlotIdentification      = 0x04
    MSI                     = 0x05
    CHS                     = 0x06
    PCIX                    = 0x07
    HyperTransport          = 0x08
    VendorSpecific          = 0x09
    DebugPort               = 0x0A
    CPCICtrl                = 0x0B
    HotPlug                 = 0x0C
    BridgeSubsystemVendorID = 0x0D
    AGP8x                   = 0x0E
    SecureDevice            = 0x0F
    PCIExpress              = 0x10
    MSIX                    = 0x11
    SerialATAConf           = 0x12
    AdvancedFeatures        = 0x13
    EnhancedAllocation      = 0x14
    FlatPortalBridge        = 0x15

    _describes = {
        0x00: "Null Capability",
        0x01: "PCI Power Management Interface",
        0x02: "AGP",
        0x03: "VPD",
        0x04: "Slot Identification",
        0x05: "Message Signaled Interrupts",
        0x06: "CompactPCI Hot Swap",
        0x07: "PCI-X",
        0x08: "HyperTransport",
        0x09: "Vendor Specific",
        0x0A: "Debug port",
        0x0B: "CompactPCI central resource control",
        0x0C: "PCI Hot-Plug",
        0x0D: "PCI Bridge Subsystem Vendor ID",
        0x0E: "AGP 8x",
        0x0F: "Secure Device",
        0x10: "PCI Express",
        0x11: "MSI-X",
        0x12: "Serial ATA Data/Index Configuration",
        0x13: "Advanced Features (AF)",
        0x14: "Enhanced Allocation",
        0x15: "Flattening Portal Brid"
    }

    @classmethod
    def from_value(cls, value):
        for n,e in cls.__members__.items():
            if e.value == value:
                return e

    def descript(self) -> str:
        describs = self._describes.value
        if self.value in describs:
            return describs[self.value]
        return ""


class PCIExtCapID(enum.Enum):
    NULL                   = 0x0000
    AER                    = 0x0001
    VCWithoutMFVC          = 0x0002
    DevSerialNum           = 0x0003
    PowerBuget             = 0x0004
    RCLinkDecl             = 0x0005
    RCLinkCtrl             = 0x0006
    RCEventCEA             = 0x0007
    MFVC                   = 0x0008
    VCWithMFVC             = 0x0009
    RCRB                   = 0x000A
    VSEC                   = 0x000B
    CAC                    = 0x000C
    ACS                    = 0x000D
    ARI                    = 0x000E
    ATS                    = 0x000F
    SRIOV                  = 0x0010
    MRIOV                  = 0x0011
    Multicast              = 0x0012
    PRI                    = 0x0013
    RsvdForAMD             = 0x0014
    ResizableBAR           = 0x0015
    DPA                    = 0x0016
    TPHRequester           = 0x0017
    LTR                    = 0x0018
    SecondaryPCIE          = 0x0019
    PMUX                   = 0x001A
    PASID                  = 0x001B
    LNR                    = 0x001C
    DPC                    = 0x001D
    L1PMSubstates          = 0x001E
    PTM                    = 0x001F
    MPCIe                  = 0x0020
    FRSQueueing            = 0x0021
    ReadinessTimeReporting = 0x0022
    DVSEC                  =  0x0023
    VFResizableBAR         =  0x0024
    DataLinkFeature        =  0x0025
    PhyLayer16GT           =  0x0026
    LaneMarginAtRecv       =  0x0027
    HierarchyID            =  0x0028
    NPEM                   = 0x0029
    PhyLayer32GT           = 0x002A
    AlternateProtocol      = 0x002B
    SFI                    = 0x002C
    ShadowFunctions        = 0x002D
    DataObjectExchange     = 0x002E

    _describes = {
        0x0000: "Null Capability",
        0x0001: "Advanced Error Reporting (AER)",
        0x0002: "Virtual Channel (VC) without MFVC Extended Cap",
        0x0003: "Device Serial Number",
        0x0004: "Power Budgeting",
        0x0005: "Root Complex Link Declaration",
        0x0006: "Root Complex Internal Link Control",
        0x0007: "Root Complex Event Collector Endpoint Association",
        0x0008: "Multi-Function Virtual Channel (MFVC)",
        0x0009: "Virtual Channel (VC) with MFVC Extended Cap",
        0x000A: "Root Complex Register Block (RCRB) Header",
        0x000B: "Vendor-Specific Extended Capability (VSEC)",
        0x000C: "Configuration Access Correlation (CAC)",
        0x000D: "Access Control Services (ACS)",
        0x000E: "Alternative Routing-ID Interpretation (ARI)",
        0x000F: "Address Translation Services (ATS)",
        0x0010: "Single Root I/O Virtualization (SR-IOV)",
        0x0011: "Deprecated; formerly Multi-Root I/O Virtualization (MR-IOV)",
        0x0012: "Multicast",
        0x0013: "Page Request Interface (PRI)",
        0x0014: "Reserved for AMD",
        0x0015: "Resizable BAR",
        0x0016: "Dynamic Power Allocation (DPA)",
        0x0017: "TPH Requester",
        0x0018: "Latency Tolerance Reporting (LTR)",
        0x0019: "Secondary PCI Express",
        0x001A: "Protocol Multiplexing (PMUX)",
        0x001B: "Process Address Space ID (PASID)",
        0x001C: "LN Requester (LNR)",
        0x001D: "Downstream Port Containment (DPC)",
        0x001E: "L1 PM Substates",
        0x001F: "Precision Time Measurement (PTM)",
        0x0020: "PCI Express over M-PHY (M-PCIe)",
        0x0021: "FRS Queueing",
        0x0022: "Readiness Time Reporting",
        0x0023: "Designated Vendor-Specific Extended Capability",
        0x0024: "VF Resizable BAR",
        0x0025: "Data Link Feature",
        0x0026: "Physical Layer 16.0 GT/s",
        0x0027: "Lane Margining at the Receiver",
        0x0028: "Hierarchy ID",
        0x0029: "Native PCIe Enclosure Management (NPEM)",
        0x002A: "Physical Layer 32.0 GT/s",
        0x002B: "Alternate Protocol",
        0x002C: "System Firmware Intermediary (SFI)",
        0x002D: "Shadow Functions",
        0x002E: "Data Object Exchang",
    }

    @classmethod
    def from_value(cls, value):
        for n,e in cls.__members__.items():
            if e.value == value:
                return e

    def descript(self) -> str:
        describs = self._describes.value
        if self.value in describs:
            return describs[self.value]
        return ""


class PCICap(object):
    def __init__(self, cap: PCICapID, start) -> None:
        super().__init__()
        self.cap = cap
        self.start = start

        self.len = 0
        self.flags = PCICapFlag.NONE
        self.extended =False
        self.content = None
        self.msix_addr = 0

    def to_dict(self):
        values = OrderedDict()
        values['cap'] = self.cap.value
        values['name'] = self.cap.name
        values['start'] = self.start
        values['len'] = self.len
        values['flags'] = self.flags.value
        values['extended'] = self.extended
        values['msix_addr'] = self.msix_addr
        return values

    @classmethod
    def parse(cls, config: BytesIO) -> list:
        caps = list()
        has_extended_caps = False

        config.seek(0x34)
        (cap_pos,) = struct.unpack('B', config.read(1))
        while cap_pos != 0:
            config.seek(cap_pos)
            cap_id, cap_next = struct.unpack('BB', config.read(2))

            _id = PCICapID.from_value(cap_id)
            if _id is None:
                print(f"cap id {cap_id} not found.")
                continue

            cap = PCICap(_id, cap_pos)

            if _id is PCICapID.PM:
                # this cap can be handed out completely
                cap.len = 8
                cap.flags = PCICapFlag.RW
            elif _id is PCICapID.MSI:
                cap.len = 10
                (msgctl,) = struct.unpack('<H', config.read(2))
                if (msgctl & (1 << 7)) != 0:  # 64-bit support
                    cap.len = 14
                if (msgctl & (1 << 8)) != 0:  # per-vector masking support
                    cap.len = 20
                cap.flags = PCICapFlag.RW
            elif _id is PCICapID.PCIExpress:
                (cap_reg,) = struct.unpack('<H', config.read(2))
                if (cap_reg & 0xf) >= 2:  # v2 capability
                    cap.len = 60
                else:
                    cap.len = 20
                # access side effects still need to be analyzed
                cap.flags = PCICapFlag.RD
                has_extended_caps = True
            elif _id is PCICapID.MSIX:
                # access will be moderated by hypervisor
                cap.len = 12
                (table,) = struct.unpack('<xxI', config.read(6))
                config.seek(0x10 + (table & 7) * 4)
                (bar,) = struct.unpack('<I', config.read(4))
                if (bar & 0x3) != 0:
                    raise RuntimeError('Invalid MSI-X BAR found')
                if (bar & 0x4) != 0:
                    bar |= struct.unpack('<I', config.read(4))[0] << 32
                cap.msix_addr = (bar & 0xfffffffffffffff0) + (table & 0xfffffff8)
                cap.flags = PCICapFlag.RW
            else:
                print(f"unknown cap {cap_id}")
                cap.len = 2
                cap.flags = PCICapFlag.RD

            config.seek(cap_pos)
            cap.content = config.read(cap.len)
            caps.append(cap)
            cap_pos = cap_next

        if not has_extended_caps:
            return caps

        cap_pos = 0x100
        while cap_pos != 0:
            config.seek(cap_pos)
            cap_id, cap_next = struct.unpack('<HH', config.read(4))
            cap_next = cap_next >> 4

            _id = PCIExtCapID.from_value(cap_id)
            if _id is None:
                print(f"extended cap {cap_id} not found")
                continue

            cap = PCICap(_id, cap_pos)
            cap.extended = True
            cap.flags = PCICapFlag.RD

            if _id is PCIExtCapID.VSEC:
                (vsec_len,) = struct.unpack('<I', config.read(4))
                cap.len = 4 + (vsec_len >> 20)
            elif _id is PCIExtCapID.ACS:
                length = 8
                (acs_cap, acs_ctrl) = struct.unpack('<HH', config.read(4))
                if acs_cap & (1 << 5) and acs_ctrl & (1 << 5):
                    vector_bits = acs_cap >> 8
                    if vector_bits == 0:
                        vector_bits = 256

                    vector_bytes = int((vector_bits + 31) / (8 * 4))
                    length += vector_bytes
                cap.len = length

            elif _id in [PCIExtCapID.VCWithMFVC, PCIExtCapID.VCWithoutMFVC]:
                # parsing is too complex, but we have at least 4 DWORDS
                cap.len = 4 * 4
            elif _id == PCIExtCapID.MFVC:
                cap.len = 4
            elif _id in [PCIExtCapID.LTR, PCIExtCapID.ARI, PCIExtCapID.PASID]:
                cap.len = 8
            elif _id in [PCIExtCapID.DevSerialNum, PCIExtCapID.PTM]:
                cap.len = 12
            elif _id in [PCIExtCapID.PowerBuget, PCIExtCapID.SecondaryPCIE]:
                cap.len = 16
            elif _id == PCIExtCapID.Multicast:
                cap.len = 48
            elif _id in [PCIExtCapID.SRIOV, PCIExtCapID.AER]:
                cap.len = 64
            else:
                # unknown/unhandled cap, mark its existence
                print(f"unknown ext cap {_id}")
                cap.len = 4

            config.seek(cap_pos)
            cap.content = config.read(cap.len)
            caps.append(cap)
            cap_pos = cap_next

        return caps



class PCIBar:
    class Type(enum.Enum):
        IO    = 'io'
        MEM   = 'mem'
        MEM64 = 'mem64'
        NONE  = 'none'

    def __init__(self, start, size, mask, _type):
        self.start = start
        self.size = size
        self.mask = mask
        self.type = _type

    def to_dict(self):
        values = OrderedDict()
        values['start'] = self.start
        values['size'] = self.size
        values['mask'] = self.mask
        values['type'] = self.type.value
        return values

    @classmethod
    def parse(cls, resource: StringIO) -> list:
        IORESOURCE_IO = 0x00000100
        IORESOURCE_MEM = 0x00000200
        IORESOURCE_MEM_64 = 0x00100000

        bars = list()

        def getline():
            values = resource.readline().split()
            return list(map(lambda x: int(x, 16), values))

        resource.seek(0)
        for i in range(6):
            start, end, flags = getline()
            bar_type = cls.Type.NONE
            size = 0
            mask = 0

            if flags & IORESOURCE_IO:
                bar_type = cls.Type.IO
                size = end - start + 1
                mask = (~(end-start)) & 0xFFFFFFFF
            elif flags & IORESOURCE_MEM:
                if flags & IORESOURCE_MEM_64:
                    bar_type = cls.Type.MEM64
                    start2, end2, flags2 = getline()
                    start = start | (start2<<32)
                    end   = end | (end2<<32)

                    size = end - start + 1
                    mask = (~(end-start)) & 0xFFFFFFFFFFFFFFFF
                else:
                    bar_type = cls.Type.MEM
                    size = end - start + 1
                    mask = (~(end-start)) & 0xFFFFFFFF

            bar = PCIBar(start, size, mask, bar_type)
            bars.append(bar)

        return bars


class PCIDevice():
    class Type(enum.Enum):
        DEVICE = 'device'
        BRIDGE = 'bridge'

    def __init__(self) -> None:
        self.path = ''
        self.type = self.Type.DEVICE
        self.caps: List[PCICap] = list()
        self.bars: List[PCIBar] = list()
        self.name = ''

        self.domain = 0
        self.bus = 0
        self.dev = 0
        self.fun = 0

        self.msi_num = 0
        self.msi_64bits = 0
        self.msi_maskable = 0
        self.msix_num = 0
        self.msix_region_size = 0
        self.msix_address = 0

    def dump(self):
        print("Capability:")
        for cap in self.caps:
            print(f'  {cap.to_dict()}')

        print("Bars:")
        for bar in self.bars:
            print(f'  {bar.to_dict()}')

    def to_dict(self):
        values = OrderedDict()
        values['path'] = self.path
        values['type'] = self.type.value
        values['name'] = self.name
        values['caps'] = list(map(lambda x: x.to_dict(), self.caps))
        values['bars'] = list(map(lambda x: x.to_dict(), self.bars))
        values['domain'] = self.domain
        values['bus'] = self.bus
        values['dev'] = self.dev
        values['fun'] = self.fun
        values['msi_num'] = self.msi_num
        values['msi_64bits'] = self.msi_64bits
        values['msi_maskable'] = self.msi_maskable
        values['msix_num'] = self.msix_num
        values['msix_region_size'] = self.msix_region_size
        values['msix_address'] = self.msix_address
        return values

    @classmethod
    def from_sysfs(cls, path: str):
        try:
            with open(os.path.join(path, 'config'), "rb") as f:
                config_data = f.read()
        except:
            print("read config file failed.")
            return None

        try:
            with open(os.path.join(path, 'resource'), "rt") as f:
                resource_data = f.read()
        except:
            print("read config file failed.")
            return None

        if len(config_data) != 4096:
            print("invalid config length", len(config_data))
            return None

        print('config length:', len(config_data))
        config = BytesIO(config_data)
        resource = StringIO(resource_data)

        dev = PCIDevice()
        dev.path = path

        slot = os.path.basename(path)
        name = os.popen("lspci -s {}".format(slot)).read().strip()
        dev.name = name[name.find(' ')+1:]

        config.seek(0)
        vendor, = struct.unpack('<I', config.read(4))
        if vendor == 0xffffffff:
            print(f'WARNING: Ignoring apparently disabled PCI device {path}')
            return None

        config.seek(0x0A)
        (classcode,) = struct.unpack('<H', config.read(2))
        if classcode == 0x0604:
            dev.type = cls.Type.BRIDGE
        else:
            dev.type = cls.Type.DEVICE

        #dev = PCIDevice().from_sysfs('/sys/bus/pci/devices/0000:09:00.0')
        domain_str, bus_str, df_str = os.path.basename(path).split(':')
        dev.domain = int(domain_str, 16)
        dev.bus    = int(bus_str, 16)
        dev.dev    = int(df_str.split('.')[0], 16)
        dev.fun    = int(df_str.split('.')[1], 16)

        dev.caps = PCICap.parse(config)
        dev.bars = PCIBar.parse(resource)

        for c in dev.caps:
            if c.cap in (PCICapID.MSI, PCICapID.MSIX):
                msg_ctrl = struct.unpack('<H', c.content[2:4])[0]
                if c.cap is PCICapID.MSI:
                    dev.msi_num = 1 << ((msg_ctrl >> 1) & 0x7)
                    dev.msi_64bits = (msg_ctrl >> 7) & 1
                    dev.msi_maskable = (msg_ctrl >> 8) & 1
                else:  # MSI-X
                    if c.msix_addr != 0:
                        vectors = (msg_ctrl & 0x7ff) + 1
                        dev.msix_num = vectors
                        dev.msix_region_size = (vectors * 16 + 0xfff) & 0xf000
                        dev.msix_address = c.msix_addr
                    else:
                        print('WARNING: Ignoring invalid MSI-X configuration'
                              ' of device %02x:%02x.%x' % (dev.bus, dev.dev, dev.fun))

        return dev

    @classmethod
    def all_from_sysfs(cls):
        devices = []
        pci_list = sorted(glob.glob('/sys/bus/pci/devices/*'))

        for pci in pci_list:
            d = PCIDevice.from_sysfs(pci)
            if d is not None:
                devices.append(d)
        return devices


if __name__ == '__main__':
    import pprint
    devs = PCIDevice().all_from_sysfs()
    for dev in devs:
        pprint.pprint(dev.to_dict())

