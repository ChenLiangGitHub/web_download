#!/usr/local/bin/python3
# -*-coding:UTF-8-*-
# __author__ = 'NB_Ren'

import json
import multiprocessing
import os
import sqlite3
import time
import urllib.request
import datetime

from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont


class Url(object):
    def __init__(self, url):
        self.url = url
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0'}
        self.request = urllib.request.Request(self.url, headers=self.headers)

    def get_soup(self):
        try:
            self.response = urllib.request.urlopen(self.request, timeout=20)
            html = self.response.read().decode('utf-8')
            self.soup = BeautifulSoup(html, "html.parser")
        except Exception as e:
            print(">>>> get_soup EXCEPTION >>>> " + str(e))
            return None
        else:
            self.headers = self.response.headers
            return True


class Catalog(Url):
    def __init__(self, url):
        Url.__init__(self, url)


class FreePeopleSpider(object):
    def __init__(self):
        self.database_file = "freepeople_spider.db"
        self.init_database()
        self.spider()

    def init_database(self):
        """
            初始化数据库
            :param operation:
                            keep:如果存在数据库，继续使用该数据库
                            new：删除现在的数据库，创建新的
        """
        conn = sqlite3.connect(self.database_file, check_same_thread=False)
        cur = conn.cursor()

        # 尝试创建目录表单
        cur.execute('''CREATE TABLE IF NOT EXISTS catalog
                                 (id            INTEGER PRIMARY KEY AUTOINCREMENT,
                                 catalog_url    TEXT UNIQUE,
                                 deal           INT)''')

        # 尝试创建商品表单
        cur.execute('''CREATE TABLE IF NOT EXISTS product
                            (id             INTEGER PRIMARY KEY AUTOINCREMENT,
                            product_url     TEXT UNIQUE,
                            name            TEXT,
                            deal            INT)''')

        try:
            # 尝试插入根节点
            cur.execute('INSERT INTO catalog VALUES (NULL,?,?)', (FP_SPIDER_ROOT_CHN_URL, 0))
        except Exception as e:
            print("Init database Error:" + str(e))

        # Save (commit) the changes
        conn.commit()
        conn.close()

    def get_soup(self, url):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0'}
        request = urllib.request.Request(url, headers=headers)
        try:
            response = urllib.request.urlopen(request, timeout=20)
            html = response.read().decode('utf-8')
            soup = BeautifulSoup(html, "html.parser")
        except Exception as e:
            print(">>>> get_soup EXCEPTION >>>> " + str(e))
            return None
        else:
            self.headers = self.response.headers
            return soup

    def spider(self):
        conn = sqlite3.connect(self.database_file, check_same_thread=False)
        cur = conn.cursor()
        cur.execute("SELECT id FROM catalog WHERE deal=0 ORDER BY id")
        result = cur.fetchall()


        while len(result) > 0:
            pool = multiprocessing.Pool(processes=100)
            for row in result:
                pool.apply_async(self.analyse_catalog, (row[0],))
            pool.close()
            pool.join()

            cur.execute("SELECT id FROM catalog WHERE deal=0 ORDER BY id")
            result = cur.fetchall()

        conn.close()
        print("It's over.")

    def analyse_catalog(self, catalog_id):
        DB_NAME = "freepeople_spider.db"
        FP_SPIDER_ROOT_CHN_URL = "https://www.freepeople.com/china/"
        FP_SPIDER_PRODUCT_CHN_PRE = 'https://www.freepeople.com/china/shop/'

        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        cur = conn.cursor()

        # 从数据库中，根据id查找对应的url
        # 以？这个替代符写sql语句的时候，
        # 后面括号里的数据类型必须是元组，
        # 所以只有一个元素的时候，后面要加一个逗号
        cur.execute("SELECT catalog_url FROM catalog WHERE id=?", (catalog_id,))
        catalog_url = cur.fetchone()[0]

        # 连接并请求网页
        soup= self.get_soup(catalog_url)

        if soup is not None:
            if catalog_url.find('?page=') < 0:
                # 只有是第一页的才尝试进行分页的操作
                # 找到total - page - count的值
                # 然后将page=2至total-page-count写入数据库

                total_page_count = 1
                span_page_count = soup.find('span',
                                            attrs={'class': 'total-page-count'})
                # 这里有可能找不到这个值，如果只有一页的话，页面上就不会有这个span

                if span_page_count is not None:
                    total_page_count = int(span_page_count.get_text())

                if total_page_count > 1:
                    # 理论上只要能够找到total_page_count的这个span，它的值就应该大于1
                    # 但是为了保险起见，这里加了一个判断
                    for page_num in range(total_page_count - 1):
                        catalog_url_page = catalog_url + '?page=' + str(page_num + 2)
                        print(catalog_url_page)
                        try:
                            cur.execute('INSERT INTO catalog VALUES (NULL,?,?)', (catalog_url_page, 0))
                        except Exception as e:
                            continue

            # 这里是正常的筛查目录和商品的地方
            for link in soup.find_all('a'):
                link_url = link.get('href')
                if link_url is not None:
                    # 对link进行处理，去掉后面的查询关键词；
                    query_pos = link_url.find('?')
                    if query_pos >= 0:
                        link_url = link_url[:query_pos]

                    # 如果link_url不是以'/'，统一加上，便于去重
                    if not link_url.endswith('/'):
                        link_url = link_url + '/'

                    # 这些是商品
                    if link_url.startswith(FP_SPIDER_PRODUCT_CHN_PRE):
                        try:
                            cur.execute('INSERT INTO product VALUES (NULL,?,NULL,?)', (link_url, 0))
                            print(link_url)
                            print("It's a product.")
                            print_now()
                        except Exception as e:
                            # print(">>>>>>>>>>> Insert product url EXCEPTION:  " + str(e))
                            continue
                    elif link_url.startswith(FP_SPIDER_ROOT_CHN_URL):
                        # 下面的就是目录
                        try:
                            cur.execute('INSERT INTO catalog VALUES (NULL,?,?)', (link_url, 0))
                            print(link_url)
                            print("It's a catalog.")
                            print_now()
                        except Exception as e:
                            # print(">>>>>>>>>>> Insert catalog url EXCEPTION:  " + str(e))
                            continue

        cur.execute('UPDATE catalog SET deal=1 WHERE id=?', (catalog_id,))
        conn.commit()
        conn.close()
        return


