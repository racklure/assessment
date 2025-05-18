from app.utils.dynamic_table import DynamicTableManager
from app.models.assessment import (
    ImportRecord, Assessment, Assessor, 
    Assessee, AssessmentRecord, AssessmentTemplate,AssessmentAssessor
)
from sqlalchemy import MetaData, Table, Column, Integer, String, Float, DateTime, Text
from flask import (
    Blueprint, render_template, redirect, url_for, 
    flash, request, jsonify, current_app
)
from flask_login import login_required, current_user
from app.models.user import User
from app import db
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import pandas as pd
from sqlalchemy.exc import OperationalError
import time

from collections import defaultdict
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash('您没有权限访问此页面')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin_bp.route('/')
@admin_required
def index():
    """管理后台首页"""
    stats = {
        'template_count': AssessmentTemplate.query.count(),
        'assessor_count': Assessor.query.count(),
        'assessee_count': Assessee.query.count(),
        'import_record_count': ImportRecord.query.count()
    }
    
    # 获取最近的5个考核
    recent_assessments = Assessment.query.order_by(Assessment.created_at.desc()).limit(5).all()
    
    return render_template('admin/index.html', 
                         stats=stats,
                         recent_assessments=recent_assessments)

@admin_bp.route('/assessments/new', methods=['GET', 'POST'])
@admin_required
def new_assessment():
    if request.method == 'POST':
        assessment_name = request.form.get('assessment_name')
        department = request.form.get('department')
        template_id = request.form.get('template_id')
        
        # 获取选择的模板
        template = AssessmentTemplate.query.get(template_id)
        if not template:
            flash('所选模板不存在')
            return redirect(request.url)
        
        assessment = Assessment(
            assessment_name=assessment_name,
            department=department,
            template_id=template_id
        )
        
        db.session.add(assessment)
        db.session.commit()
        
        flash('考核创建成功')
        return redirect(url_for('admin.assessments'))
    
    # 获取所有可用模板
    templates = AssessmentTemplate.query.all()
    return render_template('admin/new_assessment.html', templates=templates)

@admin_bp.route('/assessors')
@admin_required
def assessors():
    assessors_list = Assessor.query.all()
    return render_template('admin/assessors.html', assessors=assessors_list)

@admin_bp.route('/assessors/import', methods=['GET', 'POST'])
@admin_required
def import_assessors():
    if request.method == 'POST':
        if 'assessors_file' not in request.files:
            flash('没有上传文件')
            return redirect(request.url)
        
        file = request.files['assessors_file']
        if file.filename == '':
            flash('没有选择文件')
            return redirect(request.url)
        
        if file:
            try:
                # 读取Excel文件
                df = pd.read_excel(file)
                
                for _, row in df.iterrows():
                    # 创建用户
                    user = User(
                        username=row['username'],
                        name=row['name'],
                        role='assessor'
                    )
                    user.set_password(row['password'])  # 设置默认密码
                    db.session.add(user)
                    db.session.flush()  # 获取用户ID
                    
                    # 创建考核人
                    assessor = Assessor(
                        user_id=user.id,
                        name=row['name'],
                        group_name=row['group_name'],
                        frequency=row['frequency'],
                        score_weight=row['score_weight']
                    )
                    db.session.add(assessor)
                
                db.session.commit()
                flash('考核人导入成功')
                return redirect(url_for('admin.assessors'))
            
            except Exception as e:
                db.session.rollback()
                flash(f'导入失败: {str(e)}')
    
    return render_template('admin/import_assessors.html')

@admin_bp.route('/assessees')
@admin_required
def assessees():
    assessees_list = Assessee.query.all()
    return render_template('admin/assessees.html', assessees=assessees_list)

@admin_bp.route('/assessees/import', methods=['GET', 'POST'])
@admin_required
def import_assessees():
    if request.method == 'POST':
        if 'assessees_file' not in request.files:
            flash('没有上传文件')
            return redirect(request.url)
        
        file = request.files['assessees_file']
        if file.filename == '':
            flash('没有选择文件')
            return redirect(request.url)
        
        if file:
            try:
                # 读取Excel文件
                df = pd.read_excel(file)
                
                for _, row in df.iterrows():
                    assessee = Assessee(
                        name=row['name'],
                        department=row['department']
                    )
                    db.session.add(assessee)
                
                db.session.commit()
                flash('被考核人导入成功')
                return redirect(url_for('admin.assessees'))
            
            except Exception as e:
                db.session.rollback()
                flash(f'导入失败: {str(e)}')
    
    return render_template('admin/import_assessees.html')

