#include "cdt_operation_utils.h"
#include "client.h"
#include "conversions.h"
#include "exceptions.h"
#include "policy.h"
#include "conversions.h"

static as_status
get_optional_int64_t_check_none(as_error * err, const char* key,  PyObject * op_dict, int64_t* i64_valptr, bool* found);

/*
The caller of this does not own the pointer to binName, and should not free it. It is either
held by Python, or is added to the list of chars to free later.
*/

as_status
get_bin(as_error * err, PyObject * op_dict, as_vector * unicodeStrVector, char** binName)
{
        PyObject* intermediateUnicode = NULL;

        PyObject* py_bin = PyDict_GetItemString(op_dict, AS_PY_BIN_KEY);

        if (!py_bin) {
            return as_error_update(err, AEROSPIKE_ERR_PARAM, "Operation must contain a \"bin\" entry");
        }

        if (string_and_pyuni_from_pystring(py_bin, &intermediateUnicode, binName, err) != AEROSPIKE_OK) {
            return err->code;
        }

        if (intermediateUnicode) {
            /*
            If this happened, we have an  extra pyobject. For historical reasons, we are strduping it's char value,
            then decref'ing the item itself.
            and storing the char* on a list of items to delete.
            */
            char* dupStr = strdup(*binName);
            *binName = dupStr;
            as_vector_append(unicodeStrVector, dupStr);
            Py_DECREF(intermediateUnicode);
        }        
        return AEROSPIKE_OK;
}

as_status
get_asval(AerospikeClient * self, as_error * err, char* key, PyObject * op_dict, as_val** val,
             as_static_pool * static_pool, int serializer_type, bool required)
{
        *val = NULL;
        PyObject* py_val = PyDict_GetItemString(op_dict, key);
        if (!py_val) {
            if (required) {  
                return as_error_update(err, AEROSPIKE_ERR_PARAM, "Operation must contain a \"%s\" entry", key);
            }
            else {
                *val = NULL;
                return AEROSPIKE_OK;
            }
        }
        
        /* If the value isn't required, None indicates that it isn't provided */
        if (py_val == Py_None && !required) {
            *val = NULL;
            return AEROSPIKE_OK;
        }
        return pyobject_to_val(self, err, py_val, val, static_pool, serializer_type);
}

as_status
get_val_list(AerospikeClient * self, as_error * err, const char* list_key, PyObject * op_dict, as_list** list_val, as_static_pool * static_pool, int serializer_type)
{
        *list_val = NULL;
        PyObject* py_val = PyDict_GetItemString(op_dict, list_key);
        if (!py_val) {
            return as_error_update(err, AEROSPIKE_ERR_PARAM, "Operation must contain a \"values\" entry");
        }
        if (!PyList_Check(py_val)) {
            return as_error_update(err, AEROSPIKE_ERR_PARAM, "Value must be a list");
        }
        return pyobject_to_list(self, err, py_val, list_val, static_pool, serializer_type);
}

as_status
get_int64_t(as_error * err, const char* key, PyObject * op_dict, int64_t* i64_valptr)
{
        bool found = false;
        if (get_optional_int64_t(err, key, op_dict, i64_valptr, &found) != AEROSPIKE_OK) {
            return err->code;
        }
        if (!found) {
            return as_error_update(err, AEROSPIKE_ERR_PARAM, "Operation missing required entry %s", key);
        }
        return AEROSPIKE_OK;
}

as_status
get_optional_int64_t(as_error * err, const char* key,  PyObject * op_dict, int64_t* i64_valptr, bool* found)
{
        *found = false;
        PyObject* py_val = PyDict_GetItemString(op_dict, key);
        if (!py_val) {
            return AEROSPIKE_OK;
        }
        
        if (PyInt_Check(py_val)) {
            *i64_valptr = (int64_t)PyInt_AsLong(py_val);
            if (PyErr_Occurred()) {
                if(PyErr_ExceptionMatches(PyExc_OverflowError)) {
                    return as_error_update(err, AEROSPIKE_ERR_PARAM, "%s too large", key);
                }

                return as_error_update(err, AEROSPIKE_ERR_PARAM, "Failed to convert %s", key);

            }
        }
        else if (PyLong_Check(py_val)) {
            *i64_valptr = (int64_t)PyLong_AsLong(py_val);
            if (PyErr_Occurred()) {
                if(PyErr_ExceptionMatches(PyExc_OverflowError)) {
                    return as_error_update(err, AEROSPIKE_ERR_PARAM, "%s too large", key);
                }

                return as_error_update(err, AEROSPIKE_ERR_PARAM, "Failed to convert %s", key);
            }
        }
        else {
            return as_error_update(err, AEROSPIKE_ERR_PARAM, "%s must be an integer", key);
        }
    
        *found = true;
        return AEROSPIKE_OK;
}

as_status 
get_int(as_error* err, const char* key, PyObject* op_dict, int* int_pointer) {
    int64_t int64_return_type;

    if (get_int64_t(err, key, op_dict, &int64_return_type) != AEROSPIKE_OK) {
        return err->code;
    }

    *int_pointer = int64_return_type;
    return AEROSPIKE_OK;
}

as_status 
get_optional_int(as_error* err, const char* key, PyObject* op_dict, int* integer, int** int_p) {
    int64_t int64_return_type;
    bool found = false;

    if (get_optional_int64_t_check_none(err, key, op_dict, &int64_return_type, &found) != AEROSPIKE_OK) {
        *int_p = NULL;
        return err->code;
    }

    if ( ! found) {
        *int_p = NULL;
    }

    *integer = int64_return_type;
    return AEROSPIKE_OK;
}

static as_status
get_optional_int64_t_check_none(as_error * err, const char* key,  PyObject * op_dict, int64_t* i64_valptr, bool* found)
{
    *found = false;
    PyObject* py_val = PyDict_GetItemString(op_dict, key);
    if (!py_val) {
        return AEROSPIKE_OK;
    }
    
    if (PyInt_Check(py_val)) {
        *i64_valptr = (int64_t)PyInt_AsLong(py_val);
        if (PyErr_Occurred()) {
            if(PyErr_ExceptionMatches(PyExc_OverflowError)) {
                return as_error_update(err, AEROSPIKE_ERR_PARAM, "%s too large", key);
            }

            return as_error_update(err, AEROSPIKE_ERR_PARAM, "Failed to convert %s", key);

        }
    }
    else if (PyLong_Check(py_val)) {
        *i64_valptr = (int64_t)PyLong_AsLong(py_val);
        if (PyErr_Occurred()) {
            if(PyErr_ExceptionMatches(PyExc_OverflowError)) {
                return as_error_update(err, AEROSPIKE_ERR_PARAM, "%s too large", key);
            }

            return as_error_update(err, AEROSPIKE_ERR_PARAM, "Failed to convert %s", key);
        }
    }
    else if (py_val == Py_None) {
        return AEROSPIKE_OK;
    }
    else {
        return as_error_update(err, AEROSPIKE_ERR_PARAM, "%s must be an integer", key);
    }

    *found = true;
    return AEROSPIKE_OK;
}