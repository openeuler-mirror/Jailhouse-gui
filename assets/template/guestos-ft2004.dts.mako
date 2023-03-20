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
%>


/ {
    compatible = "phytium,2000";
    model = "FT-D2000 Guest";
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

        reg = <0x0 0x29900000 0 0x20000>,       /* GICD */
              <0x0 0x29980000 0 0x80000>,       /* GICR */
              <0x0 0x29c00000 0 0x10000>,       /* GICC */
              <0x0 0x29c10000 0 0x10000>,       /* GICH */
              <0x0 0x29c20000 0 0x10000>;       /* GICV */

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

        %if 0 in cpu['cpus']:
        cpu0: cpu@0 {
                device_type = "cpu";
                compatible = "arm,armv8";
                reg = <0x0 0x0>;
                enable-method = "psci";
                numa-node-id = <0>;
                clocks = <&scpi_dvfs 0>;
        };
        %endif
        %if 1 in cpu['cpus']:
        cpu1: cpu@1 {
                device_type = "cpu";
                compatible = "arm,armv8";
                reg = <0x0 0x1>;
                enable-method = "psci";
                numa-node-id = <0>;
                clocks = <&scpi_dvfs 0>;
        };
        %endif
        %if 2 in cpu['cpus']:
        cpu2: cpu@100 {
                device_type = "cpu";
                compatible = "arm,armv8";
                reg = <0x0 0x100>;
                enable-method = "psci";
                numa-node-id = <0>;
                clocks = <&scpi_dvfs 1>;
        };
        %endif
        %if 3 in cpu['cpus']:
        cpu3: cpu@101 {
                device_type = "cpu";
                compatible = "arm,armv8";
                reg = <0x0 0x101>;
                enable-method = "psci";
                numa-node-id = <0>;
                clocks = <&scpi_dvfs 1>;
        };
        %endif
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
		uart0: uart@28000000 {
			compatible = "arm,pl011", "arm,primecell";
			reg = <0x0 0x28000000 0x0 0x1000>;
			baud = <115200>;
			reg-shift = <2>;
			reg-io-width = <4>;
			interrupts = <${GIC_SPI} 6 ${IRQ_TYPE_LEVEL_HIGH}>;
			clocks = <&sysclk_48mhz &sysclk_48mhz>;
			clock-names = "uartclk", "apb_pclk";
		};
        %endif

        %if has_device("uart1"):
		uart1: uart@28001000 {
			compatible = "arm,pl011", "arm,primecell";
			reg = <0x0 0x28001000 0x0 0x1000>;
			baud = <115200>;
			reg-shift = <2>;
			reg-io-width = <4>;
			interrupts = <${GIC_SPI} 7 ${IRQ_TYPE_LEVEL_HIGH}>;
			clocks = <&sysclk_48mhz &sysclk_48mhz>;
			clock-names = "uartclk", "apb_pclk";
		};
        %endif

        %if has_device("uart2"):
		uart2: uart@28002000 {
			compatible = "arm,pl011", "arm,primecell";
			reg = <0x0 0x28002000 0x0 0x1000>;
			baud = <115200>;
			reg-shift = <2>;
			reg-io-width = <4>;
			interrupts = <${GIC_SPI} 8 ${IRQ_TYPE_LEVEL_HIGH}>;
			clocks = <&sysclk_48mhz &sysclk_48mhz>;
			clock-names = "uartclk", "apb_pclk";
		};
        %endif

        %if has_device("uart3"):
		uart3: uart@28003000 {
			compatible = "arm,pl011", "arm,primecell";
			reg = <0x0 0x28003000 0x0 0x1000>;
			baud = <115200>;
			reg-shift = <2>;
			reg-io-width = <4>;
			interrupts = <${GIC_SPI} 9 ${IRQ_TYPE_LEVEL_HIGH}>;
			clocks = <&sysclk_48mhz &sysclk_48mhz>;
			clock-names = "uartclk", "apb_pclk";
		};
        %endif
    };
};
