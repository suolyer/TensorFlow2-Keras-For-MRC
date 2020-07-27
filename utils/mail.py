import collections

import tensorflow as tf
import numpy as np
import six

import smtplib
from email.header import Header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

"""
modified from  https://github.com/Samathy/py3mail
"""
class Mail:
    def __init__(self, receivers: list or None, host='localhost', user=None, password=None, sender=None, port=25):
        """
        邮件初始化配置项,使用账号密码登陆SMTP邮箱代发邮件
        :param receivers: 接收邮箱,如果有多个用列表
        :param host: SMTP邮件服务器 eg smtp.qq.com
        :param user: 登陆该邮箱的用户名
        :param password: 密码
        :param sender: 默认为发送者邮箱
        :param port: 默认25
        """
        self.host = host
        self.user = user
        self.password = password
        self.receivers = receivers
        self.sender = user if sender is None else sender
        self.port = port
        self.msg = MIMEMultipart('related')
        self.img_id = 0

    def add_tittle(self, title, from_nickname=None):
        """
        添加邮件主题
        :param title:邮件主题
        :param from_nickname:发送者的昵称
        """
        self.msg['From'] = Header(self.user if from_nickname is None else from_nickname, 'utf-8')  # 昵称
        self.msg['To'] = ','.join(self.receivers) if isinstance(self.receivers, list) else self.receivers
        self.msg['Subject'] = Header(title, 'utf-8')

    def add_text(self, text):
        """
        添加纯文本邮件,纯文本模式不能添加图片及HTML
        :param text: 文本内容
        """
        self.msg.attach(MIMEText(text, 'plain', 'utf-8'))

    def add_img(self, img_name: str):
        """
        由于图片在部分邮箱中为附件时不能很好的显示,因此采用HTML模式添加图片
        纯文本模式添加的图片会变成附件
        !!! 需要注意,图片添加的顺序和<img>顺序一致
        :param img_name: 图片文件名
        """
        with open(img_name, 'rb') as fp:
            msg_img = MIMEImage(fp.read())
        self.img_id += 1
        msg_img.add_header('Content-ID', '<{}>'.format(self.img_id))
        self.msg.attach(msg_img)

    def add_html(self, html_text: str):
        """
        添加html
        注意: 如果要添加图片,需要先用add_img方法把所有图片先一个一个读入,并且要在html标记中需要添加图片的地方插入img标签:<img>
            程序会自动根据add_img方法添加图片的顺序填入img标签中
        :param html_text: HTML文本
        """
        img_count = html_text.count("<img>")
        html_text = html_text.replace('<img>', '<img src="cid:{}">')
        try:
            self.msg.attach(MIMEText(html_text.format(*[i for i in range(1, self.img_id + 1)]), 'html', 'utf-8'))
        except IndexError:
            exit('程序终止:需要添加{}张图片,当前只有{}张'.format(img_count, self.img_id, self.img_id))

    def add_attachment(self, file_name: str):
        with open(file_name, 'rb') as fn:
            f = MIMEText(fn.read(), 'base64', 'utf-8')
        f["Content-Type"] = 'application/octet-stream'
        f["Content-Disposition"] = 'attachment; filename="{}"'.format(file_name)
        self.msg.attach(f)

    def send(self):
        try:
            if self.user is not None:
                smtpObj = smtplib.SMTP()
                smtpObj.connect(self.host, self.port)  # 25 为 SMTP 端口号
                smtpObj.login(self.user, self.password)
            else:
                smtpObj = smtplib.SMTP(self.host)
            smtpObj.sendmail(self.sender, self.receivers, self.msg.as_string())

        except smtplib.SMTPSenderRefused:
            exit('发送失败: 参数 {} 不是有效的邮箱格式'.format(self.sender))
        except smtplib.SMTPException as e:
            raise e


def send_email(text):
    """
    :param text: text
    :param receivers: 接收邮箱,如果有多个用列表
    :param host: SMTP邮件服务器 eg. smtp.qq.com,如果本机有安装可用localhost
    :param user: 登陆该邮箱的用户名
    :param password: 密码
    :param sender: 默认为user,可以设置为其他邮箱
    """

    mail = Mail(receivers="sunyannuc@163.com",
                host="smtp.163.com",
                user="sunyannuc@163.com",
                password="JT",
                sender="sunyannuc@163.com",
                port=25)
    mail.add_tittle(title='代码运行结果')
    mail.add_text(text)
    mail.send()


class SendEmail(tf.keras.callbacks.Callback):

    def __init__(self):
        self.keys = None
        super(SendEmail, self).__init__()

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}

        def handle_value(k):
            is_zero_dim_ndarray = isinstance(k, np.ndarray) and k.ndim == 0
            if isinstance(k, six.string_types):
                return k
            elif isinstance(k, collections.abc.Iterable) and not is_zero_dim_ndarray:
                return '"[%s]"' % (', '.join(map(str, k)))
            else:
                return k

        if self.keys is None:
            self.keys = sorted(logs.keys())

        if self.model.stop_training:
            # We set NA so that csv parsers do not fail for this last epoch.
            logs = dict([(k, logs[k]) if k in logs else (k, 'NA') for k in self.keys])

        row_dict = collections.OrderedDict({'epoch': epoch})
        row_dict.update((key, round(handle_value(logs[key]), 4)) for key in self.keys)
        text = str(dict(row_dict))
        send_email(text)
