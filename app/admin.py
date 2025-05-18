from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from .models import db, User, Assessor, Assessee, AssessorGroup, Department, AssessorAssessee
from datetime import datetime

admin = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('需要管理员权限')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/dashboard')
@admin_required
def dashboard():
    stats = {
        'assessor_count': Assessor.query.count(),
        'assessee_count': Assessee.query.count(),
        'group_count': AssessorGroup.query.count()
    }
    return render_template('admin/dashboard.html', stats=stats)

@admin.route('/assessors')
@admin_required
def assessors():
    assessors = Assessor.query.all()
    return render_template('admin/assessors.html', assessors=assessors)

@admin.route('/assessor/new', methods=['GET', 'POST'])
@admin_required
def new_assessor():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        group_id = request.form['group_id']
        assessee_type = request.form['assessee_type']
        
        # 创建用户账号
        user = User(username=username, role='assessor')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        # 创建考核人
        assessor = Assessor(
            name=name,
            user_id=user.id,
            group_id=group_id,
            department=(assessee_type == 'department')
        )
        db.session.add(assessor)
        
        # 处理考核对象
        if assessee_type == 'person':
            assessee_ids = request.form.getlist('assessee_ids[]')
            for assessee_id in assessee_ids:
                link = AssessorAssessee(assessor_id=assessor.id, assessee_id=assessee_id)
                db.session.add(link)
        else:
            department_id = request.form['department_id']
            assessor.department_id = department_id
            
        db.session.commit()
        flash('考核人添加成功')
        return redirect(url_for('admin.assessors'))
        
    groups = AssessorGroup.query.all()
    assessees = Assessee.query.all()
    departments = Department.query.all()
    return render_template('admin/new_assessor.html', 
                         groups=groups, 
                         assessees=assessees,
                         departments=departments)

@admin.route('/assessor/<int:assessor_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_assessor():
    # ... 编辑考核人的逻辑 ...
    pass

@admin.route('/assessees')
@admin_required
def assessees():
    assessees = Assessee.query.all()
    return render_template('admin/assessees.html', assessees=assessees)

# ... 其他路由处理函数 ...