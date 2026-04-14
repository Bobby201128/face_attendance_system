# Git 管理指南

## ✅ Git 仓库已设置完成！

### 📊 当前状态

```
仓库类型: Git
分支: master
初始提交: ca74061
文件数量: 19 个文件已提交
```

---

## 📁 已版本控制的文件

### ✅ 核心代码文件
- `main.py` - 主入口
- `pc_app.py` - PyQt5 界面
- `api_server.py` - Flask API 服务
- `face_engine.py` - 人脸识别引擎
- `database.py` - 数据库管理
- `video_threads.py` - 视频处理线程
- `config.py` - 配置文件

### ✅ 配置和文档
- `requirements.txt` - Python 依赖
- `README.md` - 项目说明
- `CLAUDE.md` - 开发文档
- `.gitignore` - Git 忽略规则
- `run_with_conda.bat` - 启动脚本

### ✅ 模板和资源
- `templates/mobile.html` - Web 界面

### ✅ 关键文档
- `SUCCESS_GUIDE.md` - 使用指南
- `SOLUTION_SUMMARY.md` - 解决方案总结
- `QUICK_FIX_GUIDE.md` - 快速修复指南
- `OPTIMIZATION_SUGGESTIONS.md` - 优化建议

---

## 🚫 未版本控制的文件

### 数据和运行时文件（自动忽略）
- `data/` - 数据库、日志、缓存
- `faces/` - 人脸照片
- `__pycache__/` - Python 缓存

### 测试和诊断文件（可选提交）
- `test_*.py` - 测试脚本
- `*_test.py` - 测试文件
- `diagnose_*.py` - 诊断脚本
- `verify_*.py` - 验证脚本

### 临时文档（可选提交）
- `CURRENT_STATUS.md` - 当前状态
- `FIX_*.md` - 修复记录
- `README_FIX.md` - 修复索引

---

## 🔧 常用 Git 操作

### 查看状态
```bash
git status
```

### 查看日志
```bash
git log --oneline
git log --graph --all
```

### 查看分支
```bash
git branch
git branch -a
```

### 创建新分支
```bash
git branch feature-new-function
git checkout feature-new-function
```

### 添加文件
```bash
# 添加单个文件
git add filename.py

# 添加所有更改
git add .

# 添加特定类型文件
git add *.py
```

### 提交更改
```bash
git commit -m "描述更改内容"
```

### 推送更改
```bash
# 首次推送
git remote add origin https://github.com/username/repo.git
git push -u origin master

# 后续推送
git push
```

### 拉取更新
```bash
git pull origin master
```

---

## 📋 推荐的工作流程

### 功能开发流程

1. **创建功能分支**
   ```bash
   git checkout -b feature-name
   ```

2. **开发和测试**
   ```bash
   # 修改代码...
   python main.py  # 测试
   ```

3. **提交更改**
   ```bash
   git add .
   git commit -m "Add new feature: description"
   ```

4. **合并到主分支**
   ```bash
   git checkout master
   git merge feature-name
   ```

### 文档更新流程

1. **更新文档**
   ```bash
   # 修改 README.md 或其他文档
   ```

2. **提交文档**
   ```bash
   git add README.md
   git commit -m "Update documentation"
   ```

---

## 🎯 提交信息规范

### 格式
```
<类型>: <简短描述>

<详细说明（可选）>

类型: feat, fix, docs, style, refactor, test, chore
```

### 示例
```bash
# 新功能
git commit -m "feat: Add department statistics dashboard"

# 修复问题
git commit -m "fix: Resolve face detection error in low light conditions"

# 文档更新
git commit -m "docs: Update installation guide with conda instructions"

# 重构代码
git commit -m "refactor: Optimize face recognition performance"
```

---

## 🔍 检查点和标签

### 创建标签（版本发布）
```bash
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

### 查看标签
```bash
git tag
git show v1.0.0
```

---

## 📊 项目统计

### 代码统计
```bash
# 统计代码行数
git ls-files | xargs wc -l

# 查看文件列表
git ls-files
```

### 提交统计
```bash
# 提交数量
git rev-list --count HEAD

# 贡献者统计
git shortlog -sn
```

---

## 🚨 故障排除

### 问题: 提交信息编辑错误
```bash
# 修改最后一次提交
git commit --amend -m "新的提交信息"

# 修改历史提交信息（危险操作）
git rebase -i HEAD~3
```

### 问题: 添加了错误的文件
```bash
# 从暂存区移除
git reset HEAD <file>

# 完全删除文件
git rm --cached <file>
```

### 问题: 需要撤销提交
```bash
# 撤销最后一次提交，保留更改
git reset --soft HEAD~1

# 撤销最后一次提交，丢弃更改
git reset --hard HEAD~1
```

---

## 📞 备份和恢复

### 备份当前状态
```bash
# 创建备份分支
git branch backup-$(date +%Y%m%d)
```

### 恢复到特定提交
```bash
# 查看历史
git log --oneline

# 恢复到特定提交
git checkout <commit-hash>
```

---

## 🎉 总结

**Git 管理已设置完成！**

当前状态：
- ✅ Git 仓库已初始化
- ✅ 核心文件已提交
- ✅ .gitignore 已配置
- ✅ README.md 已创建
- ✅ 初始提交已完成

**下一步：**
1. 如需远程仓库，使用 `git remote add` 添加
2. 如需协作，创建功能分支进行开发
3. 定期提交更改并推送更新

**版本控制最佳实践：**
- 经常提交小更改
- 写清楚的提交信息
- 使用分支进行实验性开发
- 定期拉取更新
- 创建标签标记重要版本

**享受您的版本控制之旅！** 🎉
