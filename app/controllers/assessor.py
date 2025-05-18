from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app,abort
from flask_login import login_required, current_user
from app.models.assessment import Assessment, Assessor, Assessee, AssessmentRecord
from app.models.user import User
from app import db
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import json
import uuid
from app.utils.decorators import handle_db_error

assessor_bp = Blueprint('assessor', __name__, url_prefix='/assessor')

def assessor_required(f):
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:  # 先检查是否已登录
            flash('请先登录')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_assessor():  # 再检查是否是考核人
            flash('您没有权限访问此页面')
            return redirect(url_for('index'))
            
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@assessor_bp.route('/')
@assessor_bp.route('/dashboard')
@assessor_required
def dashboard():
    """考核人仪表盘：仅展示当前考核人参与的考核任务"""
    assessor = Assessor.query.filter_by(user_id=current_user.id).first()
    if not assessor:
        flash('无法访问考核人页面')
        return redirect(url_for('index'))

    # ✅ 获取当前考核人参与的考核记录中所有考核任务 ID
    assessment_ids = db.session.query(AssessmentRecord.assessment_id).filter_by(
        assessor_id=assessor.id
    ).distinct().all()

    # 提取 assessment_id 值
    assessment_ids = [id for (id,) in assessment_ids]

    # ✅ 仅获取“该考核人有参与的 + 状态为 active 的”考核任务
    assessments = Assessment.query.filter(
        Assessment.id.in_(assessment_ids),
        Assessment.status == 'active'
    ).all()

    # ✅ 获取当前考核人最近的完成记录（最多10条）
    completed_records = AssessmentRecord.query.filter_by(
        assessor_id=assessor.id
    ).filter(AssessmentRecord.status == 'completed')\
     .order_by(AssessmentRecord.create_time.desc()).limit(10).all()

    return render_template('assessor/dashboard.html',
                         assessments=assessments,
                         completed_records=completed_records)


@assessor_bp.route('/assessment/<int:assessment_id>')
@assessor_required
@handle_db_error
def assessment_detail(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    current_assessor = Assessor.query.filter_by(user_id=current_user.id).first()
    
    # 获取所有待评估的人员
    assessees = Assessee.query.join(
        AssessmentRecord,
        AssessmentRecord.assessee_id == Assessee.id
    ).filter(
        AssessmentRecord.assessment_id == assessment_id,
        AssessmentRecord.assessor_id == current_assessor.id,
        AssessmentRecord.status == 'pending'  # 只获取待评估的记录
    ).all()
    
    # 获取当前考核人的所有评估记录
    records = AssessmentRecord.query.filter_by(
        assessment_id=assessment_id,
        assessor_id=current_assessor.id,
        status='completed'  # 只获取已完成的记录
    ).all()
    
    # 创建评估记录字典，方便在模板中查找
    records_dict = {
        record.assessee_id: record 
        for record in records
    }
    
    return render_template('assessor/assessment_detail.html',
                         assessment=assessment,
                         assessees=assessees,
                         records_dict=records_dict)

@assessor_bp.route('/assessment/<int:assessment_id>/evaluate/<int:assessee_id>', methods=['GET', 'POST'])
@assessor_required
@handle_db_error
def evaluate(assessment_id, assessee_id):
    try:
        # 1. 基础验证
        assessment = Assessment.query.get_or_404(assessment_id)
        assessor = Assessor.query.filter_by(user_id=current_user.id).first()
        assessee = Assessee.query.get_or_404(assessee_id)
        
        # 2. 检查评估状态
        # 检查是否存在待评估记录
        pending_record = AssessmentRecord.query.filter_by(
            assessment_id=assessment_id,
            assessor_id=assessor.id,
            assessee_id=assessee_id,
            status='pending'
        ).first()
        
        if not pending_record:
            flash('找不到待评估记录')
            return redirect(url_for('assessor.assessment_detail', assessment_id=assessment_id))
        
        # 3. 获取考核模板
        template = assessment.template
        if not template or not template.items:
            flash('考核模板不存在或数据不完整')
            return redirect(url_for('assessor.assessment_detail', assessment_id=assessment_id))
            
        try:
            # 解析模板项目
            if isinstance(template.items, list):
                template_items = template.items
            else:
                template_items = json.loads(template.items)
        except json.JSONDecodeError:
            flash('考核模板数据格式错误')
            return redirect(url_for('assessor.assessment_detail', assessment_id=assessment_id))
        
        # 4. 获取评分项目数据
        template_data = []
        try:
            with db.engine.connect() as conn:
                sql = f"SELECT * FROM {template.table_name}"
                result = conn.execute(db.text(sql))
                template_data = [
                    {key: value for key, value in row._mapping.items()}
                    for row in result
                ]
                
                if not template_data:
                    flash('考核模板数据为空')
                    return redirect(url_for('assessor.assessment_detail', assessment_id=assessment_id))
                    
        except Exception as e:
            flash('获取考核表数据失败')
            return redirect(url_for('assessor.assessment_detail', assessment_id=assessment_id))
        
        # 5. 处理评分提交
        if request.method == 'POST':
            # 评分数据收集
            score_data = {}
            for item in template_data:
                score_value = request.form.get(f'score_{item["id"]}')
                if score_value:
                    score_data[str(item['id'])] = float(score_value)

            # 图片上传处理
            photos = request.files.getlist('photos')
            print(f"收到 {len(photos)} 张照片")

            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)

            photo_urls = []
            for photo in photos:
                print(f"文件名: {photo.filename}, 类型: {photo.content_type}, 大小: {photo.content_length}")
                if photo and photo.filename:
                    filename = f"{uuid.uuid4().hex}_{secure_filename(photo.filename)}"
                    save_path = os.path.join(upload_folder, filename)
                    photo.save(save_path)
                    photo_urls.append(f'/static/uploads/{filename}')
                    print(f"已保存：{save_path}")



            # 更新记录
            pending_record.score_data = score_data
            pending_record.photo_url = ';'.join(photo_urls)  # 或 json.dumps(photo_urls) 如果你愿意
            pending_record.status = 'completed'
            pending_record.create_time = datetime.utcnow()

            db.session.commit()
            flash('评估提交成功')
            return redirect(url_for('assessor.assessment_detail', assessment_id=assessment_id))

        
        # 6. 显示评估页面
        return render_template('assessor/evaluate.html',
                             assessment=assessment,
                             assessor=assessor,
                             assessee=assessee,
                             template_items=template_items,
                             template_data=template_data)
                             
    except Exception as e:
        current_app.logger.error(f'评估页面加载失败：{str(e)}')
        flash('数据库操作错误，请稍后重试')
        return redirect(url_for('assessor.dashboard'))
        
@assessor_bp.route('/record/<int:record_id>')
@login_required
def view_record(record_id):
    record = AssessmentRecord.query.get_or_404(record_id)

    # 获取当前考核人对象
    assessor = Assessor.query.filter_by(user_id=current_user.id).first()
    if not assessor or record.assessor_id != assessor.id:
        abort(403)

    # 获取模板表格数据
    template_data = []
    try:
        if record.assessment.template:
            table_name = record.assessment.template.table_name
            with db.engine.connect() as conn:
                sql = f"SELECT * FROM {table_name}"
                result = conn.execute(db.text(sql))
                template_data = [
                    {key: value for key, value in row._mapping.items()}
                    for row in result
                ]
    except Exception as e:
        current_app.logger.warning(f"读取模板表失败: {e}")

    return render_template(
        'assessor/view_record.html',
        record=record,
        template_data=template_data
    )
