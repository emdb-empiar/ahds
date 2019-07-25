import ahds.header as header
import sys
import os.path as path

if len(sys.argv) < 2:
    file_name = "/home/nothere/daten/projekte/NICE/studies/ImprovementTest/Brandstaetter/FEM/VentriclesAutomatonFib.am"
else:
    file_name = sys.argv[1]
if not path.isfile(file_name):
    print("\nDirectory '{}' not found!\n\n".format(file_name))
    print("Usage:\n\t{0} <directory_to_inspect>\n\n".format(path.basename(__file__)))
    sys.exit(1)
ah = header.AmiraHeader.from_file(file_name)
print(ah)
loaded = False
if 'Lattice' in ah and 'Data' in ah.Lattice:
    print(ah.Lattice.Data)
    if ah.Lattice.Data.dimension == 1:
        images = ah.Lattice.Data.to_images()
        segments = images.segments
        loaded = True
        print("#images:",len(images),"#segments:",len(segments))
if 'Patches' in ah:
    for _pid,_patch in enumerate(ah.Patches):
        if _patch is not None:
            print('Patch {}.data:'.format(_pid),_patch.Triangles.data)
if loaded:
    print("="*20 + " CHANGED Header " + "="*20)
    print(ah)

#am = ahds.AmiraFile(file_name)
#am.read()
#dt = am.data_streams[1].decoded_data
c=1
