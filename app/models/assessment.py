from app import db
from datetime import datetime

class Assessment(db.Model):
    __tablename__ = 'assessments'
    
    id = db.Column(db.Integer, primary_key=True)
    assessment_name = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(255), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('assessment_templates.id'))
    status = db.Column(db.String(50), default='pending')  # 添加状态字段
    start_date = db.Column(db.DateTime)  # 添加开始时间
    end_date = db.Column(db.DateTime)  # 添加结束时间
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    template = db.relationship('AssessmentTemplate', backref='assessments')
    records = db.relationship('AssessmentRecord', backref='assessment', lazy=True)
    assigned_assessors = db.relationship(
        'AssessmentAssessor',
        backref='assessment',
        cascade='all, delete-orphan'
    )    

class Assessor(db.Model):
    __tablename__ = 'assessors'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    group_name = db.Column(db.String(255), nullable=False)
    frequency = db.Column(db.Enum('monthly', 'quarterly'), nullable=False)
    score_weight = db.Column(db.Numeric(5, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='assessor_profile', uselist=False)
    records = db.relationship('AssessmentRecord', backref='assessor', lazy=True)

class Assessee(db.Model):
    __tablename__ = 'assessees'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(255), nullable=False)
    parent_department = db.Column(db.String(100), comment='上级部门')
    position = db.Column(db.String(100), comment='岗位')
    status = db.Column(db.String(50), comment='人员状态')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    records = db.relationship('AssessmentRecord', backref='assessee', lazy=True)

class AssessmentRecord(db.Model):
    __tablename__ = 'assessment_records'
    
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id'), nullable=False)
    assessor_id = db.Column(db.Integer, db.ForeignKey('assessors.id'), nullable=False)
    assessee_id = db.Column(db.Integer, db.ForeignKey('assessees.id'), nullable=False)
    score_data = db.Column(db.JSON, nullable=False)
    photo_url = db.Column(db.String(500))
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # 添加状态字段
    
    def get_score_data(self):
        return self.score_data
    
    def set_score_data(self, data):
        if not isinstance(data, dict):
            raise ValueError('score_data must be a dictionary')
        self.score_data = data
    
    def get_total_score(self):
        data = self.get_score_data()
        if not data:
            return 0
        total = 0
        for item in data.values():
            if isinstance(item, (int, float)):
                total += float(item)
        return total

# 在现有模型文件中添加 AssessmentTemplate 类
class AssessmentTemplate(db.Model):
    __tablename__ = 'assessment_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    template_name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100))  # 模板分类
    table_name = db.Column(db.String(100))  # 对应的评分项目表名
    items = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_items(self):
        return self.items


class ImportRecord(db.Model):
    """导入记录模型"""
    __tablename__ = 'import_records'
    
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(255), nullable=False)
    table_name = db.Column(db.String(255), nullable=False, unique=True)
    import_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    import_time = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)
    
    # 关联关系
    import_user = db.relationship('User', backref='import_records')
 
class AssessmentAssessor(db.Model):
    __tablename__ = 'assessment_assessors'

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id'), nullable=False)
    assessor_id = db.Column(db.Integer, db.ForeignKey('assessors.id'), nullable=False)

    # 可选：建立 assessor 对象引用（便于取 name）
    assessor = db.relationship('Assessor', backref='assigned_tasks')
