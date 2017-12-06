#! /usr/bin/env python

def print_dict(d):
    for key, val in d.iteritems():
        print "\t", key, val

def get_or_float_zero(obj, key):
    val = None
    if hasattr(obj, key):
        val = getattr(obj, key)
    if val is None:
        return 0.0
    return float(val)
