from unittest import TestCase
import os
import hdfmap


def check_nexus(*args, **kwargs):
    mymap = hdfmap.create_nexus_map(*args, **kwargs)
    print(f"\n{repr(mymap)}")
    print(f"  N combined: {len(mymap.combined)}")
    print(f"N scannables: {len(mymap.scannables)}")
    print(f"      length: {mymap.scannables_length()}")
    print('Addresses:')
    print(f"scan_command: {mymap.get_address('scan_command')}")
    print(f"        axes: {mymap.get_address('axes')}")
    print(f"      signal: {mymap.get_address('signal')}")
    print(f"       image: {mymap.get_image_address()}")
    print('Data:')
    with hdfmap.load_hdf(mymap.filename) as hdf:
        cmd = mymap.get_data(hdf, 'scan_command')
        axes = mymap.get_data(hdf, 'axes')
        signal = mymap.get_data(hdf, 'signal')
        image = mymap.get_image(hdf, index=0)  # index=None finds some bad files where detector only contains 1 image
        print(f"scan_command: {cmd if cmd else None}")
        print(f"        axes: {axes.shape if axes is not None else None}")
        print(f"      signal: {signal.shape if signal is not None else None}")
        print(f"       image: {image.shape if image is not None else None}")
    print("---")
    return mymap


# Test all files in this folder
FOLDERS = [
    '/scratch/grp66007/data/i16/example',
    'C:/Users/grp66007/OneDrive - Diamond Light Source Ltd/I16/Nexus_Format/example_nexus'
]


class Test(TestCase):

    def test_files_in_folders(self):
        for folder in FOLDERS:
            if os.path.isdir(folder):
                files = hdfmap.list_files(folder)  # returns empty if folder doesn't exist
                for file in files:
                    mymap = check_nexus(file)
                    self.assertIsInstance(mymap, hdfmap.NexusMap, f"{file} is not NexusMap")
            else:
                print(f"Skipping folder: {folder}")
