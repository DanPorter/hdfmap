import pytest
import os
import hdfmap

DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'data')
FILE_NEW_NEXUS = DATA_FOLDER + '/1040323.nxs'  # new nexus format

hdfmap.set_logging_levels('debug')



@pytest.fixture
def hdf_map():
    hdf_map = hdfmap.NexusMap()
    with hdfmap.load_hdf(FILE_NEW_NEXUS) as hdf:
        hdf_map.populate(hdf, groups=['instrument', 'measurement'], default_entry_only=False)
    yield hdf_map


def test_populate(hdf_map):
    assert len(hdf_map.datasets) == 431, "Wrong number of datasets"
    assert len(hdf_map.combined) == 427, "Wrong number of names in map.combined"
    assert hdf_map.scannables_length() == 21, "Wrong length for scannables"
    assert hdf_map['axes'] == '/entry/measurement/h', "Wrong path for default axes"
    assert hdf_map.get_image_path() == '/entry/instrument/pil3_100k/data', "Wrong image path"