class MultiTest(object):
    def __init__(self):
        self.url = "asdfasdfasdf"

        request_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0'}

        pool = multiprocessing.Pool(processes=40)

        for row in range(100):
            pool.apply_async(self.test, (request_headers,))

        print("Mark~ Mark~ Mark~~~~~~~~~~~~~~~~~~~~~~")
        pool.close()
        pool.join()  # 调用join之前，先调用close函数，否则会出错。执行完close后不会有新的进程加入到pool,join函数等待所有子进程结束
        print("Sub-process(es) done.")

    def test(self, a):
        print_now(self.url)

    def get_test_soup(self, url):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0'}

        request = urllib.request.Request(url, headers=headers)
        print(url)
        try:
            response = urllib.request.urlopen(request)
            html = response.read().decode('utf-8')
            soup = BeautifulSoup(html, "html.parser")
            print(soup)
        except Exception as e:
            print(">>>>>>>>>>> Get HTML soup EXCEPTION:  " + str(e))

        finally:
            return


class Item(Url):
    def __init__(self, url):
        Url.__init__(self, url)

        self.water_str_font = ImageFont.truetype("watermark\\xjlFont.ttf", 50)
        self.water_str_color = (80, 80, 80)  # 深灰色
        self.water_str_pos = (10, 10)  # 从左上角计算
        self.img_water_mark = 'watermark\\watermark_black.png'

    def water_mark(self, img_source, water_str):
        """
            在图片上打水印；
            同时在左上角写上字
            :param img_source:
            :param water_str:在左上角写的字
            :return:
            """
        try:
            im = Image.open(img_source)

            # 在图片上写字
            draw = ImageDraw.Draw(im)
            draw.text(self.water_str_pos, water_str, fill=self.water_str_color, font=self.water_str_font)
            im.save(img_source)

            # 打水印
            wm = Image.open(self.img_water_mark)
            layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
            layer.paste(wm, (im.size[0] - wm.size[0], im.size[1] - wm.size[1]))
            new_im = Image.composite(layer, im, layer)
            new_im.save(img_source)
        except Exception as e:
            print(">>>> water_mark EXCEPTION >>>> " + str(e))
        finally:
            return


