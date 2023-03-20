import enum
import ctypes

_U8 = ctypes.c_uint8
_U16 = ctypes.c_uint16
_U32 = ctypes.c_uint32
_U64 = ctypes.c_uint64
_CHAR = ctypes.c_char

JAILHOUSE_CELL_NAME_MAXLEN = 31
JAILHOUSE_SYSTEM_SIGNATURE = b"JHSYST"
JAILHOUSE_SYS_VIRTUAL_DEBUG_CONSOLE	= 0x0001

JAILHOUSE_CELL_DESC_SIGNATURE = b"JHCELL"
JAILHOUSE_CELL_PASSIVE_COMMREG	= 0x00000001
JAILHOUSE_CELL_TEST_DEVICE	= 0x00000002
JAILHOUSE_CELL_AARCH32		= 0x00000004

JAILHOUSE_CELL_VIRTUAL_CONSOLE_PERMITTED = 0x40000000
JAILHOUSE_CELL_VIRTUAL_CONSOLE_ACTIVATE = 0x80000000

class JailhouseConType(enum.Enum):
    JAILHOUSE_CON_TYPE_NONE    = 0x0000
    JAILHOUSE_CON_TYPE_EFIFB   = 0x0001
    JAILHOUSE_CON_TYPE_8250    = 0x0002
    JAILHOUSE_CON_TYPE_PL011   = 0x0003
    JAILHOUSE_CON_TYPE_XUARTPS = 0x0004
    JAILHOUSE_CON_TYPE_MVEBU   = 0x0005
    JAILHOUSE_CON_TYPE_HSCIF   = 0x0006
    JAILHOUSE_CON_TYPE_SCIFA   = 0x0007
    JAILHOUSE_CON_TYPE_IMX     = 0x0008

def jailhouse_con_type_form_str( name ):
    for item in JailhouseConType.__members__:
        if name.upper() in item:
            return JailhouseConType.__members__[item]
    return None

JAILHOUSE_CON_ACCESS_PIO	= 0x0000
JAILHOUSE_CON_ACCESS_MMIO	= 0x0001
JAILHOUSE_CON_REGDIST_1		= 0x0000
JAILHOUSE_CON_REGDIST_4		= 0x0002

JAILHOUSE_PCI_TYPE_DEVICE	= 0x01
JAILHOUSE_PCI_TYPE_BRIDGE	= 0x02
JAILHOUSE_PCI_TYPE_IVSHMEM	= 0x03

JAILHOUSE_SHMEM_PROTO_UNDEFINED    = 0x0000
JAILHOUSE_SHMEM_PROTO_VETH         = 0x0001
JAILHOUSE_SHMEM_PROTO_CUSTOM       = 0x4000
JAILHOUSE_SHMEM_PROTO_VIRTIO_FRONT = 0x8000
JAILHOUSE_SHMEM_PROTO_VIRTIO_BACK  = 0xc000

JAILHOUSE_IVSHMEM_BAR_MASK_INTX = (ctypes.c_uint32*6)(0xfffff000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000)
JAILHOUSE_PCI_EXT_CAP = 0x8000
JAILHOUSE_PCICAPS_WRITE = 0x0001


class jailhouse_memory(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
	    ('phys_start', ctypes.c_uint64),
	    ('virt_start', ctypes.c_uint64),
	    ('size', ctypes.c_uint64),
	    ('flags', ctypes.c_uint64),
    ]

class jailhouse_iommu(ctypes.LittleEndianStructure):

    class PltUnion(ctypes.Union):
        class AMD(ctypes.LittleEndianStructure):
            _pack_ = 1
            _fields_ = [
                ('bdf', _U16),
                ('base_cap', _U8),
                ('msi_cap', _U8),
                ('features', _U32)
            ]

        class TIPVU(ctypes.LittleEndianStructure):
            _pack_ = 1
            _fields_ = [
                ('tlb_base', _U64),
                ('tlb_size', _U32),
            ]

        _fields_ = [
            ('amd', AMD),
            ('vipvu', TIPVU)
        ]

    _pack_ = 1
    _fields_ = [
        ('type', _U32),
        ('base', _U64),
        ('size', _U32),
        ('plt', PltUnion)
    ]


