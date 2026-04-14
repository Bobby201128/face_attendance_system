# -*- coding: utf-8 -*-
"""
人脸识别签到系统 - 数据库管理层
SQLite数据库，管理人员信息、签到记录、系统配置等
"""
import sqlite3
import os
import json
import logging
from datetime import datetime, date, timedelta
from contextlib import contextmanager

import config

logger = logging.getLogger(__name__)


class Database:
    """数据库管理类"""

    def __init__(self, db_path=None):
        self.db_path = db_path or config.DATABASE_PATH
        self._init_db()

    @contextmanager
    def get_connection(self):
        """获取数据库连接 (上下文管理器)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            conn.close()

    def _init_db(self):
        """初始化数据库表结构"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 人员信息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS persons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    employee_id TEXT UNIQUE,
                    department TEXT DEFAULT '',
                    position TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    email TEXT DEFAULT '',
                    face_encoding BLOB,
                    face_image_path TEXT,
                    status INTEGER DEFAULT 1,
                    remark TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 签到记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER NOT NULL,
                    sign_type TEXT NOT NULL CHECK(sign_type IN ('in', 'out')),
                    sign_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confidence REAL,
                    camera_id INTEGER DEFAULT 0,
                    remark TEXT DEFAULT '',
                    FOREIGN KEY (person_id) REFERENCES persons(id)
                )
            """)

            # 系统配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 操作日志表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS operation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operator TEXT DEFAULT 'system',
                    action TEXT NOT NULL,
                    detail TEXT DEFAULT '',
                    ip_address TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attendance_person ON attendance(person_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attendance_time ON attendance(sign_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date(sign_time))")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_persons_employee ON persons(employee_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_persons_status ON persons(status)")

            # 初始化默认配置
            self._init_default_settings(cursor)

    def _init_default_settings(self, cursor):
        """初始化默认系统配置"""
        defaults = {
            "work_start": "09:00",
            "work_end": "18:00",
            "late_grace": "15",
            "sign_mode": "auto",
            "recognition_threshold": "0.6",
            "confirm_frames": "3",
            "sign_cooldown": "60",
            "camera_index": "0",
            "system_name": "人脸识别签到系统",
            "admin_password": "admin123",
        }
        for key, value in defaults.items():
            cursor.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )

    # ==================== 人员管理 ====================

    def add_person(self, name, employee_id=None, department="", position="",
                   phone="", email="", face_encoding=None, face_image_path="",
                   remark=""):
        """添加人员"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO persons (name, employee_id, department, position,
                                    phone, email, face_encoding, face_image_path, remark)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, employee_id, department, position, phone, email,
                  face_encoding, face_image_path, remark))
            return cursor.lastrowid

    def update_person(self, person_id, **kwargs):
        """更新人员信息"""
        allowed_fields = ['name', 'employee_id', 'department', 'position',
                         'phone', 'email', 'face_encoding', 'face_image_path',
                         'status', 'remark']
        updates = []
        values = []
        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                values.append(value)

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(person_id)

        with self.get_connection() as conn:
            conn.execute(
                f"UPDATE persons SET {', '.join(updates)} WHERE id = ?",
                values
            )
            return True

    def delete_person(self, person_id):
        """删除人员 (软删除)"""
        with self.get_connection() as conn:
            conn.execute("UPDATE persons SET status = 0 WHERE id = ?", (person_id,))
            return True

    def hard_delete_person(self, person_id):
        """彻底删除人员"""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM attendance WHERE person_id = ?", (person_id,))
            conn.execute("DELETE FROM persons WHERE id = ?", (person_id,))
            return True

    def get_person(self, person_id):
        """获取单个人员信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM persons WHERE id = ?", (person_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_person_by_employee_id(self, employee_id):
        """根据工号获取人员"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM persons WHERE employee_id = ? AND status = 1",
                          (employee_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_persons(self, include_inactive=False, search="", department="",
                       page=1, per_page=50):
        """获取人员列表 (分页+搜索)"""
        conditions = []
        params = []

        if not include_inactive:
            conditions.append("status = 1")

        if search:
            conditions.append("(name LIKE ? OR employee_id LIKE ? OR phone LIKE ?)")
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern, search_pattern])

        if department:
            conditions.append("department = ?")
            params.append(department)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        offset = (page - 1) * per_page

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM persons WHERE {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                params + [per_page, offset]
            )
            persons = [dict(row) for row in cursor.fetchall()]

            cursor.execute(
                f"SELECT COUNT(*) as total FROM persons WHERE {where_clause}",
                params
            )
            total = cursor.fetchone()['total']

        return persons, total

    def get_persons_with_encoding(self):
        """获取所有有面部编码的活跃人员"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, employee_id, department, face_encoding, face_image_path "
                "FROM persons WHERE face_encoding IS NOT NULL AND status = 1"
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_departments(self):
        """获取所有部门列表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT department FROM persons WHERE status = 1 AND department != '' ORDER BY department"
            )
            return [row['department'] for row in cursor.fetchall()]

    def get_person_count(self):
        """获取活跃人员总数"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM persons WHERE status = 1")
            return cursor.fetchone()['cnt']

    # ==================== 签到管理 ====================

    def add_attendance(self, person_id, sign_type, confidence=None, remark=""):
        """添加签到记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO attendance (person_id, sign_type, confidence, remark)
                VALUES (?, ?, ?, ?)
            """, (person_id, sign_type, confidence, remark))
            return cursor.lastrowid

    def get_today_attendance(self, target_date=None):
        """获取某天的签到记录"""
        target_date = target_date or date.today().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.*, p.name, p.employee_id, p.department, p.position
                FROM attendance a
                JOIN persons p ON a.person_id = p.id
                WHERE date(a.sign_time) = ?
                ORDER BY a.sign_time DESC
            """, (target_date,))
            return [dict(row) for row in cursor.fetchall()]

    def get_person_today_status(self, person_id, target_date=None):
        """获取某人某天的签到状态"""
        target_date = target_date or date.today().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sign_type, sign_time, confidence
                FROM attendance
                WHERE person_id = ? AND date(sign_time) = ?
                ORDER BY sign_time
            """, (person_id, target_date))
            records = [dict(row) for row in cursor.fetchall()]

            status = {
                "signed_in": False,
                "signed_out": False,
                "sign_in_time": None,
                "sign_out_time": None,
                "records": records
            }
            for r in records:
                if r['sign_type'] == 'in' and not status['signed_in']:
                    status['signed_in'] = True
                    status['sign_in_time'] = r['sign_time']
                elif r['sign_type'] == 'out':
                    status['signed_out'] = True
                    status['sign_out_time'] = r['sign_time']

            return status

    def get_attendance_by_date_range(self, start_date, end_date, department="",
                                     person_id=None, page=1, per_page=50):
        """按日期范围查询签到记录"""
        conditions = ["date(a.sign_time) BETWEEN ? AND ?"]
        params = [start_date, end_date]

        if department:
            conditions.append("p.department = ?")
            params.append(department)

        if person_id:
            conditions.append("a.person_id = ?")
            params.append(person_id)

        where_clause = " AND ".join(conditions)
        offset = (page - 1) * per_page

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""SELECT a.*, p.name, p.employee_id, p.department, p.position
                    FROM attendance a
                    JOIN persons p ON a.person_id = p.id
                    WHERE {where_clause}
                    ORDER BY a.sign_time DESC
                    LIMIT ? OFFSET ?""",
                params + [per_page, offset]
            )
            records = [dict(row) for row in cursor.fetchall()]

            cursor.execute(
                f"""SELECT COUNT(*) as total
                    FROM attendance a
                    JOIN persons p ON a.person_id = p.id
                    WHERE {where_clause}""",
                params
            )
            total = cursor.fetchone()['total']

        return records, total

    def get_today_statistics(self):
        """获取今日签到统计"""
        today = date.today().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 总人数
            cursor.execute("SELECT COUNT(*) as cnt FROM persons WHERE status = 1")
            total_persons = cursor.fetchone()['cnt']

            # 今日签到人数 (签到的不同人数)
            cursor.execute("""
                SELECT COUNT(DISTINCT person_id) as cnt
                FROM attendance
                WHERE date(sign_time) = ? AND sign_type = 'in'
            """, (today,))
            signed_in = cursor.fetchone()['cnt']

            # 今日签到总次数
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM attendance WHERE date(sign_time) = ?
            """, (today,))
            total_records = cursor.fetchone()['cnt']

            # 迟到人数
            settings = self.get_settings()
            work_start = settings.get('work_start', '09:00')
            late_grace = int(settings.get('late_grace', '15'))

            cursor.execute("""
                SELECT COUNT(DISTINCT person_id) as cnt
                FROM attendance
                WHERE date(sign_time) = ? AND sign_type = 'in'
                  AND time(sign_time) > time(?)
            """, (today, f"{work_start}:{late_grace:02d}:00"))
            late_count = cursor.fetchone()['cnt']

            return {
                "total_persons": total_persons,
                "signed_in": signed_in,
                "absent": total_persons - signed_in,
                "late_count": late_count,
                "total_records": total_records,
                "date": today,
                "sign_rate": round(signed_in / total_persons * 100, 1) if total_persons > 0 else 0
            }

    def get_monthly_statistics(self, year=None, month=None):
        """获取月度统计"""
        today = date.today()
        year = year or today.year
        month = month or today.month

        start_date = date(year, month, 1).isoformat()
        if month == 12:
            end_date = date(year + 1, 1, 1).isoformat()
        else:
            end_date = date(year, month + 1, 1).isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 每日签到人数统计
            cursor.execute("""
                SELECT date(sign_time) as day,
                       COUNT(DISTINCT CASE WHEN sign_type='in' THEN person_id END) as sign_in_count,
                       COUNT(*) as total_records
                FROM attendance
                WHERE date(sign_time) >= ? AND date(sign_time) < ?
                GROUP BY date(sign_time)
                ORDER BY day
            """, (start_date, end_date))
            daily_stats = [dict(row) for row in cursor.fetchall()]

            # 月度汇总
            cursor.execute("SELECT COUNT(*) as cnt FROM persons WHERE status = 1")
            total_persons = cursor.fetchone()['cnt']

            cursor.execute("""
                SELECT COUNT(DISTINCT person_id) as cnt
                FROM attendance
                WHERE date(sign_time) >= ? AND date(sign_time) < ? AND sign_type = 'in'
            """, (start_date, end_date))
            unique_signed = cursor.fetchone()['cnt']

            return {
                "year": year,
                "month": month,
                "total_persons": total_persons,
                "unique_signed": unique_signed,
                "daily_stats": daily_stats
            }

    def get_person_attendance_summary(self, person_id, year=None, month=None):
        """获取个人签到汇总"""
        today = date.today()
        year = year or today.year
        month = month or today.month

        start_date = date(year, month, 1).isoformat()
        if month == 12:
            end_date = date(year + 1, 1, 1).isoformat()
        else:
            end_date = date(year, month + 1, 1).isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date(sign_time) as day,
                       MIN(CASE WHEN sign_type='in' THEN time(sign_time) END) as first_in,
                       MAX(CASE WHEN sign_type='out' THEN time(sign_time) END) as last_out,
                       COUNT(*) as record_count
                FROM attendance
                WHERE person_id = ? AND date(sign_time) >= ? AND date(sign_time) < ?
                GROUP BY date(sign_time)
                ORDER BY day
            """, (person_id, start_date, end_date))
            return [dict(row) for row in cursor.fetchall()]

    # ==================== 系统设置 ====================

    def get_settings(self):
        """获取所有设置"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            return {row['key']: row['value'] for row in cursor.fetchall()}

    def get_setting(self, key, default=None):
        """获取单个设置"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else default

    def update_setting(self, key, value):
        """更新设置"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """, (key, str(value)))

    def update_settings_batch(self, settings_dict):
        """批量更新设置"""
        with self.get_connection() as conn:
            for key, value in settings_dict.items():
                conn.execute("""
                    INSERT INTO settings (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
                """, (key, str(value)))

    # ==================== 操作日志 ====================

    def add_log(self, action, detail="", operator="system", ip_address=""):
        """添加操作日志"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO operation_logs (operator, action, detail, ip_address)
                VALUES (?, ?, ?, ?)
            """, (operator, action, detail, ip_address))

    def get_logs(self, page=1, per_page=50, action=""):
        """获取操作日志"""
        offset = (page - 1) * per_page
        conditions = []
        params = []

        if action:
            conditions.append("action LIKE ?")
            params.append(f"%{action}%")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM operation_logs WHERE {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                params + [per_page, offset]
            )
            logs = [dict(row) for row in cursor.fetchall()]

            cursor.execute(
                f"SELECT COUNT(*) as total FROM operation_logs WHERE {where_clause}",
                params
            )
            total = cursor.fetchone()['total']

        return logs, total

    # ==================== 数据导出 ====================

    def export_attendance_excel(self, start_date, end_date, filepath):
        """导出签到记录为Excel"""
        try:
            import pandas as pd
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

            records, _ = self.get_attendance_by_date_range(start_date, end_date, per_page=10000)

            if not records:
                return False, "没有数据可导出"

            df_data = []
            for r in records:
                df_data.append({
                    "姓名": r.get('name', ''),
                    "工号": r.get('employee_id', ''),
                    "部门": r.get('department', ''),
                    "职位": r.get('position', ''),
                    "签到类型": "签到" if r['sign_type'] == 'in' else "签退",
                    "签到时间": r['sign_time'],
                    "置信度": f"{r.get('confidence', 0):.2%}" if r.get('confidence') else '',
                    "备注": r.get('remark', '')
                })

            df = pd.DataFrame(df_data)

            wb = Workbook()
            ws = wb.active
            ws.title = "签到记录"

            # 表头样式
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True, size=11)
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )

            # 写入表头
            for col_idx, col_name in enumerate(df.columns, 1):
                cell = ws.cell(row=1, column=col_idx, value=col_name)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center')
                cell.border = thin_border

            # 写入数据
            for row_idx, row_data in enumerate(df.values, 2):
                for col_idx, value in enumerate(row_data, 1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    cell.alignment = Alignment(horizontal='center')
                    cell.border = thin_border

            # 自动调整列宽
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                ws.column_dimensions[column].width = min(max_length + 4, 30)

            wb.save(filepath)
            return True, f"成功导出 {len(df_data)} 条记录"

        except ImportError:
            return False, "缺少pandas或openpyxl库，请安装: pip install pandas openpyxl"
        except Exception as e:
            return False, f"导出失败: {str(e)}"

    def export_persons_excel(self, filepath):
        """导出人员列表为Excel"""
        try:
            import pandas as pd
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

            persons, _ = self.get_all_persons(include_inactive=True, per_page=10000)

            if not persons:
                return False, "没有数据可导出"

            df_data = []
            for p in persons:
                df_data.append({
                    "姓名": p.get('name', ''),
                    "工号": p.get('employee_id', ''),
                    "部门": p.get('department', ''),
                    "职位": p.get('position', ''),
                    "电话": p.get('phone', ''),
                    "邮箱": p.get('email', ''),
                    "状态": "启用" if p.get('status', 1) == 1 else "禁用",
                    "创建时间": p.get('created_at', ''),
                    "备注": p.get('remark', '')
                })

            df = pd.DataFrame(df_data)

            wb = Workbook()
            ws = wb.active
            ws.title = "人员列表"

            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True, size=11)
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )

            for col_idx, col_name in enumerate(df.columns, 1):
                cell = ws.cell(row=1, column=col_idx, value=col_name)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal='center')
                cell.border = thin_border

            for row_idx, row_data in enumerate(df.values, 2):
                for col_idx, value in enumerate(row_data, 1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    cell.alignment = Alignment(horizontal='center')
                    cell.border = thin_border

            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                ws.column_dimensions[column].width = min(max_length + 4, 30)

            wb.save(filepath)
            return True, f"成功导出 {len(df_data)} 条记录"

        except ImportError:
            return False, "缺少pandas或openpyxl库"
        except Exception as e:
            return False, f"导出失败: {str(e)}"


# 全局数据库实例
db = Database()
