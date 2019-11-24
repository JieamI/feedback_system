from feedback import app


if __name__ == '__main__':
    #以多线程处理并发请求
    app.run(threaded = True)
        