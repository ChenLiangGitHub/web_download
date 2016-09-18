#!/usr/local/bin/python3
# -*-coding:UTF-8-*-
# __author__ = 'NB_Ren'

from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from collections import OrderedDict

import os, time
import socket
import json
import urllib.request
import sqlite3


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


def analyse_freepeople(fp_url):
    # 分析fp网址，提取商品目录名称并创建目录
    item_dir = fp_url
    item_dir = item_dir.replace(FP_ROOT_URL, '')
    item_dir = item_dir.replace('/', '')

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
    soup, response_headers = get_html_soup(fp_url, request_headers)
    if soup is None:
        print("get_html_soup error.")
        return


    # 取商品编号
    soup_id = soup.find('button',
                        attrs={'class': 'like-it button-white button-like-it'})
    if soup_id is not None:
        item_id = soup_id['data-style-number']
    print(item_id)

    div_item = soup.find('div',
                             attrs={'class': 'product-details  product-images row collapse'})
    if div_item is None:
        print("div_item is not find.")
        return

    # 取颜色列表及不同颜色的图片
    color_list = {}
    div_color = div_item.find('div',
                              attrs={'class': 'swatches'})

    for color in div_color.find_all('img'):
        color_list[color['data-color-code']] = color['data-color-name']

        color_name = color['data-color-name'].replace('/', '_')
        color_url = color['src'].replace('swatch?$swatch-detail$', '')
        fp_pos = color_url.find('FreePeople/') + len('FreePeople/')
        color_path = item_path + '\\' + color_name + '_' + color_url[fp_pos:]

        color_view = color['data-view-code']
        for view in color_view.split(','):
            color_view_url = color_url + view + '?$product$&wid=602'
            color_view_path = color_path + view + '.jpg'
            try:
                urllib.request.urlretrieve(color_view_url, color_view_path)
                water_mark(color_view_path, color_name)

            except Exception as e:
                print(">>>>>>>>>>> Get color picture EXCEPTION:  " + str(e))
                continue

            else:
                print(color_view_path)

    # # 取商品名称
    # soup_name = div_item.find('h1',
    #                           attrs={'itemprop': 'name'})
    # if soup_name is not None:
    #     item_name = soup_name.get_text().strip()
    #     # item_data_dict['title'] = '商品名称：皮淘美国代购free people ' + item_name
    #     print(item_name)
    #
    # # 取商品价格
    # soup_price = div_item.find('h3',
    #                            attrs={'itemprop': 'price'})
    # if soup_price is not None:
    #     item_price = soup_price.get_text().strip()
    #     item_price = item_price.replace('¥', '')
    #
    #     try:
    #         final_price = float(item_price) * (PROFIT_RATE + 1)
    #         item_data_dict['price'] = str(final_price)
    #         print(item_data_dict)
    #
    #     except Exception as e:
    #         print(">>>>>>>>>>> get finally price EXCEPTION:  " + str(e))
    #


    # 取商品描述
    soup_desc = div_item.find('p',
                              attrs={'class': 'product-desc'})
    if soup_desc is None:
        soup_desc = div_item.find('div',
                                  attrs={'class': 'product-desc'})
    if soup_desc is not None:
        item_desc = soup_desc.get_text().strip()
        print('商品描述：' + item_desc)
        # item_data_dict['subtitle'] = item_desc

    #
    # # 取清洁须知
    # soup_care = div_item.find('ul',
    #                           attrs={'class': 'content-bullets product-care'})
    # if soup_care is not None:
    #     item_care = soup_care.get_text().strip()
    #     print('清洁须知：' + item_care)
    #
    # item_material_list = div_item.find_all('ul',
    #                                        attrs={'class': 'content-bullets'})
    # item_material = []
    # for ul in item_material_list:
    #     for li in ul.find_all('li'):
    #         item_material.append(li.get_text().strip())
    #
    # print(item_material)

    # # 取模特穿着尺寸
    # soup_model_info = div_item.find('div',
    #                                 attrs={'class': 'model-info'})
    # if soup_model_info is not None:
    #     soup_model_size = soup_model_info.find('div',
    #                                            attrs={'class': 'model-sizes'})
    #     if soup_model_size is not None:
    #         model_size = soup_model_size.get_text().replace('\n', '').replace(' ', '')
    #         print(model_size)
    #
    #     # 看一下model_info中有几个div
    #     # 然后全部删除
    #     model_info_div_count = soup_model_info.find_all('div')
    #     if model_info_div_count is not None:
    #         for i in range(len(model_info_div_count)):
    #             soup_model_info.div.decompose()
    #
    #     if soup_model_info is not None:
    #         model_info = soup_model_info.get_text().replace('\n', '').replace(' ', '')
    #         print(model_info)
    #

    # print(type(color_list))

    # # 取不同颜色的尺码
    # color_size_list = []
    # div_size_zone = div_item.find('div',
    #                               attrs={'class': 'size-options clearfix'})
    # if div_size_zone is not None:
    #     div_size_list = div_size_zone.find_all('div')
    #     if div_size_list is not None:
    #         for div_size in div_size_list:
    #             size_available = div_size.find('button',
    #                                            attrs={'class': 'button-white button-size small '})
    #             if size_available is not None:
    #                 color_size_list.append((color_list[div_size['data-color-code']], div_size['data-product-size']))
    #
    # for color_desc in color_size_list:
    #     print(color_desc)

    # 取fpme中的图片
    fpme_url = 'https://www.freepeople.com/api/engage/v0/fp-us/styles/' + item_id + '/pictures?limit=30&offset=0'

    print(fpme_url)

    for value in response_headers.values():
        if value.find('urbn_auth_payload') >= 0:
            start_pos = value.find('%22authToken%22%3A%22') + len('%22authToken%22%3A%22')
            end_pos = value.find('%22%2C%22expiresIn%22')
            request_headers['X-Urbn-Auth-Token'] = value[start_pos: end_pos]

    try:
        request = urllib.request.Request(fpme_url, headers=request_headers)
        response = urllib.request.urlopen(request)
        json_str = response.read().decode('utf-8')
    except Exception as e:
        print(">>>>>>>>>>> Get fpme json EXCEPTION:  " + str(e))
        return
    else:
        print("Get fpme pics list success...")

    json_object = json.loads(json_str)

    for img in json_object:
        img_url = img['imageUrl'] + '?$fpme-style-pic-large$'
        ugc_pos = img['imageUrl'].find('ugc/')
        fpme_img_name = item_path + '\\' + img['imageUrl'][ugc_pos:].replace('ugc/', 'fpme_')
        fpme_img_name = fpme_img_name.replace('.tif', '.jpg')

        try:
            urllib.request.urlretrieve(img_url, fpme_img_name)
            water_mark(fpme_img_name, 'Fpme')
        except Exception as e:
            print(">>>>>>>>>>> Get fpme picture EXCEPTION:  " + str(e))
            continue
        else:
            print(fpme_img_name)

    return


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
    conn = sqlite3.connect(DB_NAME,check_same_thread = False)
    cur = conn.cursor()

    # 从数据库中，根据id查找对应的url
    # 以？这个替代符写sql语句的时候，
    # 后面括号里的数据类型必须是元组，
    # 所以只有一个元素的时候，后面要加一个逗号
    cur.execute("SELECT catalog_url FROM catalog WHERE id=?", (catalog_id,))
    catalog_url = cur.fetchone()[0]

    print(catalog_url)

    # 连接并请求网页
    request_headers = {}
    request_headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0'
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
                for page_num in range(total_page_count-1):
                    catalog_url_page = catalog_url + '?page=' + str(page_num+2)
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
                if query_pos >=0:
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
                    except Exception as e:
                        # print(">>>>>>>>>>> Insert product url EXCEPTION:  " + str(e))
                        continue
                elif link_url.startswith(FP_SPIDER_ROOT_CHN_URL):
                    # 下面的就是目录
                    try:
                        cur.execute('INSERT INTO catalog VALUES (NULL,?,?)', (link_url, 0))
                        print(link_url)
                        print("It's a catalog.")
                    except Exception as e:
                        # print(">>>>>>>>>>> Insert catalog url EXCEPTION:  " + str(e))
                        continue

    cur.execute('UPDATE catalog SET deal=1 WHERE id=?', (catalog_id,))
    conn.commit()
    conn.close()
    print(time.time()-start)
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

    conn = sqlite3.connect(DB_NAME,check_same_thread = False)
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


