from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from app.models.assessment import Assessment, Assessor, Assessee, AssessmentRecord
from app import db
import pandas as pd
import json
from io import BytesIO
from datetime import datetime

statistics_bp = Blueprint('statistics', __name__, url_prefix='/statistics')

@statistics_bp.route('/')
@login_required
def index():
    # 获取所有考核
    assessments = Assessment.query.all()
    
    # 获取所有部门
    departments = db.session.query(Assessment.department).distinct().all()
    departments = [d[0] for d in departments]
    
    return render_template('statistics/index.html', 
                          assessments=assessments,
                          departments=departments)

@statistics_bp.route('/assessment/<int:assessment_id>')
@login_required
def assessment_statistics(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    
    # 获取该考核的所有记录
    records = AssessmentRecord.query.filter_by(assessment_id=assessment_id).all()
    
    # 按被考核人分组统计
    assessee_stats = {}
    for record in records:
        assessee_id = record.assessee_id
        if assessee_id not in assessee_stats:
            assessee_stats[assessee_id] = {
                'name': record.assessee.name,
                'department': record.assessee.department,
                'records': [],
                'total_score': 0,
                'avg_score': 0
            }
        
        # 解析分数数据
        score_data = json.loads(record.score_data)
        total_score = sum(float(score) for score in score_data.values())
        
        assessee_stats[assessee_id]['records'].append({
            'assessor_name': record.assessor.name,
            'score': total_score,
            'date': record.create_time
        })
        
        assessee_stats[assessee_id]['total_score'] += total_score
    
    # 计算平均分
    for assessee_id, stats in assessee_stats.items():
        if len(stats['records']) > 0:
            stats['avg_score'] = stats['total_score'] / len(stats['records'])
    
    return render_template('statistics/assessment_statistics.html',
                          assessment=assessment,
                          assessee_stats=assessee_stats)

@statistics_bp.route('/quarterly')
@login_required
def quarterly_statistics():
    # 获取年份和季度参数
    year = request.args.get('year', datetime.now().year)
    quarter = request.args.get('quarter', (datetime.now().month - 1) // 3 + 1)
    
    # 计算季度的开始和结束月份
    start_month = (quarter - 1) * 3 + 1
    end_month = quarter * 3
    
    # 获取该季度的所有记录
    records = AssessmentRecord.query.filter(
        db.extract('year', AssessmentRecord.create_time) == year,
        db.extract('month', AssessmentRecord.create_time) >= start_month,
        db.extract('month', AssessmentRecord.create_time) <= end_month
    ).all()
    
    # 按月份和被考核人分组统计
    monthly_stats = {}
    for month in range(start_month, end_month + 1):
        monthly_stats[month] = {}
        
        # 筛选当月记录
        month_records = [r for r in records if r.create_time.month == month]
        
        for record in month_records:
            assessee_id = record.assessee_id
            if assessee_id not in monthly_stats[month]:
                monthly_stats[month][assessee_id] = {
                    'name': record.assessee.name,
                    'department': record.assessee.department,
                    'records': [],
                    'total_score': 0,
                    'avg_score': 0
                }
            
            # 解析分数数据
            score_data = json.loads(record.score_data)
            total_score = sum(float(score) for score in score_data.values())
            
            monthly_stats[month][assessee_id]['records'].append({
                'assessor_name': record.assessor.name,
                'score': total_score,
                'date': record.create_time
            })
            
            monthly_stats[month][assessee_id]['total_score'] += total_score
    
    # 计算每月平均分
    for month, assessees in monthly_stats.items():
        for assessee_id, stats in assessees.items():
            if len(stats['records']) > 0:
                stats['avg_score'] = stats['total_score'] / len(stats['records'])
    
    # 计算季度平均分
    quarterly_stats = {}
    for month, assessees in monthly_stats.items():
        for assessee_id, stats in assessees.items():
            if assessee_id not in quarterly_stats:
                quarterly_stats[assessee_id] = {
                    'name': stats['name'],
                    'department': stats['department'],
                    'monthly_scores': {},
                    'quarterly_avg': 0
                }
            
            quarterly_stats[assessee_id]['monthly_scores'][month] = stats['avg_score']
    
    # 计算季度平均分
    for assessee_id, stats in quarterly_stats.items():
        monthly_scores = stats['monthly_scores'].values()
        if monthly_scores:
            stats['quarterly_avg'] = sum(monthly_scores) / len(monthly_scores)
    
    return render_template('statistics/quarterly_statistics.html',
                          year=year,
                          quarter=quarter,
                          monthly_stats=monthly_stats,
                          quarterly_stats=quarterly_stats)

@statistics_bp.route('/export/<int:assessment_id>')
@login_required
def export_assessment(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    
    # 获取该考核的所有记录
    records = AssessmentRecord.query.filter_by(assessment_id=assessment_id).all()
    
    # 创建数据框
    data = []
    for record in records:
        score_data = json.loads(record.score_data)
        row = {
            '考核名称': assessment.assessment_name,
            '考核部门': assessment.department,
            '考核人': record.assessor.name,
            '被考核人': record.assessee.name,
            '被考核人部门': record.assessee.department,
            '考核日期': record.create_time.strftime('%Y-%m-%d'),
            '总分': sum(float(score) for score in score_data.values())
        }
        
        # 添加各项分数
        for item_id, score in score_data.items():
            row[f'项目{item_id}'] = score
        
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # 创建Excel文件
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='考核数据', index=False)
    
    output.seek(0)
    
    # 生成文件名
    filename = f"{assessment.assessment_name}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@statistics_bp.route('/export_quarterly')
@login_required
def export_quarterly():
    # 获取年份和季度参数
    year = request.args.get('year', datetime.now().year)
    quarter = request.args.get('quarter', (datetime.now().month - 1) // 3 + 1)
    
    # 计算季度的开始和结束月份
    start_month = (quarter - 1) * 3 + 1
    end_month = quarter * 3
    
    # 获取该季度的所有记录
    records = AssessmentRecord.query.filter(
        db.extract('year', AssessmentRecord.create_time) == year,
        db.extract('month', AssessmentRecord.create_time) >= start_month,
        db.extract('month', AssessmentRecord.create_time) <= end_month
    ).all()
    
    # 按月份和被考核人分组统计
    data = []
    for record in records:
        score_data = json.loads(record.score_data)
        total_score = sum(float(score) for score in score_data.values())
        
        row = {
            '年份': year,
            '季度': quarter,
            '月份': record.create_time.month,
            '考核人': record.assessor.name,
            '被考核人': record.assessee.name,
            '被考核人部门': record.assessee.department,
            '考核日期': record.create_time.strftime('%Y-%m-%d'),
            '总分': total_score
        }
        
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # 计算季度平均分
    quarterly_avg = df.groupby(['被考核人', '被考核人部门'])['总分'].mean().reset_index()
    quarterly_avg.rename(columns={'总分': '季度平均分'}, inplace=True)
    
    # 创建Excel文件
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='月度考核数据', index=False)
        quarterly_avg.to_excel(writer, sheet_name='季度平均分', index=False)
    
    output.seek(0)
    
    # 生成文件名
    filename = f"{year}年第{quarter}季度考核统计_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )