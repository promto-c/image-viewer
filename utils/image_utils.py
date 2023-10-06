import os
import numpy as np
from numbers import Number
from functools import lru_cache
import OpenEXR
import Imath
import struct
from utils.path_utils import PathSequence

def read_exr(image_path: str) -> np.ndarray:
    """Read an EXR image from file and return it as a NumPy array.

    Args:
        image_path (str): The path to the EXR image file.

    Returns:
        np.ndarray: The image data as a NumPy array.

    """
    if not os.path.isfile(image_path):
        return None

    # Open the EXR file for reading
    exr_file = OpenEXR.InputFile(image_path)

    # Get the image header
    header = exr_file.header()

    # Get the data window (bounding box) of the image
    data_window = header['dataWindow']

    # Get the channels present in the image
    channels = header['channels']

    # Calculate the width and height of the image
    width = data_window.max.x - data_window.min.x + 1
    height = data_window.max.y - data_window.min.y + 1

    # Determine the channel keys
    channel_keys = 'RGB' if len(channels.keys()) == 3 else channels.keys()

    # Read all channels at once
    channel_data = exr_file.channels(channel_keys, Imath.PixelType(Imath.PixelType.FLOAT))

    # Using list comprehension to transform the channel data
    channel_data = [
        np.frombuffer(data, dtype=np.float32).reshape(height, width)
        for data in channel_data
    ]

    # Convert to NumPy array only if necessary
    image_data = np.array(channel_data)

    return image_data.transpose(1, 2, 0)

def read_dpx_header(file):
    headers = {}
    
    generic_file_header_format = ">I I 8s I I I I I 100s 24s 100s 200s 200s I 104s"
    headers['GenericFileHeader'] = struct.unpack(
        generic_file_header_format, file.read(768)
    )

    generic_image_header_format = ">H H I I"
    headers['GenericImageHeader'] = struct.unpack(
        generic_image_header_format, file.read(12)
    )
  
    return headers

def read_dpx(image_path: str) -> np.ndarray:
    with open(image_path, "rb") as file:

        meta = read_dpx_header(file)
        width = meta['GenericImageHeader'][2]
        height = meta['GenericImageHeader'][3]
        offset = meta['GenericFileHeader'][1]

        file.seek(offset)
        raw = np.fromfile(file, dtype=np.int32, count=width*height)

    raw = raw.reshape(height, width)

    # if meta['endianness'] == 'be':
    raw.byteswap(True)

    image = np.array([raw >> 22, raw >> 12, raw >> 2], dtype=np.uint16)
    image &= 0x3FF

    # NOTE: to uint8
    # image = (image >> 2).astype(np.uint8)

    # to float32
    image = image.astype(np.float32)
    image /= 0x3FF

    return image.transpose(1, 2, 0)

class ImageSequence:

    file_type_handlers = {
        'exr': read_exr,
        'dpx': read_dpx,
    }

    def __init__(self, input_path: str) -> None:
        self.input_path = input_path

        # Set up the initial attributes
        self._setup_attributes()

    def _setup_attributes(self):
        self.path_sequence = PathSequence(self.input_path)

    @lru_cache(maxsize=400)
    def read_image(self, file_path: str):
        file_extension = file_path.split('.')[-1].lower()
        
        # Lookup read method for given file extension
        read_method = self.file_type_handlers.get(file_extension)

        if not read_method:
            supported_types = ", ".join(self.file_type_handlers.keys())
            raise ValueError(f"Unsupported file type: {file_extension}. Supported types are: {supported_types}")

        return read_method(file_path)

    def get_image_data(self, frame: Number):
        image_path = self.get_frame_path(frame)
        return self.read_image(image_path)
    
    # From Path Sequence
    # ------------------
    def frame_range(self):
        return self.path_sequence.get_frame_range()

    def get_frame_path(self, frame: Number):
        return self.path_sequence.get_frame_path(frame)
