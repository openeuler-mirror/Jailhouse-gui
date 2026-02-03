import enum
import ctypes

"""
Jailhouse虚拟化平台接口模块

本模块定义了与Jailhouse hypervisor通信所需的C结构体、枚举类型和常量，
用于描述硬件资源配置（如内存区域、PCI设备、中断控制器等）。
通过ctypes实现Python与C语言数据结构的映射，支持不同版本的Jailhouse API。
"""


# 基础数据类型定义（映射C语言类型）
_U8 = ctypes.c_uint8
_U16 = ctypes.c_uint16
_U32 = ctypes.c_uint32
_U64 = ctypes.c_uint64
_CHAR = ctypes.c_char

# 系统级常量定义
JAILHOUSE_CELL_NAME_MAXLEN = 31     # 细胞（Cell）名称最大长度
JAILHOUSE_SYSTEM_SIGNATURE = b"JHSYST"  # 系统描述符签名（固定标识）
JAILHOUSE_SYS_VIRTUAL_DEBUG_CONSOLE	= 0x0001    # 启用虚拟调试控制台标志

# 细胞描述符常量（用于标识和配置Jailhouse中的隔离单元）
JAILHOUSE_CELL_DESC_SIGNATURE = b"JHCELL"   # 细胞描述符签名
JAILHOUSE_CELL_PASSIVE_COMMREG	= 0x00000001    # 被动通信寄存器标志
JAILHOUSE_CELL_TEST_DEVICE	= 0x00000002    # 测试设备标志
JAILHOUSE_CELL_AARCH32		= 0x00000004    # ARM 32位架构标志
JAILHOUSE_CELL_VIRT_CPUID	= 0x00000100    # 虚拟CPUID标志

JAILHOUSE_CELL_VIRTUAL_CONSOLE_PERMITTED = 0x40000000   # 允许虚拟控制台
JAILHOUSE_CELL_VIRTUAL_CONSOLE_ACTIVATE = 0x80000000    # 激活虚拟控制台

class JailhouseConType(enum.Enum):
    """
    控制台类型枚举
    
    定义不同类型的硬件控制台接口，用于与Jailhouse通信。
    """
    JAILHOUSE_CON_TYPE_NONE    = 0x0000     # 无控制台
    JAILHOUSE_CON_TYPE_EFIFB   = 0x0001     # EFI帧缓冲控制台
    JAILHOUSE_CON_TYPE_8250    = 0x0002     # 8250兼容串口
    JAILHOUSE_CON_TYPE_PL011   = 0x0003     # ARM PL011串口控制器
    JAILHOUSE_CON_TYPE_XUARTPS = 0x0004     # Xilinx XUARTPS串口
    JAILHOUSE_CON_TYPE_MVEBU   = 0x0005     # Marvell MVEBU串口
    JAILHOUSE_CON_TYPE_HSCIF   = 0x0006     # 高通HSCIF串口
    JAILHOUSE_CON_TYPE_SCIFA   = 0x0007     # TI SCIFA串口
    JAILHOUSE_CON_TYPE_IMX     = 0x0008     # NXP i.MX串口控制器

def jailhouse_con_type_form_str( name ):
        """
    根据字符串名称查找对应的JailhouseConType枚举值
    
    Args:
        name: 控制台类型名称（如"8250"、"PL011"）
        
    Returns:
        匹配的JailhouseConType枚举值，未找到则返回None
    """
    for item in JailhouseConType.__members__:
        if name.upper() in item:
            return JailhouseConType.__members__[item]
    return None

# 控制台访问模式和寄存器分布常量
JAILHOUSE_CON_ACCESS_PIO	= 0x0000    # 端口输入输出访问模式
JAILHOUSE_CON_ACCESS_MMIO	= 0x0001    # 内存映射输入输出访问模式
JAILHOUSE_CON_REGDIST_1		= 0x0000    # 寄存器间隔1字节
JAILHOUSE_CON_REGDIST_4		= 0x0002    # 寄存器间隔4字节

# PCI设备类型常量
JAILHOUSE_PCI_TYPE_DEVICE	= 0x01      # 普通PCI设备
JAILHOUSE_PCI_TYPE_BRIDGE	= 0x02      # PCI桥设备
JAILHOUSE_PCI_TYPE_IVSHMEM	= 0x03      # IVSHMEM共享内存设备

