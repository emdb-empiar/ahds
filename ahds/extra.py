import sys

if sys.version_info[0] > 2:
    from collections import UserList
else:
    from UserList import UserList

import numpy as np
from skimage.measure._find_contours import find_contours

# to use relative syntax make sure you have the package installed in a virtualenv in develop mode e.g. use
# pip install -e /path/to/folder/with/setup.py
# or
# python setup.py develop

# definition of numpy data types with dedicated endianess and number of bits
# they are used by the below lookup table
from .core import (
    _dict_iter_items, _dict_iter_values, xrange
)


class Image(object):
    """Encapsulates individual images"""
    def __init__(self, z, array):
        self.z = z
        self._array = array
        self._byte_values = np.unique(self._array)

    def __getattribute__(self, attr):
        if attr in ("array", "byte_values"):
            return super(Image, self).__getattribute__("_" + attr)
        if attr in ("as_contours", "as_segments"):
            return super(Image, self).__getattribute__("_" + attr)()
        return super(Image, self).__getattribute__(attr)

    def equalise(self):
        """Increase the dynamic range of the image"""
        multiplier = 255 // len(self._byte_values)
        return self._array * multiplier

    def _as_contours(self):
        """A dictionary of lists of contours keyed by byte_value"""
        contours = dict()
        _maskbase = np.array([False, True])
        _indexbase = np.zeros(self._array.shape, dtype=np.int8)
        for byte_value in self._byte_values[self._byte_values != 0]:
            mask = _maskbase[np.equal(self._array, byte_value, out=_indexbase)]
            found_contours = find_contours(mask, 254, fully_connected='high')  # a list of array
            contours[byte_value] = ContourSet(found_contours)
        return contours

    def _as_segments(self):
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

            for contour_set in _dict_iter_values(self.as_contours):
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
    """Encapsulation for set of ``Image`` objects"""

    def __getitem__(self, index):
        return Image(index, self.data[index])

    def __getattribute__(self, attr):
        if attr in ("segments",):
            return super(ImageSet, self).__getattribute__("_" + attr)()
        return super(ImageSet, self).__getattribute__(attr)

    def _segments(self):
        """A dictionary of lists of contours keyed by z-index"""
        segments = dict()
        for i in xrange(len(self)):
            image = self[i]
            for z, contour in _dict_iter_items(image.as_segments):
                for byte_value, contour_set in _dict_iter_items(contour):
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
    """Encapsulation for a set of ``Contour`` objects"""

    def __getitem__(self, index):
        return Contour(index, self.data[index])

    def __repr__(self):
        string = "{} with {} contours".format(self.__class__, len(self))
        return string


class Contour(object):
    """Encapsulates the array representing a contour"""

    def __init__(self, z, array):
        self.z = z
        self.__array = array

    def __len__(self):
        return len(self.__array)

    def __iter__(self):
        return iter(self.__array)

    @staticmethod
    def string_repr(self):
        string = "<Contour at z={} with {} points>".format(self.z, len(self))
        return string

    def __repr__(self):
        return self.string_repr(self)

    def __str__(self):
        return self.string_repr(self)
