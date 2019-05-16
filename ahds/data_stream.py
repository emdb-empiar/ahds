# -*- coding: utf-8 -*-
"""
data_stream

The following image shows the class hierarchy for data streams.

.. image:: ../docs/ahds_classes.png

"""

import re
import struct
from UserList import UserList

import numpy
from skimage.measure._find_contours import find_contours

from ahds import header

# type of data to find in the stream
FIND = {
    'decimal': '\d',  # [0-9]
    'alphanum_': '\w',  # [a-aA-Z0-9_]
}

try:
    from ahds.decoders import byterle_decoder
except ImportError:
    def byterle_decoder(data, output_size):
        """Python drop-in replacement for compiled equivalent
        
        :param int output_size: the number of items when ``data`` is uncompressed
        :param str data: a raw stream of data to be unpacked
        :return numpy.array output: an array of ``numpy.uint8``
        """
        from warnings import warn

        warn("using pure-Python (instead of Python C-extension) implementation of byterle_decoder")

        input_data = struct.unpack('<{}B'.format(len(data)), data)
        output = numpy.zeros(output_size, dtype=numpy.uint8)
        i = 0
        count = True
        repeat = False
        no = None
        j = 0
        while i < len(input_data):
            if count:
                no = input_data[i]
                if no > 127:
                    no &= 0x7f  # 2's complement
                    count = False
                    repeat = True
                    i += 1
                    continue
                else:
                    i += 1
                    count = False
                    repeat = False
                    continue
            elif not count:
                if repeat:
                    value = input_data[i:i + no]
                    repeat = False
                    count = True
                    output[j:j + no] = numpy.array(value)
                    i += no
                    j += no
                    continue
                elif not repeat:
                    value = input_data[i]
                    output[j:j + no] = value
                    i += 1
                    j += no
                    count = True
                    repeat = False
                    continue

        assert j == output_size

        return output


def hxbyterle_decode(output_size, data):
    """Decode HxRLE data stream
    
    If C-extension is not compiled it will use a (slower) Python equivalent
    
    :param int output_size: the number of items when ``data`` is uncompressed
    :param str data: a raw stream of data to be unpacked
    :return numpy.array output: an array of ``numpy.uint8``
    """
    output = byterle_decoder(data, output_size)
    assert len(output) == output_size
    return output


def hxzip_decode(data_size, data):
    """Decode HxZip data stream
    
    :param int data_size: the number of items when ``data`` is uncompressed
    :param str data: a raw stream of data to be unpacked
    :return numpy.array output: an array of ``numpy.uint8``
    """
    import zlib
    data_stream = zlib.decompress(data)
    output = numpy.array(struct.unpack('<{}B'.format(len(data_stream)), data_stream), dtype=numpy.uint8)
    assert len(output) == data_size
    return output


def unpack_binary(data_pointer, definitions, data):
    """Unpack binary data using ``struct.unpack``
    
    :param data_pointer: metadata for the ``data_pointer`` attribute for this data stream
    :type data_pointer: :py:class:`ahds.header.Block`
    :param definitions: definitions specified in the header
    :type definitions: :py:class:`ahds.header.Block`
    :param bytes data: raw binary data to be unpacked
    :return tuple output: unpacked data 
    """

    if data_pointer.data_dimension:
        data_dimension = data_pointer.data_dimension
    else:
        data_dimension = 1  # if data_dimension is None

    if data_pointer.data_type == "float":
        data_type = "f" * data_dimension
    elif data_pointer.data_type == "int":
        data_type = "i" * data_dimension  # assume signed int
    elif data_pointer.data_type == "byte":
        data_type = "b" * data_dimension  # assume signed char

    # get this streams size from the definitions
    try:
        data_length = int(getattr(definitions, data_pointer.data_name))
    except AttributeError:
        # quickfix
        """
        :TODO: nNodes definition fix
        """
        try:
            data_length = int(getattr(definitions, 'Nodes'))
        except AttributeError:
            x, y, z = definitions.Lattice
            data_length = x * y * z

    output = numpy.array(struct.unpack('<' + '{}'.format(data_type) * data_length, data))  # assume little-endian
    output = output.reshape(data_length, data_dimension)
    return output


