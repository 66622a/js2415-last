import re
import time
import requests
from bs4 import BeautifulSoup
from urllib import parse
from pyrogram.types import Message
from urllib.parse import unquote
from pagermaid.listener import listener
from pagermaid.utils import client as http_client, alias_command


# 此版本是修改版， @fffffx2 修改
def get_filename_from_url(url):
    if "sub?target=" in url:
        pattern = r"url=([^&]*)"
        match = re.search(pattern, url)
        if match:
            encoded_url = match.group(1)
            decoded_url = unquote(encoded_url)
            return get_filename_from_url(decoded_url)
    elif "api/v1/client/subscribe?token" in url:
        if "&flag=clash" not in url:
            url = url + "&flag=clash"
        else:
            pass
        try:
            response = requests.get(url)
            header = response.headers.get('Content-Disposition')
            if header:
                pattern = r"filename\*=UTF-8''(.+)"
                result = re.search(pattern, header)
                if result:
                    filename = result.group(1)
                    filename = parse.unquote(filename)  # 对文件名进行解码
                    airport_name = filename.replace("%20", " ").replace("%2B", "+")
                    return airport_name
        except:
            return '未知'
    else:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (HTML, like Gecko) '
                          'Chrome/108.0.0.0'
                          'Safari/537.36'}
        try:
            pattern = r'(https?://)([^/]+)'
            match = re.search(pattern, url)
            base_url = None
            if match:
                base_url = match.group(1) + match.group(2)
            response = requests.get(url=base_url + '/auth/login', headers=headers, timeout=10)
            if response.status_code != 200:
                response = requests.get(base_url, headers=headers, timeout=1)
            html = response.content
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.title.string
            title = str(title).replace('登录 — ', '')
            if "Attention Required! | Cloudflare" in title:
                title = '该域名仅限国内IP访问'
            elif "Access denied" in title or "404 Not Found" in title:
                title = '该域名非机场面板域名'
            elif "Just a moment" in title:
                title = '该域名开启了5s盾'
            else:
                pass
            return title
        except:
            return '未知'


def convert_time_to_str(ts):
    return str(ts).zfill(2)


def sec_to_data(y):
    h = int(y // 3600 % 24)
    d = int(y // 86400)
    h = convert_time_to_str(h)
    d = convert_time_to_str(d)
    return d + "天" + h + "小时"


def StrOfSize(size):
    def strofsize(integer, remainder, level):
        if integer >= 1024:
            remainder = integer % 1024
            integer //= 1024
            level += 1
            return strofsize(integer, remainder, level)
        elif integer < 0:
            integer = 0
            return strofsize(integer, remainder, level)
        else:
            return integer, remainder, level

    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    integer, remainder, level = strofsize(size, 0, 0)
    if level + 1 > len(units):
        level = -1
    return ('{}.{:>03d} {}'.format(integer, remainder, units[level]))


@listener(is_plugin=True, outgoing=True, command=alias_command("cha"),
          description='识别订阅链接并获取信息\n使用方法：使用该命令发送或回复一段带有一条或多条订阅链接的文本',
          parameters='<url>')
async def subinfo(_, msg: Message):
    headers = {
        'User-Agent': 'ClashforWindows/0.18.1'
    }
    output_text = None
    try:
        message_raw = msg.reply_to_message and (msg.reply_to_message.caption or msg.reply_to_message.text) or (
                    msg.caption or msg.text)
        final_output = ''
        url_list = re.findall("https?://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]",
                              message_raw)  # 使用正则表达式查找订阅链接并创建列表
        for url in url_list:
            try:
                res = await http_client.get(url, headers=headers, timeout=5)  # 设置5秒超时防止卡死
                while res.status_code == 301 or res.status_code == 302:
                    url1 = res.headers['location']
                    res = await http_client.get(url1, headers=headers, timeout=5)
            except:
                final_output = final_output + '连接错误' + '\n\n'
                continue
            if res.status_code == 200:
                try:
                    info = res.headers['subscription-userinfo']
                    info_num = re.findall('\d+', info)
                    time_now = int(time.time())
                    output_text_head = '订阅链接：`' + url + '`\n机场名：`' + get_filename_from_url(
                        url) + '`\n已用上行：`' + StrOfSize(
                        int(info_num[0])) + '`\n已用下行：`' + StrOfSize(int(info_num[1])) + '`\n剩余：`' + StrOfSize(
                        int(info_num[2]) - int(info_num[1]) - int(info_num[0])) + '`\n总共：`' + StrOfSize(
                        int(info_num[2]))
                    if len(info_num) >= 4:
                        timeArray = time.localtime(int(info_num[3]) + 28800)
                        dateTime = time.strftime("%Y-%m-%d", timeArray)
                        if time_now <= int(info_num[3]):
                            lasttime = int(info_num[3]) - time_now
                            output_text = output_text_head + '`\n此订阅将于`' + dateTime + '`过期' + '，剩余`' + sec_to_data(
                                lasttime) + '`'
                        elif time_now > int(info_num[3]):
                            output_text = output_text_head + '`\n此订阅已于`' + dateTime + '`过期！'
                    else:
                        output_text = output_text_head + '`\n到期时间：`未知`'
                except:
                    output_text = '订阅链接：`' + url + '`\n机场名：`' + get_filename_from_url(url) + '`\n无流量信息'
            else:
                output_text = '无法访问'
            final_output = final_output + output_text + '\n\n'
        await msg.edit(final_output)
    except:
        await msg.edit('参数错误')
