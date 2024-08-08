"""
Create test files dict in test_edge_cases.py
Run this when you know all the code is working.
"""

import os
import json
import hdfmap


DATA_LOCATION = os.path.dirname(__file__) + '/data/test_files.json'
DIR = '/dls/science/groups/das/ExampleData/hdfmap_tests/'
FILES = [
    (DIR + 'i16/1040311.nxs', 'i16 pilatus eta scan, old nexus format'),
    (DIR + 'i16/1040323.nxs', 'i16 pilatus hkl scan, new nexus format'),
    (DIR + 'i16/982681.nxs', 'i16 pil2m single point scan'),
    (DIR + 'i16/928878.nxs', 'i16 merlin 2d delta gam calibration'),
    (DIR + 'i10/i10-608314.nxs', 'i10 pimte scan'),
    (DIR + 'i10/i10-618365.nxs', 'i10 scan'),
    (DIR + 'i06/i06-1-302762.nxs', 'i06 scan'),
    (DIR + 'i21/i21-157111.nxs', 'i21 xcam single point scan'),
    (DIR + 'i21/i21-157116.nxs', 'i21 xcam multi point scan'),
    (DIR + 'i13/i13-1-368910.nxs', 'i13 Excalibur axis scan')
]


def check_nexus(filename, description):
    mymap = hdfmap.create_nexus_map(filename)
    out = {
        'filename': mymap.filename,
        'description': description,
        'len_combined': len(mymap.combined),
        'len_scannables': len(mymap.scannables),
        'scannables_length': mymap.scannables_length(),
        'scan_command': mymap.get_path('scan_command'),
        'axes': mymap.get_path('axes'),
        'signal': mymap.get_path('signal'),
        'image': mymap.get_image_path()
    }
    return out


if __name__ == '__main__':
    output = []
    for file, desc in FILES:
        print(f"\n------{file}-------")
        print(f"Description: {desc}")
        output.append(check_nexus(file, desc))

    with open(DATA_LOCATION, 'w') as f:
        json.dump(output, f)