def unpack_ascii(data):
    """Unpack ASCII data using string methods``
    
    :param data_pointer: metadata for the ``data_pointer`` attribute for this data stream
    :type data_pointer: :py:class:`ahds.header.Block`
    :param definitions: definitions specified in the header
    :type definitions: :py:class:`ahds.header.Block`
    :param bytes data: raw binary data to be unpacked
    :return list output: unpacked data 
    """
    # string: split at newlines -> exclude last list item -> strip space from each 
    numstrings = map(lambda s: s.strip(), data.split('\n')[:-1])
    print numstrings
    # check if string is digit (integer); otherwise float
    if len(numstrings) == len(filter(lambda n: n.isdigit(), numstrings)):
        output = map(int, numstrings)
    else:
        output = map(float, numstrings)
    return output


class Image(object):
    """Encapsulates individual images"""

    def __init__(self, z, array):
        self.z = z
        self._array = array
        self._byte_values = set(self._array.flatten().tolist())

    @property
    def byte_values(self):
        return self._byte_values

    @property
    def array(self):
        """Accessor to underlying array data"""
        return self._array

    def equalise(self):
        """Increase the dynamic range of the image"""
        multiplier = 255 // len(self._byte_values)
        return self._array * multiplier

    @property
    def as_contours(self):
        """A dictionary of lists of contours keyed by byte_value"""
        contours = dict()
        for byte_value in self._byte_values:
            if byte_value == 0:
                continue
            mask = (self._array == byte_value) * 255
            found_contours = find_contours(mask, 254, fully_connected='high')  # a list of array
            contours[byte_value] = ContourSet(found_contours)
        return contours

    @property
    def as_segments(self):
        return {self.z: self.as_contours}

    def show(self):
        """Display the image"""
        with_matplotlib = True
        try:
            import matplotlib.pyplot as plt
        except RuntimeError:
            import skimage.io as io
            with_matplotlib = False

        if with_matplotlib:
            equalised_img = self.equalise()

            _, ax = plt.subplots()

            ax.imshow(equalised_img, cmap='gray')

            import random

            for contour_set in self.as_contours.itervalues():
                r, g, b = random.random(), random.random(), random.random()
                [ax.plot(contour[:, 1], contour[:, 0], linewidth=2, color=(r, g, b, 1)) for contour in contour_set]

            ax.axis('image')
            ax.set_xticks([])
            ax.set_yticks([])

            plt.show()
        else:
            io.imshow(self.equalise())
            io.show()

    def __repr__(self):
        return "<Image with dimensions {}>".format(self.array.shape)

    def __str__(self):
        return "<Image with dimensions {}>".format(self.array.shape)


class ImageSet(UserList):
    """Encapsulation for set of :py:class:`ahds.data_stream.Image` objects"""

    def __getitem__(self, index):
        return Image(index, self.data[index])

    @property
    def segments(self):
        """A dictionary of lists of contours keyed by z-index"""
        segments = dict()
        for i in xrange(len(self)):
            image = self[i]
            for z, contour in image.as_segments.iteritems():
                for byte_value, contour_set in contour.iteritems():
                    if byte_value not in segments:
                        segments[byte_value] = dict()
                    if z not in segments[byte_value]:
                        segments[byte_value][z] = contour_set
                    else:
                        segments[byte_value][z] += contour_set

        return segments

    def __repr__(self):
        return "<ImageSet with {} images>".format(len(self))


class ContourSet(UserList):
    """Encapsulation for a set of :py:class:`ahds.data_stream.Contour` objects"""

    def __getitem__(self, index):
        return Contour(index, self.data[index])

    def __repr__(self):
        string = "{} with {} contours".format(self.__class__, len(self))
        return string


class Contour(object):
    """Encapsulates the array representing a contour"""

    def __init__(self, z, array):
        self.z = z
        self._array = array

    def __len__(self):
        return len(self._array)

    def __iter__(self):
        return iter(self._array)

    @staticmethod
    def string_repr(self):
        string = "<Contour at z={} with {} points>".format(self.z, len(self))
        return string

    def __repr__(self):
        return self.string_repr(self)

    def __str__(self):
        return self.string_repr(self)


