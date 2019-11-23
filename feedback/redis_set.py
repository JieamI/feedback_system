import redis

class Redis_set:
    def __init__(self, name):
        self.con = redis.Redis(host='127.0.0.1', port= 6379, db= 0)

    def to_set(self, name, lis):
        for value in lis:
            self.con.zincrby(name, 1, value)

    def get_score(self, name, value):
        return self.con.zscore(name, value)

    def sort_set(self, name):
        return self.con.zrevrange(name, 0, self.con.zcard(name)+1, withscores=True)


