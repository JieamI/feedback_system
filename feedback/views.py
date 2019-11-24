from flask import Flask, render_template, make_response
from flask import request, url_for, redirect, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from feedback import app, db, User, Feedback, re_set, typelist, email, UpLoader
import json
import os
import re
import sys



#登录路由
@app.route('/login', methods = ['POST', 'GET']) 
def login():
    if request.method == 'POST':
        username = request.form.get('Username')
        password = request.form.get('Password')
        
        user = User.query.filter_by(username = username).first()
        if not user:
            flash("用户名不存在")
            return redirect(url_for('login'))
        if not user.if_pass(password):
            flash("密码错误")
            return redirect(url_for('login'))
        else:
            login_user(user)
            flash("登录成功")
            return redirect(url_for('index'))

    return render_template("login.html")


#注册路由
@app.route('/register', methods = ['POST', 'GET'])
def register():
    if request.method == 'POST':
        username = request.form.get('Username')
        password = request.form.get('Password')
        nickname = request.form.get('Nickname')
        c_password = request.form.get('Confirm_Password')
        
        if nickname == '' or username == '' or password == '' or c_password == '':
            flash("输入框不得为空")
            return redirect(url_for('register'))
        
        if password != c_password:
            flash("两次密码输入不一致")
            return redirect(url_for('register'))

        if not re.match(r'^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$', username):
            flash("请输入合法的邮箱地址")
            return redirect(url_for('register'))
        
        if User.query.filter_by(username = username).first():
            flash('用户名已存在')
            return redirect(url_for('register'))
        
        user = User(nickname = nickname, username = username, password_hash = generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash("注册成功")
        return redirect(url_for('login'))
    
    resp = make_response(render_template("register.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    if request.method == 'GET':
        return resp

#登出路由
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('登出成功')
    return redirect(url_for('index'))           

#首页路由
@app.route('/index', methods = ['POST', 'GET'])
def index():
    if current_user.is_authenticated:
        return render_template('index.html', nickname = current_user.nickname)
    else:
        return render_template('index.html')


#用户路由
@app.route('/home', methods = ['POST', 'GET'])
@login_required
def home():
    return render_template("home.html", user = current_user)

#用户反馈管理路由
@app.route('/home/fbmanage', methods = ['POST', 'GET'])
@login_required
def fbmanage():
    feedback = []
    for each in Feedback.query.filter_by(username = current_user.username).all():
        feedback.append(each.text)
    if request.method == 'POST':
        text = request.form.get("Text")
        res = Feedback.query.filter_by(username = current_user.username, text = text).first()
        for each in res.checkbox.split(','):
            re_set.con.zincrby("wdnmd", -1, each)
        db.session.delete(res)
        db.session.commit()
        return redirect(url_for('fbmanage'))
        
    return render_template('fbmanage.html', f_list = feedback)

#反馈热度路由
@app.route('/home/fbranking')
@login_required
def fbranking():
    _set = []
    print(re_set.sort_set(name = 'wdnmd'))
    for each in re_set.sort_set(name = 'wdnmd'):
        temp = []
        temp.append(each[0].decode())
        temp.append(each[1])    
        
        _set.append(temp) 
    return render_template("fbranking.html", set = _set)

#反馈类型管理路由
@app.route('/home/fbadmin', methods = ['POST', 'GET'])
@login_required
def fbadmin():
    if request.method == 'POST':
        del_type = request.form.get("delete")
        add_type = request.form.get("add")
        if del_type:
            typelist.remove(del_type)
            re_set.zrem('wdnmd', del_type)
            return redirect(url_for("fbadmin"))
        elif add_type:
            typelist.append(add_type)
            return redirect(url_for("fbadmin"))
        
    return render_template("fbadmin.html", typelist = typelist)

#反馈路由
@app.route('/feedback', methods = ['POST', 'GET'])
def feedback():
    if request.method == 'POST':
        #此处text获得是html内容,含有html标签
        text = request.form.get("Feedback")                                
        checkbox = request.form.getlist("Checkbox")
        #后端进一步验证表单，以保证数据可靠性
        if not text or not checkbox:
            flash("请保证输入完整！")
            return redirect(url_for("feedback"))
        
        #发送html格式邮件
        email(text)
        #将反馈类型存入redis
        re_set.to_set(name = 'wdnmd', lis = checkbox)
        #将列表转为字符串存进数据库
        checkbox = ','.join(checkbox)
        #将html格式过滤为只含反馈文本内容的字符串
        text_filter = re.compile('>.*?<')
        text = ''.join(re.findall(text_filter,text)).replace('>','').replace('<','')

        if current_user.is_authenticated:
            username = current_user.username
            feedback = Feedback(username = username, text = text, category = checkbox)
        else:
            #游客反馈时，不存入用户名
            feedback = Feedback(text = text, category = checkbox)                                               
        
        db.session.add(feedback)
        db.session.commit()
        flash("感谢您的反馈！")
        return redirect(url_for("index"))
    
    return render_template('feedback.html', typelist = typelist)
   

#文件上传路由   
@app.route('/upload/', methods=['GET', 'POST'])
def upload():
    result = {}
    basedir = os.path.dirname(__file__)
    action = request.args.get('action', None)
    with open(os.path.join(basedir, 'static', 'ueditor', 'python', 'config.json'), encoding='utf8') as f:
        t = f.read()
        try:
            CONFIG = json.loads(re.sub(r'\/\*.*\*\/', '', t))
        except Exception as e:
            CONFIG = {}
    #初次载入需要进行初始配置，返回读取的配置内容
    if action == 'config':
        result = CONFIG

    if request.method == 'POST':
        if action in ('uploadimage', 'uploadfile'):
            # 图片、文件、视频上传
            if action == 'uploadimage':
                fieldName = CONFIG.get('imageFieldName', None)
                config = {
                    "pathFormat": CONFIG['imagePathFormat'],
                    "maxSize": CONFIG['imageMaxSize'],
                    "allowFiles": CONFIG['imageAllowFiles']
                }
            else:
                fieldName = CONFIG.get('fileFieldName', None)
                config = {
                    "pathFormat": CONFIG['filePathFormat'],
                    "maxSize": CONFIG['fileMaxSize'],
                    "allowFiles": CONFIG['fileAllowFiles']
                }

            if fieldName in request.files:
                file = request.files[fieldName]
                uploader = UpLoader(file_obj=file, config=config, upload_path=os.path.join(basedir, 'static'))
                uploader.up_file()
                result = uploader.callback_info()
            else:
                result['state'] = '上传接口出错'

    result = json.dumps(result)
    res = make_response(result)
    res.headers['Access-Control-Allow-Origin'] = '*'
    res.headers['Access-Control-Allow-Headers'] = 'X-Requested-With,X_Requested_With'
    return res








