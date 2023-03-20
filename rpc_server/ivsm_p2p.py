import ctypes
import os

class IvsmP2P():
    so = None

    class GuestStatus(ctypes.LittleEndianStructure):
        _pack_ = 8
        _fields_ = [
            ("online", ctypes.c_int32),
            ("mem_total", ctypes.c_int64),
            ("mem_used", ctypes.c_int64),
            ("cpu_load", ctypes.c_int32)
        ]

        def to_dict(self):
            return {
                "online": self.online,
                "mem_total": self.mem_total,
                "mem_used": self.mem_used,
                "cpu_load": self.cpu_load
            }
        def __repr__(self) -> str:
            return f"online: {self.online} mem: {self.mem_used}/{self.mem_total} cpu: {self.cpu_load}"

    @classmethod
    def init(cls):
        if cls.so is None:
            self_path = os.path.realpath(__file__)
            so_path = os.path.join(os.path.dirname(self_path), 'libjhtool.so')
            print(so_path, __file__)
            cls.so = ctypes.CDLL(so_path)

            cls.so.ivsm_p2p_guestos_status.argtypes = (ctypes.c_int, ctypes.POINTER(cls.GuestStatus) )
            cls.so.ivsm_p2p_guestos_status.restype = ctypes.c_int

            cls.so.ivsm_p2p_init()

    @classmethod
    def guestos_status(cls, target):
        """
        typedef struct ivsm_p2p_guest_status{
            int32_t  online;    /* 是否在线 */
            uint64_t mem_total; /* 总内存 单位字节 */
            uint64_t mem_used;  /* 已使用内存 单位字节 */
            int32_t  cpu_load;  /* CPU负载 */
        }ivsm_p2p_guestos_status_t;
        int ivsm_p2p_guestos_status( int target, ivsm_p2p_guestos_status_t *status );
        """
        if cls.so is None:
            print("so is None")
            return None
        print("guestos status")
        cls.so.ivsm_p2p_init()

        status = cls.GuestStatus()
        a = cls.so.ivsm_p2p_guestos_status(target, status)
        return status


if __name__ == '__main__':
    print(ctypes.sizeof(IvsmP2P.GuestStatus()))
    IvsmP2P.init()
    status = IvsmP2P.guestos_status(0)
    print(status)
