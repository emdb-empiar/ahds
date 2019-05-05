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
if 'Nodes' in ah and 'Data' in ah.Nodes:
    print(ah.Nodes.Data)
    print(ah.Nodes.Data.encoded_data[:2])
    loaded = True
if 'Tetrahedra' in ah:
    if 'Nodes' in ah.Tetrahedra:
        print(ah.Tetrahedra.Nodes)
        print(ah.Tetrahedra.Nodes.encoded_data[:2])
        loaded = True
    if 'Materials' in ah.Tetrahedra:
        print(ah.Tetrahedra.Materials)
        print(ah.Tetrahedra.Materials.encoded_data[:2])
        loaded = True
if 'Nodes' in ah and 'Coordinates' in ah.Nodes:
    print(ah.Nodes.Coordinates)
    print(ah.Nodes.Coordinates.encoded_data[:2])
    loaded = True
if 'Edges' in ah and 'fromTo' in ah.Edges:
    print(ah.Edges.fromTo)
    print(ah.Edges.fromTo.encoded_data[:2])
    loaded = True
if "Vertices" in ah:
    print(ah.Vertices.Coordinates)
    print(ah.Vertices.Coordinates.encoded_data[:2])
    loaded = True
if "Surface1" in ah:
    print(ah.Surface1.Patches)
    print(ah.Surface1.Patches.stream_data[:2])
    loaded = True
if "Patch1" in ah:
    print(ah.Patch1.Triangles)
    print(ah.Patch1.Triangles.encoded_data[:2])
    loaded = True
if 'BoundaryCurve1' in ah:
    print(ah.BoundaryCurve1.Vertices)
    print(ah.BoundaryCurve1.Vertices.encoded_data)
    loaded = True
if loaded:
    print("="*20 + " CHANGED Header " + "="*20)
    print(ah)

#am = ahds.AmiraFile(file_name)
#am.read()
#dt = am.data_streams[1].decoded_data
c=1
