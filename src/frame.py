from dataclasses import dataclass
import numpy as np

@dataclass
class Frame:
    image: np.ndarray
    timestamp_ns: int
    frame_id: int