# 共享内存协议类型常量
JAILHOUSE_SHMEM_PROTO_UNDEFINED    = 0x0000     # 未定义协议
JAILHOUSE_SHMEM_PROTO_VETH         = 0x0001     # VETH虚拟网络协议
JAILHOUSE_SHMEM_PROTO_CUSTOM       = 0x4000     # 自定义协议
JAILHOUSE_SHMEM_PROTO_VIRTIO_FRONT = 0x8000     # VirtIO前端协议
JAILHOUSE_SHMEM_PROTO_VIRTIO_BACK  = 0xc000     # VirtIO后端协议

# PCI设备相关常量
JAILHOUSE_IVSHMEM_BAR_MASK_INTX = (ctypes.c_uint32*6)(0xfffff000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000)
JAILHOUSE_PCI_EXT_CAP = 0x8000      # PCI扩展能力标志
JAILHOUSE_PCICAPS_WRITE = 0x0001    # PCI能力可写标志


class jailhouse_memory(ctypes.LittleEndianStructure):
    """
    内存区域描述结构体
    
    定义一个物理内存区域，包括起始地址、大小和访问标志。
    """
    _pack_ = 1  # 1字节对齐
    _fields_ = [
	    ('phys_start', ctypes.c_uint64),    # 物理起始地址
	    ('virt_start', ctypes.c_uint64),    # 虚拟起始地址（如适用）
	    ('size', ctypes.c_uint64),  # 区域大小（字节）
	    ('flags', ctypes.c_uint64), # 访问标志（如可读/写/执行）
    ]

class jailhouse_iommu(ctypes.LittleEndianStructure):
    """
    IOMMU(输入输出内存管理单元)配置结构体
    
    描述系统中的IOMMU设备及其参数,支持不同平台的特定配置。
    """
    class PltUnion(ctypes.Union):
        """平台特定IOMMU参数联合体"""
        class AMD(ctypes.LittleEndianStructure):
            """AMD平台IOMMU参数"""
            _pack_ = 1
            _fields_ = [
                ('bdf', _U16),      # 总线/设备/功能号
                ('base_cap', _U8),  # 基础能力寄存器偏移
                ('msi_cap', _U8),   # MSI能力寄存器偏移
                ('features', _U32)  # 功能标志
            ]

        class TIPVU(ctypes.LittleEndianStructure):
            """TIPVU平台IOMMU参数"""
            _pack_ = 1
            _fields_ = [
                ('tlb_base', _U64), # TLB基地址
                ('tlb_size', _U32), # TLB大小
            ]

        _fields_ = [
            ('amd', AMD),       # AMD平台参数
            ('vipvu', TIPVU)    # TIPVU平台参数
        ]

    _pack_ = 1
    _fields_ = [
        ('type', _U32),     # IOMMU类型
        ('base', _U64),     # 基地址
        ('size', _U32),     # 地址空间大小
        ('plt', PltUnion)   # 平台特定参数
    ]


class jailhouse_console(ctypes.Structure):
    """
    控制台设备配置结构体
    
    定义系统控制台的硬件参数，包括地址、类型和通信参数。
    """
    _pack_ = 1
    _fields_ = [
        ('address', _U64),  # 控制台基地址
        ('size', _U32),     # 地址空间大小
        ('type', _U16),     # 控制台类型（JailhouseConType枚举值）
        ('flags', _U16),    # 访问标志
        ('divider', _U32),  # 波特率分频器
        ('gate_nr', _U32),  # 门控信号编号
        ('clock_reg', _U64),# 时钟寄存器地址
    ]


class jailhouse_irqchip(ctypes.Structure):
    """
    中断控制器配置结构体
    
    描述系统中的中断控制器及其支持的中断引脚。
    """
    _pack_ = 1
    _fields_ = [
	    ('address', _U64),      # 中断控制器基地址
	    ('id', _U32),           # 控制器ID
	    ('pin_base', _U32),     # 引脚基准编号
	    ('pin_bitmap', _U32*4), # 引脚位图（支持128个引脚）
    ]

