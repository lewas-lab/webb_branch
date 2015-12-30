#!/usr/bin/env python2

import logging
import os
import re
import sys
sys.path.append('../')
from itertools import izip,cycle,imap,dropwhile,starmap
from lewas.parsers import split_parser
## What is clearer, a class structure

from time import strptime

from lewas.parsers import split_parser, field_parser
from lewas.models import Measurement, Instrument
from lewas.tokenizers import splitGroupTokenizer, grouper
from lewas.types import decorated_float, itemgetter_float
from lewas.functools import compose
from lewas.ittools import taken

logger = logging.getLogger(__name__)

# NOTE: fields and field order are determined by the configuration of
# the Sonde and are not necessarily constant. Eventually we should add
# a getHeaders() function that retreives and parses the column header
# from the Sonde. To do that, send three space characters, wait for
# H?:, send 'H', read two lines, those should be the headers


decorations = { '#': ('out_of_range','Data out of sensor range'),
                '?': ('service_required','User service required or data outside calibrated range but still within sensor range'),
                '*': ('not_calibrated','Parameter not calibrated'),
                '~': ('temperature_compensation_error','Temperature compensation error'),
                '@': ('compensation_error','Non temperature parameter compensation error'),
              }

def flags_from_decoration(idx):
    def inner(data):
        logger.log(logging.DEBUG, 'Getting decorations from {}[{}]'.format(data,idx))
        decs = data[idx]
        if decs:
            return [ decorations[d][0] for d in decs ]
        else:
            return None
    return inner

sonde_float = itemgetter_float

sonde_headers = { 'Time':   (lambda m: strptime(m[0], '%H%M%S'), 'time', 'HHMMSS'), 
                  'Temp':   (sonde_float, 'water','temperature'),
                  'pH':     (sonde_float, 'water','pH'), 
                  'SpCond': (sonde_float, 'water','specific conductance'), 
                  'Sal':    (sonde_float, 'water','salinity'), 
                  'ORP':    (sonde_float, 'water','Redox potential'), 
                  'TurbSC': (sonde_float, 'water','turbidity'), 
                  'LDO%':   (sonde_float, 'water', 'LDO%'),
                  'LDO':    (sonde_float, 'water', 'dissolved oxygen'),
                  'Dep100': (sonde_float, 'water', 'depth'),
                  'IBatt':  (sonde_float, 'battery', 'voltage'),
                  'EBatt':  (sonde_float, 'battery', 'voltage')
}

sonde_units = { '\xf8C': 'C',
		'\xef\xbf\xbdC': 'C',
		'Sat': '%',
		'Units': 'pH',
                'meters': 'm',
                'Volts': 'V',
                'HHMMSS': None
              }

def typef_from_header(label):
    try:
        return sonde_typef[label]
    except KeyError:
        return decorated_float

def units_from_header(label):
    try:
        return sonde_units[label]
    except KeyError:
        return label

def parser_from_header(idx, header):
    label, units = header
    idx = idx*2
    # because the data will be a list like [ value, decorations, value, decorations, ... ]
    # alternatively we could add a group parser to group (value, decorations)
    # and then a map parser with fixed indexs for value (0) and decoratons (1)
    value_getter = sonde_headers[label][0]
    try:
        value_getter = value_getter(idx, flags=flags_from_decoration(idx+1))
    except TypeError:
        pass
    return (value_getter, sonde_headers[label][1:3], units_from_header(units))

def header_from_iter(iterable):
    metrics, units = list(taken(iterable, 2))
    return izip(metrics.split(), units.split())

def header_from_stream(stream):
    stream.write('   ')
    for line in dropwhile(lambda i: not i.startswith('HM?:'), stream):
        pass
    stream.write('H\r\n')
    return header_from_iter(dropwhile(lambda i: i.strip()=='', stream))

def header_from_file(name):
    metrics, units = None, None
    with open(name, 'r') as f:
	return header_from_iter(f.readlines())


def init(args, **kwargs):
    logger.log(logging.INFO, 'sonde init')
    if hasattr(args.reader, 'write'):
        setattr(args, 'header', header_from_stream(args.reader))
    else:
        setattr(args, 'header', header_from_file('data/sonde_headers.txt'))
    return args

def parser(args, **kwargs):
    token_sep = re.compile('(?:([{}])\s*|\s+)'.format(''.join(decorations.keys())))
    parsers = [ split_parser(token_sep, compact=False) ]
    fields = list(starmap(parser_from_header, enumerate(args.header))) # starmap(fn, iterable) ~ [ fn(*args) for args in iterable ]
    parsers.append(field_parser(fields))
    parsers.append(lambda m: filter(lambda n: n.unit, m)) # get rid of mesaurements without unit set, in this case, the time field
    parsers.reverse()

    return compose(*parsers)

if __name__ == '__main__':
    logging.basicConfig(level=getattr(logging, os.environ.get('LOGGING_LEVEL','WARN')))

    import lewas.cli as cli
    args = cli.parse(name='sonde')
    config = args.config 
    import inspect
    #logger.log(logging.DEBUG, 'using parser with source: {}'.format(inspect.getsource(args.parser([]))))
    sonde = Instrument(args.reader, parser=args.parser, name=args.instrument_name, site=config['site'])
    sonde.run(args.datastore, **config)
