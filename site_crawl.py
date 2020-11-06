import asyncio
import random
from pyppeteer import launcher
from json import dumps
from pandas import Series, DataFrame

class Spider():
    def __init__(self, Config):
        self.crawl_list = []          # 待爬取列表
        self.crawled_list = set({})   # 已经抓取的url
        self.is_finished = False
        self.config = Config
        self.format_dict = {}


    async def visit_page(self, page, url):
        """
        访问页面并获取当前页面所有链接
        """

        await page.goto(url, {"waitUntil": "networkidle2"})
        print('visit page:', url)

        link_list = await page.xpath(self.config['titleXpath'])
        page_list = await page.xpath(self.config['pageXpath'])

        await self.get_data(link_list)
        if len(page_list) > self.config['num']:
            page_list = random.sample(page_list, self.config['num'])

        for page in page_list:
            page = await (await page.getProperty('href')).jsonValue()
            await self.add_crawl_url(page)


    async def get_data(self, links):
        for link in links:
            title = await (await link.getProperty('title')).jsonValue()
            src = await (await link.getProperty('href')).jsonValue()
            self.format_dict[title] = src


    async def add_crawl_url(self, url):
        """
        判断链接是否抓取过和是否合法，将合法链接加入到待爬列表里
        """

        if self.can_crawl(url):
            self.crawl_list.append(url)


    def can_crawl(self, url):
        if url is None or url == '':
            return False
        elif 'http' not in url:
            return False
        elif '.exe' in url:
            return False
        elif url in self.crawl_list:
            return False
        elif url not in self.crawled_list:
            return True


    async def get_crawl_url(self):
        timeout_num = 1
        while True:
            if (len(self.crawl_list) == 0):
                await asyncio.sleep(10)
                timeout_num += 1
                # 当列表为空时的超时次数大于20次，即200s后，就判断爬虫抓取完毕
                if timeout_num > 20:
                    self.is_finished = True
                    return None
                else:
                    print(timeout_num)
                    continue

            # 从待爬取列表中移除并获得首元素链接
            url = self.crawl_list.pop(0)
            self.crawled_list.add(url)
            return url


    def save_to_file(self, filename):
        df = DataFrame(Series(self.format_dict), columns=['链接'])
        df.index.name = '标题'
        df.to_excel(filename + '.xlsx', sheet_name='标题列表')


async def main():
    Config = {
        'start_url': 'https://movie.douban.com/top250',
        'allow_domain': 'movie.douban.com',
        'coroutines': 2,                          # 开启的协程数量
        'num': 35,                                # 每个页面抓取链接数量
        'titleXpath': '//div[@class="hd"]/a',
        'pageXpath': '//div[@class="paginator"]/a'
    }

    task = Spider(Config)
    browser = await launcher.launch({
        'dumpio': True,
        'headless': False,
        'ignoreHTTPSErrors': True,
        'executablePath': 'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
    })

    async def worker(browser, task):
        page = await browser.newPage()
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            '(KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36')

        #删除navigator.webdriver
        await page.evaluateOnNewDocument('''
            () => {
                const newProto = navigator.__proto__;
                delete newProto.webdriver;
                navigator.__proto__ = newProto;
            }
        ''')

        await task.visit_page(page, Config['start_url'])
        while not task.is_finished:
            try:
                await task.visit_page(page, await task.get_crawl_url())
            except Exception as e:
                print('something error:', e)
                task.save_to_file('output')

    async def saver():
        while not task.is_finished:
            await asyncio.sleep(20)
            task.save_to_file('output')
            print('Crawl list:', len(task.crawl_list), '\nCrawled list:', len(task.crawled_list))

    task_list = [asyncio.create_task(worker(browser, task)) for _ in range(Config['coroutines'])]
    task_list.append(asyncio.create_task(saver()))

    await asyncio.wait(task_list)
    task.save_to_file('output')
    print("finish")

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())