import asyncio
import time
from pyppeteer import launch
from json import dumps
import tldextract

class spider():
    def __init__(self, depth, ):
        self.depth = depth  # 爬取的深度,深度为0表示只爬取当前页
        self.crawl_list = []  # 待爬取列表
        self.crawled_list = set([])  # 已经抓取的url
        self.arrange_link_url = {}  # 获取到的url
        self.arrange_load_url = {}  # 请求资源url
        self.depth_dict = {}  # 深度字典

    async def visit_page(self, page, domain):
        '''
        访问页面并获取当前页面所有链接
        '''

        await page.goto(domain, {"waitUntil": "networkidle2"})
        #等待1s
        await page.waitFor(1000)
        # await page.waitForNavigation()

        if self.depth_dict[domain] < self.depth + 1:
            # 获取所有链接
            link_list = await page.xpath('//a')
            for link in link_list:
                url = await (await link.getProperty('href')).jsonValue()
                if url not in self.depth_dict:
                    self.add_crawurl(domain, url)

    def add_crawurl(self, link, url):
        '''
        判断链接是否抓取过和是否合法，将合法链接加入到待爬列表里
        '''

        if self.can_crawl(url):
            # 将顶级域名和子域名提取到ext、sub_ext
            domain = self.get_domain(link)
            subdomain = self.get_domain(url)

            if domain not in self.arrange_link_url:
                self.arrange_link_url[domain] = {}
            if subdomain not in self.arrange_link_url[domain]:
                self.arrange_link_url[domain][subdomain] = []

            self.crawl_list.append(url)
            self.depth_dict[url] = self.depth_dict[link] + 1
            self.arrange_link_url[domain][subdomain].append(url)
        else:
            return

    def can_crawl(self, url):
        if url is None or url == '':
            return False
        elif 'http' not in url:
            return False
        elif config['allow_domain'] in url:
            return True
        elif url in self.crawled_list:
            return False

    async def get_crawurl(self):
        index = 1
        while True:
            if (len(self.crawl_list) == 0) :
                time.sleep(5)
                index += 1
                continue
            elif index >= 3:
                print('All url have crawled')
                return None

            # 从待爬取列表中移除并获得首元素链接
            url = self.crawl_list.pop(0)
            self.crawled_list.add(url)
            return url

    def get_domain(self, url):
        ext = tldextract.extract(url)
        domain = ext.subdomain + '.' + ext.domain + '.' + ext.suffix
        return domain

    def add_loadurl(self, pagelink, url):
        domain = self.get_domain(pagelink)
        subdomain = self.get_domain(url)

        if domain not in self.arrange_load_url:
            self.arrange_load_url[domain] = {}
        if subdomain not in self.arrange_load_url[domain]:
            self.arrange_load_url[domain][subdomain] = []
        #if url.endswith('js'):

        self.arrange_load_url[domain][subdomain].append(url)

    async def inject_request(self, req):
        '''
        拦截请求，将发起请求的当前页面url和请求url记录下来
        '''

        self.add_loadurl(req.frame.url, req.url)
        await req.continue_()

    def save_tofile(self, filename):
        obj = {
            'arrange_link_url': self.arrange_link_url,
            'arrange_load_url': self.arrange_load_url,
            'dict_depth': self.depth_dict
        }
        jsoncontent = dumps(obj, indent=4, ensure_ascii=False)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(jsoncontent)

config = {
    'start_url' : 'https://www.iqiyi.com',
    'allow_domain': 'iqiyi.com',
    'depth': 5,
    'coroutines': 5
}


async def brw():
    browser = await launch({
        'headless': False,
        'args': ['--autoplay-policy=AutoplayAllowed'],
        'ignoreHTTPSErrors': True,
        'dumpio': True,

    })
    return browser

async def main():
    task = spider(config['depth'])
    task.depth_dict[config['start_url']] = 0
    browser = await brw()

    async def worker(browser, task):
        page = await browser.newPage()
        await page.setViewport(viewport={'width': 1280, 'height': 800})
        #await page.setUserAgent(random.choice(task.user_agents))
        await page.setRequestInterception(True)

        page.on('request', task.inject_request)
        # page.on('error', '''()=>{}''')
        await task.visit_page(page, config['start_url'])

        while await task.get_crawurl():
            try:
                await task.visit_page(page, await task.get_crawurl())
            except:
                print('something error')
                task.save_tofile('output.json')

    async def saver():
        while True:
            await asyncio.sleep(10)
            print('write your hell')
            task.save_tofile('output.json')

    #await asyncio.wait({asyncio.create_task(worker(browser, task))})

    task_list = [asyncio.create_task(worker(browser, task)) for _ in range(config['coroutines'])]
    #task_list = [asyncio.create_task(worker(browser, task)), asyncio.create_task(worker(browser, task))]
    task_list.append(asyncio.create_task(saver()))

    await asyncio.wait(task_list)
    #loop = asyncio.get_event_loop()
    #loop.run_until_complete(asyncio.wait(tasks))
    print("finish")

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

    #main()
