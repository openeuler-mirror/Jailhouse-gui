/dts-v1/;
/memreserve/ 0x80000000 0x10000;

//#include <dt-bindings/interrupt-controller/arm-gic.h>
<%
GIC_SPI                 = 0
GIC_PPI                 = 1
IRQ_TYPE_NONE           = 0
IRQ_TYPE_EDGE_RISING    = 1
IRQ_TYPE_EDGE_FALLING   = 2
IRQ_TYPE_EDGE_BOTH	    = IRQ_TYPE_EDGE_FALLING | IRQ_TYPE_EDGE_RISING
IRQ_TYPE_LEVEL_HIGH     = 4
IRQ_TYPE_LEVEL_LOW      = 8

def has_device(name):
    for dev in devices:
        if dev['name'] == name:
            return True
    return False

def cpuid(idx):
    return (idx//4) * 0x100 + (idx%4)
%>


/ {
    compatible = "phytium,2000plus";
    model = "FT2000plus Guest";
    interrupt-parent = < &gic >;
    #address-cells = <2>;
    #size-cells = <2>;

    hypervisor {
        compatible = "jailhouse,cell";
    };

    gic: interrupt-controller@299a0000 {
        compatible = "arm,gic-v3";
        #interrupt-cells = <3>;
        #address-cells = <2>;
        #size-cells = <2>;
        ranges;
        interrupt-controller;

        reg = <0x0800 0x2a000000 0 0x10000>,    /* GICD */
              <0x0800 0x2a800000 0 0x800000>,   /* GICR */
              <0x0800 0x29c00000 0 0x10000>,    /* GICC */
              <0x0800 0x29c10000 0 0x10000>,    /* GICH */
              <0x0800 0x29c20000 0 0x10000>;    /* GICV */

        interrupts = <${GIC_PPI} 9 ${IRQ_TYPE_LEVEL_HIGH}>;
    };

    psci {
        compatible   = "arm,psci-1.0";
        method       = "smc";
        cpu_suspend  = <0xc4000001>;
        cpu_off      = <0x84000002>;
        cpu_on       = <0xc4000003>;
        sys_poweroff = <0x84000008>;
        sys_reset    = <0x84000009>;
    };

    cpus {
        #address-cells = <0x2>;
        #size-cells = <0x0>;

        %for idx in cpu['cpus']:
        cpu${idx}: cpu@${f'{cpuid(idx):x}'} {
            device_type = "cpu";
            compatible = "arm,armv8";
            reg = <0x0 ${hex(cpuid(idx))}>;
            enable-method = "psci";
			numa-node-id = <0>;
        };
        %endfor
    };

    timer {
        compatible = "arm,armv8-timer";
        interrupts = <${GIC_PPI} 13 ${IRQ_TYPE_LEVEL_LOW}>,
                     <${GIC_PPI} 14 ${IRQ_TYPE_LEVEL_LOW}>,
                     <${GIC_PPI} 11 ${IRQ_TYPE_LEVEL_LOW}>,
                     <${GIC_PPI} 10 ${IRQ_TYPE_LEVEL_LOW}>;
        clock-frequency = <48000000>;
    };

    clocks {
        #address-cells = <2>;
        #size-cells = <2>;
        ranges;

        clk250hz: clk250mhz {
            compatible = "fixed-clock";
            #clock-cells = <0>;
            clock-frequency = <250000000>;
        };
        clk48mhz: clk48mhz {
            compatible = "fixed-clock";
            #clock-cells = <0>;
            clock-frequency = <48000000>;
        };
        clk600hz: clk600mhz {
            compatible = "fixed-clock";
            #clock-cells = <0>;
            clock-frequency = <6000000>;
        };
    };

    soc {
        compatible = "simple-bus";
        #address-cells = <2>;
        #size-cells = <2>;
        dma-coherent;
        ranges;

        %if has_device("uart0"):
        uart0: serial@28000000 {
            compatible = "snps,dw-apb-uart";
            reg = <0x800 0x28000000 0x0 0x1000>;
            clock-frequency = <50000000>;
            interrupts = <${GIC_SPI} 34 ${IRQ_TYPE_LEVEL_HIGH}>;
            reg-shift = <2>;
            reg-io-width = <4>;
            status = "ok";
        };
        %endif

        %if has_device("uart1"):
        uart1: serial@28001000 {
            compatible = "snps,dw-apb-uart";
            reg = <0x800 0x28001000 0x0 0x1000>;
            clock-frequency = <50000000>;
            interrupts = <${GIC_SPI} 35 ${IRQ_TYPE_LEVEL_HIGH}>;
            reg-shift = <2>;
            reg-io-width = <4>;
            status = "ok";
        };
        %endif
    };
};
