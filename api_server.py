# -*- coding: utf-8 -*-
"""
人脸识别签到系统 - Flask API 服务端
提供RESTful API供移动端调用，同时提供Web管理界面
"""
import os
import io
import json
import pickle
import base64
import logging
import traceback
import threading
from datetime import datetime, date, timedelta
from functools import wraps

from flask import Flask, request, jsonify, send_from_directory, send_file, render_template
from flask_cors import CORS

import cv2
import numpy as np

import config
from database import db

logger = logging.getLogger(__name__)

app = Flask(__name__,
            template_folder=os.path.join(config.RESOURCE_DIR, 'templates'),
            static_folder=os.path.join(config.RESOURCE_DIR, 'static'))

CORS(app, resources={r"/api/*": {"origins": config.CORS_ORIGINS}})

# 内存签到记录（模块级初始化，确保随时可用）
app._attendance_records = []
app._attendance_id_counter = 0

# ==================== 工具函数 ====================

def success_response(data=None, message="success"):
    """成功响应"""
    resp = {"success": True, "code": 200, "message": message}
    if data is not None:
        resp["data"] = data
    return jsonify(resp)

def error_response(message="error", code=400):
    """错误响应"""
    return jsonify({"success": False, "code": code, "message": message}), code

def get_params():
    """获取请求参数 (兼容JSON和表单)"""
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()

def get_ip():
    """获取客户端IP"""
    return request.remote_addr or "unknown"


# ==================== 认证装饰器 ====================

