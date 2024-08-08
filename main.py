"""
Test hdfmap
"""

import hdfmap


nxs_file = 'tests/data/1049598.nxs'
new_file = 'tests/data/1040323.nxs'

format_string = '#{entry_identifier}: {start_time} : E={incident_energy:.3f} keV : {scan_command}'
#hdf = hdfmap.load_hdf(nxs_file)
#nxs_map = hdfmap.create_nexus_map(nxs_file)
#print(nxs_map.format_hdf(hdf, format_string))

THOUSAND_FILES = '/dls/science/groups/das/ExampleData/hdfmap_tests/i16/cm37262-1'
files = hdfmap.list_files(THOUSAND_FILES)
strings = hdfmap.hdf_format(files, format_string)

"""
new_map = hdfmap.create_nexus_map(new_file)
nxs_map = hdfmap.create_nexus_map(nxs_file, groups=['instrument', 'sample'])
print(nxs_map)
print(nxs_map.info_scannables())

rdr = hdfmap.HdfReloader(nxs_file, nxs_map)
[data1, data2] = rdr.get_data(['scan_command', 'start_time'])
print(data1, data2)
print(rdr.eval('h[len(h)//2]'))
print(rdr.format('The energy is {en} keV'))

print(f"\n\nFile: {nxs_file}\nScannables:")
with hdfmap.load_hdf(nxs_file) as nxs:
    print(nxs_map.get_scannables_str(nxs))

print(f"\n\nCreate DataObject: {nxs_file}")
with hdfmap.load_hdf(nxs_file) as nxs:
    d = nxs_map.get_data_block(nxs)
print(d.metadata.scan_command)
"""
