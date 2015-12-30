#!/usr/bin/env python2

import logging
import os
import re
import sys

from lewas.models import Instrument, Measurement
from lewas.parsers import split_parser, field_parser, ParseError
from lewas.leapi import leapiStore
from lewas.types import itemgetter_float as ig_float
from lewas.functools import compose
from lewas.ittools import compact, flatten

logger = logging.getLogger(__name__)

# weather station format is particularly annoying because the symbols -> unit
# depends on the data type, e.g. 'M' means 'mm/h' if data is Ri (rain
# intensity), but 'hits/cm2' for Hc (hail accumulation)
weather_station_metrics = { 'Pa': ( 'air', 'pressure', {'H': 'hPa', 'I': 'inHg', 'P': 'Pascal', 'B': 'Bar', 'M': 'mmHg'} ),
                            'Rc': ( 'rain', 'accumulation', {'M': 'mm', 'I': 'in'} ),
                            'Rd': ( 'rain', 'duration', 's' ),
                            'Ri': ( 'rain', 'intensity', {'M': 'mm/h', 'I': 'in/h'} ),
                            'Ta': ('air', 'temperature', {'F': 'F', 'C': 'C'}),
                            'Hc': ( 'hail', 'accumulation', {'M': 'hits/cm2', 'I': 'hits/in2'} ),
                            'Hd': ( 'hail', 'duration', 's' ),
                            'Hi': ( 'hail', 'intensity', {'M': 'hits/cm2h', 'I': 'hits/in2h'}),
                            'Sm': ('wind', 'speed', 'm/s'),
                            'Vs': ('battery', 'voltage', 'V'),
                            'Dm': ('wind', 'direction', 'degrees'),
                            'Ua': ('air', 'humidity', '%RH')
}

def metric_getter(idx):
    def inner(data):
        try:
            return tuple(weather_station_metrics[data[idx]][0:2])
        except KeyError as e:
            # raise ParseError('Unknown metric key: {}'.format(data[idx]))
            return None # because we just want to ignore metrics we don't account for 
        except IndexError as e:
            raise ParseError('Invalid index. Check that {} is a valid index and [0:2] is a valid slide into {}'.format(idx,data))
    return inner

def unit_getter(midx, idx):
    """For the data designation at midx, and unit symbol at 'idx',
    e.g. [ 'Ri', '0.05', 'I' ], set midx=0 to select 'Ri' and idx=2 to select 'I'
    """
    def inner(data):
        logger.log(logging.DEBUG, 'unit_getter({},{})({})'.format(midx,idx,data))
        try:
            unit_dict = weather_station_metrics[data[midx]][2]
        except KeyError:
            return None # ignore metrics we don't account for
        if hasattr(unit_dict, 'items'):
            # could be a dict, in which case it would have an 'items' attribute
            logger.log(logging.DEBUG, 'getting key {} in unit_dict: {}'.format(data[idx], unit_dict))
            return unit_dict[data[idx]]
        # if not, it should be a string, just return it
        return unit_dict
    return inner

def map_parser(fn):
    #parser = lambda d: map(fn, d)
    def inner(data):
        logger.log(logging.DEBUG, 'map_parser({})({})'.format(fn,data))
        result =  map(fn, data)
        logger.log(logging.DEBUG, 'result: {}'.format(result))
        return result
    return inner

# 0R5,Th=25.4242C,Vh=12.4242N,Vs=15.4242V
parse_match = re.compile(r'^0R[1-3],(.*)$')
# Th=25.4242C,Vh=12.4242N,Vs=15.4242V
parsers = [split_parser(',')]
# [ 'Th=25.4242C', 'Vh=12.4242N', 'Vs=15.4242V' ]
value_sep = re.compile(r'(?:=|([a-zA-Z/]+))') # split on a single , or = and strings of one or more letters. group the latter.
# [ '', 'Th', '', None, '25.4242', 'C', 
parsers.append(map_parser(split_parser(value_sep)))
# [ [ 'Th', '25.4242', 'C' ], [ 'Vh', '12.4242', 'N' ], [ 'Vs', '15.4242', 'V' ] ]
fields = [ (ig_float(1), metric_getter(0), unit_getter(0,2)) ]
parsers.append(map_parser(field_parser(fields, container=False)))
# [ [measurement], [measurement], [measurement] ]
parsers.append(flatten)
parsers.reverse()

def parser(args, **kwargs):
    return { parse_match: compose(*parsers) }

class WeatherStation(Instrument):
    __name__ = 'weather_station'
    ## let's just use the output of the sensor to determine metrics: one parser to rule them all.
    parsers = parser([]) 

    def start(self):
        pass
        
    ## Custom methods.  Anything beyond what is handled by the automatic API
    ## Diagnostic methods

    def check(self, metric):
        codes = { 'wind': '0WU',
          'PTH': '0TU',
          'rain': '0RU',
          'self': '0SU'
        }

        self.cmd_output(codes[metric]+'\n\r')
     
    def reset(self, code):
        codes = { 'rain': '0XZRU',
                  'intensity': '0XZRI'
              }
        output = self.cmd_output(codes[code]+'\n\r')
        

if __name__ == "__main__":
    logging.basicConfig(level=getattr(logging, os.environ.get('LOGGING_LEVEL','WARN')))

    import lewas.cli as cli
    args = cli.parse(name='weather_station')
    config = args.config 
    weather_station = Instrument(args.reader, parser=args.parser, name=args.instrument_name, site=config['site'])
    kwargs = {}
    weather_station.run(args.datastore, **kwargs)