class AmiraDataStream(object):
    """Base class for all Amira DataStreams"""
    match = None
    regex = None
    bytes_per_datatype = 4
    dimension = 1
    datatype = None
    find_type = FIND['decimal']

    def __init__(self, amira_header, data_pointer, stream_data):
        self._amira_header = amira_header
        self._data_pointer = data_pointer
        self._stream_data = stream_data
        self._decoded_length = 0

    @property
    def header(self):
        """An :py:class:`ahds.header.AmiraHeader` object"""
        return self._amira_header

    @property
    def data_pointer(self):
        """The data pointer for this data stream"""
        return self._data_pointer

    @property
    def stream_data(self):
        """All the raw data from the file"""
        return self._stream_data

    @property
    def encoded_data(self):
        """Encoded raw data in this stream"""
        return None

    @property
    def decoded_data(self):
        """Decoded data for this stream"""
        return None

    @property
    def decoded_length(self):
        """The length of the decoded stream data in relevant units e.g. tuples, integers (not bytes)"""
        return self._decoded_length

    @decoded_length.setter
    def decoded_length(self, value):
        self._decoded_length = value

    def __repr__(self):
        return "{} object of {:,} bytes".format(self.__class__, len(self.stream_data))


class AmiraMeshDataStream(AmiraDataStream):
    """Class encapsulating an AmiraMesh data stream"""
    last_stream = False
    match = 'stream'

    def __init__(self, *args, **kwargs):
        if self.last_stream:
            self.regex = r"\n@{}\n(?P<%s>.*)" % self.match
        else:
            self.regex = r"\n@{}\n(?P<%s>.*)\n@{}" % self.match
        super(AmiraMeshDataStream, self).__init__(*args, **kwargs)
        if hasattr(self.header.definitions, 'Lattice'):
            X, Y, Z = self.header.definitions.Lattice
            data_size = X * Y * Z
            self.decoded_length = data_size
        elif hasattr(self.header.definitions, 'Vertices'):
            self.decoded_length = None
        elif self.header.parameters.ContentType == "\"HxSpreadSheet\"":
            pass
        elif self.header.parameters.ContentType == "\"SurfaceField\",":
            pass
        else:
            raise ValueError("Unable to determine data size")

    @property
    def encoded_data(self):
        i = self.data_pointer.data_index
        m = re.search(self.regex.format(i, i + 1), self.stream_data, flags=re.S)
        return m.group(self.match)

    @property
    def decoded_data(self):
        if self.data_pointer.data_format == "HxByteRLE":
            return hxbyterle_decode(self.decoded_length, self.encoded_data)
        elif self.data_pointer.data_format == "HxZip":
            return hxzip_decode(self.decoded_length, self.encoded_data)
        elif self.header.designation.format == "ASCII":
            return unpack_ascii(self.encoded_data)
        elif self.data_pointer.data_format is None:  # try to unpack data
            return unpack_binary(self.data_pointer, self.header.definitions, self.encoded_data)
        else:
            return None

    def to_images(self):
        if hasattr(self.header.definitions, 'Lattice'):
            X, Y, Z = self.header.definitions.Lattice
        else:
            raise ValueError("Unable to determine data size")
        image_data = self.decoded_data.reshape(Z, Y, X)

        imgs = ImageSet(image_data[:])
        return imgs

    def to_volume(self):
        """Return a 3D volume of the data"""
        if hasattr(self.header.definitions, "Lattice"):
            X, Y, Z = self.header.definitions.Lattice
        else:
            raise ValueError("Unable to determine data size")

        volume = self.decoded_data.reshape(Z, Y, X)
        return volume