@admin_bp.route('/templates')
@admin_required
def templates():
    """获取所有模板"""
    templates = AssessmentTemplate.query.order_by(AssessmentTemplate.created_at.desc()).all()
    return render_template('admin/templates.html', templates=templates)



@admin_bp.route('/templates/preview', methods=['POST'])
@login_required
def preview_template():
    if 'file' not in request.files:
        return jsonify({'error': '没有选择文件'})
    
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': '无效的文件'})
    
    try:
        # 读取Excel文件
        df = pd.read_excel(file)
        
        # 获取表头和前5行数据
        headers = df.columns.tolist()
        preview_data = df.head().to_dict('records')
        
        return jsonify({
            'headers': headers,
            'data': preview_data,
            'total_rows': len(df)
        })
    except Exception as e:
        return jsonify({'error': f'预览失败：{str(e)}'})

@admin_bp.route('/templates/import', methods=['GET', 'POST'])
@login_required
def import_template():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('没有选择文件')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('没有选择文件')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                # 读取Excel文件
                df = pd.read_excel(file)
                
                # 从Excel表头创建items
                headers = df.columns.tolist()
                items = [
                    {
                        'name': header,
                        'criteria': f'评分标准 - {header}'  # 可以根据需要设置评分标准
                    }
                    for header in headers
                ]
                
                # 创建模板记录
                template = AssessmentTemplate(
                    template_name=os.path.splitext(file.filename)[0],
                    category='imported',
                    items=items
                )
                db.session.add(template)
                db.session.flush()  # 获取模板ID
                
                # 生成正式的数据表名
                table_name = f'template_data_{template.id}'
                template.table_name = table_name
                
                # 创建模板表并保存数据，传入file对象
                create_template_table(table_name, items, file)
                
                # 记录导入信息
                import_record = ImportRecord(
                    file_name=file.filename,
                    table_name=table_name,
                    import_user_id=current_user.id,
                    description=request.form.get('description', '')
                )
                db.session.add(import_record)
                
                db.session.commit()
                flash('模板导入成功！')
                return redirect(url_for('admin.templates'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'导入失败：{str(e)}')
                return redirect(request.url)
    
    return render_template('admin/import_template.html')

def create_template_table(table_name, items, file):
    """创建模板对应的数据表"""
    metadata = MetaData()
    
    # 基础列
    columns = [
        Column('id', Integer, primary_key=True),
        Column('created_at', DateTime, default=datetime.now),
        Column('updated_at', DateTime, default=datetime.now, onupdate=datetime.now)
    ]
    
    # 根据Excel表头动态添加列
    for item in items:
        column_name = item['name'].lower().replace(' ', '_')
        columns.append(Column(
            column_name,  # 直接使用Excel表头作为列名
            String(255),  # 存储考核指标内容
            nullable=True,
            comment=f"{item['name']} - {item['criteria']}"  # 保存原始名称和评分标准
        ))
    
    # 创建表结构
    table = Table(table_name, metadata, *columns)
    
    # 创建表
    metadata.create_all(db.engine)
    
    try:
        # 插入Excel数据
        with db.engine.connect() as conn:
            trans = conn.begin()
            try:
                # 读取Excel文件的数据并插入
                df = pd.read_excel(file)
                for _, row in df.iterrows():
                    # 准备插入数据
                    insert_data = {
                        'created_at': datetime.now(),
                        'updated_at': datetime.now()
                    }
                    # 动态添加每列的值
                    for item in items:
                        column_name = item['name'].lower().replace(' ', '_')
                        insert_data[column_name] = str(row[item['name']])  # 转换为字符串以确保兼容性
                    
                    conn.execute(table.insert().values(**insert_data))
                trans.commit()
            except Exception as e:
                trans.rollback()
                print(f"插入数据失败: {str(e)}")
                raise e
    except Exception as e:
        print(f"创建表或插入数据失败: {str(e)}")
        raise e

    return {
        'table_name': table_name,
        'columns': [col.name for col in columns],
        'item_mapping': {
            item['name']: item['name'].lower().replace(' ', '_')
            for item in items
        }
    }

@admin_bp.route('/templates/new', methods=['GET', 'POST'])
@admin_required
def new_template():
    if request.method == 'POST':
        template_name = request.form.get('template_name')
        category = request.form.get('category')
        
        # 创建模板记录
        template = AssessmentTemplate(
            template_name=template_name,
            category=category
        )
        db.session.add(template)
        db.session.flush()  # 获取模板ID
        
        # 创建独立的模板表
        table_name = f"template_{template.id}"
        items = []
        
        # 处理多级评分项目
        process_template_items(request.form, items)
        
        # 创建模板表并保存数据
        create_template_table(table_name, items)
        template.table_name = table_name
        
        try:
            db.session.commit()
            flash('考核模板创建成功')
            return redirect(url_for('admin.templates'))
        except Exception as e:
            db.session.rollback()
            flash(f'创建失败：{str(e)}')
    
    return render_template('admin/new_template.html')

def process_template_items(form_data, items, parent_id=None, prefix=''):
    """递归处理多级评分项目"""
    item_count = int(form_data.get(f'{prefix}item_count', 0))
    
    for i in range(1, item_count + 1):
        base_key = f'{prefix}item_{i}'
        name = form_data.get(f'{base_key}_name')
        score = float(form_data.get(f'{base_key}_score', 0))
        criteria = form_data.get(f'{base_key}_criteria', '')
        
        if name and score > 0:
            item = {
                'name': name,
                'score': score,
                'criteria': criteria,
                'parent_id': parent_id
            }
            items.append(item)
            
            # 处理子项目
            process_template_items(form_data, items, len(items), f'{base_key}_sub_')

@admin_bp.route('/templates/<int:template_id>')
@admin_required
def view_template(template_id):
    template = AssessmentTemplate.query.get_or_404(template_id)
    return render_template('admin/view_template.html', template=template)

@admin_bp.route('/assessors/new', methods=['GET', 'POST'])
@login_required
def new_assessor():
    if request.method == 'POST':
        # 获取表单数据
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        group_name = request.form.get('group_name')
        frequency = request.form.get('frequency')
        score_weight = request.form.get('score_weight')
        
        # 创建新用户
        user = User(
            username=username,
            name=name,  # 添加 name 字段
            role='assessor'
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # 获取用户ID
        
        # 创建考核人
        assessor = Assessor(
            user_id=user.id,
            name=name,
            group_name=group_name,
            frequency=frequency,
            score_weight=score_weight
        )
        db.session.add(assessor)
        
        try:
            db.session.commit()
            flash('考核人添加成功！')
            return redirect(url_for('admin.assessors'))
        except Exception as e:
            db.session.rollback()
            flash('添加失败，请检查输入信息。')
            return render_template('admin/new_assessor.html')
    
    return render_template('admin/new_assessor.html')

@admin_bp.route('/assessees/new', methods=['GET', 'POST'])
@login_required
def new_assessee():
    if request.method == 'POST':
        # 获取表单数据
        name = request.form.get('name')
        department = request.form.get('department')
        
        # 创建被考核人
        assessee = Assessee(
            name=name,
            department=department
        )
        
        try:
            db.session.add(assessee)
            db.session.commit()
            flash('被考核人添加成功！')
            return redirect(url_for('admin.assessees'))
        except Exception as e:
            db.session.rollback()
            flash('添加失败，请检查输入信息。')
            return render_template('admin/new_assessee.html')
    
    return render_template('admin/new_assessee.html')

@admin_bp.route('/templates/edit/<int:template_id>', methods=['GET', 'POST'])
@login_required
def edit_template(template_id):
    template = AssessmentTemplate.query.get_or_404(template_id)
    
    if request.method == 'POST':
        template_name = request.form.get('template_name')
        items = request.form.getlist('items[]')
        scores = request.form.getlist('scores[]')
        criteria = request.form.getlist('criteria[]')
        
        # 更新模板数据
        template.template_name = template_name
        template.items = [
            {
                'name': item,
                'score': float(score),
                'criteria': crit
            }
            for item, score, crit in zip(items, scores, criteria)
        ]
        
        try:
            db.session.commit()
            flash('模板更新成功！')
            return redirect(url_for('admin.templates'))
        except Exception as e:
            db.session.rollback()
            flash('更新失败：' + str(e))
    
    return render_template('admin/edit_template.html', template=template)

@admin_bp.route('/templates/delete/<int:template_id>', methods=['GET'])
@login_required
def delete_template(template_id):
    template = AssessmentTemplate.query.get_or_404(template_id)
    
    try:
        # 检查是否有考核使用此模板
        if template.assessments:
            flash('无法删除：此模板正在被使用')
            return redirect(url_for('admin.templates'))
            
        db.session.delete(template)
        db.session.commit()
        flash('模板删除成功！')
    except Exception as e:
        db.session.rollback()
        flash('删除失败：' + str(e))
    
    return redirect(url_for('admin.templates'))


# 添加允许的文件扩展名检查函数
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@admin_bp.route('/import-records')
@login_required
def import_records():
    """显示导入记录列表"""
    records = ImportRecord.query.order_by(ImportRecord.import_time.desc()).all()
    return render_template('admin/import_records.html', records=records)

@admin_bp.route('/import-records/<int:record_id>')
@login_required
def view_import_record(record_id):
    """查看单条导入记录详情"""
    record = ImportRecord.query.get_or_404(record_id)
    
    # 获取动态表数据
    table_data = []
    if record.table_name:
        with db.engine.connect() as conn:
            result = conn.execute(f"SELECT * FROM {record.table_name}")
            table_data = [dict(row) for row in result]
    
    return render_template('admin/view_import_record.html', 
                         record=record, 
                         table_data=table_data)

@admin_bp.route('/assessments')
@admin_required
def assessments():
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('keyword', '', type=str).strip()
    department = request.args.get('department', '', type=str).strip()

    query = Assessment.query

    # ✅ 模糊搜索
    if keyword:
        query = query.filter(Assessment.assessment_name.ilike(f'%{keyword}%'))

    # ✅ 部门筛选
    if department:
        query = query.filter(Assessment.department == department)

    # ✅ 分页
    pagination = query.order_by(Assessment.created_at.desc()).paginate(page=page, per_page=10)

    # 获取所有部门选项（去重）
    departments = db.session.query(Assessment.department).distinct().all()
    departments = [d[0] for d in departments if d[0]]

    return render_template('admin/assessments.html',
                           assessments=pagination,
                           keyword=keyword,
                           department=department,
                           departments=departments)

from app.utils.decorators import handle_db_error

@admin_bp.route('/assessments/<int:assessment_id>')
@admin_required
@handle_db_error
def view_assessment(assessment_id):
    """查看考核详情"""
    assessment = Assessment.query.get_or_404(assessment_id)
    records = AssessmentRecord.query.filter_by(assessment_id=assessment_id).all()

    current_assessor = Assessor.query.filter_by(user_id=current_user.id).first()
    if current_assessor:
        current_record = AssessmentRecord.query.filter_by(
            assessment_id=assessment_id,
            assessor_id=current_assessor.id
        ).first()
    else:
        current_record = None

    # ✅ 1. 获取数据库评分项表数据（含 id）
    template_data = []
    try:
        with db.engine.connect() as conn:
            sql = f"SELECT * FROM {assessment.template.table_name}"
            result = conn.execute(db.text(sql))
            template_data = [
                {key: value for key, value in row._mapping.items()}
                for row in result
            ]
    except Exception as e:
        flash('获取评分项失败：' + str(e))
        return redirect(url_for('admin.assessments'))

    # ✅ 2. 遍历记录并取 score_data 的每个分项累加
    processed_records = []
    for record in records:
        score_data = record.score_data or {}
        total_score = 0
        score_details = []

        for item in template_data:
            item_id = str(item['id'])  # 注意，这里才是 score_data 的 key
            actual_score = float(score_data.get(item_id, 0))
            total_score += actual_score
            score_details.append({
                'name': item.get('name', '未知'),
                'score': actual_score,
                'criteria': item.get('criteria', ''),
                'max_score': item.get('score', 0),
            })

        processed_records.append({
            'record': record,
            'score_details': score_details,
            'total_score': total_score
        })

    completed_records = [r for r in processed_records if r['total_score'] > 0]
    stats = {
        'total_records': len(records),
        'completed_records': len(completed_records),
        'average_score': (sum(r['total_score'] for r in completed_records) / len(completed_records)) if completed_records else 0
    }

    can_assess = (
        current_assessor is not None and
        assessment.is_active and
        (current_record is None or not current_record.is_submitted)
    )

    return render_template('admin/view_assessment.html',
                           assessment=assessment,
                           records=processed_records,
                           template_items=template_data,
                           stats=stats,
                           can_assess=can_assess)



# 修复统计分析路由错误

#需要添加统计分析路由和相关模板：

#1. 在 admin.py 中添加统计分析路由：

@admin_bp.route('/statistics')
@admin_required
def statistics():
    """统计分析页面"""
    # 获取统计数据
    stats = {
        'total_assessments': Assessment.query.count(),
        'total_assessors': Assessor.query.count(),
        'total_assessees': Assessee.query.count(),
        'total_records': AssessmentRecord.query.count()
    }
    
    # 获取部门统计
    department_stats = db.session.query(
        Assessment.department,
        db.func.count(Assessment.id).label('count')
    ).group_by(Assessment.department).all()
    
    # 获取最近的评分记录
    recent_records = AssessmentRecord.query.order_by(
        AssessmentRecord.create_time.desc()
    ).limit(10).all()
    
    return render_template('admin/statistics.html',
                         stats=stats,
                         department_stats=department_stats,
                         recent_records=recent_records)


@admin_bp.route('/assessments/<int:assessment_id>/start', methods=['POST'])
@admin_required
@handle_db_error
def start_assessment(assessment_id):
    """开始考核：仅为指定的考核人生成记录"""
    assessment = Assessment.query.get_or_404(assessment_id)

    if assessment.status == 'active':
        flash('该考核已经开始')
        return redirect(url_for('admin.view_assessment', assessment_id=assessment_id))

    # 获取指定考核人（来自 assessment_assessors 关联表）
    assessor_ids = db.session.query(AssessmentAssessor.assessor_id)\
        .filter_by(assessment_id=assessment.id).all()
    assessor_ids = [id for (id,) in assessor_ids]

    if not assessor_ids:
        flash('请先设置考核人后再开始考核', 'warning')
        return redirect(url_for('admin.view_assessment', assessment_id=assessment_id))

    assessors = Assessor.query.filter(Assessor.id.in_(assessor_ids)).all()
    assessees = Assessee.query.filter_by(department=assessment.department).all()

    if not assessees:
        flash('该部门暂无被考核人')
        return redirect(url_for('admin.view_assessment', assessment_id=assessment_id))

    # 获取模板
    template = assessment.template
    if not template:
        flash('考核模板不存在')
        return redirect(url_for('admin.view_assessment', assessment_id=assessment_id))

    count = 0
    for assessor in assessors:
        for assessee in assessees:
            if assessor.id == assessee.id:
                continue  # 不允许自评
            record = AssessmentRecord(
                assessment_id=assessment.id,
                assessor_id=assessor.id,
                assessee_id=assessee.id,
                score_data={},
                status='pending'
            )
            db.session.add(record)
            count += 1

    assessment.status = 'active'
    assessment.start_date = datetime.now()

    try:
        db.session.commit()
        flash(f'考核已开始，共生成 {count} 条记录')
        return redirect(url_for('admin.view_assessment', assessment_id=assessment_id))
    except Exception as e:
        db.session.rollback()
        flash(f'开始考核失败：{str(e)}')
        return redirect(url_for('admin.index'))


@admin_bp.route('/assessors/edit/<int:assessor_id>', methods=['GET', 'POST'])
@admin_required
def edit_assessor(assessor_id):
    """编辑考核人"""
    assessor = Assessor.query.get_or_404(assessor_id)
    
    if request.method == 'POST':
        try:
            # 更新考核人信息
            assessor.name = request.form.get('name')
            assessor.group_name = request.form.get('group_name')
            assessor.frequency = request.form.get('frequency')
            assessor.score_weight = request.form.get('score_weight')
            
            # 同时更新用户名称
            if assessor.user:
                assessor.user.name = request.form.get('name')
            
            db.session.commit()
            flash('考核人信息更新成功！')
            return redirect(url_for('admin.assessors'))
        except Exception as e:
            db.session.rollback()
            flash('更新失败：' + str(e))
            return render_template('admin/edit_assessor.html', assessor=assessor)
    
    # GET 请求，显示编辑表单
    return render_template('admin/edit_assessor.html', assessor=assessor)

@admin_bp.route('/assessors/delete/<int:assessor_id>', methods=['GET'])
@admin_required
def delete_assessor(assessor_id):
    """删除考核人"""
    assessor = Assessor.query.get_or_404(assessor_id)
    
    try:
        # 检查是否有关联的考核记录
        if assessor.records:
            flash('无法删除：此考核人已有考核记录')
            return redirect(url_for('admin.assessors'))
        
        # 删除关联的用户账号
        user = assessor.user
        if user:
            db.session.delete(user)
        
        # 删除考核人
        db.session.delete(assessor)
        db.session.commit()
        flash('考核人删除成功！')
    except Exception as e:
        db.session.rollback()
        flash('删除失败：' + str(e))
    
    return redirect(url_for('admin.assessors'))


@admin_bp.route('/assessees/edit/<int:assessee_id>', methods=['GET', 'POST'])
@admin_required
def edit_assessee(assessee_id):
    """Edit assessee information"""
    assessee = Assessee.query.get_or_404(assessee_id)
    
    if request.method == 'POST':
        try:
            # Update assessee information
            assessee.name = request.form.get('name')
            assessee.department = request.form.get('department')
            assessee.position = request.form.get('position', '')  # Optional field
            
            db.session.commit()
            flash('Successfully updated assessee information!')
            return redirect(url_for('admin.assessees'))
        except Exception as e:
            db.session.rollback()
            flash('Update failed: ' + str(e))
            return render_template('admin/edit_assessee.html', assessee=assessee)
    
    return render_template('admin/edit_assessee.html', assessee=assessee)

@admin_bp.route('/assessees/delete/<int:assessee_id>', methods=['GET'])
@admin_required
def delete_assessee(assessee_id):
    """删除被考核人"""
    assessee = Assessee.query.get_or_404(assessee_id)
    
    try:
        # 检查是否有关联的考核记录
        if assessee.records:
            flash('无法删除：此被考核人已有考核记录')
            return redirect(url_for('admin.assessees'))
        
        # 删除被考核人
        db.session.delete(assessee)
        db.session.commit()
        flash('被考核人删除成功！')
    except Exception as e:
        db.session.rollback()
        flash('删除失败：' + str(e))
        flash('删除失败：' + str(e))
    
    return redirect(url_for('admin.assessees'))

@admin_bp.route('/assessment-records/<int:id>')
@admin_required
@handle_db_error
def view_record(id):
    """查看考核记录详情"""
    # 获取考核记录
    record = AssessmentRecord.query.get_or_404(id)

    
    # 获取考核模板数据
    template = record.assessment.template
    if not template or not template.items:
        flash('考核模板不存在或数据不完整')
        return redirect(url_for('admin.view_assessment', assessment_id=record.assessment_id))
    
    # 获取评分项目数据
    template_data = []
    try:
        with db.engine.connect() as conn:
            sql = f"SELECT * FROM {template.table_name}"
            result = conn.execute(db.text(sql))
            template_data = [
                {key: value for key, value in row._mapping.items()}
                for row in result
            ]
    except Exception as e:
        flash('获取评分数据失败')
        return redirect(url_for('admin.view_assessment', assessment_id=record.assessment_id))

    return render_template('admin/view_record.html', 
                         record=record,
                         template_data=template_data)
    
    @admin_bp.route('/assessment-records/<int:id>/delete', methods=['POST'])
    @admin_required
    @handle_db_error
    def delete_record(id):
        """删除考核记录"""
        record = AssessmentRecord.query.get_or_404(id)
        
        try:
            db.session.delete(record)
            db.session.commit()
            flash('考核记录删除成功！')
        except Exception as e:
            db.session.rollback()
            flash('删除失败：' + str(e))
        
        return redirect(url_for('admin.view_assessment', assessment_id=record.assessment_id))

@admin_bp.route('/assessments/<int:assessment_id>/assign-assessors', methods=['GET', 'POST'])
@admin_required
def assign_assessors(assessment_id):
    """分配考核人并按 group_name 分组显示"""

    assessment = Assessment.query.get_or_404(assessment_id)
    all_assessors = Assessor.query.all()

    if request.method == 'POST':
        # 获取所选考核人 ID 列表
        selected_ids = request.form.getlist('assessor_ids')

        # 删除旧的分配记录
        db.session.query(AssessmentAssessor).filter_by(assessment_id=assessment_id).delete()

        # 新增分配记录
        for aid in selected_ids:
            db.session.add(AssessmentAssessor(assessment_id=assessment_id, assessor_id=int(aid)))

        db.session.commit()
        flash('考核人已保存')
        return redirect(url_for('admin.view_assessment', assessment_id=assessment_id))

    # 查询当前已分配的考核人 ID 列表
    assigned_ids = [a.assessor_id for a in assessment.assigned_assessors]

    # 按 group_name 字段对考核人进行分组（默认“未分组”）
    grouped_assessors = defaultdict(list)
    for assessor in all_assessors:
        group = assessor.group_name or "未分组"
        grouped_assessors[group].append(assessor)

    # 传入模板
    return render_template('admin/assign_assessors.html',
                           assessment=assessment,
                           grouped_assessors=grouped_assessors,
                           assigned_ids=assigned_ids)
