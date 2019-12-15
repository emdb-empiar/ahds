/*
 * Amira Decoders
 *
 * author: Paul K. Korir, PhD
 * date: 2017-01-26
 * email: pkorir@ebi.ac.uk, paul.korir@gmail.com
 *
 */
#include <stdarg.h>
#include <stdint.h>
#include <string.h>
#define PY_SSIZE_T_CLEAN ssize_t// to allow PyArg_ParseTuple use s# with PY_SIZE_T for length
#include <Python.h>
#if PY_MAJOR_VERSION < 3
#include <stdio.h>
#endif



#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION // to avoid complaint
#include <numpy/arrayobject.h> // the numpy array object definitions

// typedefs
typedef unsigned long ulong;
typedef unsigned char uchar;

struct module_state {
    PyObject *error;
};

#if PY_MAJOR_VERSION >= 3
#define GETSTATE(m) ((struct module_state*)PyModule_GetState(m))

static int myextension_traverse(PyObject *m, visitproc visit, void *arg) {
    Py_VISIT(GETSTATE(m)->error);
    return 0;
}

static int myextension_clear(PyObject *m) {
    Py_CLEAR(GETSTATE(m)->error);
    return 0;
}
#else
#define GETSTATE(m) (&_state)
static struct module_state _state;
#endif

// prototypes
static PyObject *decoders_byterle_decode(PyObject *, PyObject *,PyObject*);

// methods in this module
static PyMethodDef HxMethods[] = {
	{"byterle_decoder", (PyCFunction)decoders_byterle_decode, METH_VARARGS|METH_KEYWORDS, "Decode byte RLE stream."},
	{NULL, NULL, 0, NULL}
};


#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef HxModuledef = {
	PyModuleDef_HEAD_INIT,
	"decoders",
	NULL,
	sizeof(struct module_state),
	HxMethods,
	NULL,
	myextension_traverse,
	myextension_clear,
	NULL
};

PyMODINIT_FUNC
PyInit_decoders(void) {

	PyObject *m;

	m = PyModule_Create(&HxModuledef);
	if (m == NULL) {
	    return NULL;
	}

#else

PyMODINIT_FUNC
initdecoders(void)
{
    PyObject *m;

	m = Py_InitModule("decoders", HxMethods);
	if (m == NULL) {
	    return;
	}
#endif

	struct module_state *st = GETSTATE(m);

    st->error = PyErr_NewException("myextension.Error", NULL, NULL);
    if (st->error == NULL) {
        Py_DECREF(m);
#if PY_MAJOR_VERSION >= 3
		return NULL;
#else
		return;
#endif
    }

	// for numpy
	import_array();

#if PY_MAJOR_VERSION >= 3
	return m;
#endif
}

static PyObject * stream_error(char * format,...) {
	// helper function to raise grammar.AHDSStreamError exceptoin
	// in case a corrupted input stream is encountered
	va_list args;

	PyObject * ahds_grammar = PyImport_ImportModule("ahds.grammar");

	if ( ahds_grammar == NULL ) {
		return NULL;
	} 

	PyObject * ahds_stream_error = PyObject_GetAttrString(ahds_grammar,"AHDSStreamError");
	
	if ( ahds_stream_error == NULL ) {
		Py_DECREF(ahds_grammar);
		return NULL;
	}

	va_start(args,format);

#if PY_MAJOR_VERSION >= 3
	PyErr_FormatV(ahds_stream_error,format,args);
	va_end(args);
#else
	char message_buffer[4096];

	message_buffer[4095] = '\0';
	vsnprintf(message_buffer,4096,format,args);
	va_end(args);
	message_buffer[4095] = '\0';
	PyErr_Format(ahds_stream_error,"%s",message_buffer);
#endif
	Py_DECREF(ahds_stream_error);
	Py_DECREF(ahds_grammar);
	return NULL;
}

static PyObject *
decoders_byterle_decode(PyObject *self, PyObject *args,PyObject *kwargs)
{
	// decoder function

	// array sizes are stored in ssize_t type variable to ensure to be able
	// to handle huge block data properly
	Py_ssize_t input_size = 0;
	Py_ssize_t  output_size = 0;

	// pointer to input data byte array
	uchar *input;

	// keywords recognized by this function in accordance with numpy.frombuffer
	// function these are count specifying size of output data and dtype 
	// of output which is ignored for the sake of simplicity of python code
	// which does not distinguish between  numpy.frombuffer and
	//  decoders.byterle_decoder function
	char * keywords[] = {
		"data", // the input data
		// number of bytes expected in the output
		"count", 
		// byte_rele_decode is used as dropin method for numpy.frombuffer
		// which expect dtype object along with input bytes and number of output
		// bytes specified by count parameter
		"dtype",
		NULL
	};
	PyObject * ignore_dtype = NULL;

	// Python usage: hx.byterle_decode(input, count = output_size, dtype=numpy.dtype('<u8'))
	if (!PyArg_ParseTupleAndKeywords(args,kwargs, "s#n|O",keywords, &input, &input_size, &output_size,&ignore_dtype))
		return NULL;

	// allocate buffer and assign read and write pointer
	uchar * buffer = PyMem_New(uchar, output_size); // output byte buffer
	uchar * output = buffer; // pointer indicating positon of next output byte
	uchar * buffer_end = &(buffer[output_size]); // first byte following buffer
	uchar * terminal = &(input[input_size]); // first byte following input buffer
	size_t num_char = 0;

	while ( terminal != input ) { // while we still have some input
		num_char = (size_t)input[0];
		if ( num_char & 0x80 ) {
			// MSB is set the remaining 7 Bytes contain count of follwoing not encoded
			// bytes they have to be copied as are to output
			num_char &= 0x7F;
			if ( ( buffer_end - output ) < num_char ) {
				PyMem_Del(buffer);
				return stream_error("Failed to decode stream: output buffer size (%zd bytes) exeeded",output_size);
			}
			input = &(input[1]);
			if ( ( terminal - input ) < num_char ) {
				PyMem_Del(buffer);
				return stream_error("Failed to decode stream: end of stream not expected");
			}
			memcpy(output,input,num_char);
			input = &(input[num_char]);
			output = &(output[num_char]);
			continue;
		}

		// RLE encoded block expand value provided by next byte to specified length
		if ( (buffer_end - output) < num_char ) {
			PyMem_Del(buffer);
			return stream_error("Failed to decode stream: output buffer size (%zd bytes) exeeded",output_size);
		}
		if ( terminal - input < 2 ) {
			PyMem_Del(buffer);
			return stream_error("Failed to decode stream: end of stream not expected");
		}
		memset(output,(int)(input[1]),num_char);
		input = &(input[2]);
		output = &(output[num_char]);

	}
	if ( buffer_end != output ) {
		PyMem_Del(buffer);
		return stream_error("Failed to decode stream: %zu bytes expected %zu bytes received",output_size,(size_t)(output - buffer) );
	} 

	// create a numpy array using the buffer as the data source
	npy_intp dims[1] = {(npy_intp)output_size};
	PyObject *output_array = PyArray_SimpleNewFromData(1, dims, NPY_UINT8, buffer);

	Py_INCREF(output_array); // ... because it will be managed from Python
	return output_array;
}

