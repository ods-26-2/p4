from abc import ABC, abstractmethod

from .frame import Frame


class VideoSource(ABC):

    @abstractmethod
    def read(self) -> Frame:
        pass

    @abstractmethod
    def release(self) -> None:
        pass
