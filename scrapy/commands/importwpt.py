from scrapy.command import ScrapyCommand
from scrapy.utils.misc import load_object
from scrapy.conf import settings
from scrapy.exceptions import UsageError
from scrapy import log
from lxml import objectify
from lxml.etree import XMLSyntaxError
import re
import sys

XMLNS = '{http://www.omfica.org/schemas/ow/0.9}' 

template = """
from scrapy.spider import BaseSpider

class ${domain}Spider(BaseSpider):
    name = "${domain}"
    allowed_domains = ["${domain}"]
    start_urls = [${urls}]

    def parse(self, response):
        filename = response.url.split("/")[-2]
        open(filename, 'wb').write(response.body)
"""

wpt_url = "http://www.w3.org/Submission/WPT/"

log.start()

class Command(ScrapyCommand):
    """
    Do a import of a WPT file 
    """
    requires_project = True

    def syntax(self):
        return "<file.xml>"

    def short_desc(self):
        return "Create a spider based on a Website Parse Template (WPT) file"

    def add_options(self, parser):
        ScrapyCommand.add_options(self, parser)

    def run(self, args, opts):

        if len(args) != 1:
            raise UsageError()

        filename = args[0]

        try:
            template = open(filename).read()

            root = objectify.fromstring(template)
            if not self._check_if_wpt_file_has_valid_url(root):
                log.msg("ERROR: attribute 'host' of 'wpt' tag does not have a valid URL",log.ERROR)

            if not self._check_if_wpt_has_at_least_one_template_with_one_block(xml):
                log.msg("ERROR: The WPT file must have at least one template tag\
                        with one block tag. See %s for more info" % wpt_url,log.ERROR);
    
            if not self._check_if_every_template_has_at_least_one_block(xml):
                log.msg("ERROR: Every template tag must have at least one block tag",log.ERROR)
    
            if not self._check_if_every_block_has_at_least_one_html_element_reference(xml):
                log.msg("ERROR: Every block tag must have at least one \
                        specific HTML tag reference (tagid, pattern or xpath).\
                        See %s for more info" % wpt_url,log.ERROR)

            if not self._check_if_every_template_has_a_unique_name(xml):
                log.msg("ERROR: Each template's name must be unique")
            
            if not self._check_if_url_section_is_valid_if_templates_has_no_urls(xml):
                log.msg("ERROR: Every template which does not have an 'ow:url'\
                        attribute must declare it in urls section. \
                        See %s for more info" % wpt_url,log.ERROR )

        except XMLSyntaxError,e:
            log.msg("ERROR: There is a markup error in %s" %filename,log.ERROR)
        except:
            log.msg("ERROR: File not found: %s" % filename,log.ERROR)
       
    def _check_if_wpt_file_has_valid_url(self,xml):
        try:
            url = xml.attrib[XMLNS+'host']
            p = re.compile('https?://([-A-Za-z0-9+&@#/%?=~_()|!:,.;]*[-A-Za-z0-9+&@#/%=~_()|])')
            domains = p.findall(url)
            
            if not domains: 
                return False
    
     
            domain = domains[0]
     
            if domain.__contains__('/'):
                domain = domain.split('/')[0]
     
            site_name = domain.split('.')[0]
     
            if site_name == 'www':
                site_name = domain.split('.')[1]

        except:
            return False
    
        return True

    def _check_if_every_block_has_at_least_one_html_element_reference(self,xml):
        for t in xml.template:
            if not _check_if_every_block_has_at_least_one_html_element_reference(t.block):
                return False

        return True
   
    def _check_if_block_has_at_least_one_html_element_reference(self,block):
        if hasattr(block,'block'): 
            if not self._check_if_block_has_at_least_one_html_element_reference(block.block):
                return False

        for b in block:
            has_xpath = b.attrib.__contains__(XMLNS+'xpath')
            has_tagid = b.attrib.__contains__(XMLNS+'tagid')
            has_pattern = b.attrib.__contains__(XMLNS+'pattern')
            if not (has_xpath or has_tagid or has_pattern):
                return False

        return True
 
    def _check_if_every_template_has_at_least_one_block(self,xml):
        try:
            for i in range(0,xml.template.__len__()):
                if not self._template_has_block(xml,i):
                    return False
        except AttributeError:
            return False
        return True

    def _check_if_wpt_has_at_least_one_template_with_one_block(self,xml):
        return self._template_has_block(xml,0)

    def _template_has_block(self,xml,template_id):
        try:
            return hasattr(xml.template[template_id],'block')
        except AttributeError:
            return False
   
    def _check_if_every_template_has_a_unique_name(self,xml):
        template_names = []
        for t in xml.template:
            if t.attrib[XMLNS+'name'] in template_names:
                return False
            template_names.append(t.attrib[XMLNS+'name'])

        return True
    def _check_if_url_section_is_valid_if_templates_has_no_urls(self,xml):
        for t in xml.template:
            if t.attrib.__contains__(XMLNS+'url'):
                continue

            name = t.attrib[XMLNS+'name']
            urls = [u for u in xml.urls if u.attrib[XMLNS+'template']==name]

            if  len(urls)==0:
                return False

        return True

    def _get_templates_urls(self, xml):
        return [i.attrib['{http://www.omfica.org/schemas/ow/0.9}url'] for i in xml]
