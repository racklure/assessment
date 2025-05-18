from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os
from config import Config
from datetime import datetime
import json

# 初始化扩展
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db.session.remove()    
    
    # 注册蓝图
    from app.controllers.auth import auth_bp
    from app.controllers.admin import admin_bp
    from app.controllers.assessor import assessor_bp
    from app.controllers.statistics import statistics_bp
    from app.controllers.score_analysis import score_analysis_bp

    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(assessor_bp)
    app.register_blueprint(statistics_bp)
    app.register_blueprint(score_analysis_bp)
    
    # 添加根路由，重定向到登录页面
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))
    
    # 添加全局上下文处理器，为所有模板提供now变量
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}
    
    # 注册自定义过滤器
    app.jinja_env.filters['json_decode'] = lambda x: json.loads(x) if isinstance(x, str) else x
    @app.template_filter('cntime')
    def convert_to_shanghai(value):
        import pendulum
        if value:
            return pendulum.instance(value).in_timezone('Asia/Shanghai').format('YYYY-MM-DD HH:mm:ss')
        return ''

    
    return app

