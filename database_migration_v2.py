# -*- coding: utf-8 -*-
"""
数据库迁移脚本 v2.0
添加环境系统、分类体系、人脸审核功能
"""
import sqlite3
import os
import logging
from datetime import datetime

import config

logger = logging.getLogger(__name__)


class DatabaseMigrationV2:
    """数据库版本2迁移类"""

    def __init__(self, db_path=None):
        self.db_path = db_path or config.DATABASE_PATH
        self.backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def backup_database(self):
        """备份数据库"""
        try:
            import shutil
            shutil.copy2(self.db_path, self.backup_path)
            logger.info(f"数据库备份完成: {self.backup_path}")
            return True, f"备份成功: {self.backup_path}"
        except Exception as e:
            logger.error(f"数据库备份失败: {e}")
            return False, f"备份失败: {str(e)}"

    def check_migration_needed(self):
        """检查是否需要迁移"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 检查新表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='environments'")
        has_environments = cursor.fetchone() is not None

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='categories'")
        has_categories = cursor.fetchone() is not None

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='face_images'")
        has_face_images = cursor.fetchone() is not None

        conn.close()

        return not (has_environments and has_categories and has_face_images)

    def migrate(self):
        """执行迁移"""
        logger.info("开始数据库迁移 v2.0...")

        # 1. 备份数据库
        success, msg = self.backup_database()
        if not success:
            return False, msg

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")

            # 2. 扩展 persons 表
            self._extend_persons_table(cursor)

            # 3. 创建 environments 表
            self._create_environments_table(cursor)

            # 4. 创建 categories 表
            self._create_categories_table(cursor)

            # 5. 创建 person_environment_rel 表
            self._create_person_environment_rel_table(cursor)

            # 6. 创建 face_images 表
            self._create_face_images_table(cursor)

            # 7. 创建索引
            self._create_indexes(cursor)

            # 8. 插入初始数据
            self._insert_initial_data(cursor)

            conn.commit()
            conn.close()

            logger.info("数据库迁移完成！")
            return True, "迁移成功完成"

        except Exception as e:
            logger.error(f"迁移失败: {e}")
            # 恢复备份
            try:
                import shutil
                shutil.copy2(self.backup_path, self.db_path)
                logger.info("已从备份恢复数据库")
            except:
                pass
            return False, f"迁移失败: {str(e)}"

    def _extend_persons_table(self, cursor):
        """扩展 persons 表，添加新字段"""
        logger.info("扩展 persons 表...")

        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(persons)")
        existing_columns = [row[1] for row in cursor.fetchall()]

        # 添加新字段
        new_columns = {
            'category_id': 'INTEGER DEFAULT NULL',  # 关联分类体系
            'enroll_status': "TEXT DEFAULT 'active'",  # 入职状态: active/inactive/resigned
            'hire_date': 'DATE DEFAULT NULL',  # 入职日期
            'supervisor_id': 'INTEGER DEFAULT NULL',  # 直属上级ID
        }

        for column, definition in new_columns.items():
            if column not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE persons ADD COLUMN {column} {definition}")
                    logger.info(f"  - 添加字段: {column}")
                except Exception as e:
                    logger.warning(f"  - 添加字段 {column} 失败: {e}")

    def _create_environments_table(self, cursor):
        """创建环境配置表"""
        logger.info("创建 environments 表...")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS environments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                work_start_hour INTEGER DEFAULT 9,
                work_start_minute INTEGER DEFAULT 0,
                work_end_hour INTEGER DEFAULT 18,
                work_end_minute INTEGER DEFAULT 0,
                late_grace_minutes INTEGER DEFAULT 15,
                sign_in_required INTEGER DEFAULT 1,
                sign_out_required INTEGER DEFAULT 1,
                sign_mode TEXT DEFAULT 'auto',
                recognition_threshold REAL DEFAULT 0.55,
                confirm_frames INTEGER DEFAULT 3,
                sign_cooldown_seconds INTEGER DEFAULT 60,
                is_active INTEGER DEFAULT 1,
                default_env INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        logger.info("  - environments 表创建完成")

    def _create_categories_table(self, cursor):
        """创建分类体系表"""
        logger.info("创建 categories 表...")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER DEFAULT NULL,
                level INTEGER NOT NULL CHECK(level IN (1,2,3,4)),
                sort_order INTEGER DEFAULT 0,
                description TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE CASCADE
            )
        """)

        logger.info("  - categories 表创建完成")

    def _create_person_environment_rel_table(self, cursor):
        """创建人员环境关联表"""
        logger.info("创建 person_environment_rel 表...")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS person_environment_rel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                environment_id INTEGER NOT NULL,
                is_primary INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE,
                FOREIGN KEY (environment_id) REFERENCES environments(id) ON DELETE CASCADE,
                UNIQUE(person_id, environment_id)
            )
        """)

        logger.info("  - person_environment_rel 表创建完成")

    def _create_face_images_table(self, cursor):
        """创建人脸照片表"""
        logger.info("创建 face_images 表...")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS face_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                image_path TEXT NOT NULL,
                face_encoding BLOB,
                upload_source TEXT DEFAULT 'mobile',
                approval_status TEXT DEFAULT 'pending',
                approved_by INTEGER DEFAULT NULL,
                approved_at TIMESTAMP DEFAULT NULL,
                reject_reason TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE,
                FOREIGN KEY (approved_by) REFERENCES persons(id)
            )
        """)

        logger.info("  - face_images 表创建完成")

    def _create_indexes(self, cursor):
        """创建索引"""
        logger.info("创建索引...")

        indexes = [
            ("idx_persons_category", "persons", "category_id"),
            ("idx_persons_supervisor", "persons", "supervisor_id"),
            ("idx_persons_enroll_status", "persons", "enroll_status"),
            ("idx_environments_active", "environments", "is_active"),
            ("idx_categories_parent", "categories", "parent_id"),
            ("idx_categories_level", "categories", "level"),
            ("idx_person_env_rel_person", "person_environment_rel", "person_id"),
            ("idx_person_env_rel_env", "person_environment_rel", "environment_id"),
            ("idx_face_images_person", "face_images", "person_id"),
            ("idx_face_images_status", "face_images", "approval_status"),
        ]

        for idx_name, table, column in indexes:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
                logger.info(f"  - 索引 {idx_name} 已创建")
            except Exception as e:
                logger.warning(f"  - 创建索引 {idx_name} 失败: {e}")

    def _insert_initial_data(self, cursor):
        """插入初始数据"""
        logger.info("插入初始数据...")

        # 创建默认环境
        cursor.execute("""
            INSERT OR IGNORE INTO environments
            (id, name, description, default_env)
            VALUES (1, '默认环境', '系统默认的签到环境', 1)
        """)
        logger.info("  - 默认环境已创建")

        # 创建示例分类体系（可选）
        # level 1: 集团
        cursor.execute("""
            INSERT OR IGNORE INTO categories (id, name, parent_id, level, sort_order)
            VALUES (1, '示例集团', NULL, 1, 1)
        """)

        # level 2: 公司
        cursor.execute("""
            INSERT OR IGNORE INTO categories (id, name, parent_id, level, sort_order)
            VALUES
                (2, '北京分公司', 1, 2, 1),
                (3, '上海分公司', 1, 2, 2)
        """)

        # level 3: 部门
        cursor.execute("""
            INSERT OR IGNORE INTO categories (id, name, parent_id, level, sort_order)
            VALUES
                (4, '研发部', 2, 3, 1),
                (5, '市场部', 2, 3, 2),
                (6, '人事部', 2, 3, 3),
                (7, '研发部', 3, 3, 1),
                (8, '市场部', 3, 3, 2)
        """)

        # level 4: 小组
        cursor.execute("""
            INSERT OR IGNORE INTO categories (id, name, parent_id, level, sort_order)
            VALUES
                (9, '前端组', 4, 4, 1),
                (10, '后端组', 4, 4, 2),
                (11, '测试组', 4, 4, 3)
        """)

        logger.info("  - 示例分类体系已创建")