def require_auth(f):
    """简单密码认证 - 仅用于敏感操作"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        password = db.get_setting('admin_password', 'admin123')

        # 如果未提供认证信息，允许访问（用于手机端无密码模式）
        if not auth:
            return f(*args, **kwargs)

        # 如果提供了认证信息，则验证
        if auth.startswith('Bearer '):
            token = auth[7:]
            if token != password:
                return error_response("认证失败", 401)

        return f(*args, **kwargs)
    return decorated


# ==================== 认证接口 ====================

@app.route('/api/auth/login', methods=['POST'])
def login():
    """登录认证"""
    params = get_params()
    password = params.get('password', '')

    stored_password = db.get_setting('admin_password', 'admin123')

    if password == stored_password:
        return success_response({
            "token": stored_password,
            "system_name": db.get_setting('system_name', '人脸识别签到系统')
        })
    return error_response("密码错误", 401)


@app.route('/api/auth/change-password', methods=['POST'])
@require_auth
def change_password():
    """修改密码"""
    params = get_params()
    old_password = params.get('old_password', '')
    new_password = params.get('new_password', '')

    stored = db.get_setting('admin_password', 'admin123')
    if old_password != stored:
        return error_response("原密码错误")

    if len(new_password) < 4:
        return error_response("新密码至少4位")

    db.update_setting('admin_password', new_password)
    db.add_log("change_password", "修改管理员密码", ip_address=get_ip())
    return success_response(message="密码修改成功")


# ==================== 人员管理接口 ====================

@app.route('/api/persons', methods=['GET'])
@require_auth
def get_persons():
    """获取人员列表"""
    search = request.args.get('search', '')
    department = request.args.get('department', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    include_inactive = request.args.get('include_inactive', '0') == '1'

    persons, total = db.get_all_persons(
        include_inactive=include_inactive,
        search=search,
        department=department,
        page=page,
        per_page=per_page
    )

    # 不返回人脸编码数据 (太大)
    result_persons = []
    for p in persons:
        rp = {k: v for k, v in p.items() if k != 'face_encoding'}
        rp['has_face'] = p.get('face_encoding') is not None
        result_persons.append(rp)

    return success_response({
        "persons": result_persons,
        "total": total,
        "page": page,
        "per_page": per_page
    })


@app.route('/api/persons/<int:person_id>', methods=['GET'])
@require_auth
def get_person(person_id):
    """获取单个人员详情"""
    person = db.get_person(person_id)
    if not person:
        return error_response("人员不存在", 404)

    result = {k: v for k, v in person.items() if k != 'face_encoding'}
    result['has_face'] = person.get('face_encoding') is not None
    return success_response(result)


@app.route('/api/persons', methods=['POST'])
@require_auth
def add_person():
    """添加人员 - 简化版：只保留姓名和手机号"""
    params = get_params()

    name = params.get('name', '').strip()
    if not name:
        return error_response("姓名不能为空")

    person_id = db.add_person(
        name=name,
        phone=params.get('phone', ''),
        remark=params.get('remark', '')  # 手机号作为备注
    )

    db.add_log("add_person", f"添加人员: {name} (ID={person_id})", ip_address=get_ip())
    return success_response({"person_id": person_id}, "添加成功")


@app.route('/api/persons/<int:person_id>', methods=['PUT'])
@require_auth
def update_person(person_id):
    """更新人员信息"""
    person = db.get_person(person_id)
    if not person:
        return error_response("人员不存在", 404)

    params = get_params()
    update_fields = {}
    for field in ['name', 'phone', 'remark']:  # 只保留这3个字段
        if field in params:
            update_fields[field] = params[field]

    if update_fields:
        db.update_person(person_id, **update_fields)
        db.add_log("update_person", f"更新人员 ID={person_id}: {update_fields}", ip_address=get_ip())

    return success_response(message="更新成功")


@app.route('/api/persons/<int:person_id>', methods=['DELETE'])
@require_auth
def delete_person(person_id):
    """删除人员"""
    person = db.get_person(person_id)
    if not person:
        return error_response("人员不存在", 404)

    hard = request.args.get('hard', '0') == '1'
    if hard:
        db.hard_delete_person(person_id)
        db.add_log("hard_delete_person", f"彻底删除人员: {person['name']} (ID={person_id})", ip_address=get_ip())
    else:
        db.delete_person(person_id)
        db.add_log("delete_person", f"删除人员: {person['name']} (ID={person_id})", ip_address=get_ip())

    return success_response(message="删除成功")


@app.route('/api/persons/<int:person_id>/face', methods=['POST'])
@require_auth
def register_face(person_id):
    """注册人脸 (上传图片)"""
    person = db.get_person(person_id)
    if not person:
        return error_response("人员不存在", 404)

    if 'image' not in request.files:
        return error_response("请上传图片")

    file = request.files['image']
    if file.filename == '':
        return error_response("未选择文件")

    # 保存图片
    import uuid
    ext = os.path.splitext(file.filename)[1] or '.jpg'
    filename = f"{person_id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(config.FACES_DIR, filename)
    file.save(filepath)

    # 提取人脸编码（直接用face_recognition模块函数，不碰共享的face_engine实例）
    try:
        import face_recognition
        import numpy as np

        image = face_recognition.load_image_file(filepath)
        face_locations = face_recognition.face_locations(image)

        if not face_locations:
            os.remove(filepath)
            return error_response("图片中未检测到人脸，请使用正面清晰照片")

        # 取最大的人脸
        if len(face_locations) > 1:
            areas = [(r - t) * (b - l) for t, r, b, l in face_locations]
            best_idx = int(np.argmax(areas))
            face_locations = [face_locations[best_idx]]

        encoding = face_recognition.face_encodings(image, face_locations)[0]

        if encoding is None:
            os.remove(filepath)
            return error_response("人脸编码提取失败")

        encoding_blob = pickle.dumps(encoding)
        db.update_person(person_id, face_encoding=encoding_blob, face_image_path=filepath)

        # 重新加载人脸到运行中的引擎
        try:
            engine = getattr(app, '_face_engine', None)
            if engine:
                persons = db.get_persons_with_encoding()
                engine.load_known_faces(persons)
                logger.info(f"人脸注册成功并已重新加载: {person['name']} (ID={person_id})")
        except Exception as e:
            logger.error(f"重新加载人脸失败: {e}")

        db.add_log("register_face", f"注册人脸: {person['name']} (ID={person_id})", ip_address=get_ip())

        return success_response({
            "person_id": person_id,
            "face_image": filename
        }, "人脸注册成功")

    except Exception as e:
        logger.error(f"人脸注册失败: {e}")
        return error_response(f"人脸注册失败: {str(e)}")


@app.route('/api/persons/<int:person_id>/face', methods=['DELETE'])
@require_auth
def delete_face(person_id):
    """删除人脸数据"""
    person = db.get_person(person_id)
    if not person:
        return error_response("人员不存在", 404)

    # 删除图片文件
    if person.get('face_image_path') and os.path.exists(person['face_image_path']):
        os.remove(person['face_image_path'])

    db.update_person(person_id, face_encoding=None, face_image_path=None)
    db.add_log("delete_face", f"删除人脸: {person['name']} (ID={person_id})", ip_address=get_ip())
    return success_response(message="人脸数据已删除")


@app.route('/api/persons/<int:person_id>/photo', methods=['GET'])
@require_auth
def get_person_photo(person_id):
    """获取人员照片"""
    person = db.get_person(person_id)
    if not person or not person.get('face_image_path'):
        return error_response("照片不存在", 404)

    filepath = person['face_image_path']
    if not os.path.exists(filepath):
        return error_response("照片文件不存在", 404)

    return send_file(filepath)


@app.route('/api/persons/batch-status', methods=['PUT'])
@require_auth
def batch_update_person_status():
    """批量启用/禁用人员"""
    params = get_params()
    ids = params.get('ids', [])
    status = int(params.get('status', 1))

    if not ids or not isinstance(ids, list):
        return error_response("请提供人员ID列表")

    db.batch_update_person_status(ids, status)
    action = "启用" if status == 1 else "禁用"
    db.add_log("batch_update_status", f"批量{action}人员: {ids}", ip_address=get_ip())
    return success_response(message=f"已{action} {len(ids)} 人")


@app.route('/api/persons/clear-all', methods=['DELETE'])
@require_auth
def clear_all_persons():
    """清空所有人员和人脸数据"""
    try:
        with db.get_connection() as conn:
            conn.execute("DELETE FROM attendance")
            conn.execute("DELETE FROM persons")
        # 清理人脸图片文件
        import shutil
        if os.path.exists(config.FACES_DIR):
            shutil.rmtree(config.FACES_DIR)
            os.makedirs(config.FACES_DIR, exist_ok=True)
        # 重置人脸引擎
        face_engine = getattr(app, '_face_engine', None)
        if face_engine:
            face_engine.load_known_faces([])
        db.add_log("clear_all", "清空所有人员和签到数据", ip_address=get_ip())
        return success_response(message="所有数据已清空")
    except Exception as e:
        logger.error(f"清空数据失败: {e}")
        return error_response(f"清空失败: {str(e)}")


# ==================== 签到记录接口 ====================

@app.route('/api/attendance/today', methods=['GET'])
@require_auth
def get_today_attendance():
    """获取今日签到记录"""
    target_date = request.args.get('date', date.today().isoformat())
    records = [r for r in app._attendance_records if r["sign_time"].startswith(target_date)]
    return success_response({"records": records, "date": target_date})


@app.route('/api/attendance', methods=['GET'])
@require_auth
def get_attendance():
    """查询签到记录 (按日期范围)"""
    start_date = request.args.get('start_date', date.today().isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    person_id = request.args.get('person_id', '')

    records = [r for r in app._attendance_records
               if start_date <= r["sign_time"][:10] <= end_date]
    if person_id:
        records = [r for r in records if r["person_id"] == int(person_id)]

    return success_response({"records": records, "total": len(records)})


@app.route('/api/attendance/manual', methods=['POST'])
@require_auth
def manual_sign():
    """手动签到/签退"""
    params = get_params()
    person_id = params.get('person_id')
    sign_type = params.get('sign_type', 'in')
    remark = params.get('remark', '')

    if not person_id:
        return error_response("请指定人员ID")

    person = db.get_person(int(person_id))
    if not person:
        return error_response("人员不存在")

    record, err = add_attendance_record(
        person_id=int(person_id),
        name=person['name'],
        phone=person.get('phone', ''),
        sign_type=sign_type,
        remark=remark or "手动签到"
    )
    if err:
        return error_response(err)

    db.add_log("manual_sign", f"手动签到: {person['name']} ({sign_type})", ip_address=get_ip())
    return success_response({"record_id": record["id"]}, f"{person['name']} {'签到' if sign_type == 'in' else '签退'}成功 第{record['sign_index']}次")


@app.route('/api/attendance/<int:record_id>', methods=['DELETE'])
@require_auth
def delete_attendance(record_id):
    """删除签到记录"""
    before = len(app._attendance_records)
    app._attendance_records = [r for r in app._attendance_records if r["id"] != record_id]
    if len(app._attendance_records) == before:
        return error_response("记录不存在")
    return success_response(message="记录已删除")


@app.route('/api/attendance/batch-delete', methods=['POST'])
@require_auth
def batch_delete_attendance():
    """批量删除签到记录"""
    params = get_params()
    ids = params.get('ids', [])
    if not ids or not isinstance(ids, list):
        return error_response("请提供记录ID列表")
    id_set = set(int(i) for i in ids)
    app._attendance_records = [r for r in app._attendance_records if r["id"] not in id_set]
    return success_response(message=f"已删除 {len(ids)} 条记录")


# ==================== 统计接口 ====================

@app.route('/api/statistics/today', methods=['GET'])
@require_auth
def get_today_stats():
    """获取今日统计"""
    return success_response(get_today_stats_from_memory())


@app.route('/api/statistics/monthly', methods=['GET'])
@require_auth
def get_monthly_stats():
    """获取月度统计"""
    year = int(request.args.get('year', date.today().year))
    month = int(request.args.get('month', date.today().month))
    stats = db.get_monthly_statistics(year, month)
    return success_response(stats)


@app.route('/api/statistics/person/<int:person_id>', methods=['GET'])
@require_auth
def get_person_stats(person_id):
    """获取个人签到统计"""
    year = int(request.args.get('year', date.today().year))
    month = int(request.args.get('month', date.today().month))

    person = db.get_person(person_id)
    if not person:
        return error_response("人员不存在", 404)

    summary = db.get_person_attendance_summary(person_id, year, month)
    return success_response({
        "person": {k: v for k, v in person.items() if k != 'face_encoding'},
        "summary": summary
    })


@app.route('/api/statistics/departments', methods=['GET'])
@require_auth
def get_department_stats():
    """获取部门统计"""
    departments = db.get_departments()
    stats = []

    today = date.today().isoformat()
    for dept in departments:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # 部门总人数
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM persons WHERE department = ? AND status = 1",
                (dept,)
            )
            total = cursor.fetchone()['cnt']

            # 今日签到人数
            cursor.execute("""
                SELECT COUNT(DISTINCT a.person_id) as cnt
                FROM attendance a
                JOIN persons p ON a.person_id = p.id
                WHERE p.department = ? AND date(a.sign_time) = ? AND a.sign_type = 'in'
            """, (dept, today))
            signed = cursor.fetchone()['cnt']

        stats.append({
            "department": dept,
            "total": total,
            "signed": signed,
            "absent": total - signed,
            "rate": round(signed / total * 100, 1) if total > 0 else 0
        })

    return success_response({"departments": stats})


# ==================== 系统设置接口 ====================

@app.route('/api/settings', methods=['GET'])
@require_auth
def get_settings():
    """获取系统设置"""
    settings = db.get_settings()
    # 隐藏密码
    if 'admin_password' in settings:
        settings['admin_password'] = '******'
    return success_response(settings)


@app.route('/api/settings', methods=['PUT'])
@require_auth
def update_settings():
    """更新系统设置"""
    params = get_params()
    allowed_keys = [
        'work_start', 'work_end', 'late_grace', 'sign_mode',
        'recognition_threshold', 'confirm_frames', 'sign_cooldown',
        'camera_index', 'system_name'
    ]

    updates = {k: v for k, v in params.items() if k in allowed_keys}

    if updates:
        db.update_settings_batch(updates)
        db.add_log("update_settings", f"更新设置: {updates}", ip_address=get_ip())

    return success_response(message="设置已更新")


# ==================== 数据导出接口 ====================

@app.route('/api/export/attendance', methods=['GET'])
@require_auth
def export_attendance():
    """导出签到记录"""
    import openpyxl
    from io import BytesIO

    start_date = request.args.get('start_date', date.today().isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())

    records = [r for r in app._attendance_records
               if start_date <= r["sign_time"][:10] <= end_date]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "签到记录"
    ws.append(["ID", "姓名", "手机号", "类型", "签到时间", "第几次", "置信度", "备注"])
    for r in records:
        ws.append([
            r["id"], r["name"], r["phone"],
            "签到" if r["sign_type"] == "in" else "签退",
            r["sign_time"],
            r.get("sign_index", ""),
            f"{r['confidence']:.2%}" if r["confidence"] else "",
            r.get("remark", "")
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"签到记录_{start_date}_{end_date}.xlsx"
    return send_file(output, as_attachment=True, download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.route('/api/export/persons', methods=['GET'])
@require_auth
def export_persons():
    """导出人员列表"""
    filename = f"人员列表_{date.today().isoformat()}.xlsx"
    filepath = os.path.join(config.EXPORT_DIR, filename)

    success, msg = db.export_persons_excel(filepath)

    if success:
        return send_file(filepath, as_attachment=True, download_name=filename)
    return error_response(msg)


# ==================== 操作日志接口 ====================

@app.route('/api/logs', methods=['GET'])
@require_auth
def get_logs():
    """获取操作日志"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    action = request.args.get('action', '')

    logs, total = db.get_logs(page=page, per_page=per_page, action=action)
    return success_response({"logs": logs, "total": total, "page": page})