class AmiraHxSurfaceDataStream(AmiraDataStream):
    """Base class for all HyperSurface data streams that inherits from :py:class:`ahds.data_stream.AmiraDataStream`"""

    def __init__(self, *args, **kwargs):
        self.regex = r"%s (?P<%s>%s+)\n" % (self.match, self.match.lower(), self.find_type)
        super(AmiraHxSurfaceDataStream, self).__init__(*args, **kwargs)
        self._match = re.search(self.regex, self.stream_data)
        self._name = None
        self._count = None
        self._start_offset = None
        self._end_offset = None

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def count(self):
        return self._count

    @count.setter
    def count(self, value):
        self._count = value

    @property
    def start_offset(self):
        return self._start_offset

    @start_offset.setter
    def start_offset(self, value):
        self._start_offset = value

    @property
    def end_offset(self):
        return self._end_offset

    @end_offset.setter
    def end_offset(self, value):
        self._end_offset = value

    @property
    def match_object(self):
        return self._match

    def __str__(self):
        return """\
            \r{} object
            \r\tname:         {}
            \r\tcount:        {}
            \r\tstart_offset: {}
            \r\tend_offset:   {}
            \r\tmatch_object: {}""".format(
            self.__class__,
            self.name,
            self.count,
            self.start_offset,
            self.end_offset,
            self.match_object,
        )


class VoidDataStream(AmiraHxSurfaceDataStream):
    def __init__(self, *args, **kwargs):
        super(VoidDataStream, self).__init__(*args, **kwargs)

    @property
    def encoded_data(self):
        return []

    @property
    def decoded_data(self):
        return []


class NamedDataStream(VoidDataStream):
    find_type = FIND['alphanum_']

    def __init__(self, *args, **kwargs):
        super(NamedDataStream, self).__init__(*args, **kwargs)
        self.name = self.match_object.group(self.match.lower())


class ValuedDataStream(VoidDataStream):
    def __init__(self, *args, **kwargs):
        super(ValuedDataStream, self).__init__(*args, **kwargs)
        self.count = int(self.match_object.group(self.match.lower()))


class LoadedDataStream(AmiraHxSurfaceDataStream):
    def __init__(self, *args, **kwargs):
        super(LoadedDataStream, self).__init__(*args, **kwargs)
        self.count = int(self.match_object.group(self.match.lower()))
        self.start_offset = self.match_object.end()
        self.end_offset = max(
            [self.start_offset, self.start_offset + self.count * (self.bytes_per_datatype * self.dimension)])

    @property
    def encoded_data(self):
        return self.stream_data[self.start_offset:self.end_offset]

    @property
    def decoded_data(self):
        points = struct.unpack('>' + ((self.datatype * self.dimension) * self.count), self.encoded_data)
        x, y, z = (points[::3], points[1::3], points[2::3])
        return zip(x, y, z)


class VerticesDataStream(LoadedDataStream):
    match = "Vertices"
    datatype = 'f'
    dimension = 3


class NBranchingPointsDataStream(ValuedDataStream):
    match = "NBranchingPoints"


class NVerticesOnCurvesDataStream(ValuedDataStream):
    match = "NVerticesOnCurves"


class BoundaryCurvesDataStream(ValuedDataStream):
    match = "BoundaryCurves"


class PatchesInnerRegionDataStream(NamedDataStream):
    match = "InnerRegion"


class PatchesOuterRegionDataStream(NamedDataStream):
    match = "OuterRegion"


class PatchesBoundaryIDDataStream(ValuedDataStream):
    match = "BoundaryID"


class PatchesBranchingPointsDataStream(ValuedDataStream):
    match = "BranchingPoints"


class PatchesTrianglesDataStream(LoadedDataStream):
    match = "Triangles"
    datatype = 'i'
    dimension = 3


