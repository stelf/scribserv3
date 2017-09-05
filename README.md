# scribserv3
Scribus remote templating server example

This small server can be started inside Scribus as to serve as automation connector for templateing of texts and colours.

Will look all text fields that contain code like {{TEXT}} and all colors with codes such as {{COLOUR}} and replace them with values provided via simple TCP connection. 

Valid commands upon connedtion :

* EXIT:  

  exits (please note the ':' sign)

* CONVERT:location:PARAMS

  process the currently open template. for example :

```
 DBG-color.pdf:%7B%22NAME%22%3A%20%22THE%20FUCKMAN%22%2C%22BABA%22%3A%20%22cmyk%28100%2C%2020%2C%2050%2C%2010%29%22%7D
```

* EXPORT:location

  repeat export
  
* OPEN:location

  close the current, and open new file

## Trivia

This uses the old Scribus API. Was tested with scribus 1.5.3 on Windows 10, Mint 18, and OS/X 10.6

The code is pretty self-exmplanatory.
