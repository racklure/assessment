from datetime import datetime
from . import db

class AssessorGroup(db.Model):
    """考核人分组"""
    __tablename__ = 'assessor_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String(100), nullable=False)
    frequency = db.Column(db.String(20), nullable=False)  # monthly, quarterly, yearly
    score_weight = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Assessor(db.Model):
    """考核人"""
    __tablename__ = 'assessors'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('assessor_group.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='assessor', uselist=False)
    group = db.relationship('AssessorGroup', backref='assessors')
    department = db.relationship('Department', backref='assessors')

class AssessorAssessee(db.Model):
    """考核人与被考核人关联"""
    __tablename__ = 'assessor_assessees'
    
    id = db.Column(db.Integer, primary_key=True)
    assessor_id = db.Column(db.Integer, db.ForeignKey('assessor.id'), nullable=False)
    assessee_id = db.Column(db.Integer, db.ForeignKey('assessee.id'), nullable=False)
    
    assessor = db.relationship('Assessor', backref='assessee_links')
    assessee = db.relationship('Assessee', backref='assessor_links')