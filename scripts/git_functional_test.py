"""git 各类指令功能测试，使用随机四则运算公式作为测试内容。

测试会在本仓库内创建临时目录，生成随机公式文件，然后依次执行并校验：

    init / config / status / add / commit / log / show / diff / branch / switch
    merge（含冲突解决）/ tag / stash / revert / reset（soft/mixed/hard）/
    cherry-pick / rebase / blame / rev-parse / ls-files / rm --cached / mv /
    clean / check-ignore / fsck / gc / remote / push / ls-remote / clone /
    fetch / pull / worktree

用法：

    .venv\\Scripts\\python.exe scripts\\git_functional_test.py
    .venv\\Scripts\\python.exe scripts\\git_functional_test.py --github
    .venv\\Scripts\\python.exe scripts\\git_functional_test.py --keep   # 保留临时目录
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from random_formula import evaluate, generate_formulas, write_formulas  # noqa: E402

GIT = shutil.which("git") or "git"
GIT_ENV = {
    **os.environ,
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_CONFIG_NOSYSTEM": "1",
}
IDENTITY = [
    "-c",
    "user.name=Git Functional Test",
    "-c",
    "user.email=git-functional-test@example.com",
    "-c",
    "commit.gpgsign=false",
]


class Checks:
    """收集每个 git 指令的通过 / 失败情况。"""

    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.failures: list[tuple[str, str]] = []

    def record_pass(self, name: str) -> None:
        self.passed += 1
        print(f"[PASS] {name}")

    def record_fail(self, name: str, error: str) -> None:
        self.failed += 1
        self.failures.append((name, error))
        print(f"[FAIL] {name}：{error}")


class step:
    """上下文管理器：捕获异常后继续执行后续测试。"""

    def __init__(self, checks: Checks, name: str) -> None:
        self.checks = checks
        self.name = name

    def __enter__(self) -> "step":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:  # noqa: ANN001
        if exc is None:
            self.checks.record_pass(self.name)
        else:
            self.checks.record_fail(self.name, str(exc))
        return True  # 吞掉异常，让测试继续


def git(cwd: Path | str, *args: str, check: bool = True, input_text: str | None = None):
    result = subprocess.run(
        [GIT, *IDENTITY, *args],
        cwd=str(cwd),
        env=GIT_ENV,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} 退出码 {result.returncode}："
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return result


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def rev(cwd: Path, *ref: str) -> str:
    return git(cwd, "rev-parse", *(ref or ("HEAD",))).stdout.strip()


def write_batch(directory: Path, batch: int, seed: int, count: int = 6) -> Path:
    """写入一批随机公式文件，返回文件路径。"""
    formulas = generate_formulas(count, seed=seed)
    return write_formulas(directory / f"batch-{batch:03d}.txt", formulas)


def check_formula_file(path: Path) -> None:
    """确认文件内容确实是可求值的随机公式。"""
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    require(len(lines) > 0, f"{path.name} 没有内容")
    for line in lines:
        expression = line.rsplit(" = ", 1)[0]
        evaluate(expression)


def run_local_suite(root: Path, checks: Checks) -> None:
    repo = root / "formula-repo"
    remote = root / "formula-remote.git"
    clone = root / "formula-clone"

    with step(checks, "git init（初始化仓库，默认分支 main）"):
        git(root, "init", "-b", "main", str(repo))
        require((repo / ".git").exists(), ".git 目录不存在")
        current_branch = git(repo, "symbolic-ref", "--short", "HEAD").stdout.strip()
        require(current_branch == "main", f"默认分支不是 main：{current_branch}")

    with step(checks, "git config（读写仓库级配置）"):
        git(repo, "config", "user.name", "Git Functional Test")
        require(git(repo, "config", "--get", "user.name").stdout.strip() == "Git Functional Test",
                "user.name 配置读取不一致")

    with step(checks, "写入随机公式文件"):
        batch1 = write_batch(repo / "formulas", 1, seed=101)
        check_formula_file(batch1)

    with step(checks, "git status（未跟踪文件）"):
        status = git(repo, "status", "--porcelain").stdout
        require("formulas/" in status, f"status 未显示未跟踪文件：{status!r}")

    with step(checks, "git add（暂存文件）"):
        git(repo, "add", ".")
        staged = git(repo, "diff", "--cached", "--name-only").stdout
        require("formulas/batch-001.txt" in staged, "文件没有被暂存")

    with step(checks, "git commit（首次提交）"):
        git(repo, "commit", "-m", "test(git): 加入第 1 批随机公式")
        require(git(repo, "rev-list", "--count", "HEAD").stdout.strip() == "1", "提交数量不是 1")

    with step(checks, "git log（查看提交历史）"):
        subject = git(repo, "log", "-1", "--format=%s").stdout.strip()
        require(subject == "test(git): 加入第 1 批随机公式", f"log 主题不一致：{subject!r}")

    with step(checks, "git show（查看提交内容）"):
        output = git(repo, "show", "--stat", "--oneline", "HEAD").stdout
        require("formulas/batch-001.txt" in output, "show 未包含公式文件")

    with step(checks, "git branch（创建分支）"):
        git(repo, "branch", "feature")
        branches = git(repo, "branch", "--list", "feature").stdout
        require("feature" in branches, "feature 分支不存在")

    with step(checks, "git switch（切换分支）"):
        git(repo, "switch", "feature")
        require(rev(repo, "--abbrev-ref", "HEAD") == "feature", "没有切换到 feature")

    with step(checks, "git diff（工作区差异）"):
        extra_formula = generate_formulas(1, seed=999)[0]
        with (repo / "formulas" / "batch-001.txt").open("a", encoding="utf-8") as file:
            file.write(extra_formula.format() + "\n")
        diff = git(repo, "diff").stdout
        require(extra_formula.expression in diff, "diff 未显示新增内容")

    with step(checks, "feature 分支上的第二次提交"):
        write_batch(repo / "formulas", 2, seed=202)
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "feat: feature 分支加入第 2 批公式")
        require(git(repo, "rev-list", "--count", "HEAD").stdout.strip() == "2", "提交数量不是 2")

    with step(checks, "git diff main..feature（分支差异）"):
        stat = git(repo, "diff", "--stat", "main..feature").stdout
        require("batch-002.txt" in stat, "分支差异中没有新公式文件")

    with step(checks, "git merge --no-ff（合并分支）"):
        git(repo, "switch", "main")
        git(repo, "merge", "--no-ff", "feature", "-m", "merge: 合并 feature 分支")
        merges = git(repo, "rev-list", "--merges", "--count", "HEAD").stdout.strip()
        require(merges == "1", f"没有生成合并提交：{merges}")
        require((repo / "formulas" / "batch-002.txt").exists(), "合并后缺少第 2 批公式")

    with step(checks, "git tag（附注标签）"):
        git(repo, "tag", "-a", "v1.0", "-m", "v1.0 功能测试标签")
        tags = git(repo, "tag", "--list").stdout
        require("v1.0" in tags, "v1.0 标签不存在")
        require(rev(repo, "v1.0^{commit}") == rev(repo), "标签与 HEAD 不一致")

    with step(checks, "git stash（暂存与恢复修改）"):
        with (repo / "formulas" / "batch-001.txt").open("a", encoding="utf-8") as file:
            file.write("# STASH-MARKER\n")
        git(repo, "stash", "push", "-m", "stash 功能测试")
        require("STASH-MARKER" not in (repo / "formulas" / "batch-001.txt").read_text(encoding="utf-8"),
                "stash 后工作区仍有修改")
        require("stash 功能测试" in git(repo, "stash", "list").stdout, "stash list 中没有记录")
        git(repo, "stash", "pop")
        require("STASH-MARKER" in (repo / "formulas" / "batch-001.txt").read_text(encoding="utf-8"),
                "stash pop 后修改没有恢复")
        git(repo, "checkout", "--", "formulas/batch-001.txt")

    with step(checks, "git merge（冲突产生与解决）"):
        git(repo, "switch", "-c", "conflict")
        (repo / "shared.txt").write_text("同一行来自 conflict 分支\n", encoding="utf-8")
        git(repo, "add", "shared.txt")
        git(repo, "commit", "-m", "test: conflict 分支修改共享文件")
        git(repo, "switch", "main")
        (repo / "shared.txt").write_text("同一行来自 main 分支\n", encoding="utf-8")
        git(repo, "add", "shared.txt")
        git(repo, "commit", "-m", "test: main 分支修改共享文件")
        merge_result = git(repo, "merge", "conflict", check=False)
        require(merge_result.returncode != 0, "应当产生合并冲突，但合并成功了")
        require("<<<<<<<" in (repo / "shared.txt").read_text(encoding="utf-8"), "冲突文件中没有标记")
        (repo / "shared.txt").write_text("已解决的共享内容\n", encoding="utf-8")
        git(repo, "add", "shared.txt")
        git(repo, "commit", "-m", "merge: 解决共享文件冲突")

    with step(checks, "git revert（撤销普通提交）"):
        (repo / "revert-me.txt").write_text("将被撤销的文件\n", encoding="utf-8")
        git(repo, "add", "revert-me.txt")
        git(repo, "commit", "-m", "test: 待撤销的提交")
        git(repo, "revert", "--no-edit", "HEAD")
        require(not (repo / "revert-me.txt").exists(), "revert 后文件仍然存在")

    with step(checks, "git reset --soft（软重置）"):
        (repo / "soft-reset.txt").write_text("软重置内容\n", encoding="utf-8")
        git(repo, "add", "soft-reset.txt")
        git(repo, "commit", "-m", "test: 软重置前的提交")
        git(repo, "reset", "--soft", "HEAD~1")
        staged = git(repo, "diff", "--cached", "--name-only").stdout
        require("soft-reset.txt" in staged, "reset --soft 后没有保留暂存内容")
        git(repo, "commit", "-m", "test: 软重置后重新提交")

    with step(checks, "git reset --hard（硬重置）"):
        (repo / "formulas" / "batch-001.txt").write_text("垃圾内容\n", encoding="utf-8")
        git(repo, "reset", "--hard", "HEAD")
        require(git(repo, "status", "--porcelain").stdout.strip() == "", "reset --hard 后工作区不干净")
        check_formula_file(repo / "formulas" / "batch-001.txt")

    with step(checks, "git reset --mixed（默认重置）"):
        (repo / "mixed-reset.txt").write_text("混合重置内容\n", encoding="utf-8")
        git(repo, "add", "mixed-reset.txt")
        git(repo, "commit", "-m", "test: 混合重置前的提交")
        git(repo, "reset", "HEAD~1")
        status = git(repo, "status", "--porcelain").stdout
        require("mixed-reset.txt" in status, "reset 后文件应变为未跟踪")

    with step(checks, "git cherry-pick（挑选提交）"):
        git(repo, "switch", "-c", "cherry", "main")
        (repo / "cherry.txt").write_text("cherry-pick 内容\n", encoding="utf-8")
        git(repo, "add", "cherry.txt")
        git(repo, "commit", "-m", "test: cherry 分支的提交")
        cherry_sha = rev(repo)
        git(repo, "switch", "main")
        git(repo, "cherry-pick", cherry_sha)
        require((repo / "cherry.txt").exists(), "cherry-pick 后文件不存在")
        require("cherry" in git(repo, "log", "-1", "--format=%s").stdout, "cherry-pick 提交信息不一致")

    with step(checks, "git rebase（变基保持线性历史）"):
        git(repo, "switch", "-c", "rebase", "main")
        (repo / "rebase.txt").write_text("rebase 内容\n", encoding="utf-8")
        git(repo, "add", "rebase.txt")
        git(repo, "commit", "-m", "test: rebase 分支的提交")
        git(repo, "switch", "main")
        (repo / "mainline.txt").write_text("main 分支新内容\n", encoding="utf-8")
        git(repo, "add", "mainline.txt")
        git(repo, "commit", "-m", "test: main 分支前进")
        git(repo, "switch", "rebase")
        git(repo, "rebase", "main")
        require((repo / "mainline.txt").exists(), "rebase 后缺少 main 的新提交内容")
        require((repo / "rebase.txt").exists(), "rebase 后缺少本分支内容")
        require(git(repo, "rev-list", "--merges", "--count", "main..rebase").stdout.strip() == "0",
                "rebase 后不应存在合并提交")

    with step(checks, "git blame（逐行追溯）"):
        blame = git(repo, "blame", "formulas/batch-001.txt").stdout
        require("Git Functional Test" in blame, "blame 输出中没有提交者")

    with step(checks, "git rev-parse / git ls-files（对象与索引查询）"):
        head = rev(repo)
        require(len(head) == 40 and all(char in "0123456789abcdef" for char in head), f"HEAD 格式不正确：{head}")
        tracked = git(repo, "ls-files").stdout
        require("formulas/batch-001.txt" in tracked, "ls-files 中没有公式文件")

    with step(checks, "git rm --cached（取消跟踪但保留文件）"):
        (repo / "untrack.txt").write_text("取消跟踪\n", encoding="utf-8")
        git(repo, "add", "untrack.txt")
        git(repo, "commit", "-m", "test: 添加待取消跟踪文件")
        git(repo, "rm", "--cached", "untrack.txt")
        require((repo / "untrack.txt").exists(), "rm --cached 后磁盘文件被删除了")
        require("untrack.txt" in git(repo, "status", "--porcelain").stdout, "rm --cached 后状态未变化")

    with step(checks, "git mv（重命名并跟踪）"):
        (repo / "move-me.txt").write_text("移动文件\n", encoding="utf-8")
        git(repo, "add", "move-me.txt")
        git(repo, "commit", "-m", "test: 添加待移动文件")
        git(repo, "mv", "move-me.txt", "moved.txt")
        require((repo / "moved.txt").exists(), "git mv 后新文件不存在")
        require("moved.txt" in git(repo, "status", "--porcelain").stdout, "git mv 后状态未更新")

    with step(checks, "git clean（清理未跟踪文件）"):
        (repo / "junk.tmp").write_text("临时文件\n", encoding="utf-8")
        git(repo, "clean", "-f", "--", "junk.tmp")
        require(not (repo / "junk.tmp").exists(), "git clean 后临时文件仍然存在")

    with step(checks, "git check-ignore（忽略规则校验）"):
        (repo / ".gitignore").write_text("*.tmp\n", encoding="utf-8")
        git(repo, "add", ".gitignore")
        git(repo, "commit", "-m", "chore: 增加忽略规则")
        (repo / "ignored.tmp").write_text("被忽略\n", encoding="utf-8")
        result = git(repo, "check-ignore", "ignored.tmp", check=False)
        require(result.returncode == 0, "check-ignore 没有命中忽略规则")

    with step(checks, "git fsck（仓库完整性）"):
        result = git(repo, "fsck", "--no-dangling", check=False)
        require(result.returncode == 0, f"fsck 失败：{result.stderr.strip()}")

    with step(checks, "git gc（垃圾回收）"):
        git(repo, "gc")

    with step(checks, "git init --bare / remote / push / ls-remote（本地远端）"):
        git(root, "init", "--bare", str(remote))
        git(repo, "remote", "add", "origin", str(remote))
        git(repo, "push", "-u", "origin", "main")
        git(repo, "push", "origin", "v1.0")
        refs = git(repo, "ls-remote", "origin").stdout
        require("refs/heads/main" in refs, "远端缺少 main 分支")
        require("refs/tags/v1.0" in refs, "远端缺少 v1.0 标签")

    with step(checks, "git clone（克隆远端）"):
        git(root, "clone", str(remote), str(clone))
        require((clone / "formulas" / "batch-001.txt").exists(), "clone 后缺少公式文件")

    with step(checks, "git fetch / git pull（同步远端）"):
        git(repo, "switch", "main")
        (repo / "fetch-me.txt").write_text("fetch/pull 内容\n", encoding="utf-8")
        git(repo, "add", "fetch-me.txt")
        git(repo, "commit", "-m", "test: fetch/pull 演示提交")
        git(repo, "push")
        git(clone, "fetch", "origin")
        require("refs/remotes/origin/main" in git(clone, "show-ref").stdout, "fetch 后没有远程分支引用")
        git(clone, "pull", "--ff-only")
        require((clone / "fetch-me.txt").exists(), "pull 后缺少新提交的文件")

    with step(checks, "git worktree（多工作区）"):
        worktree = root / "formula-wt"
        git(repo, "worktree", "add", "--detach", str(worktree), "HEAD")
        require((worktree / "formulas" / "batch-001.txt").exists(), "worktree 中缺少文件")
        git(repo, "worktree", "remove", str(worktree))

    with step(checks, "git archive（导出快照）"):
        archive = root / "snapshot.zip"
        git(repo, "archive", "--format=zip", "-o", str(archive), "HEAD")
        require(archive.exists() and archive.stat().st_size > 0, "archive 没有生成文件")


def run_github_checks(root: Path, checks: Checks) -> None:
    github_url = "https://github.com/grf01m203/cyn-py-vsc.git"
    github_clone = root / "github-clone"

    with step(checks, "GitHub：git ls-remote（通过 SSH 改写访问远程仓库）"):
        refs = git(root, "ls-remote", github_url).stdout
        require("refs/heads/master" in refs, "远程仓库缺少 master 分支")

    with step(checks, "GitHub：git clone --depth 1（浅克隆远程仓库）"):
        git(root, "clone", "--depth", "1", github_url, str(github_clone))
        require((github_clone / "hello.py").exists(), "克隆结果缺少 hello.py")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="git 各类指令功能测试")
    parser.add_argument("--github", action="store_true", help="额外验证 GitHub 远程访问（ls-remote / 浅克隆）")
    parser.add_argument("--keep", action="store_true", help="保留测试产生的临时目录")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    work_root = REPO_ROOT / ".git-tests" / timestamp
    work_root.mkdir(parents=True, exist_ok=True)

    checks = Checks()
    print("=" * 60)
    print("git 指令功能测试（内容：随机四则运算公式）")
    print("临时目录：" + str(work_root))
    print("=" * 60)

    run_local_suite(work_root, checks)
    if args.github:
        run_github_checks(work_root, checks)

    print("=" * 60)
    print(f"结果：{checks.passed + checks.failed} 项检查，通过 {checks.passed}，失败 {checks.failed}")
    if checks.failures:
        print("失败列表：")
        for name, error in checks.failures:
            print(f"  - {name}：{error}")
    print("=" * 60)

    if not args.keep and checks.failed == 0:
        shutil.rmtree(work_root, ignore_errors=True)
    return 0 if checks.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
