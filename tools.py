#wechat
import pysnooper
import sys, json, re
import urllib.request as urllib2
import urllib
import Config

#dingtalk
import re,sys,json,time,logging
import requests,urllib,hmac,base64,hashlib
import queue

config = Config.Config()

_ver = sys.version_info
is_py3 = (_ver[0] == 3)

try:
    quote_plus = urllib.parse.quote_plus
except AttributeError:
    quote_plus = urllib.quote_plus

try:
    JSONDecodeError = json.decoder.JSONDecodeError
except AttributeError:
    JSONDecodeError = ValueError


def is_not_null_and_blank_str(content):
    """
    非空字符串
    :param content: 字符串
    :return: 非空 - True，空 - False

    >>> is_not_null_and_blank_str('')
    False
    >>> is_not_null_and_blank_str(' ')
    False
    >>> is_not_null_and_blank_str('  ')
    False
    >>> is_not_null_and_blank_str('123')
    True
    """
    if content and content.strip():
        return True
    else:
        return False


class DingtalkChatbot(object):
    """
    钉钉群自定义机器人（每个机器人每分钟最多发送20条），支持文本（text）、连接（link）、markdown三种消息类型！
    """

    def __init__(self, webhook, secret=None, pc_slide=False):
        """
        机器人初始化
        :param webhook: 钉钉群自定义机器人webhook地址
        :param secret: 机器人安全设置页面勾选“加签”时需要传入的密钥
        :param pc_slide: 消息链接打开方式，默认False为浏览器打开，设置为True时为PC端侧边栏打开
        """
        super(DingtalkChatbot, self).__init__()
        self.headers = {'Content-Type': 'application/json; charset=utf-8'}
        self.queue = queue.Queue(20)  # 钉钉官方限流每分钟发送20条信息
        self.webhook = webhook
        self.secret = secret
        self.pc_slide = pc_slide
        self.start_time = time.time()  # 加签时，请求时间戳与请求时间不能超过1小时，用于定时更新签名
        if self.secret is not None and self.secret.startswith('SEC'):
            self.update_webhook()

    def update_webhook(self):
        """
        钉钉群自定义机器人安全设置加签时，签名中的时间戳与请求时不能超过一个小时，所以每个1小时需要更新签名
        """
        if is_py3:
            timestamp = round(self.start_time * 1000)
            string_to_sign = '{}\n{}'.format(timestamp, self.secret)
            hmac_code = hmac.new(self.secret.encode(), string_to_sign.encode(), digestmod=hashlib.sha256).digest()
        else:
            timestamp = long(round(self.start_time * 1000))
            secret_enc = bytes(self.secret).encode('utf-8')
            string_to_sign = '{}\n{}'.format(timestamp, self.secret)
            string_to_sign_enc = bytes(string_to_sign).encode('utf-8')
            hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()

        sign = quote_plus(base64.b64encode(hmac_code))
        self.webhook = '{}&timestamp={}&sign={}'.format(self.webhook, str(timestamp), sign)

    def sendto(self, msg, is_at_all=False, at_mobiles=[], at_dingtalk_ids=[], is_auto_at=True):
        """
        text类型
        :param msg: 消息内容
        :param is_at_all: @所有人时：true，否则为false（可选）
        :param at_mobiles: 被@人的手机号（注意：可以在msg内容里自定义@手机号的位置，也支持同时@多个手机号，可选）
        :param at_dingtalk_ids: 被@人的dingtalkId（可选）
        :param is_auto_at: 是否自动在msg内容末尾添加@手机号，默认自动添加，可设置为False取消（可选）
        :return: 返回消息发送结果
        """
        data = {"msgtype": "text", "at": {}}
        if is_not_null_and_blank_str(msg):
            data["text"] = {"content": msg}
        else:
            logging.error("text类型，消息内容不能为空！")
            raise ValueError("text类型，消息内容不能为空！")

        if is_at_all:
            data["at"]["isAtAll"] = is_at_all

        if at_mobiles:
            at_mobiles = list(map(str, at_mobiles))
            data["at"]["atMobiles"] = at_mobiles
            if is_auto_at:
                mobiles_text = '\n@' + '@'.join(at_mobiles)
                data["text"]["content"] = msg + mobiles_text

        if at_dingtalk_ids:
            at_dingtalk_ids = list(map(str, at_dingtalk_ids))
            data["at"]["atDingtalkIds"] = at_dingtalk_ids

        logging.debug('text类型：%s' % data)
        return self.post(data)

    def post(self, data):
        """
        发送消息（内容UTF-8编码）
        :param data: 消息数据（字典）
        :return: 返回发送结果
        """
        now = time.time()

        # 钉钉自定义机器人安全设置加签时，签名中的时间戳与请求时不能超过一个小时，所以每个1小时需要更新签名
        if now - self.start_time >= 3600 and self.secret is not None and self.secret.startswith('SEC'):
            self.start_time = now
            self.update_webhook()

        # 钉钉自定义机器人现在每分钟最多发送20条消息
        self.queue.put(now)
        if self.queue.full():
            elapse_time = now - self.queue.get()
            if elapse_time < 60:
                sleep_time = int(60 - elapse_time) + 1
                logging.debug('钉钉官方限制机器人每分钟最多发送20条，当前发送频率已达限制条件，休眠 {}s'.format(str(sleep_time)))
                time.sleep(sleep_time)

        try:
            post_data = json.dumps(data)
            response = requests.post(self.webhook, headers=self.headers, data=post_data)
        except requests.exceptions.HTTPError as exc:
            logging.error("消息发送失败， HTTP error: %d, reason: %s" % (exc.response.status_code, exc.response.reason))
            raise
        except requests.exceptions.ConnectionError:
            logging.error("消息发送失败，HTTP connection error!")
            raise
        except requests.exceptions.Timeout:
            logging.error("消息发送失败，Timeout error!")
            raise
        except requests.exceptions.RequestException:
            logging.error("消息发送失败, Request Exception!")
            raise
        else:
            try:
                result = response.json()
            except JSONDecodeError:
                logging.error("服务器响应异常，状态码：%s，响应内容：%s" % (response.status_code, response.text))
                return {'errcode': 500, 'errmsg': '服务器响应异常'}
            else:
                logging.debug('发送结果：%s' % result)
                if result['errcode']:
                    error_data = {"msgtype": "text", "text": {"content": "钉钉机器人消息发送失败，原因：%s" % result['errmsg']},
                                  "at": {"isAtAll": True}}
                    logging.error("消息发送失败，自动通知：%s" % error_data)
                    requests.post(self.webhook, headers=self.headers, data=json.dumps(error_data))
                return result


