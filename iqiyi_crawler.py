#! /usr/bin/env python
# -*- coding:utf-8 -*-

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException,TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

import time
import datetime
import pandas as pd
import numpy as np
from pandas import DataFrame,Series
import tldextract

class spider():
    def __init__(self, domain, depth, brw):
        self.domain = domain            #开始爬取的域名
        self.depth = depth              #爬取的深度
        self.crawl_list = set([])       #获取到的url
        self.crawled_list = set([])     #已经爬取的url
        self.crawl_err_list = set([])   #爬取失败url
        if brw.lower() == 'chrome':
            self.browser = webdriver.Chrome()  
            
    def get_url(self):
        '''
        获取页面中所有的url,返回WebElement对象列表
        '''
        self.browser.get(self.domain)
        wait = WebDriverWait(self.browser, 10)
        try:
            #显式等待所有a标签加载出来
            wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, 'a'))) 
        except TimeoutException:
            #如果该链接超时，加入爬取失败的列表
            print('Crawl Error! Url is', self.browser.current_url, 'try again..')
            if self.browser.current_url not in self.crawl_err_list:
                self.crawl_err_list.append(self.browser.current_url)
        
        pagelinks = self.browser.find_elements_by_tag_name('a')
        return pagelink
        
    
                           
ii = spider('http://www.iqiyi.com/',1, 'chrome')
ii.get_url()
