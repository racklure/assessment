import os

class Config:
    # 基本配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-for-assessment-system'
    
    # 数据库配置
    #SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://assess:z123456@192.168.15.181/assess_db'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:z123456@localhost/assess_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 自动检测断开的连接 + 设置连接回收时间（单位：秒）
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,      # 自动探测死连接
        "pool_recycle": 1800,       # 每 30 分钟强制断开重连
        "pool_size": 10,            # 正常连接池容量
        "max_overflow": 20          # 峰值临时连接数
    }


    # 上传文件配置
    UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB 限制
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