class PatchesDataStream(LoadedDataStream):
    match = "Patches"

    def __init__(self, *args, **kwargs):
        super(PatchesDataStream, self).__init__(*args, **kwargs)
        self._patches = dict()
        for _ in xrange(self.count):
            #  in order of appearance
            inner_region = PatchesInnerRegionDataStream(self.header, None, self.stream_data[self.start_offset:])
            outer_region = PatchesOuterRegionDataStream(self.header, None, self.stream_data[self.start_offset:])
            boundary_id = PatchesBoundaryIDDataStream(self.header, None, self.stream_data[self.start_offset:])
            branching_points = PatchesBranchingPointsDataStream(self.header, None, self.stream_data[self.start_offset:])
            triangles = PatchesTrianglesDataStream(self.header, None, self.stream_data[self.start_offset:])
            patch = {
                'InnerRegion': inner_region,
                'OuterRegion': outer_region,
                'BoundaryID': boundary_id,
                'BranchingPoints': branching_points,
                'Triangles': triangles,
            }
            if inner_region.name not in self._patches:
                self._patches[inner_region.name] = [patch]
            else:
                self._patches[inner_region.name] += [patch]
            # start searching from the end of the last search
            self.start_offset = self._patches[inner_region.name][-1]['Triangles'].end_offset
            self.end_offset = None

    def __iter__(self):
        return iter(self._patches.keys())

    def __getitem__(self, index):
        return self._patches[index]

    def __len__(self):
        return len(self._patches)

    @property
    def encoded_data(self):
        return None

    @property
    def decoded_data(self):
        return None


class DataStreams(object):
    """Class to encapsulate all the above functionality"""

    def __init__(self, fn, *args, **kwargs):
        # private attrs
        self._fn = fn  #  property
        self._amira_header = header.AmiraHeader.from_file(fn)  # property
        self._data_streams = dict()
        self._filetype = None
        self._stream_data = None
        self._data_streams = self._configure()

    def _configure(self):
        with open(self._fn, 'rb') as f:
            self._stream_data = f.read().strip('\n')
            if self._amira_header.designation.filetype == "AmiraMesh":
                self._filetype = "AmiraMesh"
                i = 0
                while i < len(self._amira_header.data_pointers.attrs) - 1:  # refactor
                    data_pointer = getattr(self._amira_header.data_pointers, 'data_pointer_{}'.format(i + 1))
                    self._data_streams[i + 1] = AmiraMeshDataStream(self._amira_header, data_pointer,
                                                                     self._stream_data)
                    i += 1
                AmiraMeshDataStream.last_stream = True
                data_pointer = getattr(self._amira_header.data_pointers, 'data_pointer_{}'.format(i + 1))
                self._data_streams[i + 1] = AmiraMeshDataStream(self._amira_header, data_pointer, self._stream_data)
                # reset AmiraMeshDataStream.last_stream
                AmiraMeshDataStream.last_stream = False
            elif self._amira_header.designation.filetype == "HyperSurface":
                self._filetype = "HyperSurface"
                if self._amira_header.designation.format == "BINARY":
                    self._data_streams['Vertices'] = VerticesDataStream(self._amira_header, None, self._stream_data)
                    self._data_streams['NBranchingPoints'] = NBranchingPointsDataStream(self._amira_header, None,
                                                                                         self._stream_data)
                    self._data_streams['NVerticesOnCurves'] = NVerticesOnCurvesDataStream(self._amira_header, None,
                                                                                           self._stream_data)
                    self._data_streams['BoundaryCurves'] = BoundaryCurvesDataStream(self._amira_header, None,
                                                                                     self._stream_data)
                    self._data_streams['Patches'] = PatchesDataStream(self._amira_header, None, self._stream_data)
                elif self._amira_header.designation.format == "ASCII":
                    self._data_streams['Vertices'] = VerticesDataStream(self._amira_header, None, self._stream_data)
                    print self._data_streams['Vertices']
        #                     f.seek(self._data_streams['Vertices'].start_offset)
        #                     print f.readline(),
        #                     print f.readline(),
        #                     print f.readline(),
        #                     print f.readline(),
        return self._data_streams

    @property
    def file(self):
        return self._fn

    @property
    def header(self):
        return self._amira_header

    @property
    def stream_data(self):
        return self._stream_data

    @property
    def filetype(self):
        return self._filetype

    def __iter__(self):
        return iter(self._data_streams.values())

    def __len__(self):
        return len(self._data_streams)

    def __getitem__(self, key):
        return self._data_streams[key]

    def __repr__(self):
        return "{} object with {} stream(s): {}".format(
            self.__class__,
            len(self),
            ", ".join(map(str, self._data_streams.keys())),
        )
