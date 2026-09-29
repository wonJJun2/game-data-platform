import os

import redis


redis_url = os.environ["REDIS_URL"]

redis_client = redis.Redis.from_url(
    redis_url,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)