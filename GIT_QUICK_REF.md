# Git 快速参考卡

## 常用命令速查

### 🔍 状态查看
```bash
git status              # 查看当前状态
git log --oneline       # 查看提交历史
git branch               # 查看分支
```

### ➕ 添加和提交
```bash
git add .               # 添加所有更改
git add file.py         # 添加单个文件
git commit -m "msg"     # 提交更改
```

### 🔄 分支操作
```bash
git branch new-branch                    # 创建分支
git checkout new-branch                  # 切换分支
git checkout -b new-branch              # 创建并切换
git merge branch                          # 合并分支
git branch -d branch                      # 删除分支
```

### 📡 远程仓库
```bash
git remote add origin https://github.com/user/repo.git
git push -u origin master                  # 首次推送
git push                                   # 后续推送
git pull                                   # 拉取更新
```

## 提交信息格式

```bash
# 新功能
feat: Add feature description

# 修复问题
fix: Fix bug description

# 文档更新
docs: Update documentation

# 重构
refactor: Optimize code structure

# 测试
test: Add test for feature
```

## 常见场景

### 修改代码后提交
```bash
git add .
git commit -m "feat: Add new functionality"
git push
```

### 撤销最后一次提交
```bash
git reset --soft HEAD~1
# 修改后重新提交
git add .
git commit -m "fixed message"
```

### 查看文件历史
```bash
git log --follow file.py
git blame file.py
```

### 暂存更改
```bash
git stash                    # 暂存当前更改
git stash pop              # 恢复暂存的更改
```

## 项目特定

### 忽略的文件/目录
- `data/` - 数据库、日志
- `faces/` - 人脸照片
- `__pycache__/` - Python 缓存
- `test_*.py` - 测试文件

### 已版本控制的核心文件
- `*.py` - 源代码
- `templates/` - Web 模板
- `requirements.txt` - 依赖
- `*.md` - 文档
- `run_with_conda.bat` - 启动脚本
