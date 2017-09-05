# scribserv3

Scribus remote templating server example

## Description

This small server can be started inside Scribus to serve as automation connector for templating of texts and colours.

Upon command, service will effectively look all text fields that contain code like {{TEXT}} and all colors with codes such as {{COLOUR}} and consequently replace them with values provided via simple TCP connection.

## Starting

Is best started with xvfb-run under Linux. 

```bash
xvfb-run -n 2 scribus-ng  -py ./scribserv3.py 22025 -- template.sla
```

## Commands

Valid commands upon connection :

* EXIT:

  exits (please note the ':' sign)

* CONVERT:location:PARAMS

  process the currently open template. for example :

```raw
CONVERT:DBG-color.pdf:%7B%22NAME%22%3A%20%22THE%20FUCKMAN%22%2C%22BABA%22%3A%20%22cmyk%28100%2C%2020%2C%2050%2C%2010%29%22%7D
```

* EXPORT:location

  repeat export
  
* OPEN:location

  close the current, and open new file

## Generating serialized and url-encoded JSON 

You can easily generate template param strings for testing purposes with the following snippet:

```python
import urllib
code = 'CONVERT'
arg = '{"NAME": "THE DUCKMAN", "COLOR": "cmyk(100, 20, 50, 10)"}'
print urllib.quote(arg)
```

## Configration

The config params are at the top. Defaults are:

```python
CONNECTION_TIMEOUT = 60
INACTIVE_TIMEOUT = 120
DEFAULT_PORT = 22022
LOGFILE = 'scribserv.log'
```

## Debugging

The service was developed in VSCode and can be debugged standalone. In case the ```import scribus``` expression fails, all calls divert to a 'mock' version of the object.

The service can also be debugged with winpdbg (<http://winpdb.org>) by uncommenting the lines:

```python
# import rpdb2;
# rpdb2.start_embedded_debugger('slivi4smet')
```

## reg. Scribus APIs

* This uses the old Scribus v1 API.
* Code was tested to be running with Scribus 1.5.3 on Windows 10, Mint 18, and OS/X 10.6
* A missing ```replaceText()``` API was added to workaround loss of styles with ```setText()```

## TODO

* implement the OPEN command without closing the running instance
* maybe strip the network handler class off static methods and make them procedures
