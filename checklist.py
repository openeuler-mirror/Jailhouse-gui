import os
import abc
import click
import itertools
from typing import List
from jh_resource import ResourceBase, Resource, ResourceBoard, ResourcePlatform, ResourceComm
from jh_resource import ResourceJailhouse, ResourceRootCell
from jh_resource import ResourceGuestCellList, ResourceGuestCell
from jh_resource import MemRegion, MemMap, MemRegionList
from jh_resource import ResourceMgr
from jh_resource import CommonOSRunInfo, LinuxRunInfo, ACoreRunInfo

# TODO
# ERROR 仅仅一个device table
# WARN  设备表不超过1MB


def align_4k(value) -> bool:
    if value & (4096-1):
        return False
    return True


class CheckResult():
    def __init__(self, name) -> None:
        self.name = name
        self.state = True
        self.failed_messages = list()
        self.warning_messages = list()

    def failed(self, msg):
        self.state = False
        self.failed_messages.append(msg)

    def warning(self, msg):
        self.warning_messages.append(msg)

    def __bool__(self):
        return self.state

    def __str__(self) -> str:
        value = list()
        if self.state:
            value.append(f'{self.name} : 成功')
        else:
            value.append(f'{self.name} : 失败')
        for msg in self.failed_messages:
            value.append(f'    {msg}')
        for msg in self.warning_messages:
            value.append(f'    {msg}')
        return '\n'.join(value)

