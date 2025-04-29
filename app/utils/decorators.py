from functools import wraps
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from flask import flash, redirect, url_for
from app import db

def handle_db_error(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except OperationalError as e:
            db.session.rollback()
            try:
                db.session.ping()  # 尝试重连
                return f(*args, **kwargs)
            except Exception:
                flash('数据库连接错误，请稍后重试')
                return redirect(url_for('admin.index'))
        except SQLAlchemyError:
            db.session.rollback()
            flash('数据库操作错误，请稍后重试')
            return redirect(url_for('admin.index'))
    return decorated_function