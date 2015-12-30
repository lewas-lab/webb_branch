# Webb Branch Instrument Configuration

This repository contains configuration information
for LEWAS instruments installed at the Webb Branch site.

After installing the lewas package, create symbolic links for
each sensor name to `/usr/local/bin/sensor-init`: 

```
$ ln -s /usr/local/bin/sensor-init /usr/local/bin/raingauge
```

and make sure there is a section for the sensor in the `config` file

```
[raingauge]
name=tipping_raingauge
inches_per_tip=0.1
report_interval=60
units=in/h
parser=raingauge.parser
```
