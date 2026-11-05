import ctypes


class TSCClockConverter:
    def __init__(self, library_path: str):
        self.library = ctypes.CDLL(library_path)

        funcao = self.library.p4_tsc_raw_offset_ns
        funcao.argtypes = []
        funcao.restype = ctypes.c_int64

        self.offset_ns = funcao()

        if self.offset_ns == -1:
            raise RuntimeError(
                "Não foi possível medir o offset entre "
                "TSC e CLOCK_MONOTONIC_RAW."
            )

    def to_monotonic_raw_ns(self, timestamp_ns: int) -> int:
        return timestamp_ns - self.offset_ns