class jailhouse_pci_device_r13(ctypes.Structure):
    """
    Jailhouse v13版本PCI设备配置结构体
    
    描述PCI设备的配置参数，包括BDF编号、BAR配置和中断设置。
    """
    _pack_ = 1
    _fields_ = [
        ('type', _U8),              # 设备类型（PCI/PCIe/IVSHMEM）
        ('iommu', _U8),             # 关联的IOMMU索引
        ('domain', _U16),           # PCI域号
        ('bdf', _U16),              # 总线/设备/功能号
        ('bar_mask', _U32*6),       # BAR（基地址寄存器）掩码
        ('caps_start', _U16),       # 能力寄存器起始偏移
        ('num_caps', _U16),         # 能力寄存器数量
        ('num_msi_vectors', _U8),   # MSI向量数量
        # ctypes不支持位域， [0]: 64bit  [1]: maskable
        ('msi', _U8),               # MSI配置（位0: 64位地址，位1: 可屏蔽）
        ('num_msix_vectors', _U16),     # MSI-X向量数量
        ('msix_region_size', _U16),     # MSI-X区域大小
        ('msix_address', _U64),         # MSI-X基地址
        ('shmem_regions_start', _U32),  # 共享内存区域起始索引
        ('shmem_dev_id', _U8),          # 共享内存设备ID
        ('shmem_peers', _U8),           # 共享内存对等设备数量
        ('shmem_protocol', _U16),       # 共享内存协议类型
    ]

class jailhouse_pci_device_r14(ctypes.Structure):
    """
    Jailhouse v14版本PCI设备配置结构体
    
    扩展自v13版本，增加了虚拟BDF支持。
    """
    _pack_ = 1
    _fields_ = [
        ('type', _U8),                  # 设备类型
        ('iommu', _U8),                 # IOMMU索引
        ('domain', _U16),               # PCI域号
        ('bdf', _U16),                  # 物理BDF
        ('virt_bdf', _U32),             # 虚拟BDF（v14新增）
        ('bar_mask', _U32*6),           # BAR掩码
        ('caps_start', _U16),           # 能力起始偏移
        ('num_caps', _U16),             # 能力数量
        ('num_msi_vectors', _U8),       # MSI向量数
        # ctypes不支持位域， [0]: 64bit  [1]: maskable
        ('msi', _U8),                   # MSI配置
        ('num_msix_vectors', _U16),     # MSI-X向量数
        ('msix_region_size', _U16),     # MSI-X区域大小
        ('msix_address', _U64),         # MSI-X基地址
        ('shmem_regions_start', _U32),  # 共享内存起始索引
        ('shmem_dev_id', _U8),          # 共享内存设备ID
        ('shmem_peers', _U8),           # 共享内存对等设备数
        ('shmem_protocol', _U16),       # 共享内存协议
    ]


class jailhouse_pci_capability(ctypes.Structure):
    """
    PCI设备能力描述结构体
    
    描述PCI设备支持的特定能力，如MSI、PCIe等。
    """
    _pack_ = 1
    _fields_ = [
        ('id', _U16),       # 能力ID
        ('start', _U16),    # 能力起始偏移
        ('len', _U16),      # 能力数据长度
        ('flags', _U16),    # 能力标志（如可写）
    ]


class jailhouse_cell_desc(ctypes.Structure):
    """
    Jailhouse细胞描述符结构体
    
    定义一个Jailhouse细胞（隔离单元）的配置参数，包括内存、CPU和设备分配。
    """
    _pack_ = 1
    _fields_ = [
        ('signature', _CHAR*6),         # 签名（必须为"JHCELL"）
        ('revision', _U16),             # 版本号
        ('name', _CHAR*(JAILHOUSE_CELL_NAME_MAXLEN+1)), # 细胞名称
        ('id', _U32),                   # 细胞ID
        ('flags', _U32),                # 细胞标志
        ('cpu_set_size', _U32),         # CPU集合大小
        ('num_memory_regions', _U32),   # 内存区域数量
        ('num_cache_regions', _U32),    # 缓存区域数量
        ('num_irqchips', _U32),         # 中断控制器数量
        ('num_pio_regions', _U32),      # PIO区域数量
        ('num_pci_devices', _U32),      # PCI设备数量
        ('num_pci_caps', _U32),         # PCI能力数量
        ('num_stream_ids', _U32),       # 流ID数量
        ('vpci_irq_base', _U32),        # vPCI中断基准
        ('cpu_reset_address', _U64),    # CPU重置地址
        ('msg_reply_timeout', _U64),    # 消息回复超时
        ('console', jailhouse_console)  # 控制台配置
    ]

