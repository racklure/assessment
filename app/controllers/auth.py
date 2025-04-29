from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # 根据用户角色重定向到不同页面
        if current_user.role == 'admin':
            return redirect(url_for('admin.index'))
        elif current_user.role == 'assessor':
            return redirect(url_for('assessor.dashboard'))
        else:
            return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            # 根据用户角色重定向
            if user.role == 'admin':
                return redirect(url_for('admin.index'))
            elif user.role == 'assessor':
                return redirect(url_for('assessor.dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('用户名或密码错误')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


# 在现有auth_bp蓝图中添加以下路由

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # 验证当前密码
        if not current_user.check_password(current_password):
            flash('当前密码不正确')
            return redirect(url_for('auth.change_password'))
        
        # 验证新密码
        if new_password != confirm_password:
            flash('两次输入的新密码不一致')
            return redirect(url_for('auth.change_password'))
        
        # 更新密码
        current_user.set_password(new_password)
        db.session.commit()
        
        flash('密码修改成功')
        return redirect(url_for('auth.change_password'))
    
    return render_template('auth/change_password.html')