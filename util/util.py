#! /usr/bin/env python

# Iterate through key/vals in dictionary and print
def print_dict(d, delim = '\t'):
    for key, val in d.iteritems():
        print delim, key, val

# Get key from object and return 0 if missing or None
# Convert to float
def get_or_float_zero(obj, key):
    val = None
    if hasattr(obj, key):
        val = getattr(obj, key)
    # Found as None or not found at all => 0.0
    if val is None:
        return 0.0
    return float(val)