class Checklist(object):

    def __init__(self) -> None:
        super().__init__()

    @classmethod
    def check(cls, rsc: Resource) -> List[CheckResult]:
        results = list()
        rootcell = rsc.jailhouse().rootcell()
        guestcells = rsc.jailhouse().guestcells()
        board = rsc.platform().board()

        results.extend(cls.platform_check(rsc.platform()))
        results.extend(cls.rootcell_check(rsc.jailhouse().rootcell()))

        # guestcell检查
        for guestcell in guestcells:
            results.extend(cls.guestcell_check(guestcell))

        # 运行检查
        for guestcell in guestcells:
            results.extend(cls.run_check(guestcell))

        results.extend(cls.conflict_check(rsc))

        return results

    @classmethod
    def platform_check(cls, platform: ResourcePlatform) -> List[CheckResult]:
        results = list()
        # 检查CPU的region地址空间
        # 1. 重叠区域
        # 2. 4KB对齐
        item = CheckResult("检查CPU地址空间")
        regions = platform.cpu().regions()
        for r in regions:
            if r.addr() & (4096-1) > 0:
                item.failed(f'{r.name()} 起始地址为按4K对齐')
            if r.size() & (4096-1) > 0:
                item.failed(f'{r.name()} 大小未按4K对齐')
        for r1, r2, in itertools.combinations(regions, 2):
            if MemRegion(r1.addr(), r1.size()).is_overlap(MemRegion(r2.addr(), r2.size())):
                item.failed(f"{r1.name()}({r1.size():x}@{r1.addr():x}) 与 {r2.name()}({r2.size():x}@{r2.addr():x}) 地址空间重叠")
        results.append(item)
        return results

    @classmethod
    def rootcell_check(cls, rootcell: ResourceRootCell) -> List[CheckResult]:
        results = list()
        name = rootcell.name()
        board: ResourceBoard = rootcell.find(ResourceBoard)

        item = CheckResult("检查rootcell名称")
        if not ResourceRootCell.check_name(name):
            item.failed("名称 {name} 非法")
        results.append(item)

        # 检查hypervisor固件内存
        # * 不小于2MB
        # * 4K对齐
        # * 应该在板级内存空间中
        item = CheckResult("检查hypervisor固件内存")
        mem = rootcell.hypervisor()
        if not board.ram_region_list().contains(mem):
            item.failed(f"hypervisor固件内存 {mem} 未包含在板级内存中")
        if mem.size() < 2*1024*1024:
            item.failed(f"hypervisor固件内存 {mem} 空间太小")
        if not align_4k(mem.addr()) or not align_4k(mem.size()):
            item.failed(f"hypervisor固件内存 {mem} 未4K对齐")
        results.append(item)

        # 检查rootcell系统内存
        # * 系统内存不为空
        # * 4K对齐
        # * 应该在板级内存空间中
        for mem in rootcell.system_mem():
            if not board.ram_region_list().contains(mem):
                item.failed(f"rootcell系统内存 {mem} 未包含在板级内存中")
            if not align_4k(mem.addr()) or not align_4k(mem.size()):
                item.failed(f"rootcell系统内存 {mem} 未4K对齐")
        results.append(item)

        return results

    @classmethod
    def conflict_check(cls, rsc: Resource) -> List[CheckResult]:
        """
        资源冲突检查
        """
        rootcell = rsc.jailhouse().rootcell()
        guestcells = rsc.jailhouse().guestcells()
        results = list()

        ivshmem = rsc.jailhouse().ivshmem()
        ivshmem_size = ivshmem.ivshmem_state_size() + ivshmem.ivshmem_rw_size() + ivshmem.ivshmem_out_size()*guestcells.cell_count()
        ivshmem_addr = ivshmem.ivshmem_phys()

        # 检查内存空间分配冲突
        item = CheckResult("检查内存空间分配冲突")
        memorys = list()
        memorys.append( (f"hypervisor固件内存", rootcell.hypervisor()) )
        memorys.append( (f"ivshmem内存 {ivshmem_size:x}@{ivshmem_addr:x}", MemRegion(ivshmem_addr, ivshmem_size)) )
        for mem in rootcell.system_mem():
            memorys.append( (f"rootcell系统内存 {mem} {mem.addr():x}~{mem.end():x}", mem) )
        for guestcell in guestcells:
            for mem in guestcell.system_mem():
                memorys.append( (f"guestcell({guestcell.name()}) {mem.size():x}@{mem.phys():x}~{mem.phys()+mem.size():x}", MemRegion(mem.phys(), mem.size())) )
        for r1, r2, in itertools.combinations(memorys, 2):
            if r1[1].is_overlap(r2[1]):
                item.failed(f"{r1[0]} 与 {r2[0]} 地址空间重叠")
        results.append(item)

        # 检查设备分配冲突
        item = CheckResult("检查设备分配冲突")
        devices = list()
        for guestcell in guestcells:
            devices.append( (f"{guestcell.name()}", set(guestcell.devices())) )
        for d1, d2, in itertools.combinations(devices, 2):
            conflict = d1[1].intersection(d2[1])
            if len(conflict) > 0:
                item.failed(f"guestcell {d1[0]}和P{d2[0]} 包含相同的设备 {' '.join(conflict)}")
        results.append(item)

        # 检查CPU分配冲突
        item = CheckResult("CPU分配冲突检查")
        for c1, c2, in itertools.combinations(list(guestcells), 2):
            conflict = c1.cpus().intersection(c2.cpus())
            if len(conflict) > 0:
                item.failed(f"guestcell {c1.name()}和P{c2.name()} 包含相同的CPU {conflict}")
        guestcells_cpus = set()
        for cell in guestcells:
            guestcells_cpus = guestcells_cpus.union(cell.cpus())
        #rootcell_cpus = set([i for i in range(rsc.platform().cpu().cpu_count())]).difference(guestcells_cpus)
        enabled_cpus = rsc.platform().board().cpus()
        if not guestcells_cpus.issubset(enabled_cpus):
            item.failed(f"guest cell 的 CPU {guestcells_cpus.difference(enabled_cpus)} 未开启")
        rootcell_cpus = enabled_cpus.difference(guestcells_cpus)
        if len(rootcell_cpus) == 0:
            item.failed("所有CPU全部分配给guest cell,root cell无CPU可用")
        results.append(item)

        return results

    @classmethod
    def guestcell_check(cls, cell: ResourceGuestCell) -> List[CheckResult]:
        cellname = cell.name()
        results = list()

        board: ResourceBoard = cell.find(ResourceBoard)
        board_mem = board.ram_region_list()
        ivshmem: ResourceComm = cell.find(ResourceJailhouse).ivshmem()
        guestcells: ResourceGuestCellList = cell.find(ResourceGuestCellList)
        rootcell: ResourceRootCell = cell.find(ResourceRootCell)
        ivshmem_size = ivshmem.ivshmem_state_size() + ivshmem.ivshmem_rw_size() + ivshmem.ivshmem_out_size()*guestcells.cell_count()
        ivshmem_addr = cell.ivshmem_virt_addr()
        ivshmem_region = MemRegion(ivshmem_addr, ivshmem_size)
        comm_region = MemRegion(cell.comm_region(), 64*1024)
        # TODO 大小应该为多少？
        pci_mmcfg = MemRegion( rootcell.pci_mmconfig().base_addr, 0x08000000)


        # 检查guestcell CPU
        item = CheckResult(f"检查 guestcell [{cellname}] CPU")
        if len(cell.cpus()) == 0:
            item.failed(f'CPU为空')
        results.append(item)

        # 检查guestcell系统内存
        # * 系统内存不为空
        # * 地址和大小按4K对齐
        # * 系统内存位于物理内存中
        item = CheckResult(f"检查 guestcell ({cellname}) 系统内存")
        if len(cell.system_mem_normal()) == 0:
            item.failed("未指定系统内存")
        if cell.system_mem_resource_table() is None:
            item.warning("未指定资源表内存, 如果guest操作系统依赖资源表，会导致guest操作无法运行")
        for mem in cell.system_mem():
            if not align_4k(mem.phys()) or not align_4k(mem.virt()) or not align_4k(mem.size()):
                item.failed(f"系统内存 {mem.size():x}@{mem.phys():x}:{mem.virt():x} 未按4K对齐")
            if mem.size() == 0:
                item.failed(f"系统内存 {mem.size():x}@{mem.phys():x}:{mem.virt():x} 大小为0")
            if not board_mem.contains(MemRegion(mem.phys(), mem.size())):
                item.failed(f"系统内存 {mem.size():x}@{mem.phys():x} 未包含在板级内存中")
        results.append(item)

        # 检查guestcell虚拟内存空间冲突
        item = CheckResult(f"检查 guestcell (cellname) 虚拟地址空间冲突")
        memorys = list()
        memorys.append( (f"ivshmem空间 {ivshmem_region}", ivshmem_region) )
        memorys.append( (f"communication region空间 {comm_region}", comm_region) )
        memorys.append( (f"pci mmconfig空间 {comm_region}", pci_mmcfg) )
        # TODO 设备地址空间
        for mem in cell.system_mem():
            region = MemRegion(mem.virt(), mem.size())
            memorys.append( (f"系统内存 {region}", region) )
        for mem in cell.memmaps():
            region = MemRegion(mem.virt(), mem.size())
            memorys.append( (f"地址空间映射 {region}", region) )
        for r1, r2, in itertools.combinations(memorys, 2):
            if r1[1].is_overlap(r2[1]):
                item.failed(f"{r1[0]} 与 {r2[0]} 地址空间重叠")
        results.append(item)

        return results

    @classmethod
    def run_check(cls, guestcell: ResourceGuestCell) -> List[CheckResult]:
        """
        检查guestcell运行配置
        """
        rsc: Resource = guestcell.find(Resource)
        cellname = guestcell.name()
        results = list()
        runinfo = guestcell.runinfo()
        os_runinfo = runinfo.os_runinfo()

        virt_regions = MemRegionList()
        for mem in guestcell.system_mem_normal():
            virt_regions.add(mem.virt(), mem.phys())

        # 通用系统
        if isinstance(os_runinfo, CommonOSRunInfo):
            item = CheckResult(f"检查 {cellname} guestcell 镜像数量")
            count = 0
            for image in os_runinfo.images():
                if not image.enable:
                    continue
                count = count + 1
            if count == 0:
                item.failed("镜像为空")
            results.append(item)

            for image in os_runinfo.images():
                if not image.enable:
                    continue
                item = CheckResult(f"检查 {cellname} 镜像 {image}")
                if len(image.filename.strip()) == 0:
                    item.failed("未指定镜像文件名")
                if not virt_regions.contains(MemRegion(image.addr,4)):
                    item.failed("镜像起始地址未包含在虚拟地址空间中")
                if os.path.isfile(rsc.abs_path(image.filename)):
                    size = os.path.getsize(rsc.abs_path(image.filename))
                    if not virt_regions.contains(MemRegion(image.addr,size)):
                        item.failed("镜像内容未包含在虚拟地址空间中")
                else:
                    item.failed("镜像文件不存在")
                results.append(item)

            item = CheckResult(f"检查 {cellname} 入口地址")
            if not virt_regions.contains(MemRegion(os_runinfo.reset_addr(),4)):
                item.failed("入口地址不在虚拟地址空间中")
            results.append(item)

        # linux系统
        elif isinstance(os_runinfo, LinuxRunInfo):
            item = CheckResult(f"检查 {cellname} linux 内核镜像")
            if not os.path.isfile(rsc.abs_path(os_runinfo.kernel)):
                item.failed("内核镜像不存在")
            results.append(item)

            item = CheckResult(f"检查 {cellname} linux ramdisk")
            if not os.path.isfile(rsc.abs_path(os_runinfo.kernel)):
                item.failed("ramdisk镜像不存在")
            results.append(item)

            item = CheckResult(f"检查 {cellname} communication region 地址")
            if guestcell.comm_region() != 0x80000000:
                item.failed("communication region地址必须指定为0x80000000, 否则linux无法启动")
            results.append(item)

            item = CheckResult(f"检查 Linux 运行配置")
            if guestcell.virt_cpuid():
                item.failed("运行Guest Linux系统不能配置虚拟CPUID")

        # 天脉系统
        elif isinstance(os_runinfo, ACoreRunInfo):
            item = CheckResult(f"检查 {cellname} MSL 镜像")
            msl = os_runinfo.msl
            if os.path.isfile(rsc.abs_path(msl.filename)):
                size = os.path.getsize(rsc.abs_path(msl.filename))
                if not virt_regions.contains(MemRegion(msl.addr,size)):
                    item.failed("镜像内容未包含在虚拟地址空间中")
            else:
                item.failed("MSL镜像不存在")
            if msl.addr != 0:
                item.failed("MSL地址因该为0")

            item = CheckResult(f"检查 {cellname} OS 镜像")
            os_img = os_runinfo.os
            if os.path.isfile(rsc.abs_path(os_img.filename)):
                size = os.path.getsize(rsc.abs_path(os_img.filename))
                if not virt_regions.contains(MemRegion(os_img.addr,size)):
                    item.failed("镜像内容未包含在虚拟地址空间中")
            else:
                item.failed("OS镜像不存在")

            if os_runinfo.app.enable:
                item = CheckResult(f"检查 {cellname} APP 镜像")
                app_img = os_runinfo.app
                if os.path.isfile(rsc.abs_path(app_img.filename)):
                    size = os.path.getsize(rsc.abs_path(app_img.filename))
                    if not virt_regions.contains(MemRegion(app_img.addr,size)):
                        item.failed("镜像内容未包含在虚拟地址空间中")
                else:
                    item.failed("APP镜像不存在")

            results.append(item)

        return results


@click.command()
@click.argument('jhr')
def check_cli(jhr):
    rsc = ResourceMgr.get_instance().open(jhr)
    if rsc is None:
        print("open failed.")
        return False

    results = Checklist.check(rsc)
    for result in results:
        print(result)


if __name__ == '__main__':
    check_cli()