class FreePeopleItem(Item):
    def __init__(self, url):
        Item.__init__(self, url)

        self.desc = None
        self.div_product = ""
        self.id = ""
        self.item_name_eng = ""
        self.item_dir = ""
        self.memo = []
        self.model_info = None
        self.model_size = None
        self.name = ""

        if self.get_soup() is not None:
            if self.make_dir() is not None:
                self.get_id()
                self.get_name()
                self.get_product_div()
                self.get_picture()
                self.get_fpme()
                self.get_desc()
                self.draw_desc_picture()

    def make_dir(self):
        # 分析fp网址，提取商品目录名称并创建目录
        self.item_name_eng = self.url.replace(FP_ITEM_PRE_URL, '')
        if self.item_name_eng.find("/") >= 0:
            self.item_name_eng = self.item_name_eng[:self.item_name_eng.find("/")]

        if self.item_name_eng is None:
            return None

        self.item_dir = os.getcwd() + '\\' + self.item_name_eng + '\\'

        if os.path.exists(self.item_name_eng):
            return True

        try:
            os.mkdir(self.item_name_eng)
        except Exception as e:
            print(">>>> make_dir EXCEPTION >>>> " + str(e))
            return None
        else:
            return True

    def get_id(self):
        # 取商品编号
        button_id = self.soup.find('button',
                                   attrs={'class': 'like-it button-white button-like-it'})
        if button_id is not None:
            self.id = button_id['data-style-number']

    def get_name(self):
        h1_name = self.soup.find('h1',
                                 attrs={'itemprop': 'name'})
        if h1_name is not None:
            self.name = h1_name.get_text()

    def get_product_div(self):
        self.div_product = self.soup.find('div',
                                          attrs={'class': 'product-details  product-images row collapse'})

        if self.div_product is None:
            print("div_product is not find.")
            return

    def get_picture(self):
        # 取颜色列表及不同颜色的图片
        self.color_list = {}
        div_color = self.div_product.find('div',
                                          attrs={'class': 'swatches'})

        for color in div_color.find_all('img'):
            self.color_list[color['data-color-code']] = color['data-color-name']

            color_name = color['data-color-name'].replace('/', '_')
            color_url = color['src'].replace('swatch?$swatch-detail$', '')
            fp_pos = color_url.find('FreePeople/') + len('FreePeople/')
            color_path = self.item_dir + '\\' + color_name + '_' + color_url[fp_pos:]

            color_view = color['data-view-code']
            for view in color_view.split(','):
                color_view_url = color_url + view + '?$product$&wid=602'
                color_view_path = color_path + view + '.jpg'
                try:
                    urllib.request.urlretrieve(color_view_url, color_view_path)
                    self.water_mark(color_view_path, color_name)
                except Exception as e:
                    print(">>>>>>>>>>> Get color picture EXCEPTION:  " + str(e))
                    continue
                else:
                    print(color_view_path)

    def get_fpme(self):
        # 取fpme中的图片
        self.fpme_url = 'https://www.freepeople.com/api/engage/v0/fp-us/styles/' + self.id + '/pictures?limit=30&offset=0'
        self.fpme_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0'}

        print(">>>> fpme url is:")
        print(self.fpme_url)

        for value in self.headers.values():
            if value.find('urbn_auth_payload') >= 0:
                start_pos = value.find('%22authToken%22%3A%22') + len('%22authToken%22%3A%22')
                end_pos = value.find('%22%2C%22expiresIn%22')
                self.fpme_headers['X-Urbn-Auth-Token'] = value[start_pos: end_pos]

        try:
            request = urllib.request.Request(self.fpme_url, headers=self.fpme_headers)
            response = urllib.request.urlopen(request, timeout=20)
            json_str = response.read().decode('utf-8')
        except Exception as e:
            print(">>>> get_fpme json EXCEPTION >>>> " + str(e))
            return
        else:
            print("Get fpme pics list success...")

        json_object = json.loads(json_str)

        for img in json_object:
            img_url = img['imageUrl'] + '?$fpme-style-pic-large$'
            ugc_pos = img['imageUrl'].find('ugc/')
            fpme_img_name = self.item_dir + '\\' + img['imageUrl'][ugc_pos:].replace('ugc/', 'fpme_')
            fpme_img_name = fpme_img_name.replace('.tif', '.jpg')

            try:
                urllib.request.urlretrieve(img_url, fpme_img_name)
                self.water_mark(fpme_img_name, 'Fpme')
            except Exception as e:
                print(">>>> get_fpme picture EXCEPTION >>>>  " + str(e))
                continue
            else:
                print(fpme_img_name)

        return

    def get_desc(self):
        # 取商品描述
        div_desc = self.div_product.find('div',
                                         attrs={'class': 'product-desc'})
        if div_desc is not None:
            self.desc = div_desc.get_text()
            if self.desc is not None:
                self.desc = self.desc.strip()

        # # 有的描述里面会写由什么什么出品，一般都是以*开头，这里去掉，防止客户产生歧义
        # if self.desc.find("*") >= 0:
        #     self.desc = self.desc[:self.desc.find("*")]

        # 取注意事项
        li_memo = self.div_product.find('li',
                                        attrs={'class': 'content active'})
        if li_memo is not None:
            for li in li_memo.find_all('li'):
                li_str = li.get_text()
                if li_str is not None:
                    self.memo.append(li_str.strip())

        # 取模特穿着尺寸及模特身材
        div_model_info = self.div_product.find('div',
                                               attrs={'class': 'model-info'})
        if div_model_info is not None:
            div_model_size = div_model_info.find('div',
                                                 attrs={'class': 'model-sizes'})
            if div_model_size is not None:
                model_size_str = div_model_size.get_text()
                if model_size_str is not None:
                    model_size_str = model_size_str.replace('\n', '')
                    self.model_size = model_size_str.replace(' ', '')

            # 看一下model_info中有几个div
            # 然后全部删除
            # 删除所有div后剩下的就是模特的身材数据
            model_info_div_list = div_model_info.find_all('div')
            if model_info_div_list is not None:
                for i in range(len(model_info_div_list)):
                    div_model_info.div.decompose()

            # 删除之后 再判断一次
            if div_model_info is not None:
                model_info_str = div_model_info.get_text()
                if model_size_str is not None:
                    model_info_str = model_info_str.replace('\n', '')
                    self.model_info = model_info_str.replace(' ', '')

    def draw_desc_picture(self):
        desc_list = []
        desc_split_str = "-" * 48
        desc_list.append(desc_split_str)

        # 把描述写入列表
        desc_str = self.desc
        while len(desc_str) > 0:
            # 在图片上写字使用25号徐静蕾体
            # 600px宽的背景，一行能写22个字
            # 这里指的是汉字，没有考虑英文分词的问题
            desc_list.append(desc_str[0:20])
            desc_str = desc_str[20:]

        for line in self.memo:
            desc_list.append("   > " + line)

        if self.model_size is not None:
            desc_list.append(desc_split_str)
            desc_list.append(self.model_size)

        if self.model_info is not None:
            model_info_list = self.model_info.split("|")
            for info in model_info_list:
                desc_list.append("  > " + info.strip())

        desc_list.append(desc_split_str)

        # 新建一张空背景图
        background_color = (237, 237, 239, 0)
        background_width = 600
        background_heigth = 45 * len(desc_list)

        text_font = ImageFont.truetype("watermark\\xjlFont.ttf", 25)
        text_color = (80, 80, 80)  # 深灰色
        text_pos_x = 10  # 从左计算
        text_pos_y = 10  # 从上计算

        layer = Image.new('RGBA', (background_width, background_heigth), background_color)

        # 在图片上写字
        draw = ImageDraw.Draw(layer)
        for str in desc_list:
            draw.text((text_pos_x, text_pos_y), str, fill=text_color, font=text_font)
            text_pos_y = text_pos_y + 45

        self.desc_picture_path = self.item_dir + "\\shuoming.jpg"
        layer.save(self.desc_picture_path)
        print(self.desc_picture_path)


