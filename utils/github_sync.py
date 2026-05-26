"""GitHub 数据源同步 —— git clone / pull + 变更检测 + 增量索引"""

import os
import glob
import hashlib
import logging
import time
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class GitHubSyncManager:
    def __init__(self):
        from config import Config

        self.repo_url = Config.GITHUB_REPO_URL
        self.branch = Config.GITHUB_BRANCH
        self.token = Config.GITHUB_TOKEN
        self.local_path = Config.GITHUB_LOCAL_PATH
        self.doc_patterns = Config.GITHUB_DOC_PATTERNS
        self._repo = None
        self._last_sync = 0
        self._last_commit = None

    @property
    def configured(self) -> bool:
        return bool(self.repo_url)

    @property
    def cloned(self) -> bool:
        return os.path.isdir(os.path.join(self.local_path, ".git"))

    def _get_auth_url(self) -> str:
        if self.token and self.repo_url.startswith("https://"):
            # 将 token 嵌入 URL 用于认证
            url = self.repo_url.replace("https://", f"https://{self.token}@")
            return url
        return self.repo_url

    # ── Clone / Pull ─────────────────────────────────────

    def clone(self) -> Tuple[bool, str]:
        """首次克隆仓库"""
        if self.cloned:
            return True, "仓库已存在，跳过克隆"

        os.makedirs(os.path.dirname(self.local_path), exist_ok=True)
        try:
            import git

            url = self._get_auth_url()
            logger.info(f"克隆仓库: {self.repo_url} → {self.local_path}")
            self._repo = git.Repo.clone_from(url, self.local_path, branch=self.branch, depth=1)
            self._last_commit = self._repo.head.commit.hexsha
            self._last_sync = time.time()
            return True, f"克隆成功: {self._repo.head.commit.hexsha[:8]}"
        except Exception as e:
            error_msg = str(e).replace(self.token, "***") if self.token else str(e)
            logger.error(f"克隆失败: {error_msg}")
            return False, f"克隆失败: {error_msg}"

    def pull(self) -> Tuple[bool, str, List[str]]:
        """拉取最新变更，返回变更文件列表"""
        if not self.cloned:
            return False, "仓库尚未克隆，请先执行 clone", []

        try:
            import git

            if self._repo is None:
                self._repo = git.Repo(self.local_path)

            old_commit = self._repo.head.commit.hexsha

            # 拉取
            origin = self._repo.remotes.origin
            origin.pull(self.branch)

            new_commit = self._repo.head.commit.hexsha

            if old_commit == new_commit:
                self._last_sync = time.time()
                return True, "已是最新，无变更", []

            # 获取变更文件
            changed_files = self._get_changed_files(old_commit, new_commit)

            self._last_commit = new_commit
            self._last_sync = time.time()
            logger.info(f"拉取成功: {old_commit[:8]} → {new_commit[:8]}, {len(changed_files)} 文件变更")
            return True, f"更新成功: {old_commit[:8]} → {new_commit[:8]}", changed_files

        except Exception as e:
            error_msg = str(e).replace(self.token, "***") if self.token else str(e)
            logger.error(f"拉取失败: {error_msg}")
            return False, f"拉取失败: {error_msg}", []

    # ── 变更检测 ─────────────────────────────────────────

    def _get_changed_files(self, old_commit: str, new_commit: str) -> List[str]:
        """通过 git diff 获取变更的文件"""
        changed = []
        try:
            import git

            if self._repo is None:
                self._repo = git.Repo(self.local_path)
            diff = self._repo.git.diff("--name-only", old_commit, new_commit)
            for line in diff.split("\n"):
                line = line.strip()
                if line and self._matches_pattern(line):
                    abs_path = os.path.join(self.local_path, line)
                    if os.path.exists(abs_path):
                        changed.append(abs_path)
        except Exception as e:
            logger.warning(f"Git diff 失败，回退到文件扫描: {e}")
            changed = self._scan_files()
        return changed

    def _matches_pattern(self, filename: str) -> bool:
        import fnmatch

        return any(fnmatch.fnmatch(filename.lower(), p) for p in self.doc_patterns)

    def _scan_files(self) -> List[str]:
        """全量扫描匹配的文件"""
        files = []
        for pattern in self.doc_patterns:
            search = os.path.join(self.local_path, "**", pattern)
            files.extend(glob.glob(search, recursive=True))
        # 排除 .git 目录
        files = [f for f in files if ".git" not in f.replace(os.sep, "/").split("/")]
        return files

    def list_documents(self) -> List[str]:
        """列出所有可索引的文档文件"""
        if not self.cloned:
            return []
        return self._scan_files()

    # ── 文件哈希（用于增量索引） ─────────────────────────

    def file_hash(self, file_path: str) -> str:
        return hashlib.md5(open(file_path, "rb").read()).hexdigest()

    # ── 状态 ─────────────────────────────────────────────

    def get_status(self) -> dict:
        status = {
            "configured": self.configured,
            "repo_url": self.repo_url.replace(self.token, "***") if self.token else self.repo_url,
            "branch": self.branch,
            "cloned": self.cloned,
            "local_path": self.local_path,
            "last_sync": self._last_sync,
            "last_commit": self._last_commit[:8] if self._last_commit else None,
            "document_count": len(self.list_documents()) if self.cloned else 0,
        }
        if self.cloned and self._repo:
            try:
                status["current_commit"] = self._repo.head.commit.hexsha[:8]
            except Exception:
                pass
        return status


# ── 全局实例 ─────────────────────────────────────────────

_sync_manager: Optional[GitHubSyncManager] = None


def get_github_sync() -> GitHubSyncManager:
    global _sync_manager
    if _sync_manager is None:
        _sync_manager = GitHubSyncManager()
    return _sync_manager
