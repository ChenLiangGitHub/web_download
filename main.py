#!/usr/local/bin/python3
# -*-coding:UTF-8-*-
# __author__ = 'NB_Ren'

from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from collections import OrderedDict

import os
import socket
import json
import urllib.request


def write_csv(csv_file, item_data_dict):
    """
    接收orderdict格式的商品数据
    写入csv文件
    :param csv_file:
    :param item_data:
    """
    item_data_list = item_data_dict.values()
    item_data_str = '\t'.join(item_data_list)

    file = open(csv_file, 'a', encoding='utf16')
    file.write(item_data_str + '\n')
    file.close()
    print('商品数据写入CSV文件成功...')


def creat_csv(csv_file):
    """
    根据模板创建csv文件
    :param csv_file:
    :return:
    OrderedDict格式的模板数据；
    没个数据成对出现；
    """
    templet_csv_file = 'templet\\templet.csv'

    file_src = open(templet_csv_file, 'r', encoding='utf16')
    templet_lines = file_src.read().split('\n')
    file_src.close()

    file_tar = open(csv_file, 'w', encoding='utf16')
    file_tar.write(templet_lines[0] + '\n')
    file_tar.write(templet_lines[1] + '\n')
    file_tar.write(templet_lines[2] + '\n')
    file_tar.close()
    print('创建CSV文件成功：' + csv_file)

    templet_data_dict = OrderedDict()
    title_eng_list = templet_lines[1].split('\t')
    data_list = templet_lines[3].split('\t')

    for i in range(len(title_eng_list)):
        templet_data_dict[title_eng_list[i]] = data_list[i]

    return templet_data_dict


def water_mark(img_source, water_str):
    """
    在图片上打水印；
    同时在左上角写上字
    :param img_source:
    :param water_str:在左上角写的字
    :return:
    """
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


def make_dir(item_dir):
    """
    根据url的最后一个字段
    创建对应名称的文件夹
    :param item_dir:
    :return:
    返回文件夹绝对路径
    """
    FP_ROOT_URL = 'https://www.freepeople.com/china/shop/'
    item_dir = item_dir.replace(FP_ROOT_URL, '')
    folder_rel_path = item_dir.replace('/', '')

    try:
        if not os.path.exists(folder_rel_path):
            os.mkdir(folder_rel_path)

    except Exception as e:
        print(">>>>>>>>>>> Make dir EXCEPTION:  " + str(e))
        return None

    else:
        folder_abs_path = os.getcwd() + '\\' + folder_rel_path + '\\'
        return folder_abs_path, folder_rel_path


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
        return None
    else:
        return soup, response.headers


def check_url(url):
    """
    检查输入的url是否是FP中国的地址
    :param url:
    :return:
    """
    FP_ROOT_URL = 'https://www.freepeople.com/china/shop/'
    if url.startswith(FP_ROOT_URL):
        return True
    else:
        print('错误：输入的地址不是FP中国的商品地址...')
        return False


def analyse_freepeople(fp_url):
    item_path, item_rel_path = make_dir(fp_url)

    request_headers = {}
    request_headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0'
    soup, response_headers = get_html_soup(fp_url, request_headers)

    div_item = soup.find('div',
                         attrs={'class': 'product-details  product-images row collapse'})

    # # 取商品名称
    # soup_name = div_item.find('h1',
    #                           attrs={'itemprop': 'name'})
    # if soup_name is not None:
    #     item_name = soup_name.get_text().strip()
    #     item_data_dict['title'] = '商品名称：皮淘美国代购free people ' + item_name
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
    # 取商品编号
    soup_id = div_item.find('p',
                            attrs={'itemprop': 'productID'})
    if soup_id is not None:
        item_id = soup_id.get_text().replace('款式: ', '').strip()

    # # 取商品描述
    # soup_desc = div_item.find('p',
    #                           attrs={'class': 'product-desc'})
    # if soup_desc is not None:
    #     item_desc = soup_desc.get_text().strip()
    #     print('商品描述：' + item_desc)
    #     item_data_dict['subtitle'] = item_desc
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

    print(response_headers)

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
            water_mark(fpme_img_name, 'Fpme Pic')
        except Exception as e:
            print(">>>>>>>>>>> Get fpme picture EXCEPTION:  " + str(e))
            continue
        else:
            print(fpme_img_name)

    return


def main():
    while True:
        print('/===========================/')
        print('input a free people url....')
        url = input('>>')

        if not check_url(url):
            return

        analyse_freepeople(url)


def assemble_item_data(templet_data_dict, item_data_dict):
    for key in item_data_dict.keys():
        templet_data_dict[key] = item_data_dict[key]
    return templet_data_dict


def FP_spider():
    ROOT = 'https://www.freepeople.com/china/'

    headers = {}
    headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0'
    soup, cookie = get_html_soup(ROOT, headers)

    for link in soup.find_all('a'):
        print(link)


def test():
    # while True:
    #     print('/===========================/')
    #     print('input a free people url....')
    #     url = input('>>')
    #     main(url)

    url = 'https://www.freepeople.com/china/shop/modern-kimono-dress/'
    analyse_freepeople(url)


if __name__ == '__main__':
    # 设定利润率
    PROFIT_RATE = 0.2

    # 设置全局超时时间
    socket.setdefaulttimeout(10)

    main()