def water_mark(img_source, water_str, color='black'):
    """
    在图片上打水印；
    同时在左上角写上字
    :param img_source:
    :param water_str:在左上角写的字
    :return:
    """
    img_water_mark = ''
    if color == 'black':
        img_water_mark = 'watermark\\watermark_black.png'
    else:
        img_water_mark = 'watermark\\watermark.png'

    text_font = ImageFont.truetype("watermark\\xjlFont.ttf", 50)
    text_color = (80, 80, 80)  # 深灰色
    text_pos = (10, 10)  # 从左上角计算

    try:
        im = Image.open(img_source)

        # 在图片上写字
        draw = ImageDraw.Draw(im)
        draw.text(text_pos, water_str, fill=text_color, font=text_font)
        im.save(img_source)

        # 打水印
        wm = Image.open(img_water_mark)
        layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
        layer.paste(wm, (im.size[0] - wm.size[0], im.size[1] - wm.size[1]))
        new_im = Image.composite(layer, im, layer)
        new_im.save(img_source)

    except Exception as e:
        print(">>>>>>>>>>> WaterMark EXCEPTION:")
        print(str(e))
        return False
    else:
        return True


def get_html_soup(url, headers):
    """

    :param url:
    :param headers:
    :return:

    """
    request = urllib.request.Request(url, headers=headers)
    try:
        response = urllib.request.urlopen(request)
        html = response.read().decode('utf-8')
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        print(">>>>>>>>>>> Get HTML soup EXCEPTION:  " + str(e))
        return None, None
    else:
        return soup, response.headers


