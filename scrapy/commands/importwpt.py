from scrapy.command import ScrapyCommand
from scrapy.project import crawler
from scrapy.utils.misc import load_object
from scrapy.conf import settings
from scrapy import log

class Command(ScrapyCommand):
    """
    Do a import of a WPT file 
    """
    requires_project = True

    def short_desc(self):
        return "Start Scrapy in server mode"

    def run(self, args, opts):

        filename = args[0]
        try:
            template = open(filename,'r').read()
            log.msg("ERROR: There is a markup error in mytemplate.xml")
        except:
            log.msg("ERROR: File not found: %s" % filename,log.ERROR)




