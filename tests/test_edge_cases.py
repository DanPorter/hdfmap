import os
import json
import hdfmap


# Edge case files, create this list from create_test_files.py
TEST_FILES = os.path.join(os.path.dirname(__file__), 'data', 'test_files.json')
with open(TEST_FILES, 'r') as f:
    CHECK_FILES = json.load(f)


def test_edge_cases():
    n = 0
    for chk in CHECK_FILES:
        assert os.path.isfile(chk['filename']) == True, f"{chk['filename']} doesn't exist"
        mymap = hdfmap.create_nexus_map(chk['filename'])
        assert isinstance(mymap, hdfmap.NexusMap), f"{chk['filename']} is not NexusMap"
        assert len(mymap.combined) == chk['len_combined'], "{chk['filename']} has wrong size of combined"
        assert len(mymap.scannables) == chk['len_scannables'], f"{chk['filename']} has wrong size of scannables"
        assert mymap.scannables_length() == chk['scannables_length'], f"{chk['filename']} has wrong scannables_length"
        assert mymap.get_address('scan_command') == chk['scan_command'], f"{chk['filename']} has wrong scan_command"
        assert mymap.get_address('axes') == chk['axes'], f"{chk['filename']} has wrong axes"
        assert mymap.get_address('signal') == chk['signal'], f"{chk['filename']} has wrong signal"
        assert mymap.get_image_address() == chk['image'], f"{chk['filename']} has wrong image address"
        n += 1
    print(f"Completed {n} edge case files")
