import pytest
import os
import hdfmap


DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'data')
FILE_HKL = DATA_FOLDER + "/1049598.nxs"  # hkl scan, pilatus


@pytest.fixture
def hdf_map():
    hdf_map = hdfmap.HdfMap()
    with hdfmap.load_hdf(FILE_HKL) as hdf:
        hdf_map.populate(hdf)
    hdf_map.generate_scannables(hdf_map.most_common_size())
    yield hdf_map


def test_populate(hdf_map):
    assert len(hdf_map.datasets) == 360, "Wrong number of datasets loaded"
    assert len(hdf_map.combined) == 283, "Wrong number of names in map.combined"


def test_most_common_size(hdf_map):
    assert hdf_map.most_common_size() == 101, "Most common size should be 101"


def test_scannables_length(hdf_map):
    assert hdf_map.scannables_length() == 101, "scannables length should be 101"


def test_generate_scannables(hdf_map):
    hdf_map.generate_scannables(3)
    assert hdf_map.scannables_length() == 3, "Scannable size should be 3"


def test_get_item(hdf_map):
    assert hdf_map['sum'] == '/entry1/pil3_100k/sum', '__get_item__ failed'
    assert 'sum' in hdf_map, '__contains__ failed'
    assert len([address for address in hdf_map]) == 283, '__iter__ failed'


def test_get_address(hdf_map):
    assert hdf_map.get_address('/entry1/measurement/sum') == '/entry1/measurement/sum', 'address is wrong'
    assert hdf_map.get_address('sum') == '/entry1/pil3_100k/sum', 'name is wrong'
    assert hdf_map.get_address('NXdata') == '/entry1/measurement', 'class is wrong'


def test_get_group_address(hdf_map):
    assert hdf_map.get_group_address('sum') == '/entry1/pil3_100k'


def test_find(hdf_map):
    assert len(hdf_map.find('eta')) == 10, "Can't find eta in names"
    assert len(hdf_map.find('eta', False)) == 11, "Can't find eta anywhere"


def test_find_attr(hdf_map):
    assert len(hdf_map.find_attr('signal')) == 4, "Wrong number of 'signal' attributes found"

def test_get_image_address(hdf_map):
    assert hdf_map.get_image_address() == '/entry1/pil3_100k/data'

def test_get_group_datasets(hdf_map):
    assert len(hdf_map.get_group_datasets('NXdata')) == 29


"--------------------------------------------------------"
"---------------------- FILE READERS --------------------"
"--------------------------------------------------------"

def test_get_data(hdf_map):
    with hdfmap.load_hdf(FILE_HKL) as hdf:
        en = hdf['/entry1/before_scan/mono/en'][()]
        h = hdf['/entry1/measurement/h'][()]
        cmd = hdf['/entry1/scan_command'][()]
        assert hdf_map.get_data(hdf, 'en') == en, "'en' produces wrong result"
        assert (hdf_map.get_data(hdf, 'h') == h).all(), "'h' produces wrong result"
        assert hdf_map.get_data(hdf, 'scan_command') == cmd, "'cmd' produces wrong result"


def test_get_image(hdf_map):
    with hdfmap.load_hdf(FILE_HKL) as hdf:
        assert hdf_map.get_image(hdf, None).shape == (195, 487)


def test_get_data_object(hdf_map):
    with hdfmap.load_hdf(FILE_HKL) as hdf:
        d = hdf_map.get_data_block(hdf)
    assert d.metadata.filepath == FILE_HKL, "Filename not included in data object metadata"
    assert int(100*d.metadata.en) == 358, "metadata energy is wrong"
    assert d.h.shape == (101, ), "scannable h is wrong shape"


def test_get_metadata(hdf_map):
    with hdfmap.load_hdf(FILE_HKL) as hdf:
        meta = hdf_map.get_metadata(hdf)
    assert len(meta) == 213, "Length of metadata wrong"
    assert meta['filename'] == '1049598.nxs', "filename is wrong"


def test_get_scannables(hdf_map):
    with hdfmap.load_hdf(FILE_HKL) as hdf:
        scannables = hdf_map.get_scannables(hdf)
    assert len(scannables) == 66, "Length of scannables is wrong"


def test_get_scannables_array(hdf_map):
    with hdfmap.load_hdf(FILE_HKL) as hdf:
        scannables = hdf_map.get_scannables_array(hdf)
        assert scannables.shape == (65, 101), "scannables array is wrong shape"


def test_get_scannables_str(hdf_map):
    with hdfmap.load_hdf(FILE_HKL) as hdf:
        scannables = hdf_map.get_scannables_str(hdf, '\t')
        assert len(scannables) == 82500, "scannables str is wrong length"


def test_eval(hdf_map):
    with hdfmap.load_hdf(FILE_HKL) as hdf:
        out = hdf_map.eval(hdf, 'int(np.max(sum / Transmission / count_time))')
        assert out == 6533183, "Expression output gives wrong result"


def test_format_hdf(hdf_map):
    with hdfmap.load_hdf(FILE_HKL) as hdf:
        out = hdf_map.format_hdf(hdf, 'The energy is {en:.3} keV')
        assert out == 'The energy is 3.58 keV', "Expression output gives wrong result"
