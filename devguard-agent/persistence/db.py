import pymysql
from pymysql.cursors import DictCursor
import os


class DBConfig:
    """数据库配置"""
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", 3306))
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    database = os.getenv("DB_NAME", "devguard")
    charset = "utf8mb4"


class DBPool:
    """
    简单数据库连接管理器
    每次操作获取连接，自动关闭，避免长连接超时
    """

    @staticmethod
    def get_conn():
        """获取一个新的数据库连接"""
        return pymysql.connect(
            host=DBConfig.host,
            port=DBConfig.port,
            user=DBConfig.user,
            password=DBConfig.password,
            database=DBConfig.database,
            charset=DBConfig.charset,
            cursorclass=DictCursor,
            autocommit=False
        )

    @staticmethod
    def execute(sql: str, args: tuple = None, fetch: bool = False):
        """
        执行 SQL
        fetch=True 时返回查询结果列表，否则返回影响行数
        """
        conn = None
        try:
            conn = DBPool.get_conn()
            with conn.cursor() as cursor:
                rows = cursor.execute(sql, args)
                if fetch:
                    return cursor.fetchall()
                conn.commit()
                return rows
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
