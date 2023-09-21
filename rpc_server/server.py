import zerorpc
from typing import Optional
from api import RPCApi
import psutil


class RPCServer(object):
    def __init__(self, addr: str, api: RPCApi):
        self._addr = addr
        self._api = api
        self._server: Optional[zerorpc.Server] = None

    def run(self) -> bool:
        if self._server is not None:
            return False
        self._server = zerorpc.Server(self._api)
        self._server.bind(self._addr)
        self._server.run()
        return True

    def stop(self):
        if self._server is None:
            return
        self._server.stop()
        self._server = None


class TestAPI(RPCApi):
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
