
import scribus

# print dir(scribus)

colorNames = scribus.getColorNames()
for name in colorNames:
    color = scribus.getColor(name)
    print "%s %s" % (name, color)
    scribus.changeColor(name, 1, 2, 4, 5)
