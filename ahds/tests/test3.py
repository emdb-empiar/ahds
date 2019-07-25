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
    if ah.Nodes.dimension > 5:
        print(ah.Nodes.Data.decoded_data[:5,:])
    else:
        print(ah.Nodes.Data.decoded_data)
    loaded = True
if 'Tetrahedra' in ah:
    if 'Nodes' in ah.Tetrahedra:
        print(ah.Tetrahedra.Nodes)
        if ah.Tetrahedra.dimension > 5:
            print(ah.Tetrahedra.Nodes.decoded_data[:5,:])
        else:
            print(ah.Tetrahedra.Nodes.decoded_data)
        loaded = True
    if 'Materials' in ah.Tetrahedra:
        print(ah.Tetrahedra.Materials)
        if ah.Tetrahedra.dimension > 5:
            print(ah.Tetrahedra.Materials.decoded_data[:5])
        else:
            print(ah.Tetrahedra.Materials.decoded_data)
        loaded = True
if 'Nodes' in ah and 'Coordinates' in ah.Nodes:
    print(ah.Nodes.Coordinates)
    if ah.Nodes.dimension > 5:
        print(ah.Nodes.Coordinates.decoded_data[:5,:])
    else:
        print(ah.Nodes.Coordinates.decoded_data)
    loaded = True
if 'Edges' in ah and 'fromTo' in ah.Edges:
    print(ah.Edges.fromTo)
    if ah.Edges.dimension > 5:
        print(ah.Edges.fromTo.decoded_data[:5,:])
    else:
        print(ah.Edges.fromTo.decoded_data)
    loaded = True
if "Vertices" in ah:
    print(ah.Vertices.Coordinates)
    decoded_data = ah.Vertices.Coordinates.decoded_data
    if ah.Vertices.dimension > 5:
        print(decoded_data[:5,:])
    else:
        print(decoded_data)
    loaded = True
if "Surface1" in ah:
    print(ah.Surface1.Patches)
    print(ah.Surface1.Patches.decoded_data[:])
    loaded = True
if "Patch1" in ah:
    print(ah.Patch1.Triangles)
    decoded_data =  ah.Patch1.Triangles.decoded_data
    if decoded_data.shape[0] > 5:
        print(ah.Patch1.Triangles.decoded_data[:5,:])
    else:
        print(ah.Patch1.Triangles.decoded_data)
    loaded = True
if 'BoundaryCurve1' in ah:
    print(ah.BoundaryCurve1.Vertices)
    print(ah.BoundaryCurve1.Vertices.decoded_data)
    loaded = True
if 'Column' in ah and 'ColumnSheet' in ah.Column:
    print(ah.Column.ColumnSheet)
    print(ah.Column.ColumnSheet.data.shape,'\n',ah.Column.ColumnSheet.data)
    loaded = True
if 'AT' in ah and 'ATSheet' in ah.AT:
    print(ah.AT.ATSheet)
    print(ah.AT.ATSheet.data.shape,'\n',ah.AT.ATSheet.data)
    loaded = True
if loaded:
    print("="*20 + " CHANGED Header " + "="*20)
    print(ah)

#am = ahds.AmiraFile(file_name)
#am.read()
#dt = am.data_streams[1].decoded_data
c=1
