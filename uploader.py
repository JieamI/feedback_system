#负责用户反馈中的附件上传
import os
import re
import urllib
import json
from flask import url_for
from datetime import datetime
from random import randrange
import logging
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)


class UpLoader(object):
    stateMap = [  
        "SUCCESS",  
        "文件大小超出 upload_max_filesize 限制",
        "文件大小超出 MAX_FILE_SIZE 限制",
        "文件未被完整上传",
        "没有文件被上传",
        "上传文件为空",
    ]

    state_error = {
        "ERROR_TMP_FILE": "临时文件错误",
        "ERROR_TMP_FILE_NOT_FOUND": "找不到临时文件",
        "ERROR_SIZE_EXCEED": "文件大小超出网站限制",
        "ERROR_TYPE_NOT_ALLOWED": "文件类型不允许",
        "ERROR_CREATE_DIR": "目录创建失败",
        "ERROR_DIR_NOT_WRITEABLE": "目录没有写权限",
        "ERROR_FILE_MOVE": "文件保存时出错",
        "ERROR_FILE_NOT_FOUND": "找不到上传文件",
        "ERROR_WRITE_CONTENT": "写入文件内容错误",
        "ERROR_UNKNOWN": "未知错误",
        "ERROR_DEAD_LINK": "链接不可用",
        "ERROR_HTTP_LINK": "链接不是http链接",
        "ERROR_HTTP_CONTENTTYPE": "链接contentType不正确"
    }

    def __init__(self, file_obj=None, upload_path=None, config=None, _type=None):
        self.file_obj = file_obj
        self.upload_path = upload_path
        self.config = config
        self._type = _type
        self.base_name = self.get_file_path()
        self.filename = ''

    def up_file(self):
        if self.check_size():
            _ext = self.check_file_type()
            if _ext:
                self.base_name = self.base_name + _ext
                base_name = os.path.abspath(self.upload_path + self.base_name)
                if not os.path.isdir(os.path.dirname(base_name)):
                    try:
                        os.makedirs(os.path.dirname(base_name))
                    except IOError as e:
                        logger.exception(e)
                        self.state_info = self.get_state_error('ERROR_CREATE_DIR')
                self.filename = os.path.basename(base_name)
                try:
                    print(base_name)
                    self.file_obj.save(base_name)
                    self.state_info = self.stateMap[0]
                except Exception as e:
                    logger.exception(e)
                    self.state_info = self.get_state_error('ERROR_FILE_MOVE')
            else:
                self.state_info = self.get_state_error('ERROR_TYPE_NOT_ALLOWED')
        else:
            self.state_info = self.get_state_error('ERROR_SIZE_EXCEED')

   #检查文件大小是否满足上传条件
    def check_size(self):
        size = self.file_obj.stream.read()  # 读完文件流，需要把指针设回起点
        self.file_obj.stream.seek(0, 0)
        length = len(size)
        print(length)
        if length > self.config.get('maxSize'):
            return False
        return True
    #检查文件类型
    def check_file_type(self):
        file_name = secure_filename(self.file_obj.filename)
        if file_name:
            file_postfix = file_name.split('.')[1]
            file_extension = '.' + file_postfix.lower()
            if file_extension in self.config.get('allowFiles', None):
                return file_extension
        return False
    #获取文件存入路径
    def get_file_path(self):
        filename_path = self.config.get('pathFormat', None)
        if filename_path:
            now = datetime.now()
            filename_path = filename_path.replace('{yyyy}{mm}{dd}',
                                                  str(now.year) + '-' + str(now.month) + '-' + str(now.day))
            filename_path = filename_path.replace('{time}', now.strftime('%H%M%S'))

            rand_re = r'\{rand\:(\d*)\}'
            _pattern = re.compile(rand_re, flags=re.I)
            ret_list = re.findall(_pattern, filename_path)
            if ret_list:
                num = int(ret_list[0])
                rand_nums = str(randrange(10 ** (num - 1), 10 ** num))
                _path = _pattern.sub(rand_nums, filename_path)
                return _path
        return None
    #上传错误
    def get_state_error(self, err):
        
        return self.state_error.get(err, 'ERROR_UNKNOWN')
    #返回信息
    def callback_info(self):
        return {
            "state": self.state_info,
            "url": url_for('static', filename=self.base_name[1:], _external=True),
            "title": self.filename,
            "original": self.filename,
        }
