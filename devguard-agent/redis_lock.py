import redis
import uuid


class RedisDistributedLock:
    """Redis 分布式任务锁：原子抢占 + 自动过期 + 安全释放"""

    def __init__(self, host="localhost", port=6379, db=0):
        self.redis = redis.Redis(
            host=host, port=port, db=db, decode_responses=True
        )
        self.lock_prefix = "devguard:task:lock:"
        self.lock_holders = {}  # 记录当前持有的锁标识，防止误删

    def try_lock(self, task_id: int, expire_seconds: int = 600) -> bool:
        """
        非阻塞尝试获取任务锁
        :param task_id: 任务ID
        :param expire_seconds: 锁过期时间，默认10分钟，大于任务最大超时
        :return: 是否获取成功
        """
        lock_key = f"{self.lock_prefix}{task_id}"
        holder_id = str(uuid.uuid4())

        # SET NX + EX 原子操作：不存在才设置，同时设置过期时间
        success = self.redis.set(
            lock_key, holder_id, ex=expire_seconds, nx=True
        )

        if success:
            self.lock_holders[task_id] = holder_id
            return True
        return False

    def unlock(self, task_id: int) -> bool:
        """
        安全释放任务锁：校验持有者身份 + Lua 原子删除
        """
        lock_key = f"{self.lock_prefix}{task_id}"
        holder_id = self.lock_holders.get(task_id)

        if not holder_id:
            return False

        # Lua 脚本保证「校验+删除」原子性，避免校验后锁过期被别人持有
        lua_script = """
        if redis.call("GET", KEYS[1]) == ARGV[1] then
            return redis.call("DEL", KEYS[1])
        else
            return 0
        end
        """
        result = self.redis.eval(lua_script, 1, lock_key, holder_id)

        self.lock_holders.pop(task_id, None)
        return result == 1
