# -*- coding: utf-8 -*-
"""
自动集成脚本 - 将新功能UI集成到mobile.html (修复编码问题版本)
"""
import os
import re
import shutil
import sys
import io
from datetime import datetime

# 设置UTF-8编码输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def print_section(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def backup_file(file_path):
    """备份文件"""
    backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"[OK] 备份完成: {backup_path}")
    return backup_path


def integrate_mobile_ui():
    """集成新功能UI到mobile.html"""
    print("=" * 60)
    print("手机端UI自动集成工具")
    print("=" * 60)

    mobile_html_path = "templates/mobile.html"
    new_features_path = "templates/mobile_new_features.html"

    # 检查文件是否存在
    if not os.path.exists(mobile_html_path):
        print(f"[ERROR] 找不到文件: {mobile_html_path}")
        return False

    if not os.path.exists(new_features_path):
        print(f"[ERROR] 找不到文件: {new_features_path}")
        return False

    # 备份原文件
    print_section("1. 备份原文件")
    backup_path = backup_file(mobile_html_path)

    # 读取文件内容
    print_section("2. 读取文件内容")
    with open(mobile_html_path, 'r', encoding='utf-8') as f:
        mobile_html = f.read()

    with open(new_features_path, 'r', encoding='utf-8') as f:
        new_features = f.read()

    # 提取新功能的各个部分
    print_section("3. 提取新功能组件")

    # 提取所有页面HTML（从环境管理页面到人脸审核页面结束）
    pages_match = re.search(r'<!-- ===== 环境管理页面 ===== -->(.*?)<!-- ===== 环境编辑弹窗 ===== -->', new_features, re.DOTALL)
    if not pages_match:
        print("[ERROR] 无法提取页面HTML")
        return False

    pages_html = pages_match.group(0)

    # 提取弹窗HTML（从环境编辑弹窗到JavaScript之前）
    modals_match = re.search(r'<!-- ===== 环境编辑弹窗 ===== -->(.*?)<script>', new_features, re.DOTALL)
    if not modals_match:
        print("[ERROR] 无法提取弹窗HTML")
        return False

    modals_html = modals_match.group(0)

    # 提取JavaScript代码
    js_match = re.search(r'<script>(.*?)</script>', new_features, re.DOTALL)
    if not js_match:
        print("[ERROR] 无法提取JavaScript代码")
        return False

    js_code = js_match.group(1)

    # 提取CSS样式
    css_match = re.search(r'<style>(.*?)</style>', new_features, re.DOTALL)
    if not css_match:
        print("[ERROR] 无法提取CSS样式")
        return False

    css_code = css_match.group(1)

    print("[OK] 页面HTML提取完成")
    print("[OK] 弹窗HTML提取完成")
    print("[OK] JavaScript代码提取完成")
    print("[OK] CSS样式提取完成")

    # 集成到mobile.html
    print_section("4. 集成到mobile.html")

    # 1. 在设置页面结束之前添加新页面
    settings_end_pattern = r'(</div>\s*</div>\s*</div>\s*<!-- Bottom Navigation -->)'
    if re.search(settings_end_pattern, mobile_html):
        mobile_html = re.sub(
            settings_end_pattern,
            f'{pages_html}\\1',
            mobile_html
        )
        print("[OK] 新页面已添加")
    else:
        print("[ERROR] 无法找到设置页面结束位置")
        return False

    # 2. 在Person Modal之后添加新弹窗
    person_modal_pattern = r'(</div>\s*<!-- ===== Person Modal ===== -->)'
    if re.search(person_modal_pattern, mobile_html):
        mobile_html = re.sub(
            person_modal_pattern,
            f'\\1\n{modals_html}',
            mobile_html
        )
        print("[OK] 新弹窗已添加")
    else:
        print("[ERROR] 无法找到Person Modal")
        return False

    # 3. 在</style>之前添加新样式
    style_end_pattern = r'(\s*</style>)'
    if re.search(style_end_pattern, mobile_html):
        mobile_html = re.sub(
            style_end_pattern,
            f'{css_code}\\1',
            mobile_html
        )
        print("[OK] 新样式已添加")
    else:
        print("[ERROR] 无法找到style结束标签")
        return False

    # 4. 在</script>之前添加新JavaScript代码
    script_end_pattern = r'(\s*</script>)'
    if re.search(script_end_pattern, mobile_html):
        mobile_html = re.sub(
            script_end_pattern,
            f'{js_code}\\1',
            mobile_html
        )
        print("[OK] 新JavaScript代码已添加")
    else:
        print("[ERROR] 无法找到script结束标签")
        return False

    # 5. 在设置页面添加新功能入口
    settings_system_card_pattern = r'(<div class="card">\s*<div class="card-title">系统</div>.*?</div>\s*<button class="btn btn-primary".*?保存设置</button>)'
    if re.search(settings_system_card_pattern, mobile_html, re.DOTALL):
        new_features_menu = '''
        <div class="card">
            <div class="card-title">新功能管理</div>
            <div class="setting-item" onclick="switchPage('Environments')">
                <div>
                    <div class="setting-label">环境管理</div>
                    <div class="setting-desc">管理多个签到场景</div>
                </div>
                <button class="btn-icon" style="color:var(--primary);">➔</button>
            </div>
            <div class="setting-item" onclick="switchPage('Categories')">
                <div>
                    <div class="setting-label">分类管理</div>
                    <div class="setting-desc">四级分类体系</div>
                </div>
                <button class="btn-icon" style="color:var(--primary);">➔</button>
            </div>
            <div class="setting-item" onclick="switchPage('FaceApproval')">
                <div>
                    <div class="setting-label">人脸审核</div>
                    <div class="setting-desc">审核待批准的人脸照片</div>
                </div>
                <button class="btn-icon" style="color:var(--primary);">➔</button>
            </div>
        </div>
        '''

        mobile_html = re.sub(
            settings_system_card_pattern,
            f'\\1\n{new_features_menu}',
            mobile_html
        )
        print("[OK] 新功能菜单已添加到设置页面")
    else:
        print("[ERROR] 无法找到设置页面系统卡片")
        return False

    # 保存修改后的文件
    print_section("5. 保存修改")
    with open(mobile_html_path, 'w', encoding='utf-8') as f:
        f.write(mobile_html)

    print(f"[OK] 文件已保存: {mobile_html_path}")

    # 总结
    print_section("集成完成")
    print("[OK] 所有组件已成功集成到mobile.html")
    print()
    print("新增功能:")
    print("  1. 环境管理页面 - 设置 -> 环境管理")
    print("  2. 分类管理页面 - 设置 -> 分类管理")
    print("  3. 人脸审核页面 - 设置 -> 人脸审核")
    print()
    print("下一步:")
    print("  1. 启动系统: python main.py")
    print("  2. 访问移动端界面")
    print("  3. 进入设置页面，测试新功能")
    print()
    print(f"原文件备份于: {backup_path}")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        success = integrate_mobile_ui()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] 集成过程发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
