# 贡献指南 Contributing Guide

感谢你对本项目的关注！我们欢迎各种形式的贡献。

---

## 🎯 贡献方式

### 报告 Bug
如果你发现了 bug，请通过 [GitHub Issues](https://github.com/yourusername/werewolf_game/issues) 提交问题，包括：
- 问题描述
- 复现步骤
- 期望行为
- 实际行为
- 系统环境信息

### 提出新功能
如果你有新功能的想法：
1. 先在 Issues 中讨论
2. 等待社区反馈
3. 获得认可后再开始开发

### 提交代码
1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature-name`
3. 提交代码：`git commit -m 'Add some feature'`
4. 推送分支：`git push origin feature/your-feature-name`
5. 提交 Pull Request

---

## 📝 代码规范

### Python 代码风格
- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 规范
- 使用 4 个空格缩进
- 每行不超过 120 个字符
- 使用有意义的变量名

### 注释规范
```python
def function_name(param1: str, param2: int) -> bool:
    """
    函数的简短描述。
    
    Args:
        param1 (str): 参数1的描述
        param2 (int): 参数2的描述
        
    Returns:
        bool: 返回值的描述
    """
    pass
```

### 提交信息规范
使用清晰的提交信息：
- ✨ `feat:` 新功能
- 🐛 `fix:` Bug 修复
- 📚 `docs:` 文档更新
- 🎨 `style:` 代码格式调整
- ♻️ `refactor:` 代码重构
- ⚡ `perf:` 性能优化
- ✅ `test:` 测试相关
- 🔧 `chore:` 构建/工具配置

示例：
```
feat: 添加守卫角色
fix: 修复女巫解药无效的问题
docs: 更新 README 中的安装说明
```

---

## 🧪 测试

在提交 PR 之前，请确保：
- [ ] 代码能正常运行
- [ ] 没有破坏现有功能
- [ ] 添加了必要的注释
- [ ] 更新了相关文档

---

## 📖 开发建议

### 添加新角色
1. 在 `prompts/` 创建角色提示词文件
2. 在 `configs.py` 添加角色配置
3. 在 `game_master.py` 实现角色逻辑
4. 更新胜负判定条件
5. 添加测试用例

### 优化 AI 策略
1. 修改 `prompts/` 中的系统提示词
2. 调整上下文注入的信息量
3. 测试不同模型的表现
4. 记录优化结果

### 改进日志系统
1. 在 `logger.py` 中扩展功能
2. 保持日志格式的一致性
3. 考虑日志文件大小
4. 添加日志过滤功能

---

## 🤔 问题讨论

如果你有任何疑问：
1. 查看 [文档](README.md)
2. 搜索 [已有 Issues](https://github.com/yourusername/werewolf_game/issues)
3. 在 [Discussions](https://github.com/yourusername/werewolf_game/discussions) 中提问

---

## 📜 代码审查

所有 Pull Request 都需要经过代码审查。审查重点：
- 代码质量和可读性
- 功能完整性
- 性能影响
- 文档完善度

---

## 🎉 致谢

感谢所有贡献者！你们的努力让这个项目变得更好。

贡献者列表：[Contributors](https://github.com/yourusername/werewolf_game/graphs/contributors)
