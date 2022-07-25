import json
import time

import redis

from config import settings
from utils import log

logger = log.getLogger("redis")

Pool = redis.ConnectionPool(host=settings.redis_host, port=settings.redis_port, db=settings.redis_db,
                            password=settings.redis_pwd, max_connections=10)


def clearCurrentIp(host, ip):
    logger.info(f"服务器:{host};删除ip:{ip}")
    conn = redis.Redis(connection_pool=Pool, decode_responses=True)
    conn.hgetall(settings.redis_key)
    conn.hdel(settings.redis_key, ip)


def addCurrentIp(host, ip):
    logger.info(f"服务器:{host};添加ip:{ip}")
    conn = redis.Redis(connection_pool=Pool, decode_responses=True)
    conn.hgetall(settings.redis_key)
    conn.hset(settings.redis_key, ip, json.dumps({
        "private_ip": ip,
        "ts": time.strftime('%Y-%m-%d %H:%M:%S'),
        "host":host
    }))