def run_migration():
    """运行迁移"""
    import sys
    import io

    # 设置输出编码为UTF-8
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    print("=" * 60)
    print("数据库迁移 v2.0")
    print("=" * 60)
    print(f"数据库路径: {config.DATABASE_PATH}")
    print()

    migrator = DatabaseMigrationV2()

    # 检查是否需要迁移
    if not migrator.check_migration_needed():
        print("[OK] 数据库已经是最新版本，无需迁移")
        return True

    print("[!] 发现需要迁移的数据库结构")
    print()

    # 执行迁移
    success, message = migrator.migrate()

    print()
    print("=" * 60)
    if success:
        print("[OK] 迁移成功完成！")
        print()
        print("新增功能:")
        print("  1. 环境系统 - 支持多场景签到配置")
        print("  2. 分类体系 - 四级分类管理（集团→公司→部门→小组）")
        print("  3. 人员扩展 - 入职状态、入职日期、直属上级")
        print("  4. 人脸审核 - 人脸照片审批流程")
        print("  5. 人员环境关联 - 一个人可在多个环境签到")
    else:
        print(f"[ERROR] 迁移失败: {message}")
        print("数据库已从备份恢复，请检查错误信息后重试")
    print("=" * 60)

    return success


if __name__ == "__main__":
    import sys
    try:
        success = run_migration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[ERROR] 迁移过程发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
