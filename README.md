# cyn-py-vsc：Python + VS Code 练习仓库

这是陈以诺（cyn）的 Python 练习 / Git 练习仓库，使用 **Visual Studio Code** 打开和维护。

- 仓库名含义：`cyn` = 陈以诺，`py` = Python，`vsc` = Visual Studio Code。
- 保留原有的 `hello.py` 练习代码和 Git 历史（合并、分支、标签等练习记录）。
- 本次新增：随机四则运算公式工具、pytest 测试、以及一整套 **git 各类指令功能测试**。

## 目录结构

```
cyn-py-vsc/
├─ hello.py                     # 原有练习代码（保留）
├─ random_formula.py            # 随机公式生成 / 安全求值 / 导出工具
├─ requirements.txt             # Python 依赖（pytest）
├─ pytest.ini                   # pytest 配置（pythonpath、tests 目录）
├─ tests/
│  └─ test_random_formula.py    # 随机公式工具的 pytest 测试
├─ scripts/
│  └─ git_functional_test.py    # git 指令功能测试（用随机公式作为测试内容）
├─ .vscode/                     # VS Code 本地配置（已被 .gitignore 忽略）
│  ├─ settings.json             # 解释器指向 .venv + 开启 pytest 测试发现
│  ├─ launch.json               # F5 调试：当前文件 / pytest / git 功能测试
│  ├─ tasks.json                # 测试、git 功能测试、公式演示任务
│  └─ extensions.json           # 推荐扩展
└─ .venv/                       # 本机虚拟环境（已被 .gitignore 忽略）
```

## 环境配置（本机已执行）

```powershell
# 1. 创建虚拟环境
python -m venv .venv

# 2. 安装 pytest（国内镜像，避免外网超时）
.\.venv\Scripts\python.exe -m pip install -i https://mirrors.cloud.tencent.com/pypi/simple pytest
```

- Python：3.14
- pytest：9.1.1
- VS Code：1.142.0（已安装 Python / Pylance / Debugpy / GitLens 扩展）

## 运行测试

```powershell
# pytest 单元测试
.\.venv\Scripts\python.exe -m pytest tests -v

# 随机公式演示
.\.venv\Scripts\python.exe random_formula.py --count 8 --seed 2026

# git 各类指令功能测试（本地约 40 项检查）
.\.venv\Scripts\python.exe scripts\git_functional_test.py

# 附带 GitHub 远程访问验证（ls-remote / 浅克隆）
.\.venv\Scripts\python.exe scripts\git_functional_test.py --github
```

在 VS Code 中：

- 左侧 **测试** 面板可直接 Run All Tests（pytest）；
- 按 `Ctrl+Shift+P` → **Tasks: Run Test Task** 可运行默认任务“运行全部测试（pytest）”；
- 在 **运行和调试** 面板选择“Python: 运行 git 指令功能测试”可按 F5 运行。

## git 指令功能测试覆盖范围

`scripts/git_functional_test.py` 会在 `.git-tests/<时间戳>/` 下创建临时仓库，写入随机公式文件，然后逐项校验：

- 仓库：`init`、`config`、`status`、`add`、`commit`、`log`、`show`、`diff`、`rev-parse`、`ls-files`、`fsck`、`gc`、`archive`
- 分支：`branch`、`switch`、`merge --no-ff`、合并冲突产生与解决
- 标签：`tag -a`、`tag --list`、推送标签
- 撤销与整理：`stash push/pop`、`revert`、`reset --soft/--mixed/--hard`、`cherry-pick`、`rebase`
- 文件操作：`rm --cached`、`mv`、`clean`、`check-ignore`、`blame`
- 远端：`init --bare`、`remote add`、`push`、`ls-remote`、`clone`、`fetch`、`pull`、`worktree`

每一批测试内容都是**随机生成的算式**（例如 `(7 + 19) / 4 = 6.5`），因此每次运行都会写入不同的公式文件。

## GitHub 访问（本机已配置）

本机通过 SSH 访问 GitHub（HTTPS 被本机 hosts 中的 Steam++ 记录指向 127.0.0.1，因此 Git 统一走 SSH）：

```powershell
# 已写入用户级 Git 配置：
git config --global core.sshCommand "C:/Windows/System32/OpenSSH/ssh.exe"
git config --global url."git@github.com:".insteadOf "https://github.com/"
```

验证：

```powershell
ssh -T git@github.com        # Hi grf01m203! You've successfully authenticated
git ls-remote https://github.com/grf01m203/cyn-py-vsc.git
```

日常命令：

```powershell
git pull --rebase origin master
git add .
git commit -m "test(git): 随机公式与 git 指令功能测试"
git push origin master
```
