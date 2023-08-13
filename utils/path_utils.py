import re
import glob
import os

class PathSequence:
    def __init__(self, path: str):
        self.path = path
        self.name_part, self.frame_padding, self.extension = self._extract_components()
        self.padding_length = len(self.frame_padding)

    def _extract_components(self):
        return self.path.rsplit('.', 2)
    
    def get_frame_range(self):
        # Use glob to get all matching filenames
        matching_files = sorted(glob.glob(self.path.replace("#", "*")))
        
        if not matching_files:
            return None, None
        
        # Extracting frame numbers from the first and last filenames
        first_frame = int(matching_files[0].split('.')[-2])
        last_frame = int(matching_files[-1].split('.')[-2])
        
        return first_frame, last_frame
    
    def get_frame_count_from_range(self):
        first_frame, last_frame = self.get_frame_range()
        
        if first_frame is None or last_frame is None:
            return 0
        
        return last_frame - first_frame + 1
    
    def get_frame_path(self, frame_number: int):
        return f'{self.name_part}.{frame_number:0{self.padding_length}}.{self.extension}'

    def __str__(self):
        return f"Name Part: {self.name_part}, Frame Padding: {self.frame_padding} (Length: {self.padding_length}), Extension: {self.extension}"


if __name__ == '__main__':
    path = 'example_exr_plates\C0653.####.exr'
    path_sequence = PathSequence(path)

    print(path_sequence.get_frame_range())
    print(path_sequence.padding_length)
