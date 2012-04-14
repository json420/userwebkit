#!/usr/bin/python3

import tempfile
import cProfile

(fileno, filename) = tempfile.mkstemp()

def run():
    import userwebkit


cProfile.run('run()', filename)

import pstats
p = pstats.Stats(filename)
p.sort_stats('cumulative').print_stats(20)
