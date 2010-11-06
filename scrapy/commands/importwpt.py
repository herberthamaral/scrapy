from scrapy.command import ScrapyCommand
from scrapy.utils.misc import load_object
from scrapy.conf import settings
from scrapy.exceptions import UsageError
from scrapy import log
from lxml import objectify
from lxml.etree import XMLSyntaxError
import re
import sys
import string

XMLNS = '{http://www.omfica.org/schemas/ow/0.9}' 

spider_template = """from scrapy.spider import BaseSpider
from scrapy.contrib.loader import XPathItemLoader

class ${spider_class}(BaseSpider):
    name = ${name}
    allowed_domains = [${name}]
    start_urls = [${start_urls}]

    def parse(self, response):
        ${item_load}
"""

item_template = """
class ${item}(Item):
    ${fields}
"""

field_template="    ${field}=Field(${default})"

item_load_template = """l = XPathItemLoader(item = TemplateExampleItem1(),response=response)
        l.add_xpath('bubble','id("ex1")/text()') 
        i = l.load_item()"""


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

            self.domain = domain 

            if domain.__contains__('/'):
                domain = domain.split('/')[0]
     
            site_name = domain.split('.')[0]
     
            if site_name == 'www':
                site_name = domain.split('.')[1]

            self.site_name = site_name

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

    def generate_spider_from_wpt(self,xml):
        oxml = objectify.fromstring(xml)

        item = self.get_items_from_wpt(oxml)
        t = string.Template(spider_template)
        spider_class = oxml.template.attrib[XMLNS+'name'].replace(' ','')
        name = "'"+self.domain+"'"
        start_urls = "'"+oxml.template.attrib[XMLNS+'url']+"'"
        item_load = self.get_items_load_from_wpt(oxml) 

        py = t.substitute(spider_class=spider_class,name=name,start_urls=start_urls,item_load=item_load)
        
        py = item+"\n"+py
        return py
    
    def get_items_from_wpt(self,xml):
        items = "\nfrom scrapy.item import Item, Field\n"
        blocks = xml.template.block
        class_counter = 1
        item_class_prefix = xml.template.attrib[XMLNS+'name'].replace(' ','')

        for b in blocks:
            class_name = item_class_prefix+"Item"+str(class_counter) 
            class_counter += 1
            fields = "%s = Field()" % b.attrib['name']

            t = string.Template(item_template) 
            items += t.substitute(item=class_name,fields=fields) 
        return items

    def get_items_load_from_wpt(self,xml):
        blocks = xml.template.block
        class_counter = 1
        item_class_prefix = xml.template.attrib[XMLNS+'name'].replace(' ','')
        item_load = ""
        for b in blocks:
            class_name = item_class_prefix+"Item"+str(class_counter)
            class_counter += 1
            t = string.Template(item_load_template)

            if b.attrib.__contains__(XMLNS+'tagid'):
                xpath = 'id("%s")/text()' % b.attrib[XMLNS+'tagid']
            
            field_name = b.attrib['name']

            item_load += t.substitute(class_name=class_name,field_name=field_name,xpath=xpath)

        return item_load
