import pytest
import os
import hdfmap.file_functions as ff

DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'data')


@pytest.fixture
def files():
    files = ff.list_files(DATA_FOLDER)
    yield files


def test_create_hdf_map(files):
    for file in files:
        assert isinstance(ff.create_hdf_map(file), ff.HdfMap), f"{file} is not HdfMap"


def test_create_nexus_map(files):
    for file in files:
        assert isinstance(ff.create_nexus_map(file), ff.NexusMap), f"{file} is not NexusMap"


def test_hdf_data(files):
    assert len(ff.hdf_data(files, 'en')) == len(files), "shape of hdf_data output is wrong"
    assert len(ff.hdf_data(files[0], ['en', 'sum'])) == 2, "shape of hdf_data output is wrong"


def test_hdf_eval(files):
    file = files[0]
    mymap = ff.create_hdf_map(file)
    expr = "int(total[0] / Transmission)"
    with ff.load_hdf(file) as hdf:
        out = mymap.eval(hdf, expr)
    assert ff.hdf_eval(file, expr) == out, "expression output doesn't match"


def test_hdf_format(files):
    file = files[0]
    mymap = ff.create_hdf_map(file)
    expr = "energy is {en:.2f} keV"
    with ff.load_hdf(file) as hdf:
        out = mymap.format_hdf(hdf, expr)
    assert ff.hdf_format(file, expr) == out, "expression output doesn't match"


def test_hdf_image(files):
    file = files[0]
    mymap = ff.create_hdf_map(file)
    with ff.load_hdf(file) as hdf:
        image = mymap.get_image(hdf)
    assert ff.hdf_image(file).shape == image.shape, "image doesn't match"