def analyse_revolve(revolve_url):
    # 分析revolve网址，提取商品目录名称并创建目录
    item_dir = revolve_url
    item_dir = item_dir.replace(REVOLVE_ROOT_URL, '')
    item_dir = item_dir[:item_dir.find('/')]
    item_name_with_color = item_dir
    item_dir = item_dir[:item_dir.find('-in-')]

    try:
        if not os.path.exists(item_dir):
            os.mkdir(item_dir)

    except Exception as e:
        print(">>>>>>>>>>> Make dir EXCEPTION:  " + str(e))
        return None

    else:
        item_path = os.getcwd() + '\\' + item_dir + '\\'

    # 连接并请求网页
    request_headers = {}
    request_headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0'
    soup, response_headers = get_html_soup(revolve_url, request_headers)

    div_img_page = soup.find('div',
                             attrs={'id': 'js-primary-slideshow__pager'})

    item_color = soup.find('span',
                           attrs={'class': 'u-font-primary u-uppercase u-margin-l--md selectedColor'}).get_text()

    for img in div_img_page.find_all('a'):
        img_url = img['data-zoom-image']
        img_name = img_url[img_url.rfind('/') + 1:]

        try:
            urllib.request.urlretrieve(img_url, item_path + img_name)
            water_mark(item_path + img_name, item_color, 'black')
            print(item_color + '-' + img_name)
        except Exception as e:
            print(">>>>>>>>>>> Get picture EXCEPTION:  " + str(e))
            continue

    # # 看是否有其他颜色
    color_list = soup.find('div',
                           attrs={'class': 'product-swatches product-swatches--lg u-margin-t--none'})

    if color_list is not None:
        for li in color_list.find_all('li'):
            color_url = li['onclick']
            color_url = color_url[color_url.find("('/") + 3: color_url.find("§")]
            if item_name_with_color not in color_url:
                revolve_url = REVOLVE_ROOT_URL + color_url
                soup, response_headers = get_html_soup(revolve_url, request_headers)

                div_img_page = soup.find('div',
                                         attrs={'id': 'js-primary-slideshow__pager'})

                item_color = soup.find('span',
                                       attrs={
                                           'class': 'u-font-primary u-uppercase u-margin-l--md selectedColor'}).get_text()

                for img in div_img_page.find_all('a'):
                    img_url = img['data-zoom-image']
                    img_name = img_url[img_url.rfind('/') + 1:]

                    try:
                        urllib.request.urlretrieve(img_url, item_path + img_name)
                        water_mark(item_path + img_name, item_color, 'black')
                        print(item_color + '-' + img_name)
                    except Exception as e:
                        print(">>>>>>>>>>> Get picture EXCEPTION:  " + str(e))
                        continue
    return


