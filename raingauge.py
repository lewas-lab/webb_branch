import logging

from time import sleep
from random import randrange

import lewas
from lewas.models import Measurement, Instrument
from lewas.stores import RESTStore
from lewas.leapi import fields as leapiFields
import lewas.rpi as rpi

import RPi.GPIO as GPIO
from lewas.sources import GPIOEventSource

logger = logging.getLogger(__name__)

import os
__RPi__ = os.uname()[4][:3] == 'arm'

class RandomAccumulator:
	def __init__(self, start, stop):
		self._start=start
		self._stop=stop

	@property
	def count(self):
		return randrange(self._start, self._stop)

def raingauge_reader(accumulator, interval):
	while True:
		yield accumulator.count
		sleep(interval)

def parser(args):
    config = args.config
    inches_per_tip = float(config['inches_per_tip'])
    report_interval = float(config['report_interval'])
    units = config['units']
    unit_time = units.split('/')[1]
    time_scale = { 'h': 60*60, 'm': 60 }
    scale = time_scale[unit_time]/report_interval
    def parse(tips):
        logging.debug('tips: {}, inches_per_tip: {}, scale: {}'.format(tips, inches_per_tip, scale))
        m = Measurement(tips*inches_per_tip*scale, ('rain', 'intensity'), units)
        return m
    return parse

def datasource(config):
    """Raingauge data source"""

    logger.log(logging.INFO, 'creating datasource')
    
    interval = float(config['report_interval'])

    if not __RPi__:
        logger.log(logging.INFO, 'not running on a Raspberry Pi, using RandomAccumulator')
        return raingauge_reader(RandomAccumulator(0,5), interval)
    inpin = config['inpin']
    outpin = config['outpin']
    bouncetime = config.get('bouncetime', 300)

    pins = [ rpi.inpin(inpin, pull_up_down=GPIO.PUD_DOWN),
             rpi.outpin(outpin, GPIO.HIGH) ]
    source = GPIOEventSource(pins, interval=interval, direction=GPIO.RISING, bouncetime=bouncetime)
    return source 

class RainGauge(Instrument):
	__name__ = 'tipping_raingauge'
	
if __name__ == '__main__':
	config = lewas.readConfig('./config')
	raingaugeConfig = config.instruments['raingauge']
	datastore = RESTStore(config, fields=leapiFields)
	interval = float(raingaugeConfig['report_interval'])	

	tip_accumulator = RandomAccumulator(0,5)

	reader = raingauge_reader(tip_accumulator, interval)
	raingauge = RainGauge(reader, parser=parser(raingaugeConfig), site=config.site)

	raingauge.run(datastore)
