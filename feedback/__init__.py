from flask_sqlalchemy import SQLAlchemy 
from flask import Flask, render_template, make_response
from flask import request, url_for, redirect, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from threading import Thread
from feedback.redis_set import Redis_set
from feedback.uploader import UpLoader
import json
import os
import re
import sys

app = Flask(__name__)

#配置数据库路径前缀
WIN = sys.platform.startswith('win')
if WIN:
    prefix = 'sqlite:///'
else:
    prefix = 'sqlite:////'


#初始化redis实例，新建'wdnmd'有序集合
re_set = Redis_set(name = 'wdnmd')

#配置模型数据库的地址   
app.config['SQLALCHEMY_DATABASE_URI'] = prefix + os.path.join(app.root_path, 'data.db')
#app.config['SQLALCHEMY_DATABASE_URI'] = prefix + os.path.join(os.path.dirname(app.root_path), 'data.db')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False    
 #配置邮箱地址  
app.config['MAIL_SERVER'] = 'smtp.qq.com'
app.config['MAIL_PORT'] = '465'
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = '1732615826@qq.com'
app.config['MAIL_PASSWORD'] = 'nhisiijuagxrdcci'     
app.config['MAIL_DEFAULT_SENDER'] = "1732615826@qq.com"  

#邮件发送
def send_async_email(app, msg):
    mail = Mail(app)
    with app.app_context():
        mail.send(msg)
#使邮件发送功能能并发处理
def email(content):
    msg = Message(subject='feedback', sender='1732615826@qq.com', recipients=['1732615826@qq.com'])
    msg.html = content
    thread = Thread(target=send_async_email, args=[app, msg])
    thread.start()
#在传入实例之前配置
db = SQLAlchemy(app) 
#初始化flask-login,登录后变量current_user即为当前用户模型类记录              
login_manager = LoginManager(app)
#当访客不处于登录状态时将其重定向至login端点   
login_manager.login_view = 'login'
#将当前用户实例返回给current_user
@login_manager.user_loader
def load_user(id):
    user = User.query.get(int(id))
    return user

#创建用户数据库，通过继承于UserMixin使current_user拥有is_authenticated等方法
class User(db.Model, UserMixin):                
    id = db.Column(db.Integer, primary_key = True)
    nickname = db.Column(db.String(20))
    username = db.Column(db.String(20))
    #存入密码的散列值以增强安全性
    password_hash = db.Column(db.String(20))       
    
    def if_pass(self, password):
        return check_password_hash(self.password_hash, password)

 #创建反馈数据库
class Feedback(db.Model, UserMixin):         
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(20))
    text = db.Column(db.Text)
    category = db.Column(db.String(50))

#自定义模板语言过滤器
@app.template_filter('textfilter')
def textfilter(text):
    return text[:20]+"..."
    
@app.template_filter('size')
def get_size(lis):
    return len(lis)

from feedback import views