# ==================== 环境管理接口 ====================

@app.route('/api/environments', methods=['GET'])
@require_auth
def get_environments():
    """获取环境列表"""
    include_inactive = request.args.get('include_inactive', '0') == '1'
    environments = db.get_all_environments(include_inactive=include_inactive)
    return success_response({"environments": environments})


@app.route('/api/environments', methods=['POST'])
@require_auth
def create_environment():
    """创建环境"""
    params = get_params()

    # 验证必填字段
    if not params.get('name'):
        return error_response("环境名称不能为空")

    try:
        env_id = db.add_environment(
            name=params.get('name'),
            description=params.get('description', ''),
            work_start_hour=int(params.get('work_start_hour', 9)),
            work_start_minute=int(params.get('work_start_minute', 0)),
            work_end_hour=int(params.get('work_end_hour', 18)),
            work_end_minute=int(params.get('work_end_minute', 0)),
            late_grace_minutes=int(params.get('late_grace_minutes', 15)),
            sign_in_required=int(params.get('sign_in_required', 1)),
            sign_out_required=int(params.get('sign_out_required', 1)),
            sign_mode=params.get('sign_mode', 'auto'),
            recognition_threshold=float(params.get('recognition_threshold', 0.55)),
            confirm_frames=int(params.get('confirm_frames', 3)),
            sign_cooldown_seconds=int(params.get('sign_cooldown_seconds', 60)),
            is_active=int(params.get('is_active', 1)),
            default_env=int(params.get('default_env', 0))
        )
        db.add_log("create_environment", f"创建环境: {params.get('name')}", ip_address=get_ip())
        return success_response({"id": env_id}, "环境创建成功")
    except Exception as e:
        logger.error(f"创建环境失败: {e}")
        return error_response(f"创建失败: {str(e)}")


