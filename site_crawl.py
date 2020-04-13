import asyncio
import time

import pyppeteer
from pyppeteer import launch
from lxml import etree
import tldextract

class spider():
    def __init__(self, depth, ):
        self.depth = depth  # 爬取的深度,深度为1表示只爬取当前页
        self.crawl_list = []  #待爬取列表
        self.crawled_list = set({}) # 已经抓取的url
        self.arrange_link_url = {}  # 获取到的url
        self.arrange_load_url = {}  #请求资源url
        self.depth_dict = {} #深度字典

    async def visit_page(self, page, domain):
        '''
        访问页面并获取页面所有链接
        '''

        await page.goto(domain, {"waitUntil": "networkidle2"})
        #await page.waitForNavigation()

        if self.depth_dict[domain] < self.depth + 1:
            # 获取所有链接
            link_list = await page.xpath('//a')
            for link in link_list:
                url = await (await link.getProperty('href')).jsonValue()
                if url not in self.depth_dict:
                    self.add_crawurl(domain, url)

    def add_crawurl(self, link, url):
        '''
        判断链接是否抓取过和是否合法，将合法链接加入获取到的集合里
        '''

        if url in self.crawled_list:
            return
        elif url is None or url == '':
            return
        if 'http' not in url:
            return

        # 将顶级域名提取到ext
        #ext = tldextract.extract(url)
        #domain = ext.subdomain + '.' + ext.domain + '.' + ext.suffix

        if link not in self.arrange_link_url:
            self.arrange_link_url[link] = {}
        if url not in self.arrange_link_url[link]:
            self.arrange_link_url[link][url] = []

        self.crawl_list.append(url)
        self.depth_dict[url] = self.depth_dict[link] + 1
        self.arrange_link_url[link][url].append(url)

    async def get_crawurl(self,):
        while True:
            if(len(self.crawl_list) == 0):
                time.sleep(5)
                continue

            #从待爬取列表中移除并获得首元素链接
            url = self.crawl_list.pop(0)
            print(url)
            self.crawled_list.add(url)
            return url
        return None

    def add_loadurl(self, pagelink, url):

        if pagelink not in self.arrange_load_url:
            self.arrange_load_url[pagelink] = {}
        if url not in self.arrange_load_url[pagelink]:
            self.arrange_load_url[pagelink][url] = []

        self.arrange_load_url[pagelink][url].append(url)

    async def inject_request(self, req):
        '''
        拦截请求，将发起请求的当前页面url和请求url记录下来
        '''

        self.add_loadurl(req.frame.url, req.url)
        await req.continue_()

async def main():
    domain = 'http://www.iqiyi.com'
    task = spider(1)
    task.depth_dict[domain] = 0

    browser = await launch({
        'headless': False,
        'args': ['--autoplay-policy=AutoplayAllowed'],
    })

    page = await browser.newPage()
    await page.setViewport(viewport={'width': 1280, 'height': 800})
    #await page.setUserAgent('')

    #page.on('error', '''()=>{}''')
    await page.setRequestInterception(True)
    page.on('request', task.inject_request)
    await task.visit_page(page, domain)

    while await task.get_crawurl():
        await task.visit_page(page, await task.get_crawurl())

    #print(task.arrange_load_url)
    print(task.arrange_link_url)

asyncio.get_event_loop().run_until_complete(main())