def fp_spider():
    init_DB()

    print(time.time()-start)

    conn = sqlite3.connect(DB_NAME,check_same_thread = False)
    cur = conn.cursor()
    cur.execute("SELECT id FROM catalog WHERE deal=0 ORDER BY id")
    catalog_id = cur.fetchone()[0]
    conn.close()

    while catalog_id:
        print('catalog id is:' + str(catalog_id))
        fp_spider_analyze_catalog(catalog_id)
        conn = sqlite3.connect(DB_NAME,check_same_thread = False)
        cur = conn.cursor()
        try:
            cur.execute("SELECT id FROM catalog WHERE deal=0 ORDER BY id")
            catalog_id = cur.fetchone()[0]
        except Exception as e:
            # print(">>>>>>>>>>> Insert product url EXCEPTION:  " + str(e))
            catalog_id = None
            continue
        conn.close()

    print("It's over.")

    return


def main():
    while True:
        print('/---------------------------/')
        print('支持以下网站：')
        print('Freepeople中国')
        print('Revolve')
        print('/---------------------------/')
        print('请输入一个商品地址....')
        url = input('>>')

        if url.startswith(FP_ROOT_URL):
            analyse_freepeople(url)
        elif url.startswith(REVOLVE_ROOT_URL):
            analyse_revolve(url)
        else:
            print('错误：输入的地址不是合法的商品地址...')
            print('\n')


def test():
    id = 15
    fp_spider_analyze_catalog(id)


if __name__ == '__main__':
    # 设置全局超时时间
    socket.setdefaulttimeout(10)

    # 设置全局起始时间
    start = time.time()

    # 设置全局变量
    FP_SPIDER_ROOT_CHN_URL = "https://www.freepeople.com/china/"
    FP_SPIDER_PRODUCT_CHN_PRE = 'https://www.freepeople.com/china/shop/'
    FP_ROOT_URL = 'https://www.freepeople.com/china/shop/'
    REVOLVE_ROOT_URL = 'http://www.revolve.com/'
    DB_NAME = "fp_spider.db"

    main()
    # test()
    # fp_spider()

    # spider_class_test  = freepeople_spider('asdf')
    # print(spider_class_test.database)