@app.route('/api/environments/<int:env_id>', methods=['GET'])
@require_auth
def get_environment(env_id):
    """获取单个环境"""
    env = db.get_environment(env_id)
    if not env:
        return error_response("环境不存在", 404)
    return success_response({"environment": env})


@app.route('/api/environments/<int:env_id>', methods=['PUT'])
@require_auth
def update_environment(env_id):
    """更新环境"""
    params = get_params()

    # 检查环境是否存在
    env = db.get_environment(env_id)
    if not env:
        return error_response("环境不存在", 404)

    try:
        db.update_environment(env_id, **params)
        db.add_log("update_environment", f"更新环境: {env_id}", ip_address=get_ip())
        return success_response(message="环境更新成功")
    except Exception as e:
        logger.error(f"更新环境失败: {e}")
        return error_response(f"更新失败: {str(e)}")


@app.route('/api/environments/<int:env_id>', methods=['DELETE'])
@require_auth
def delete_environment(env_id):
    """删除环境"""
    env = db.get_environment(env_id)
    if not env:
        return error_response("环境不存在", 404)

    if env.get('default_env'):
        return error_response("不能删除默认环境")

    try:
        db.delete_environment(env_id)
        db.add_log("delete_environment", f"删除环境: {env_id}", ip_address=get_ip())
        return success_response(message="环境删除成功")
    except Exception as e:
        logger.error(f"删除环境失败: {e}")
        return error_response(f"删除失败: {str(e)}")


@app.route('/api/environments/<int:env_id>/set-default', methods=['PUT'])
@require_auth
def set_default_environment(env_id):
    """设置默认环境"""
    env = db.get_environment(env_id)
    if not env:
        return error_response("环境不存在", 404)

    try:
        db.set_default_environment(env_id)
        db.add_log("set_default_environment", f"设置默认环境: {env_id}", ip_address=get_ip())
        return success_response(message="默认环境设置成功")
    except Exception as e:
        logger.error(f"设置默认环境失败: {e}")
        return error_response(f"设置失败: {str(e)}")


@app.route('/api/environments/active', methods=['GET'])
@require_auth
def get_active_environment():
    """获取当前激活的环境"""
    env = db.get_active_environment()
    if not env:
        return error_response("未找到激活的环境", 404)
    return success_response({"environment": env})


@app.route('/api/environments/<int:env_id>/activate', methods=['PUT'])
@require_auth
def activate_environment(env_id):
    """激活环境（切换预设环境）"""
    try:
        env = db.get_environment(env_id)
        if not env:
            return error_response("环境不存在", 404)

        # 设为默认环境
        db.set_default_environment(env_id)

        # 更新 settings 表的工作时间
        work_start = f"{env['work_start_hour']:02d}:{env['work_start_minute']:02d}"
        work_end = f"{env['work_end_hour']:02d}:{env['work_end_minute']:02d}"
        db.update_settings_batch({
            'work_start': work_start,
            'work_end': work_end,
            'late_grace': str(env.get('late_grace_minutes', 15)),
            'recognition_threshold': str(env.get('recognition_threshold', 0.55)),
            'confirm_frames': str(env.get('confirm_frames', 3)),
            'sign_cooldown': str(env.get('sign_cooldown_seconds', 60)),
        })

        # 更新 face_engine 参数
        face_engine = getattr(app, '_face_engine', None)
        if face_engine:
            face_engine.set_threshold(env.get('recognition_threshold', 0.55))
            face_engine.set_confirm_frames(env.get('confirm_frames', 3))
            face_engine.set_cooldown(env.get('sign_cooldown_seconds', 60))
            # 重新加载人脸
            persons = db.get_persons_with_encoding()
            face_engine.load_known_faces(persons)
            logger.info(f"环境已切换: {env['name']}, 阈值={env.get('recognition_threshold')}, 确认帧={env.get('confirm_frames')}")

        db.add_log("activate_environment", f"激活环境: {env['name']} (ID={env_id})", ip_address=get_ip())
        return success_response({"environment": env}, f"已切换到「{env['name']}」")
    except Exception as e:
        logger.error(f"激活环境失败: {e}")
        return error_response(f"切换失败: {str(e)}")


# ==================== 分类管理接口 ====================

@app.route('/api/categories', methods=['GET'])
@require_auth
def get_categories():
    """获取分类列表"""
    include_inactive = request.args.get('include_inactive', '0') == '1'
    level = request.args.get('level')

    if level:
        level = int(level)
        categories = db.get_categories_by_level(level)
    else:
        categories = db.get_all_categories(include_inactive=include_inactive)

    return success_response({"categories": categories})


@app.route('/api/categories/tree', methods=['GET'])
@require_auth
def get_category_tree():
    """获取分类树"""
    tree = db.get_category_tree()
    return success_response({"tree": tree})