def fp_spider_analyze_catalog(catalog_id):
    DB_NAME = "fp_spider.db"
    FP_SPIDER_ROOT_CHN_URL = "https://www.freepeople.com/china/"
    FP_SPIDER_PRODUCT_CHN_PRE = 'https://www.freepeople.com/china/shop/'

    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cur = conn.cursor()

    # 从数据库中，根据id查找对应的url
    # 以？这个替代符写sql语句的时候，
    # 后面括号里的数据类型必须是元组，
    # 所以只有一个元素的时候，后面要加一个逗号
    cur.execute("SELECT catalog_url FROM catalog WHERE id=?", (catalog_id,))
    catalog_url = cur.fetchone()[0]

    # 连接并请求网页
    request_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0'}
    soup, response_headers = get_html_soup(catalog_url, request_headers)

    if soup is not None:
        if catalog_url.find('?page=') < 0:
            # 只有是第一页的才尝试进行分页的操作
            # 找到total - page - count的值
            # 然后将page=2至total-page-count写入数据库

            total_page_count = 1
            span_page_count = soup.find('span',
                                        attrs={'class': 'total-page-count'})
            # 这里有可能找不到这个值，如果只有一页的话，页面上就不会有这个span

            if span_page_count is not None:
                total_page_count = int(span_page_count.get_text())

            if total_page_count > 1:
                # 理论上只要能够找到total_page_count的这个span，它的值就应该大于1
                # 但是为了保险起见，这里加了一个判断
                for page_num in range(total_page_count - 1):
                    catalog_url_page = catalog_url + '?page=' + str(page_num + 2)
                    print(catalog_url_page)
                    try:
                        cur.execute('INSERT INTO catalog VALUES (NULL,?,?)', (catalog_url_page, 0))
                    except Exception as e:
                        continue

        # 这里是正常的筛查目录和商品的地方
        for link in soup.find_all('a'):
            link_url = link.get('href')
            if link_url is not None:
                # 对link进行处理，去掉后面的查询关键词；
                query_pos = link_url.find('?')
                if query_pos >= 0:
                    link_url = link_url[:query_pos]

                # 如果link_url不是以'/'，统一加上，便于去重
                if not link_url.endswith('/'):
                    link_url = link_url + '/'

                # 这些是商品
                if link_url.startswith(FP_SPIDER_PRODUCT_CHN_PRE):
                    try:
                        cur.execute('INSERT INTO product VALUES (NULL,?,NULL,?)', (link_url, 0))
                        print(link_url)
                        print("It's a product.")
                        print_now()
                    except Exception as e:
                        # print(">>>>>>>>>>> Insert product url EXCEPTION:  " + str(e))
                        continue
                elif link_url.startswith(FP_SPIDER_ROOT_CHN_URL):
                    # 下面的就是目录
                    try:
                        cur.execute('INSERT INTO catalog VALUES (NULL,?,?)', (link_url, 0))
                        print(link_url)
                        print("It's a catalog.")
                        print_now()
                    except Exception as e:
                        # print(">>>>>>>>>>> Insert catalog url EXCEPTION:  " + str(e))
                        continue

    cur.execute('UPDATE catalog SET deal=1 WHERE id=?', (catalog_id,))
    conn.commit()
    conn.close()
    print_now()
    return


def init_DB(operation='keep'):
    """
    初始化数据库
    :param operation:
                    keep:如果存在数据库，继续使用该数据库
                    new：删除现在的数据库，创建新的
    """
    if operation == "new":
        os.remove(DB_NAME)

    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cur = conn.cursor()

    # 尝试创建目录表单
    cur.execute('''CREATE TABLE IF NOT EXISTS catalog
                         (id            INTEGER PRIMARY KEY AUTOINCREMENT,
                         catalog_url    TEXT UNIQUE,
                         deal           INT)''')

    # 尝试创建商品表单
    cur.execute('''CREATE TABLE IF NOT EXISTS product
                    (id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_url     TEXT UNIQUE,
                    name            TEXT,
                    deal            INT)''')

    try:
        # 尝试插入根节点
        cur.execute('INSERT INTO catalog VALUES (NULL,?,?)', (FP_SPIDER_ROOT_CHN_URL, 0))
    except Exception as e:
        print("It's good.")

    # Save (commit) the changes
    conn.commit()
    conn.close()


