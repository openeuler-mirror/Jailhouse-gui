<%
    def uint64_cells(value):
        return f"0x{value>>32:08x} 0x{value&0xFFFFFFFF:08x}"

    cpu_bitmap = 0
    for c in cpu['cpus']:
        cpu_bitmap = cpu_bitmap | (1<<c)

%>
/dts-v1/;

/ {
    #address-cells = <2>;
    #size-cells = <2>;

    cpu_name = "${system['cpu_name']}";
    cell_name = "${name}";

    memorys {
        #address-cells = <2>;
        #size-cells = <0>;
        %for idx,mem in enumerate(system_mem):
        %if mem['type'] == 'NORMAL':
        memory@${idx} {
            phys = <${uint64_cells(mem['phys'])}>;
            virt = <${uint64_cells(mem['virt'])}>;
            size = <${uint64_cells(mem['size'])}>;
        };
        %endif
        %endfor
    };

    gic@0 {
        reg = <${uint64_cells(gic['gicd_base'])} 0 0x10000>,   // GICD
              <${uint64_cells(gic['gicr_base'])} 0 0x100000>,  // GICR
              <${uint64_cells(gic['gicc_base'])} 0 0x10000>,   // GICC
              <${uint64_cells(gic['gich_base'])} 0 0x10000>,   // GICH
              <${uint64_cells(gic['gicv_base'])} 0 0x10000>;   // GICV
    };

    cpu {
        mask = <${uint64_cells(cpu_bitmap)}>;
    };

    devices {
        #address-cells = <2>;
        #size-cells = <2>;
        %for dev in devices:
        ${dev['name']} {
            reg = <${uint64_cells(dev['addr'])} ${uint64_cells(dev['size'])}>;
            %if len(dev['irq']) > 0:
            irq = <${' '.join(map(lambda x: f"{x}", dev['irq']))}>;
            %endif
        };
        %endfor
    };
};