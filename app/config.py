class Config:
    # ... 现有配置 ...
    
    # MySQL 连接池配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,  # 连接池大小
        'pool_recycle': 3600,  # 连接回收时间（秒）
        'pool_pre_ping': True,  # 自动检测连接是否有效
        'pool_timeout': 30  # 连接超时时间（秒）
    }