class jailhouse_system(ctypes.LittleEndianStructure):
    """
    Jailhouse系统描述符结构体
    
    定义整个Jailhouse系统的全局配置，包括内存布局、平台信息和根细胞配置。
    """

    class PlatformInfo(ctypes.LittleEndianStructure):
         """平台特定信息结构体"""
        class PlatformInfoUnion(ctypes.Union):
            """不同架构平台信息联合体"""
            class PlatformInfoX86(ctypes.LittleEndianStructure):
                 """x86平台特定信息"""
                _pack_ = 1
                _fields_ = [
                    ('pm_timer_address', _U16),     # PM定时器地址
                    ('apic_mode', _U8),             # APIC模式
                    ('padding', _U8),               # 填充字节
                    ('vtd_interrupt_limit', _U32),  # VT-d中断限制
                    ('tsc_khz', _U32),              # TSC频率（kHz）
                    ('apic_khz', _U32),             # APIC频率（kHz）
                ]

            class PlatformInfoARM(ctypes.LittleEndianStructure):
                """ARM平台特定信息"""
                _pack_ = 1
                _fields_ = [
                    ('maintenance_irq', _U8),   # 维护中断号
                    ('gic_version', _U8),       # GIC版本           
                    ('padding', _U8*2),         # 填充字节
                    ('gicd_base', _U64),        # GICD基地址
                    ('gicc_base', _U64),        # GICC基地址
                    ('gich_base', _U64),        # GICH基地址
                    ('gicv_base', _U64),        # GICV基地址
                    ('gicr_base', _U64),        # GICR基地址
                ]

            _pack_ = 1
            _fields_ = [
                ('x86', PlatformInfoX86),   # x86平台信息
                ('arm', PlatformInfoARM),   # ARM平台信息
            ]

        _pack_ = 1
        _fields_ = [
            ('pci_mmconfig_base', _U64),            # PCI MMConfig基地址
            ('pci_machine_mmconfig_base', _U64),    # 机器特定MMConfig基地址
            ('pci_mmconfig_end_bus', _U8),          # MMConfig结束总线
            ('pci_is_virtual', _U8),                # 是否为虚拟PCI
            ('pci_domain', _U16),                   # PCI域号
            ('iommu_units', jailhouse_iommu*8),     # IOMMU单元数组
            ('plt', PlatformInfoUnion)              # 平台特定信息
        ]

    _pack_ = 1
    _fields_ = [
        ('signature', ctypes.c_char*6),             # 签名（必须为"JHSYST"）
        ('revision', ctypes.c_uint16),              # 版本号
        ('flags', ctypes.c_uint32),                 # 系统标志
        ('hypervisor_memory', jailhouse_memory),    # 管理程序内存区域
        ('debug_console', jailhouse_console),       # 调试控制台配置
        ('platform_info', PlatformInfo),            # 平台特定信息
        ('root_cell', jailhouse_cell_desc)          # 根细胞配置
    ]

class Revision13:
    """
    Jailhouse API v13版本定义
    
    包含v13版本的结构体映射和常量定义。
    """
    revision = 13
    sys_signature = JAILHOUSE_SYSTEM_SIGNATURE
    cell_signature = JAILHOUSE_CELL_DESC_SIGNATURE
    system = jailhouse_system
    cell_desc = jailhouse_cell_desc
    memory = jailhouse_memory
    irqchip = jailhouse_irqchip
    pci_device = jailhouse_pci_device_r13
    pci_capability = jailhouse_pci_capability


class Revision14:
    """
    Jailhouse API v14版本定义
    
    包含v14版本的结构体映射和常量定义，扩展了v13版本的功能。
    """
    revision = 14
    sys_signature = JAILHOUSE_SYSTEM_SIGNATURE
    cell_signature = JAILHOUSE_CELL_DESC_SIGNATURE
    system = jailhouse_system
    cell_desc = jailhouse_cell_desc
    memory = jailhouse_memory
    irqchip = jailhouse_irqchip
    pci_device = jailhouse_pci_device_r14
    pci_capability = jailhouse_pci_capability
