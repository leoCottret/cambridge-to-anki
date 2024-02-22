from scrapy.exporters import CsvItemExporter

class CsvCustomSeperator(CsvItemExporter):
    def __init__(self, *args, **kwargs):
        kwargs['encoding'] = 'utf-8'
        # the whole point of this file, having semi colons delimiters instead of commas
        # remove one click from the user each time it imports new words
        kwargs['delimiter'] = ';' 
        super(CsvCustomSeperator, self).__init__(*args, **kwargs)