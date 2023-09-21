<%
    KB = 1024
    MB = 1024*1024
    GB = 1024*1024*1024
    def readable_size(value):
        if value > GB:
            return f"{value/GB} GB"
        if value > MB:
            return f"{value/MB} MB"
        if value > KB:
            return f"{value/KB} KB"
        return value
%>
/*
 * Jailhouse, a Linux-based partitioning hypervisor
 * Guest cell configuration for ${name}
 * Created by resource-tool
 */

#include <jailhouse/types.h>
#include <jailhouse/cell-config.h>

struct {
    struct jailhouse_cell_desc cell;
    __u64 cpus[${len(cpu["bitmap"])}];
    struct jailhouse_memory mem_regions[${len(system_mem)+len(memmaps)+len(devices)+ivshmem['count']+2+1}];
    struct jailhouse_irqchip irqchips[1];
    struct jailhouse_pci_device pci_devices[${1+len(pci_devices["devices"])}];
    %if len(pci_devices["caps"]) > 0:
    struct jailhouse_pci_capability pci_caps[${len(pci_devices["caps"])}];
    %endif
} __attribute__((packed)) config = {
    .cell = {
        .signature = JAILHOUSE_CELL_DESC_SIGNATURE,
        .revision = JAILHOUSE_CONFIG_REVISION,
        .name = "${name}",
        <%
            cell_flags = list()
            cell_flags.append('JAILHOUSE_CELL_PASSIVE_COMMREG')
            if system['arch'] == 'AArch32':
                cell_flags.append('JAILHOUSE_CELL_AARCH32')
            if system['virt_console']:
                cell_flags.append('JAILHOUSE_CELL_VIRTUAL_CONSOLE_PERMITTED')
        %>
        .flags = ${'|'.join(cell_flags)},

        .cpu_reset_address = ${hex(system['reset_addr'])},

        .cpu_set_size = sizeof(config.cpus),
        .num_memory_regions = ARRAY_SIZE(config.mem_regions),
        .num_irqchips = ARRAY_SIZE(config.irqchips),
        .num_pci_devices = ARRAY_SIZE(config.pci_devices),
        %if len(pci_devices["caps"]) > 0:
        .num_pci_caps = ARRAY_SIZE(config.pci_caps),
        %endif

        .vpci_irq_base = ${system["vpci_irq_base"]},
        %if system['virt_cpuid']:
        .use_virt_cpuid = 1,
        %endif

        %if console:
        .console = {
            .address = ${hex(console['addr'])},
            .size = ${hex(console['size'])},
            .type = ${console['type'].name}
            .flags = JAILHOUSE_CON_ACCESS_MMIO | JAILHOUSE_CON_REGDIST_4,
        },
        %endif
    },

    .cpus = {
        // CPU: ${cpu['cpus']}
        ${', '.join(cpu['bitmap'])}
    },

    .irqchips = {
        {
            .address = ${hex(gic["gicd_base"])},
            .pin_base = 32,
            .pin_bitmap = {
                %for bitmap in system['irq_bitmaps']:
                ${f"0x{bitmap['bitmap']:08x}"},  // ${bitmap['comment']}
                %endfor
            },
        },
    },

    .mem_regions = {
        %if ivshmem:
        /* IVSHMEM regions */
        {
            .phys_start = ${hex(ivshmem['phys'])},
            .virt_start = ${hex(ivshmem['virt'])},
            .size       = ${hex(ivshmem['state_size'])},  // ${ivshmem['state_size']/1024} KB
            .flags      = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_ROOTSHARED,
        },
        {
            .phys_start = ${hex(ivshmem['phys']+ivshmem['state_size'])},
            .virt_start = ${hex(ivshmem['virt']+ivshmem['state_size'])},
            .size       = ${hex(ivshmem['rw_size'])},  // ${ivshmem['rw_size']/1024} KB
            .flags      = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_ROOTSHARED,
        },
        %for idx in range(ivshmem['count']):
        {
            .phys_start = ${hex(ivshmem['phys']+ivshmem['state_size']+ivshmem['rw_size'] + ivshmem['out_size']*idx)},
            .virt_start = ${hex(ivshmem['virt']+ivshmem['state_size']+ivshmem['rw_size'] + ivshmem['out_size']*idx)},
            .size       = ${hex(ivshmem['out_size'])},  // ${ivshmem['out_size']/1024} KB
            %if idx == ivshmem['id']:
            .flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_ROOTSHARED,
            %else:
            .flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_ROOTSHARED,
            %endif
        },
        %endfor
        %endif

        /****************/
        /* System memory
         ****************/

        %for mem in system_mem:
        %if len(mem['comment']) > 0:
        /* ${mem['comment']} */
        %endif
        {
            .phys_start = ${hex(mem["phys"])},
            .virt_start = ${hex(mem['virt'])},
            .size = ${hex(mem['size'])},  // ${readable_size(mem['size'])}
            %if mem['type'] == 'RESOURCE_TABLE':
            .flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_LOADABLE | JAILHOUSE_MEM_DMA | JAILHOUSE_MEM_RESOURCE_TABLE,
            %else:
            .flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_EXECUTE | JAILHOUSE_MEM_LOADABLE | JAILHOUSE_MEM_DMA,
            %endif
        },
        %endfor

        /*************/
        /* Memory map
         *************/

        %for mem in memmaps:
        %if len(mem['comment']) > 0:
        /* ${mem['comment']} */
        %endif
        {
            .phys_start = ${hex(mem["phys"])},
            .virt_start = ${hex(mem['virt'])},
            .size = ${hex(mem['size'])},  // ${mem['size']/1024/1024} MB
            .flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE,
        },
        %endfor

        /*************/
        /* device
         *************/

        %for dev in devices:
        /* ${dev['name']} */
        {
            .phys_start = ${hex(dev['addr'])},
            .virt_start = ${hex(dev['addr'])},
            .size       = ${hex(dev['size'])},
            .flags      = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO |JAILHOUSE_MEM_ROOTSHARED,
        },
        %endfor

        /* communication region */
        {
            .virt_start = ${hex(comm_region)},
            .size = 0x00001000,
            .flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_COMM_REGION,
        },
    },

    .pci_devices = {
        /* ivshmem */
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

        /* host pci deivce */
        %for idx, dev in enumerate(pci_devices["devices"]):
        /* ${dev['name']} */
        {
            .type = JAILHOUSE_PCI_TYPE_DEVICE,
            .domain = ${dev['domain']},
            .bdf = ${hex(dev['bdf'])},
            .virt_bdf = ${(idx+1)} << 3,
            %if dev['num_caps'] > 0:
            .caps_start = ${dev['caps_start']},
            .num_caps = ${dev['num_caps']},
            %endif
            .bar_mask = {
                ${', '.join(map(lambda x: f'0x{x:08x}', dev['bar_mask']))}
            }
        },
        %endfor
    },
    %if len(pci_devices["caps"]) > 0:
    .pci_caps = {
        %for dev in pci_devices["devices"]:
        %if dev['num_caps'] > 0:
        /* ${dev['name']} */
        %for i in range(dev['caps_start'], dev['caps_start']+dev['num_caps']):
        {
            %if pci_devices['caps'][i]['extended']:
            .id    = ${pci_devices['caps'][i]['id']} | JAILHOUSE_PCI_EXT_CAP,
            %else:
            .id    = ${pci_devices['caps'][i]['id']},
            %endif
            .start = ${pci_devices['caps'][i]['start']},
            .len = ${pci_devices['caps'][i]['len']},
            .flags = ${pci_devices['caps'][i]['flags_str']}
        },
        %endfor
        %endif
        %endfor
    }
    %endif
};