def print_now():
    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


def fp_spider():
    print_now()

    init_DB()

    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("SELECT id FROM catalog WHERE deal=0 ORDER BY id")
    result = cur.fetchall()
    conn.close()

    while len(result) > 0:
        pool = multiprocessing.Pool(processes=100)
        for row in result:
            pool.apply_async(fp_spider_analyze_catalog, (row[0],))
        pool.close()
        pool.join()

        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        cur = conn.cursor()
        cur.execute("SELECT id FROM catalog WHERE deal=0 ORDER BY id")
        result = cur.fetchall()
        conn.close()

    print("It's over.")

    return


def main():
    split_str = "=" * 60
    while True:
        print(split_str)
        print(">> 支持以下网站：")
        print(">> Freepeople中国")
        print(">> Revolve")
        print("")
        print(">> 输入3，可以遍历整个FP中国网站，耗时较长，慎用")
        print(">> 输入0，用于测试")
        print(split_str)
        print(">> 请输入一个商品地址....")
        url = input(">> ")

        if url.startswith(FP_ITEM_PRE_URL):
            freepeople_item = FreePeopleItem(url)
        elif url.startswith(REVOLVE_ROOT_URL):
            analyse_revolve(url)
        elif url == "3":
            fp_spider()
        elif url == "0":
            test()
        else:
            print("错误：输入的地址不是合法的商品地址...")
            print("\n")


def get_test_soup(url):
    """

    :param url:
    :param headers:
    :return:

    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0'}

    request = urllib.request.Request(url, headers=headers)
    print(url)
    try:
        response = urllib.request.urlopen(request)
        html = response.read().decode('utf-8')
        soup = BeautifulSoup(html, "html.parser")
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    except Exception as e:
        print(">>>>>>>>>>> Get HTML soup EXCEPTION:  " + str(e))

    finally:
        return


def test():
    # url = "https://www.freepeople.com/china/shop/that-girl-maxi-dress/"
    # freepeople_item = FreePeopleItem(url)
    # # analyse_freepeople(url)
    # print(freepeople_item.memo)
    # 新线程执行的代码:

    fp_spider = FreePeopleSpider()

    # while catalog_id:
    #     print('catalog id is:' + str(catalog_id))
    #     fp_spider_analyze_catalog(catalog_id)
    #     conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    #     cur = conn.cursor()
    #     try:
    #         cur.execute("SELECT id FROM catalog WHERE deal=0 ORDER BY id")
    #         catalog_id = cur.fetchone()[0]
    #     except Exception as e:
    #         # print(">>>>>>>>>>> Insert product url EXCEPTION:  " + str(e))
    #         catalog_id = None
    #         continue
    #     conn.close()
    #
    # print("It's over.")

    return

    # pool = multiprocessing.Pool(processes=5)
    # result = pool.apply_async(f, [10])
    # print(result.get(timeout=1))
    # print(pool.map(f, range(10)))


if __name__ == '__main__':
    # 设置全局超时时间
    # socket.setdefaulttimeout(10)

    # 设置全局起始时间
    start = time.time()

    # 设置全局变量
    FP_SPIDER_ROOT_CHN_URL = "https://www.freepeople.com/china/"
    FP_SPIDER_PRODUCT_CHN_PRE = 'https://www.freepeople.com/china/shop/'
    FP_ITEM_PRE_URL = 'https://www.freepeople.com/china/shop/'
    REVOLVE_ROOT_URL = 'http://www.revolve.com/'
    DB_NAME = "fp_spider.db"

    main()
    # test()
    # fp_spider()

    # spider_class_test  = freepeople_spider('asdf')
    # print(spider_class_test.database)
