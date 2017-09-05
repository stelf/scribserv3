def exportPDF(opath='VR_EXPORT.pdf'):
    if 'PDFfile' in globals():
        pdf = PDFfile()
        pdf.compress = 0
        pdf.version = 15
        pdf.bleedr = 2
        pdf.file = opath
        pdf.embedPDF = True
        pdf.save()
    else:
        logger.warn('no PDF printing in standalone run')

exportPDF()