class WechatCharbot(object):

    def __init__(self):
        self.CropID = 'ww68d301f8c4911662'
        self.Secret = 'YlZbgV_sGsD3a3jPDfM3S-LC12qcYWneHse1bhNkLY8'
        self.AppID = 1000002

    def sendto(self, users, Msg):
        # defaultencoding = 'utf-8'
        # if sys.getdefaultencoding() != defaultencoding:
        #     reload(sys)
        # sys.setdefaultencoding(defaultencoding)

        UserID = users
        GURL = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=' + self.CropID + '&corpsecret=' + self.Secret
        Request = urllib2.Request(GURL)
        Response = urllib2.urlopen(Request)
        access_token = eval(Response.read())['access_token']
        PURL = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=' + access_token
        data = {
            "touser": UserID,
            # "toparty": PartyID,
            "msgtype": "text",
            "agentid": self.AppID,
            "text": {
                "content": Msg
            },
            "safe": 0
        }

        encodeData = json.dumps(data, ensure_ascii=False).encode('utf-8')
        Request = urllib2.Request(PURL, encodeData)
        result = json.loads(str(urllib2.urlopen(Request).read(),'utf-8'))

        errcode = result['errcode']
        if not errcode:
            msg = 'Wechat message send to ' + users + ' success: ' + Msg
            #logging.debug(msg)
            return True
        else:
            errmsg = result['errmsg']
            msg = 'Wechat message send to ' + users + ' send failure: ' + errmsg
            #logging.warnning(msg)
            return False

if __name__ == '__main__':
   main()