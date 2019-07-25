/*
 * Amira Decoders
 *
 * author: Paul K. Korir, PhD
 * date: 2017-01-26
 * email: pkorir@ebi.ac.uk, paul.korir@gmail.com
 *
 */
#define PY_SSIZE_T_CLEAN unsigned long // to allow PyArg_ParseTuple use s# with unsigned long for length
#include <Python.h>


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
static PyObject *decoders_byterle_decode(PyObject *, PyObject *);
static void get_multiple(uchar *, uchar *, ulong, ulong);
static void set_multiple_diff(uchar *, uchar *, ulong, ulong);
static void set_multiple_same(uchar *, uchar, ulong, ulong);

// methods in this module
static PyMethodDef HxMethods[] = {
	{"byterle_decoder", (PyCFunction)decoders_byterle_decode, METH_VARARGS, "Decode byte RLE stream."},
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

static PyObject *
decoders_byterle_decode(PyObject *self, PyObject *args)
{
	ulong input_size, output_size=0;
	uchar *input;

	// Python usage: hx.byterle_decode(input, output_size)
	if (!PyArg_ParseTuple(args, "s#k", &input, &input_size, &output_size))
		return NULL;

	uchar *output = PyMem_New(uchar, output_size);
	ulong i=0, j=0;
	int count=1, repeat=0; // count/repeat: true = 1; false = 0
	uchar no=0;

	// two state machine that oscillates between getting counts and getting data
	while (i < input_size) { // while we still have some input
		if (count) { // get count
			no = input[i];
			// determine if this is a repeat or a non-repeat
			if (no > 127) {
				no &= 0x7f; // 2's complement
				count = 0;
				repeat = 1;
				i++;
			}
			else {
				i++;
				count = 0;
				repeat = 0;
			}
		}
		else { // get data
			if (repeat) {
				if (no > 0) {
					uchar *value = (uchar *)malloc(no*sizeof(uchar));
					get_multiple(input, value, i, i+no);
					repeat = 0;
					count = 1;
					set_multiple_diff(output, value, j, j+no);
					free(value);
					i += no;
					j += no;
				}
			}
			else {
				uchar value;
				value = input[i];
				set_multiple_same(output, value, j, j+no);
				i++;
				j += no;
				count = 1;
				repeat = 0;
			}
		}
	}

	int nd=1;
	npy_intp dims[1] = {static_cast<npy_intp>(j)};
	// create a numpy array using the buffer as the data source
	PyObject *output_array = PyArray_SimpleNewFromData(nd, dims, NPY_UINT8, output);
	Py_INCREF(output_array); // ... because it will be managed from Python
	return output_array;
}

static void
get_multiple(uchar *input, uchar *value, ulong start_index, ulong end_index)
{
	ulong i;

	for (i=0; i < end_index - start_index; i++) {
		value[i] = input[i + start_index];
	}
}

static void
set_multiple_diff(uchar *output, uchar *value, ulong start_index, ulong end_index)
{
	ulong i;

	for (i=0; i < end_index - start_index; i++) {
		output[i + start_index] = value[i];
	}
}

static void
set_multiple_same(uchar *output, uchar value, ulong start_index, ulong end_index)
{
	ulong i;

	for (i=start_index; i < end_index; i++) {
		output[i] = value;
	}
}

