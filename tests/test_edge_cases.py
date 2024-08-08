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
        assert os.path.isfile(chk['filename']) is True, f"{chk['filename']} doesn't exist"
        mymap = hdfmap.create_nexus_map(chk['filename'])
        assert isinstance(mymap, hdfmap.NexusMap), f"{chk['filename']} is not NexusMap"
        assert len(mymap.combined) == chk['len_combined'], "{chk['filename']} has wrong size of combined"
        assert len(mymap.scannables) == chk['len_scannables'], f"{chk['filename']} has wrong size of scannables"
        assert mymap.scannables_length() == chk['scannables_length'], f"{chk['filename']} has wrong scannables_length"
        assert mymap.get_path('scan_command') == chk['scan_command'], f"{chk['filename']} has wrong scan_command"
        assert mymap.get_path('axes') == chk['axes'], f"{chk['filename']} has wrong axes"
        assert mymap.get_path('signal') == chk['signal'], f"{chk['filename']} has wrong signal"
        assert mymap.get_image_path() == chk['image'], f"{chk['filename']} has wrong image path"
        n += 1
    print(f"Completed {n} edge case files")


def test_old_i16_file():
    filename = '/dls/science/groups/das/ExampleData/hdfmap_tests/i16/1040311.nxs'
    mymap = hdfmap.create_nexus_map(filename)
    with hdfmap.load_hdf(filename) as hdf:
        value, address = mymap.eval(hdf, 'np.sum(sum), _sum')
    assert abs(value + 407) < 0.01, 'expression "np.sum(sum)" gives wrong result'
    assert address == '/entry1/measurement/sum', 'expression "_sum" returns wrong address'


def test_new_i16_file():
    filename = '/dls/science/groups/das/ExampleData/hdfmap_tests/i16/1040323.nxs'
    mymap = hdfmap.create_nexus_map(filename)
    with hdfmap.load_hdf(filename) as hdf:
        h, k, l, hkl, _h, fname = mymap.eval(hdf, 'h, k, l, hkl, _h, filename')
    assert h.shape == (21,), 'expression "h" has wrong shape'
    assert hkl == '--', 'default for expression "hkl" is incorrect'
    assert fname == '1040323.nxs'