class jailhouse_console(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('address', _U64),
        ('size', _U32),
        ('type', _U16),
        ('flags', _U16),
        ('divider', _U32),
        ('gate_nr', _U32),
        ('clock_reg', _U64),
    ]


class jailhouse_irqchip(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
	    ('address', _U64),
	    ('id', _U32),
	    ('pin_base', _U32),
	    ('pin_bitmap', _U32*4),
    ]

class jailhouse_pci_device(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('type', _U8),
        ('iommu', _U8),
        ('domain', _U16),
        ('bdf', _U16),
        ('bar_mask', _U32*6),
        ('caps_start', _U16),
        ('num_caps', _U16),
        ('num_msi_vectors', _U8),
        # ctypes不支持位域， [0]: 64bit  [1]: maskable
        ('msi', _U8),
        ('num_msix_vectors', _U16),
        ('msix_region_size', _U16),
        ('msix_address', _U64),
        ('shmem_regions_start', _U32),
        ('shmem_dev_id', _U8),
        ('shmem_peers', _U8),
        ('shmem_protocol', _U16),
    ]


class jailhouse_pci_capability(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('id', _U16),
        ('start', _U16),
        ('len', _U16),
        ('flags', _U16),
    ]


class jailhouse_cell_desc(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('signature', _CHAR*6),
        ('revision', _U16),
        ('name', _CHAR*(JAILHOUSE_CELL_NAME_MAXLEN+1)),
        ('id', _U32),
        ('flags', _U32),
        ('cpu_set_size', _U32),
        ('num_memory_regions', _U32),
        ('num_cache_regions', _U32),
        ('num_irqchips', _U32),
        ('num_pio_regions', _U32),
        ('num_pci_devices', _U32),
        ('num_pci_caps', _U32),
        ('num_stream_ids', _U32),
        ('vpci_irq_base', _U32),
        ('cpu_reset_address', _U64),
        ('msg_reply_timeout', _U64),
        ('console', jailhouse_console)
    ]

class jailhouse_system(ctypes.LittleEndianStructure):

    class PlatformInfo(ctypes.LittleEndianStructure):
        class PlatformInfoUnion(ctypes.Union):
            class PlatformInfoX86(ctypes.LittleEndianStructure):
                _pack_ = 1
                _fields_ = [
                    ('pm_timer_address', _U16),
                    ('apic_mode', _U8),
                    ('padding', _U8),
                    ('vtd_interrupt_limit', _U32),
                    ('tsc_khz', _U32),
                    ('apic_khz', _U32),
                ]

            class PlatformInfoARM(ctypes.LittleEndianStructure):
                _pack_ = 1
                _fields_ = [
                    ('maintenance_irq', _U8),
                    ('gic_version', _U8),
                    ('padding', _U8*2),
                    ('gicd_base', _U64),
                    ('gicc_base', _U64),
                    ('gich_base', _U64),
                    ('gicv_base', _U64),
                    ('gicr_base', _U64),
                ]

            _pack_ = 1
            _fields_ = [
                ('x86', PlatformInfoX86),
                ('arm', PlatformInfoARM),
            ]

        _pack_ = 1
        _fields_ = [
            ('pci_mmconfig_base', _U64),
            ('pci_mmconfig_end_bus', _U8),
            ('pci_is_virtual', _U8),
            ('pci_domain', _U16),
            ('iommu_units', jailhouse_iommu*8),
            ('plt', PlatformInfoUnion)
        ]

    _pack_ = 1
    _fields_ = [
        ('signature', ctypes.c_char*6),
        ('revision', ctypes.c_uint16),
        ('flags', ctypes.c_uint32),
        ('hypervisor_memory', jailhouse_memory),
        ('debug_console', jailhouse_console),
        ('platform_info', PlatformInfo),
        ('root_cell', jailhouse_cell_desc)
    ]

class Revision13:
    revision = 13
    sys_signature = JAILHOUSE_SYSTEM_SIGNATURE
    cell_signature = JAILHOUSE_CELL_DESC_SIGNATURE
    system = jailhouse_system
    cell_desc = jailhouse_cell_desc
    memory = jailhouse_memory
    irqchip = jailhouse_irqchip
    pci_device = jailhouse_pci_device
    pci_capability = jailhouse_pci_capability
