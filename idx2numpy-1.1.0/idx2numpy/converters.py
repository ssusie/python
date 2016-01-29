from __future__ import absolute_import
from __future__ import with_statement

import sys
import struct
import numpy
import operator
import contextlib
from six import string_types as six_string_types
from six.moves import reduce
try:
    from StringIO import StringIO as BytesIO  # for python 2.5
except ImportError:
    from io import BytesIO

from .FormatError import FormatError


def convert_from_file(file):
    '''
    Reads the content of file in IDX format, converts it into numpy.ndarray and
    returns it.
    file is a file-like object (with read() method) or a file name.
    '''
    if isinstance(file, six_string_types):
        with open(file, 'rb') as f:
            return _internal_convert(f)
    else:
        return _internal_convert(file)


def convert_from_string(idx_string):
    '''
    Converts string which presents file in IDX format into numpy.ndarray and
    returns it.
    '''
    with contextlib.closing(BytesIO(idx_string)) as sio:
        return _internal_convert(sio)


def _internal_convert(input):
    '''
    Converts file in IDX format provided by file-like input into numpy.ndarray
    and returns it.
    '''
    '''
    Converts file in IDX format provided by file-like input into numpy.ndarray
    and returns it.
    '''

    # Possible data types.
    # Keys are IDX data type codes.
    # Values: (ndarray data type name, name for struct.unpack, size in bytes).
    DATA_TYPES = {
        0x08: ('ubyte', 'B', 1),
        0x09: ('byte', 'b', 1),
        0x0B: ('int16', 'h', 2),
        0x0C: ('int32', 'i', 4),
        0x0D: ('float', 'f', 4),
        0x0E: ('double', 'd', 8)
    }

    # Read the "magic number" - 4 bytes.
    try:
        mn = struct.unpack('>BBBB', input.read(4))
    except struct.error:
        raise FormatError(struct.error)

    # First two bytes are always zero, check it.
    if mn[0] != 0 or mn[1] != 0:
        msg = ("Incorrect first two bytes of the magic number: " +
               "0x{0:02X} 0x{1:02X}".format(mn[0], mn[1]))
        raise FormatError(msg)

    # 3rd byte is the data type code.
    dtype_code = mn[2]
    if dtype_code not in DATA_TYPES:
        msg = "Incorrect data type code: 0x{0:02X}".format(dtype_code)
        raise FormatError(msg)

    # 4th byte is the number of dimensions.
    dims = int(mn[3])

    # See possible data types description.
    dtype, dtype_s, el_size = DATA_TYPES[dtype_code]

    # 4-byte integer for length of each dimension.
    try:
        dims_sizes = struct.unpack('>'+'I'*dims, input.read(4*dims))
    except struct.error as e:
        raise FormatError('Dims sizes: {0}'.format(e))

    # Full length of data.
    full_length = reduce(operator.mul, dims_sizes, 1)

    result_array = numpy.ndarray(shape=[full_length], dtype=dtype)

    # Read data "in the line".
    unpack_str = '>' + dtype_s*full_length
    try:
        result_array[0:full_length] = struct.unpack(
            unpack_str, input.read(full_length * el_size))
    except struct.error as e:
        raise FormatError('Data: {0}'.format(e))

    # Check for superfluous data.
    if len(input.read(1)) > 0:
        raise FormatError('Superfluous data detected.')

    # Reshape data according to dimensions sizes.
    result = numpy.reshape(result_array, dims_sizes)
    return result


def convert_to_file(file, ndarr):
    '''
    Writes the contents of the numpy.ndarray ndarr to file in IDX format.
    file is a file-like object (with write() method) or a file name.
    '''
    if isinstance(file, six_string_types):
        with open(file, 'w') as fp:
            _internal_write(fp, ndarr)
    else:
        _internal_write(file, ndarr)


def convert_to_string(ndarr):
    '''
    Writes the contents of the numpy.ndarray ndarr to bytes in IDX format and
    returns it.
    '''
    with contextlib.closing(BytesIO()) as bytesio:
        _internal_write(bytesio, ndarr)
        return bytesio.getvalue()


def _internal_write(out_stream, arr):
    '''
    Writes numpy.ndarray arr to a file-like object (with write() method) in
    IDX format.
    '''
    # Possible data types.
    # Keys are ndarray data type name.
    # Values: (IDX data type code, name for struct.pack, size in bytes).
    DATA_TYPES = {
        'uint8': (0x08, 'B'),
        'int8': (0x09, 'b'),
        'int16': (0x0B, 'h'),
        'int32': (0x0C, 'i'),
        'float32': (0x0D, 'f'),
        'float64': (0x0E, 'd'),
    }

    if arr.size == 0:
        raise FormatError('Cannot encode empty array.')

    try:
        type_byte, struct_lib_type = DATA_TYPES[str(arr.dtype)]
    except KeyError:
        raise FormatError('numpy ndarray type not supported by IDX format.')

    MAX_IDX_DIMENSIONS = 255
    if arr.ndim > MAX_IDX_DIMENSIONS:
        raise FormatError('IDX format cannot encode array with dimensions > 255')

    MAX_AXIS_LENGTH = pow(2, 32) - 1
    if max(arr.shape) > MAX_AXIS_LENGTH:
        raise FormatError('IDX format cannot encode array with more than ' + 
                          str(MAX_AXIS_LENGTH) + ' elements along any axis')
    
    # Write magic number
    out_stream.write(struct.pack('BBBB', 0, 0, type_byte, arr.ndim))

    # Write array dimensions
    out_stream.write(struct.pack('>'+'I'*arr.ndim, *arr.shape))

    # Horrible hack to deal with horrible bug when using struct.pack to encode
    # unsigned ints in 2.7 and lower, see http://bugs.python.org/issue2263
    if sys.version_info < (2, 7) and str(arr.dtype) == 'uint8':
        arr_as_list = [int(i) for i in arr.reshape(-1)]
        out_stream.write(struct.pack('>'+struct_lib_type*arr.size,
                                     *arr_as_list))
    else:
        # Write array contents - note that the limit to number of arguments doesn't
        # apply to unrolled arguments
        out_stream.write(struct.pack('>'+struct_lib_type*arr.size,
                                     *arr.reshape(-1)))

