# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

class ScrapyAnkiCambridgeItem(scrapy.Item):
    # define the fields for your item here like: (good practice)
    front = scrapy.Field()
    zback = scrapy.Field()
    anote_id = scrapy.Field()
    # debug = scrapy.Field()
    pass