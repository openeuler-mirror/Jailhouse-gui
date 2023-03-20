<%!
    import math
%>
/*
 * Jailhouse, a Linux-based partitioning hypervisor
 * Root cell configuration for ${name}
 * Created by resource-tool
 */

#include <jailhouse/types.h>
#include <jailhouse/cell-config.h>

struct {
    struct jailhouse_system header;
    __u64 cpus[${len(cpu["bitmap"])}];
    struct jailhouse_memory mem_regions[${len(devices)+len(board_mems)+len(regions)+ivshmem['count']+2}];
    struct jailhouse_irqchip irqchips[1];
    struct jailhouse_pci_device pci_devices[${1+len(pci_devices)}];
} __attribute__((packed)) config = {
    .header = {
        .signature = JAILHOUSE_SYSTEM_SIGNATURE,
        .revision = JAILHOUSE_CONFIG_REVISION,
        .flags = JAILHOUSE_SYS_VIRTUAL_DEBUG_CONSOLE,
        .hypervisor_memory = {
            .phys_start = ${hex(hypervisor["addr"])},
            .size =       ${hex(hypervisor["size"])},
        },
        %if debug_console:
        .debug_console = {
            .address = ${hex(debug_console['addr'])},
            .size = ${hex(debug_console['size'])},
            /* TODO */
            %if system['cpu_name'] == 'ft2000plus':
            .type = JAILHOUSE_CON_TYPE_8250,
            %else:
            .type = JAILHOUSE_CON_TYPE_PL011,
            %endif
            .flags = JAILHOUSE_CON_ACCESS_MMIO | JAILHOUSE_CON_REGDIST_4,
        },
        %endif
        .platform_info = {
            /* TODO PCI配置空间地址, 当前写死, 后面需要根据平台修改 */
            // %if system['cpu_name'] == 'ft2000plus':
            // .pci_machine_mmconfig_base = 0x80040000000,
            // %else:
            // .pci_machine_mmconfig_base = 0x40000000,
            // %endif
            .pci_mmconfig_base = ${hex(pci_mmconfig["base"])},
            .pci_mmconfig_end_bus = ${hex(pci_mmconfig["end_bus"])},
            .pci_is_virtual = 1,
            .pci_domain = ${pci_mmconfig["pci_domain"]},

            .arm = {
                .gic_version = ${gic_info["gic_version"]},
                .gicd_base = ${hex(gic_info["gicd_base"])},
                .gicr_base = ${hex(gic_info["gicr_base"])},
                .gicc_base = ${hex(gic_info["gicc_base"])},
                .gich_base = ${hex(gic_info["gich_base"])},
                .gicv_base = ${hex(gic_info["gicv_base"])},
                .maintenance_irq = 25,
            },
        },
        .root_cell = {
            .name = "${name}",

            .cpu_set_size = sizeof(config.cpus),
            .num_memory_regions = ARRAY_SIZE(config.mem_regions),
            .num_irqchips = ARRAY_SIZE(config.irqchips),
            .num_pci_devices = ARRAY_SIZE(config.pci_devices),

            .vpci_irq_base = ${vpci_irq_base},
        },
    },

    .cpus = {
        // CPU count: cpu['count']
        ${', '.join(cpu['bitmap'])}
    },

    .mem_regions = {
        %if ivshmem:
        /* IVSHMEM regions */
        {
            .phys_start = ${hex(ivshmem['phys'])},
            .virt_start = ${hex(ivshmem['virt'])},
            .size       = ${hex(ivshmem['state_size'])},  // ${ivshmem['state_size']/1024} KB
            .flags      = JAILHOUSE_MEM_READ,
        },
        {
            .phys_start = ${hex(ivshmem['phys']+ivshmem['state_size'])},
            .virt_start = ${hex(ivshmem['virt']+ivshmem['state_size'])},
            .size       = ${hex(ivshmem['rw_size'])},  // ${ivshmem['rw_size']/1024} KB
            .flags      = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE,
        },
        %for idx in range(ivshmem['count']):
        {
            .phys_start = ${hex(ivshmem['phys']+ivshmem['state_size']+ivshmem['rw_size'] + ivshmem['out_size']*idx)},
            .virt_start = ${hex(ivshmem['virt']+ivshmem['state_size']+ivshmem['rw_size'] + ivshmem['out_size']*idx)},
            .size       = ${hex(ivshmem['out_size'])},  // ${ivshmem['out_size']/1024} KB
            %if idx == ivshmem['id']:
            .flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE,
            %else:
            .flags = JAILHOUSE_MEM_READ,
            %endif
        },
        %endfor
        %endif

        /* system memory */
        %for mem in board_mems:
        {
            .phys_start = ${hex(mem['addr'])},
            .virt_start = ${hex(mem['addr'])},
            .size       = ${hex(mem['size'])}, // ${mem['size']/1024/1024} MB
            .flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_EXECUTE,
        },
        %endfor

        /*****************/
        /* Devices
         *****************/
        %for dev in devices:
        /* ${dev['name']} */
        {
            .phys_start = ${hex(dev['addr'])},
            .virt_start = ${hex(dev['addr'])},
            .size       = ${hex(dev['size'])}, // ${dev['size']/1024} KB
            .flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO,
        },
        %endfor

        /*****************/
        /* Regions
         *****************/
        %for region in regions:
        /* ${region['name']} */
        {
            .phys_start = ${hex(region['addr'])},
            .virt_start = ${hex(region['addr'])},
            .size       = ${hex(region['size'])}, // ${region['size']/1024} KB
            .flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO,
        },
        %endfor
    },

    .irqchips = {
        /* GIC */
        {
            .address = ${hex(gic_info["gicd_base"])},
            .pin_base = 32,
            .pin_bitmap = {
                0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff,
            },
        },
    },

    %if len(pci_devices) > 0 or ivshmem is not None:
    .pci_devices = {
        %if ivshmem is not None:
        {
            .type = JAILHOUSE_PCI_TYPE_IVSHMEM,
            .domain = 1,
            .bdf = 0 << 3,
            .bar_mask = JAILHOUSE_IVSHMEM_BAR_MASK_INTX,
            .shmem_regions_start = 0,
            .shmem_dev_id = ${ivshmem['id']},
            .shmem_peers = ${ivshmem['count']},
            .shmem_protocol = JAILHOUSE_SHMEM_PROTO_UNDEFINED,
        },
        %endif
    },
    %endif
};
