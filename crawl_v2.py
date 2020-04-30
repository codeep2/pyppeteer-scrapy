import asyncio
from pyppeteer import launcher
from json import dumps
import tldextract
import random
from datetime import datetime

class Spider():
    def __init__(self, depth, ):
        self.depth = depth  # 爬取的深度,深度为0表示只爬取当前页
        self.crawl_list = []  # 待爬取列表
        self.crawled_list = set({})  # 已经抓取的url
        self.arrange_link_url = {}  # 获取到的url
        self.arrange_load_url = {}  # 请求资源url
        self.depth_dict = {}  # 深度字典
        self.is_finished = False

    async def visit_page(self, page, domain, num):
        '''
        访问页面并获取当前页面所有链接
        '''

        await page.goto(domain, {"waitUntil": "networkidle2"})
        print('visit page:', domain)

        #访问首页时等待30秒
        if domain == config['start_url']:
            #await page.waitFor(30000)
            if self.depth_dict[domain] < self.depth + 1:
                # 获取所有链接
                link_list = await page.xpath('//a')
                for link in link_list:
                    url = await (await link.getProperty('href')).jsonValue()
                    await self.add_crawurl(domain, url)
                    #print(len(self.crawl_list))
        else:
            await page.waitFor(5000)
            if self.depth_dict[domain] < self.depth + 1:
                # 首页之外的页面只获取num数量链接

                link_list = await page.xpath('//a')
                if len(link_list) > num:
                    url_list = random.sample(link_list, num)

                    for link in url_list:
                        url = await (await link.getProperty('href')).jsonValue()
                        await self.add_crawurl(domain, url)
                else:
                    for link in link_list:
                        url = await (await link.getProperty('href')).jsonValue()
                        await self.add_crawurl(domain, url)

        # await page.waitForNavigation()

    async def add_crawurl(self, link, url):
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
            if url in self.arrange_link_url[domain][subdomain]:
                return

            self.crawl_list.append(url)
            lock = asyncio.Lock()
            if self.depth_dict[link] == config['start_url']:
                self.depth_dict[link] = 0
            else:
                async with lock:
                    self.depth_dict[url] = self.depth_dict[link] + 1

            self.arrange_link_url[domain][subdomain].append(url)
            #print('crawl_list:', len(self.crawl_list))
        else:
            return

    def can_crawl(self, url):
        if url is None or url == '':
            return False
        elif 'http' not in url:
            return False
        elif '.exe' in url:
            return False
        elif config['allow_domain'] in url:
            return True
        elif url in self.crawled_list:
            return False

    async def get_crawurl(self):
        timeout_num = 1
        while True:
            if (len(self.crawl_list) == 0):
                await asyncio.sleep(10)
                timeout_num += 1
                # 当列表为空时的超时次数大于20次，就判断爬虫抓取完毕
                if timeout_num > 20:
                    self.is_finished = True
                    return None
                else:
                    print('continue')
                    continue

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
        if url in self.arrange_load_url[domain][subdomain]:
            return
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
            #'crawl_list': self.crawled_list
            #'dict_depth': self.depth_dict
        }

        jsoncontent = dumps(obj, indent=4, ensure_ascii=False)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(jsoncontent)

config = {
    'start_url': 'http://www.idy667.com/',
    'allow_domain': 'idy667.com',
    'depth': 15,
    'coroutines': 5,
    'num': 25
}

async def main():
    task = Spider(config['depth'])
    browser = await launcher.launch({
        #'browserWSEndpoint': 'ws://127.0.0.1:51082/devtools/browser/5b932bc5-52d8-422f-81c4-c7f06a824b1c',
        'headless': False,
        'args': ['--autoplay-policy=AutoplayAllowed'],
        'ignoreHTTPSErrors': True,
        'dumpio': True,
        'executablePath': 'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
    })

    #print(browser.wsEndpoint)
    async def worker(browser, task):
        task.depth_dict[config['start_url']] = 0
        page = await browser.newPage()

        await page.setViewport(viewport={'width': 1280, 'height': 800})
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36')
        await page.setRequestInterception(True)

        page.on('request', task.inject_request)
        await task.visit_page(page, config['start_url'], config['num'])

        while not task.is_finished:
            try:
                await task.visit_page(page, await task.get_crawurl(), config['num'])

            except Exception as e:
                print('something error:', e)
                task.save_tofile('output.json')
        print('Done!!!')

    async def saver():
        while not task.is_finished:
            await asyncio.sleep(60)
            task.save_tofile('output.json')
            print('Crawl list:', len(task.crawl_list), '\nCrawled list:', len(task.crawled_list))

    task_list = [asyncio.create_task(worker(browser, task)) for _ in range(config['coroutines'])]
    #task_list = [asyncio.create_task(worker(browser, task))]
    task_list.append(asyncio.create_task(saver()))

    await asyncio.wait(task_list)

    print("finish")

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())