@app.route('/api/categories', methods=['POST'])
@require_auth
def create_category():
    """创建分类"""
    params = get_params()

    if not params.get('name'):
        return error_response("分类名称不能为空")

    try:
        category_id = db.add_category(
            name=params.get('name'),
            parent_id=int(params.get('parent_id')) if params.get('parent_id') else None,
            level=int(params.get('level', 1)),
            sort_order=int(params.get('sort_order', 0)),
            description=params.get('description', ''),
            is_active=int(params.get('is_active', 1))
        )
        db.add_log("create_category", f"创建分类: {params.get('name')}", ip_address=get_ip())
        return success_response({"id": category_id}, "分类创建成功")
    except Exception as e:
        logger.error(f"创建分类失败: {e}")
        return error_response(f"创建失败: {str(e)}")


@app.route('/api/categories/<int:category_id>', methods=['GET'])
@require_auth
def get_category(category_id):
    """获取单个分类"""
    category = db.get_category(category_id)
    if not category:
        return error_response("分类不存在", 404)
    return success_response({"category": category})


@app.route('/api/categories/<int:category_id>', methods=['PUT'])
@require_auth
def update_category(category_id):
    """更新分类"""
    params = get_params()

    category = db.get_category(category_id)
    if not category:
        return error_response("分类不存在", 404)

    try:
        db.update_category(category_id, **params)
        db.add_log("update_category", f"更新分类: {category_id}", ip_address=get_ip())
        return success_response(message="分类更新成功")
    except Exception as e:
        logger.error(f"更新分类失败: {e}")
        return error_response(f"更新失败: {str(e)}")


@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
@require_auth
def delete_category(category_id):
    """删除分类"""
    category = db.get_category(category_id)
    if not category:
        return error_response("分类不存在", 404)

    try:
        db.delete_category(category_id)
        db.add_log("delete_category", f"删除分类: {category_id}", ip_address=get_ip())
        return success_response(message="分类删除成功")
    except Exception as e:
        logger.error(f"删除分类失败: {e}")
        return error_response(f"删除失败: {str(e)}")


@app.route('/api/categories/level/<int:level>', methods=['GET'])
@require_auth
def get_categories_by_level(level):
    """按层级获取分类"""
    parent_id = request.args.get('parent_id')
    if parent_id:
        parent_id = int(parent_id)

    categories = db.get_categories_by_level(level, parent_id)
    return success_response({"categories": categories})


# ==================== 人脸审核接口 ====================

@app.route('/api/persons/<int:person_id>/face-upload', methods=['POST'])
@require_auth
def upload_face_image(person_id):
    """上传人脸照片（手机端）"""
    person = db.get_person(person_id)
    if not person:
        return error_response("人员不存在", 404)

    # 检查是否有文件上传
    if 'image' not in request.files:
        return error_response("未找到图片文件")

    file = request.files['image']
    if file.filename == '':
        return error_response("未选择文件")

    # 保存图片
    import uuid
    filename = f"{person_id}_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    filepath = os.path.join('faces', filename)

    os.makedirs('faces', exist_ok=True)
    file.save(filepath)

    # 提取人脸编码
    import face_recognition
    import numpy as np

    try:
        image = face_recognition.load_image_file(filepath)
        encodings = face_recognition.face_encodings(image)

        if len(encodings) == 0:
            os.remove(filepath)
            return error_response("未检测到人脸")

        if len(encodings) > 1:
            os.remove(filepath)
            return error_response("检测到多个人脸，请上传单人照片")

        face_encoding = pickle.dumps(encodings[0])

        # 直接激活人脸，无需审批
        # 更新人员表的人脸编码
        db.update_person(person_id, face_encoding=face_encoding, face_image_path=filepath)

        # 保存人脸记录（状态为已激活）
        face_image_id = db.add_face_image(
            person_id=person_id,
            image_path=filepath,
            face_encoding=face_encoding,
            upload_source="mobile"
        )

        # 直接标记为已激活
        import sqlite3
        with db.get_connection() as conn:
            conn.execute("UPDATE face_images SET approval_status='approved', is_active=1 WHERE id=?", (face_image_id,))

        db.add_log("upload_face", f"上传并激活人脸: 人员ID={person_id}", ip_address=get_ip())
        return success_response({"id": face_image_id, "message": "人脸上传成功并已激活"})

    except Exception as e:
        logger.error(f"人脸处理失败: {e}")
        if os.path.exists(filepath):
            os.remove(filepath)
        return error_response(f"人脸处理失败: {str(e)}")


