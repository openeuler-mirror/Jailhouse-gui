"""
RPC 服务与测试 API 模块。

该模块封装了基于 `zerorpc` 的 RPC 服务运行/停止逻辑，并提供一个用于本地
测试的 `TestAPI` 实现（继承 `RPCApi`），便于在开发时快速验证 RPC 通信与
返回结构。

主要类:
- `RPCServer`: 封装 `zerorpc.Server`，提供 `run()` 与 `stop()` 接口。
- `TestAPI`: `RPCApi` 的示例实现，包含若干 stub 方法与一个返回主机状态的 `get_status()`。

使用示例:
```
from rpc_server.server import RPCServer, TestAPI
s = RPCServer("tcp://0.0.0.0:4240", TestAPI())
s.run()
```

注意: 本模块依赖 `zerorpc` 和 `psutil`，用于运行 RPC 服务与获取主机性能数据。
"""

import zerorpc
from typing import Optional
from api import RPCApi
import psutil


class RPCServer(object):
    """RPC 服务封装类。

    Args:
        addr (str): 绑定地址，例如 `tcp://0.0.0.0:4240`。
        api (RPCApi): 实现了 RPC 接口的对象实例，被 `zerorpc.Server` 暴露。
    """

    def __init__(self, addr: str, api: RPCApi):
        self._addr = addr
        self._api = api
        self._server: Optional[zerorpc.Server] = None

    def run(self) -> bool:
        """启动 RPC 服务并阻塞运行。

        返回:
            bool: 成功启动返回 True；若服务已存在则返回 False。
        """
        if self._server is not None:
            return False
        self._server = zerorpc.Server(self._api)
        self._server.bind(self._addr)
        self._server.run()
        return True

    def stop(self):
        """停止正在运行的 RPC 服务（若存在）。"""
        if self._server is None:
            return
        self._server.stop()
        self._server = None


class TestAPI(RPCApi):
    """用于本地测试的 RPC 接口实现（多数方法为 stub）。

    该类实现 `RPCApi` 接口以便在开发阶段快速启动 RPC 服务并测试 RPC 通信。
    大多数方法返回未实现的提示，`get_status` 返回主机资源信息。
    """

    def hello(self, msg: str):
        return RPCApi.Result(True, result=msg).to_dict()

    def compile_cell(self, src_txt: str) -> dict:
        return RPCApi.Result(False, msg="unimplement").to_dict()

    def pci_devices(self) -> dict:
        return RPCApi.Result(False, msg="unimplement").to_dict()

    def jailhouse_enable(self, rootcell: bytes) -> dict:
        return RPCApi.Result(False, msg="unimplement").to_dict()

    def jailhouse_disable(self) -> dict:
        return RPCApi.Result(False, msg="unimplement").to_dict()

    def list_cell(self) -> dict:
        return RPCApi.Result(False, msg="unimplement").to_dict()

    def create_cell(self, cell: bytes) -> dict:
        return RPCApi.Result(False, msg="unimplement").to_dict()

    def destroy_cell(self, name: str) -> dict:
        return RPCApi.Result(False, msg="unimplement").to_dict()

    def load_cell(self, name, addr, data) -> dict:
        return RPCApi.Result(False, msg="unimplement").to_dict()

    def start_cell(self, name) -> dict:
        return RPCApi.Result(False, msg="unimplement").to_dict()

    def stop_cell(self, name) -> dict:
        return RPCApi.Result(False, msg="unimplement").to_dict()

    def get_status(self) -> dict:
        """返回主机状态信息，包含内存、CPU 时间和 CPU 负载。

        Returns:
            dict: 使用 `RPCApi.Result` 包装的结果字典，`result` 字段包含 `rootcell` 子字典：
                  - `meminfo`: `psutil.virtual_memory()` 的 dict 表示
                  - `cputimes`: `psutil.cpu_times()` 的 dict 表示
                  - `cpuload`: `psutil.cpu_percent()` 的值
        """
        status = dict()
        rootcell = dict()
        rootcell['meminfo'] = psutil.virtual_memory()._asdict()
        rootcell['cputimes'] = psutil.cpu_times()._asdict()
        rootcell['cpuload'] = psutil.cpu_percent()

        status['rootcell'] = rootcell
        return RPCApi.Result(True, result=status).to_dict()


if __name__ == "__main__":
    s = RPCServer("tcp://0.0.0.0:4240", TestAPI())
    s.run()
