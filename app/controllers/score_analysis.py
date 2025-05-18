from flask import Blueprint, jsonify, render_template, request, send_file, current_app
from sqlalchemy import extract
from datetime import datetime
from collections import defaultdict
from app.models.assessment import AssessmentRecord, Assessee, Assessor
from app import db
import io
import pandas as pd
import unicodedata

# 标准化字符串：全角转半角 + 去空格 + 去换行
def normalize(text):
    return unicodedata.normalize('NFKC', str(text)).strip().replace(' ', '').replace('\n', '')

score_analysis_bp = Blueprint('score_analysis', __name__, url_prefix='/summary')


@score_analysis_bp.route('/star_summary_view')
def star_summary_view():
    return render_template('admin/score_analysis.html')


@score_analysis_bp.route('/quarter', methods=['GET'])
def quarterly_star_summary():
    now = datetime.utcnow()
    year = int(request.args.get('year', now.year))
    quarter = int(request.args.get('quarter', (now.month - 1) // 3 + 1))
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 2

    records = (
        db.session.query(AssessmentRecord)
        .filter(
            extract('year', AssessmentRecord.create_time) == year,
            extract('month', AssessmentRecord.create_time).between(start_month, end_month),
            AssessmentRecord.status == 'completed'
        )
        .all()
    )

    score_map = defaultdict(lambda: defaultdict(list))
    weight_map = defaultdict(lambda: defaultdict(list))
    assessee_info = {}

    # 全局映射：group_name ➜ 角色名
    group_role_map = {}

    for record in records:
        g = normalize(record.assessor.group_name)
        d = normalize(record.assessee.department)
        if g == d:
            group_role_map[g] = '店长'

    all_roles = set()

    for record in records:
        assessee = record.assessee
        assessor = record.assessor
        if not assessee or not assessor:
            continue

        group_name = normalize(assessor.group_name)
        department = normalize(assessee.department)
        role = group_role_map.get(group_name, group_name)

        score = record.get_total_score()
        weight = float(assessor.score_weight or 0)

        score_map[assessee.id][role].append(score)
        weight_map[assessee.id][role].append(weight)
        all_roles.add(role)

        if assessee.id not in assessee_info:
            assessee_info[assessee.id] = {
                '地区': assessee.department.strip(),
                '部门': assessee.parent_department.strip(),
                '岗位': assessee.position.strip(),
                '姓名': assessee.name.strip()
            }

    # 平均权重（百分转小数）
    role_weight_avg = {}
    for role in all_roles:
        all_weights = []
        for aid in weight_map:
            all_weights += weight_map[aid].get(role, [])
        avg_weight = round(sum(all_weights) / len(all_weights), 4) / 100 if all_weights else 0.0
        role_weight_avg[role] = avg_weight

    sorted_roles = sorted(all_roles, key=lambda r: role_weight_avg.get(r, 0.0))

    base_columns = ['地区', '部门', '岗位', '姓名']
    dynamic_columns = [f'{role}打分（{int(role_weight_avg[role]*100)}%）' for role in sorted_roles]
    columns = base_columns + dynamic_columns + ['综合得分', '排名']

    results = []

    for aid, info in assessee_info.items():
        entry = {col: info[col] for col in base_columns}
        total_score = 0.0

        for role in sorted_roles:
            col_label = f'{role}打分（{int(role_weight_avg[role]*100)}%）'
            scores = score_map[aid].get(role, [])
            avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
            weight = role_weight_avg.get(role, 0.0)
            weighted_score = round(avg_score * weight, 2)
            entry[col_label] = f"{avg_score} / {weighted_score}"
            total_score += weighted_score

        entry['综合得分'] = round(total_score, 2)
        results.append(entry)

    grouped = defaultdict(list)
    for item in results:
        key = f"{item['地区']}|{item['部门']}"
        grouped[key].append(item)

    final_output = []
    for group in grouped.values():
        group.sort(key=lambda x: x['综合得分'], reverse=True)
        for idx, item in enumerate(group, start=1):
            item['排名'] = idx
            final_output.append(item)

    return jsonify({
        'code': 200,
        'columns': columns,
        'data': final_output
    })


@score_analysis_bp.route('/export_excel', methods=['GET'])
def export_excel():
    now = datetime.utcnow()
    year = int(request.args.get('year', now.year))
    quarter = int(request.args.get('quarter', (now.month - 1) // 3 + 1))

    # ✅ 修复：使用 current_app 代替 Blueprint
    with current_app.test_request_context(f'/quarter?year={year}&quarter={quarter}'):
        resp = quarterly_star_summary()
        res = resp.get_json()
        data = res.get('data', [])
        columns = res.get('columns', [])

    df = pd.DataFrame(data)
    df = df[columns]

    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    filename = f"服务明星汇总表-{year}-Q{quarter}.xlsx"
    return send_file(
        output,
        download_name=filename,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