@app.route('/api/faces/pending', methods=['GET'])
@require_auth
def get_pending_faces():
    """获取待审核的人脸照片"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    pending, total = db.get_pending_faces(page=page, per_page=per_page)

    # 转换图片为base64
    for face in pending:
        if face.get('image_path') and os.path.exists(face['image_path']):
            with open(face['image_path'], 'rb') as f:
                face['image_base64'] = base64.b64encode(f.read()).decode('utf-8')

    return success_response({
        "faces": pending,
        "total": total,
        "page": page,
        "per_page": per_page
    })


@app.route('/api/faces/<int:face_id>/approve', methods=['PUT'])
@require_auth
def approve_face(face_id):
    """批准人脸照片"""
    # 获取审核人ID（从token解析，暂时使用固定ID）
    admin_id = 1  # TODO: 从认证token中解析真实的操作人ID

    try:
        success, message = db.approve_face_image(face_id, admin_id)
        if success:
            db.add_log("approve_face", f"批准人脸照片: ID={face_id}", ip_address=get_ip())
            return success_response(message=message)
        else:
            return error_response(message)
    except Exception as e:
        logger.error(f"批准人脸失败: {e}")
        return error_response(f"操作失败: {str(e)}")


@app.route('/api/faces/<int:face_id>/reject', methods=['PUT'])
@require_auth
def reject_face(face_id):
    """拒绝人脸照片"""
    params = get_params()
    reason = params.get('reason', '')

    try:
        db.reject_face_image(face_id, reason)
        db.add_log("reject_face", f"拒绝人脸照片: ID={face_id}, 原因: {reason}", ip_address=get_ip())
        return success_response(message="人脸照片已拒绝")
    except Exception as e:
        logger.error(f"拒绝人脸失败: {e}")
        return error_response(f"操作失败: {str(e)}")


@app.route('/api/persons/<int:person_id>/faces', methods=['GET'])
@require_auth
def get_person_faces(person_id):
    """获取人员的人脸照片列表"""
    person = db.get_person(person_id)
    if not person:
        return error_response("人员不存在", 404)

    faces = db.get_person_face_images(person_id)

    # 转换图片为base64
    for face in faces:
        if face.get('image_path') and os.path.exists(face['image_path']):
            with open(face['image_path'], 'rb') as f:
                face['image_base64'] = base64.b64encode(f.read()).decode('utf-8')

    return success_response({"faces": faces})


# ==================== 人员环境关联接口 ====================

@app.route('/api/persons/<int:person_id>/environments', methods=['GET'])
@require_auth
def get_person_environments(person_id):
    """获取人员所属的环境"""
    person = db.get_person(person_id)
    if not person:
        return error_response("人员不存在", 404)

    environments = db.get_person_environments(person_id)
    return success_response({"environments": environments})


@app.route('/api/persons/<int:person_id>/environments', methods=['PUT'])
@require_auth
def update_person_environments(person_id):
    """设置人员环境关联"""
    person = db.get_person(person_id)
    if not person:
        return error_response("人员不存在", 404)

    params = get_params()
    environment_ids = params.get('environment_ids', [])

    if not isinstance(environment_ids, list):
        return error_response("environment_ids必须是数组")

    try:
        # 先清除现有关联
        with db.get_connection() as conn:
            conn.execute("DELETE FROM person_environment_rel WHERE person_id = ?", (person_id,))

        # 添加新关联
        for idx, env_id in enumerate(environment_ids):
            is_primary = 1 if idx == 0 else 0
            db.add_person_to_environment(person_id, env_id, is_primary)

        db.add_log("update_person_environments", f"更新人员环境: 人员ID={person_id}, 环境={environment_ids}",
                  ip_address=get_ip())
        return success_response(message="人员环境设置成功")
    except Exception as e:
        logger.error(f"设置人员环境失败: {e}")
        return error_response(f"设置失败: {str(e)}")


@app.route('/api/environments/<int:env_id>/persons', methods=['GET'])
@require_auth
def get_environment_persons(env_id):
    """获取环境中的所有人员"""
    env = db.get_environment(env_id)
    if not env:
        return error_response("环境不存在", 404)

    persons = db.get_environment_persons(env_id)

    # 不返回人脸编码
    result_persons = []
    for p in persons:
        rp = {k: v for k, v in p.items() if k != 'face_encoding'}
        rp['has_face'] = p.get('face_encoding') is not None
        result_persons.append(rp)

    return success_response({"persons": result_persons})


# ==================== 实时监控接口 ====================

@app.route('/api/monitor/snapshot', methods=['GET'])
def get_camera_snapshot():
    """获取摄像头当前截图 (Base64)"""
    camera_running = getattr(app, '_camera_running', False)
    snapshot = getattr(app, '_camera_snapshot', None)
    if snapshot is None or not camera_running:
        return success_response({"image": None, "running": False})
    _, buffer = cv2.imencode('.jpg', snapshot, [cv2.IMWRITE_JPEG_QUALITY, 80])
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
    return success_response({"image": f"data:image/jpeg;base64,{jpg_as_text}", "running": True})


@app.route('/api/camera/toggle', methods=['POST'])
def toggle_camera():
    """通过API控制摄像头开关"""
    # 直接根据当前状态决定：运行中则关，未运行则开
    running = getattr(app, '_camera_running', False)
    app._camera_toggle_requested = not running
    return success_response({"requested": not running})


@app.route('/api/monitor/status', methods=['GET'])
@require_auth
def get_system_status():
    """获取系统运行状态"""
    import psutil
    try:
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
    except ImportError:
        cpu = 0
        memory = 0

    # 获取人脸引擎状态
    face_engine = getattr(app, '_face_engine', None)
    face_count = 0
    camera_running = False

    if face_engine:
        try:
            face_count = face_engine.get_face_count()
            camera_running = getattr(app, '_camera_running', False)
        except Exception as e:
            logger.error(f"获取人脸引擎状态失败: {e}")

    return success_response({
        "camera_running": camera_running,
        "face_count": face_count,
        "recognition_mode": getattr(app, '_recognition_mode', 'balanced'),
        "cpu_usage": cpu,
        "memory_usage": memory,
        "uptime": str(datetime.now() - app._start_time).split('.')[0] if hasattr(app, '_start_time') else 'unknown'
    })


# ==================== 辅助接口 ====================

@app.route('/api/departments', methods=['GET'])
@require_auth
def get_departments():
    """获取部门列表"""
    departments = db.get_departments()
    return success_response({"departments": departments})


@app.route('/api/person-count', methods=['GET'])
@require_auth
def get_person_count():
    """获取人员总数"""
    count = db.get_person_count()
    return success_response({"count": count})


# ==================== 设备配置接口 ====================

@app.route('/api/device/config', methods=['GET'])
def get_device_config():
    """获取设备配置"""
    config = db.get_device_config()
    return success_response(config)


@app.route('/api/device/config', methods=['PUT'])
@require_auth
def update_device_config():
    """更新设备配置"""
    params = get_params()

    device_name = params.get('device_name', '').strip()
    location = params.get('location', '').strip()
    description = params.get('description', '').strip()

    if not device_name:
        return error_response("设备名称不能为空")

    db.update_device_config(
        device_name=device_name,
        location=location,
        description=description
    )

    # 添加日志
    db.add_log("设备配置更新", f"设备名称: {device_name}")

    return success_response({
        "device_name": device_name,
        "location": location,
        "description": description
    })


@app.route('/api/device/discover', methods=['POST'])
def discover_devices():
    """搜索局域网内的设备（扫描同网段）"""
    try:
        import socket
        import concurrent.futures
        from config import get_local_ip, get_network_name

        local_ip = get_local_ip()
        network_name = get_network_name()

        # 推断网段
        parts = local_ip.split('.')
        subnet = '.'.join(parts[:3])

        # 要扫描的IP列表
        scan_ips = [f"{subnet}.{i}" for i in range(1, 255)]

        def check_device(ip):
            """检查单个IP是否有签到服务"""
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.3)
                result = sock.connect_ex((ip, config.API_PORT))
                sock.close()
                if result == 0:
                    # 找到开放端口，尝试获取设备信息
                    import urllib.request
                    url = f"http://{ip}:{config.API_PORT}/api/device/config"
                    req = urllib.request.Request(url, method='GET')
                    with urllib.request.urlopen(req, timeout=1) as resp:
                        data = json.loads(resp.read().decode('utf-8'))
                        if data.get('success'):
                            d = data.get('data', {})
                            return {
                                'name': d.get('device_name', '未知设备'),
                                'id': d.get('device_id', ''),
                                'ip': ip,
                                'port': config.API_PORT,
                                'location': d.get('location', ''),
                            }
            except Exception:
                pass
            return None

        # 并行扫描（最多50个线程）
        devices = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = {executor.submit(check_device, ip): ip for ip in scan_ips}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    devices.append(result)

        return success_response({
            "devices": devices,
            "network_name": network_name,
            "subnet": subnet
        })

    except Exception as e:
        logger.error(f"设备搜索失败: {e}")
        return error_response(f"设备搜索失败: {str(e)}")


@app.route('/api/device/network-info', methods=['GET'])
def get_network_info():
    """获取当前网络信息"""
    from config import get_local_ip, get_network_name
    return success_response({
        "network_name": get_network_name(),
        "local_ip": get_local_ip()
    })


@app.route('/api/device/heartbeat', methods=['GET'])
def device_heartbeat():
    """设备心跳接口"""
    return success_response({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "device_config": db.get_device_config()
    })


# ==================== 控制台会话管理 ====================

# 初始化控制台会话状态
if not hasattr(app, '_console_session'):
    app._console_session = {
        "session_id": None,
        "claimed_at": None,
        "last_heartbeat": None
    }

CONSOLE_TIMEOUT = 30  # 30秒无心跳自动释放


def _is_console_expired():
    """检查控制台会话是否已过期"""
    session = app._console_session
    if session["last_heartbeat"] is None:
        return True
    elapsed = (datetime.now() - session["last_heartbeat"]).total_seconds()
    if elapsed > CONSOLE_TIMEOUT:
        logger.info("控制台会话已过期，自动释放")
        app._console_session = {
            "session_id": None,
            "claimed_at": None,
            "last_heartbeat": None
        }
        return True
    return False


@app.route('/api/console/status', methods=['GET'])
def console_status():
    """查询控制台占用状态"""
    if _is_console_expired():
        return success_response({
            "occupied": False,
            "has_password": bool(db.get_setting('mobile_password'))
        })

    occupied = app._console_session["session_id"] is not None
    return success_response({
        "occupied": occupied,
        "has_password": bool(db.get_setting('mobile_password'))
    })


@app.route('/api/console/verify-password', methods=['POST'])
def console_verify_password():
    """验证控制台密码"""
    params = get_params()
    password = params.get('password', '')

    if not password:
        return error_response("请输入密码")

    stored = db.get_setting('mobile_password')
    if not stored:
        return error_response("尚未设置密码", 404)

    from werkzeug.security import check_password_hash
    if check_password_hash(stored, password):
        return success_response({"verified": True})
    else:
        return error_response("密码错误", 403)


@app.route('/api/console/claim', methods=['POST'])
def console_claim():
    """申请占用控制台"""
    params = get_params()
    session_id = params.get('session_id', '')
    password = params.get('password', '')

    # 检查是否过期
    _is_console_expired()

    # 如果已被占用
    if app._console_session["session_id"] is not None:
        # 同一个session续期
        if session_id and session_id == app._console_session["session_id"]:
            app._console_session["last_heartbeat"] = datetime.now()
            return success_response({
                "session_id": session_id,
                "renewed": True
            })
        # 不同session，拒绝
        return error_response("当前签到设备正在被操作，请稍后再试", 409)

    # 首次设置密码
    stored_password = db.get_setting('mobile_password')
    if not stored_password:
        if not password or len(password) < 4:
            return error_response("请设置至少4位密码")
        from werkzeug.security import generate_password_hash
        hashed = generate_password_hash(password)
        db.update_setting('mobile_password', hashed)
        logger.info("控制台密码已设置")

    # 验证密码（非首次时）
    else:
        if not password:
            return error_response("请输入密码")
        from werkzeug.security import check_password_hash
        if not check_password_hash(stored_password, password):
            return error_response("密码错误", 403)

    # 占用控制台
    import uuid
    new_session = str(uuid.uuid4())[:12]
    app._console_session = {
        "session_id": new_session,
        "claimed_at": datetime.now().isoformat(),
        "last_heartbeat": datetime.now()
    }

    logger.info(f"控制台已被占用: session={new_session}")
    return success_response({
        "session_id": new_session,
        "renewed": False
    })


@app.route('/api/console/heartbeat', methods=['POST'])
def console_heartbeat():
    """控制台心跳（续期）"""
    params = get_params()
    session_id = params.get('session_id', '')

    if not session_id or app._console_session["session_id"] != session_id:
        return error_response("会话无效", 401)

    app._console_session["last_heartbeat"] = datetime.now()
    return success_response({"status": "ok"})


@app.route('/api/console/release', methods=['POST'])
def console_release():
    """释放控制台"""
    params = get_params()
    session_id = params.get('session_id', '')

    if app._console_session["session_id"] == session_id:
        app._console_session = {
            "session_id": None,
            "claimed_at": None,
            "last_heartbeat": None
        }
        logger.info("控制台已释放")

    return success_response({"released": True})


@app.route('/api/console/change-password', methods=['POST'])
def console_change_password():
    """移动端修改控制台密码"""
    params = get_params()
    session_id = params.get('session_id', '')
    old_password = params.get('old_password', '')
    new_password = params.get('new_password', '')

    # 验证会话
    if not session_id or app._console_session["session_id"] != session_id:
        return error_response("会话无效", 401)

    if not old_password or not new_password:
        return error_response("请输入原密码和新密码")

    if len(new_password) < 4:
        return error_response("新密码至少4位")

    # 验证原密码
    from werkzeug.security import check_password_hash, generate_password_hash
    stored = db.get_setting('mobile_password')
    if stored and not check_password_hash(stored, old_password):
        return error_response("原密码错误", 403)

    # 设置新密码
    hashed = generate_password_hash(new_password)
    db.update_setting('mobile_password', hashed)
    logger.info("移动端修改了控制台密码")
    return success_response(message="密码修改成功")


# ==================== Web 管理界面 ====================

@app.route('/')
def index():
    """移动端管理界面"""
    return render_template('mobile.html')


@app.route('/m')
def mobile_console():
    """移动端控制台（扫码入口）"""
    mobile_path = os.path.join(config.RESOURCE_DIR, 'local_mobile.html')
    return send_file(mobile_path)


@app.route('/<path:filename>')
def static_files(filename):
    """静态文件"""
    return send_from_directory(app.static_folder, filename)


# ==================== TTS 语音播报（百度翻译 TTS） =================
_tts_last_file = os.path.join(config.CACHE_DIR, "tts_last.mp3")
_tts_last_id = 0


def _tts_generate(text, filepath):
    """从百度翻译 TTS 接口获取语音并本地播放"""
    print(f"[TTS] 开始生成语音: {text}")
    try:
        import urllib.request, urllib.parse, subprocess
        url = f"https://fanyi.baidu.com/gettts?lan=zh&text={urllib.parse.quote(text)}&spd=5"
        print(f"[TTS] 请求URL: {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read()
            print(f"[TTS] 下载完成: {len(data)} bytes")
            if len(data) < 100:
                print(f"[TTS] 音频过小，跳过")
                return
            with open(filepath, 'wb') as f:
                f.write(data)
        print(f"[TTS] 文件已保存: {filepath}")
        abs_path = os.path.abspath(filepath)
        print(f"[TTS] 开始播放: {abs_path}")
        import ctypes
        try:
            ctypes.windll.winmm.mciSendStringW(f'open "{abs_path}" type mpegvideo alias tts_audio', None, 0, None)
            ctypes.windll.winmm.mciSendStringW('play tts_audio wait', None, 0, None)
            ctypes.windll.winmm.mciSendStringW('close tts_audio', None, 0, None)
            print(f"[TTS] 播放完成")
        except Exception as e:
            print(f"[TTS] 播放失败: {e}")
    except Exception as e:
        print(f"[TTS] 失败: {e}")


def _trigger_tts(record):
    """签到后触发语音播报"""
    global _tts_last_id
    print(f"[TTS] _trigger_tts 被调用, record={record}")
    try:
        env = db.get_active_environment()
        print(f"[TTS] 环境: {env}")
        if not env:
            print("[TTS] 跳过: 无活跃环境")
            return
        if not env.get('sound_enabled'):
            print("[TTS] 跳过: sound_enabled=0")
            return
        text = ""
        if env.get('sound_read_name'):
            text += record.get('name') or "有人"
        else:
            text = "有人"
        text += "签到成功"
        extra = env.get('sound_text', '')
        if extra:
            text += "，" + extra
        _tts_last_id = record['id']
        print(f"[TTS] 启动播报线程: {text}")
        threading.Thread(target=_tts_generate, args=(text, _tts_last_file), daemon=True).start()
    except Exception as e:
        print(f"[TTS] 触发失败: {e}")


# ==================== 内存签到记录 ====================

def add_attendance_record(person_id, name, phone="", sign_type="in", confidence=None, remark=""):
    """添加签到记录到内存列表，返回 (record, error_msg)"""
    # 检查每日签到次数限制
    max_count = 0  # 0 = 不限
    try:
        env = db.get_active_environment()
        if env:
            max_count = int(env.get('max_sign_count', 0) or 0)
    except Exception:
        pass

    if max_count > 0:
        today = date.today().isoformat()
        today_count = sum(1 for r in app._attendance_records
                         if r["person_id"] == person_id and r["sign_time"].startswith(today))
        if today_count >= max_count:
            return None, f"{name} 今日已达{max_count}次上限"

    # 计算当日第几次
    today = date.today().isoformat()
    sign_index = sum(1 for r in app._attendance_records
                     if r["person_id"] == person_id and r["sign_time"].startswith(today)) + 1

    app._attendance_id_counter += 1
    record = {
        "id": app._attendance_id_counter,
        "person_id": person_id,
        "name": name,
        "phone": phone or "",
        "sign_type": sign_type,
        "sign_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "confidence": confidence,
        "remark": remark,
        "sign_index": sign_index
    }
    app._attendance_records.append(record)
    # 触发语音播报
    _trigger_tts(record)
    return record, None


def get_today_records():
    """获取今日签到记录（从内存）"""
    today = date.today().isoformat()
    return [r for r in app._attendance_records if r["sign_time"].startswith(today)]


def get_today_stats_from_memory():
    """从内存计算今日统计"""
    today_records = get_today_records()
    total_persons = db.get_person_count()
    signed_ids = set(r["person_id"] for r in today_records if r["sign_type"] == "in")
    signed_in = len(signed_ids)
    return {
        "total_persons": total_persons,
        "signed_in": signed_in,
        "absent": total_persons - signed_in,
        "total_records": len(today_records),
        "date": date.today().isoformat(),
        "sign_rate": round(signed_in / total_persons * 100, 1) if total_persons > 0 else 0
    }


# ==================== 启动函数 ====================

def start_api_server(host=None, port=None, face_engine=None, camera_manager=None):
    """启动API服务器

    Args:
        host: 监听地址
        port: 监听端口
        face_engine: 人脸识别引擎实例
        camera_manager: 摄像头管理器实例
    """
    host = host or config.API_HOST
    port = port or config.API_PORT

    # 保存引用
    if face_engine:
        app._face_engine = face_engine
    if camera_manager:
        app._camera_manager = camera_manager

    app._start_time = datetime.now()
    app._camera_running = False
    app._camera_snapshot = None
    app._face_count = 0
    app._recognition_mode = config.RECOGNITION_MODE

    logger.info(f"API服务启动于 http://{host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start_api_server()
