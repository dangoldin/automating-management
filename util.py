#! /usr/bin/env python

import os
import logging

FORMAT = "%(asctime)-15s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
logger = logging.getLogger("util")

# Iterate through key/vals in dictionary and print
def print_dict(d, delim="\t"):
    final_str = ""
    for key, val in d.items():
        final_str += delim + " " + str(key) + " " + str(val)
    return final_str


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


# Read from either a config map or environment variable
def get_conf_or_env(key, config_map, default_val=None):
    return os.environ.get(key, config_map.get(key, default_val))


# Read config file
def read_config_file(filepath):
    out = {}
    if os.path.exists(filepath):
        logger.info("Found config file at " + filepath)
        with open(filepath, "r") as f:
            data = f.read()
            for line in data.split("\n"):
                if "=" in line:
                    key, val = line.split("=")
                    out[key] = val
    else:
        logger.warn("Unable to find config file at " + filepath)
    return out
