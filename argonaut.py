#!/usr/bin/env python2

import logging
import os
import re
import sys
sys.path.append('../')

from lewas.parsers import field_parser, split_parser
from lewas.types import itemgetter_float as ig_float 
from lewas.models import Instrument
from lewas.functools import compose

#see page 257 of manual
#2015 02 22 09 43 51     7.4     0.4   0.376   4.1   4.0  10.0 194 191 139   0    0.0   0.0   0.0  0.0  0.0  0.0   4.06      0.000    0.000  11.6   0.1    0.4  30  30  29

# We ignore the time for now
#    UnitParser(int, ('time','hour'), None),
#    UnitParser(int, ('time', 'month'), None),
#    UnitParser(int, ('time', 'day'), None),
#    UnitParser(int, ('time', 'hour'), None),
#    UnitParser(int, ('time', 'minute'), None),
#    UnitParser(int, ('time', 'second'), None),

# or will each one be passed a grouped item?
# parsing change
start_parsers = []
start_line = r'^[2-9][0-9]{3}\s+[0-9]{2}\s+[0-9]{2}\s+[0-9]{2}\s+[0-9]{2}\s+[0-9]{2}\s+(([0-9\.\-]+\s+){24}[0-9\.\-]+)'
start_re = re.compile(start_line)
#start_parsers.append(split_parser(start_re))
# this will match start line returning everything past the time
# then we split on whitespace
start_parsers.append(split_parser()) # default is to split on whitespace
# we now have a list of numbers

fields = [
    (ig_float(0, stderr=3), ('water', 'downstream velocity'), 'cm/s'),
    (ig_float(1, stderr=4), ('water', 'lateral velocity'), 'cm/s'),
    (ig_float(2, stderr=5), ('water', 'depth'), 'm'),
    (ig_float(6), ('beam', 'signal strength 1'), 'counts'),
    (ig_float(7), ('beam', 'signal strength 2'), 'counts'),
    (ig_float(8), ('beam', 'signal strength 3'), 'counts'),
#    (float, 'pings', 'good', None),
#    (stderr_float, 'package', 'heading', None),
#    (stderr_float, 'package', 'pitch', None),
#    (stderr_float, 'package', 'roll', None),
    (ig_float(16), ('water', 'temperature'), 'C'),
#    (stderr_float, 'water', 'pressure', None),
    (ig_float(19), ('battery', 'voltage'), 'V'),
    (ig_float(20), ('beam', 'vertical sample start'), 'm'),
    (ig_float(21), ('beam', 'vertical sample end'), 'm'),
    (ig_float(22), ('beam', 'noise level 1'), 'counts'),
    (ig_float(23), ('beam', 'noise level 2'), 'counts'),
    (ig_float(24), ('beam', 'noise level 3'), 'counts'),
]    

start_parsers.append(field_parser(fields))

# Cell parsing
# an integer, followed by 4 floating points, followed by 2 integers
cell_re = re.compile(r'^\s?([1-9][0-9]?\s+(?:-?[0-9]+(?:\.[0-9]+)?\s+){4}[1-9][0-9]{0,2}\s+[1-9][0-9]{0,2})\s*$')

# split by whitespace
cell_parsers = [ split_parser() ]

def cell_offset(idx):
    return lambda data: ('cell', data[idx])

co = cell_offset(0)

cell_fields = [
            (ig_float(1, stderr=3, offset=co), ('water', 'downstream velocity'), 'cm/s'),
            (ig_float(2, stderr=4, offset=co), ('water', 'lateral velocity'), 'cm/s'),
            (ig_float(5, offset=co), ('beam', 'signal strength 1'), 'counts'),
            (ig_float(6, offset=co), ('beam', 'signal strength 2'), 'counts')
        ]

cell_parsers.append( field_parser(cell_fields) )

# we appended parsing steps in the reverse order that compose will compose them
start_parsers.reverse()
cell_parsers.reverse()

def parser(args, **kwargs):
     return { start_re: compose(*start_parsers),
              cell_re:  compose(*cell_parsers)
            }
    
if __name__ == '__main__':
    logging.basicConfig(level=getattr(logging, os.environ.get('LOGGING_LEVEL','WARN')))

    import lewas.cli as cli
    args = cli.parse(name='argonaut')
    config = args.config 
    argonaut = Instrument(args.reader, parser=args.parser, name=args.instrument_name, site=config['site'])

    #start_line = '10.0     5.5   0.362   3.9   3.9  10.0 179 177 169   0    0.0   0.0   0.0  0.0  0.0  0.0   4.34      0.000 0.000  11.6   0.1    0.3  29  30  30'
    #m = args.parser[start_re](start_line)
    #print(m)
    #for i in range(1,5):
    #    cell_line = '{}     4.7    -2.2   4.4   4.3 179 175'.format(i)
    #    m = args.parser[cell_re](cell_line)
    #    print(m)
    
    #sys.exit(0)
    kwargs = {}
    argonaut.run(args.datastore, **kwargs)
