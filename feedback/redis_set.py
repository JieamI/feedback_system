import redis

class Redis_set:
    def __init__(self, name):
        self.con = redis.Redis(host='127.0.0.1', port= 6379, db= 0)
        self.name = name
    def to_set(self, lis):
        for value in lis:
            self.con.zincrby(self.name, 1, value)
            #self.con.zincrby(self.name, value, 1)

    def get_score(self, value):
        return self.con.zscore(self.name, value)

    def sort_set(self):
        return self.con.zrevrange(self.name, 0, self.con.zcard(self.name)+1, withscores=True)


