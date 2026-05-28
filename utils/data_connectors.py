"""TOC 提取器 + Notion/S3 数据源连接器

TOC: 从 Markdown/PDF 提取文档目录层级结构
Notion: Notion API 数据库/页面同步
S3: S3 兼容存储桶文件同步
"""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════
# TOC 提取器
# ══════════════════════════════════════════


def extract_toc_from_markdown(content: str, max_depth: int = 3) -> list[dict]:
    """从 Markdown 内容提取目录结构。

    Returns:
        [{"level": 1-3, "title": "标题文本", "line": N, "children": [...]}, ...]
    """
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+?)(?:\s*\{.*?\})?\s*$", re.MULTILINE)
    toc = []
    stack: list[dict] = []  # parent chain

    for match in heading_pattern.finditer(content):
        level = len(match.group(1))
        title = match.group(2).strip()
        line = content[: match.start()].count("\n") + 1

        if level > max_depth:
            continue

        entry = {"level": level, "title": title, "line": line, "children": []}

        # Find parent
        while stack and stack[-1]["level"] >= level:
            stack.pop()

        if stack:
            stack[-1]["children"].append(entry)
        else:
            toc.append(entry)

        stack.append(entry)

    return toc


def extract_toc_from_pdf(pdf_path: str, max_depth: int = 3) -> list[dict]:
    """从 PDF 提取目录（使用 PyMuPDF 内置 TOC）"""
    try:
        import fitz

        doc = fitz.open(pdf_path)
        raw_toc = doc.get_toc()
        doc.close()

        if not raw_toc:
            return []

        toc = []
        stack: list[dict] = []

        for level, title, page in raw_toc:
            if level > max_depth:
                continue
            entry = {"level": level, "title": title.strip(), "page": page, "children": []}
            while stack and stack[-1]["level"] >= level:
                stack.pop()
            if stack:
                stack[-1]["children"].append(entry)
            else:
                toc.append(entry)
            stack.append(entry)

        return toc
    except Exception as e:
        logger.warning(f"PDF TOC 提取失败: {e}")
        return []


def toc_to_tree_string(toc: list[dict], indent: int = 0) -> str:
    """目录 → 树状字符串（用于 LLM 上下文）"""
    lines = []
    for entry in toc:
        prefix = "  " * indent + ("├─ " if indent > 0 else "")
        lines.append(f"{prefix}{entry['title']}")
        if entry.get("children"):
            lines.append(toc_to_tree_string(entry["children"], indent + 1))
    return "\n".join(lines)


# ══════════════════════════════════════════
# Notion 连接器
# ══════════════════════════════════════════


class NotionConnector:
    """Notion API 数据源连接器。

    Usage:
        conn = NotionConnector(api_key="ntn_xxx")
        docs = conn.list_pages(database_id="xxx")
        content = conn.get_page_content(page_id="xxx")
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.getenv("NOTION_API_KEY", "")
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

    def _request(self, endpoint: str, method: str = "GET", data: dict = None) -> dict:
        import urllib.error
        import urllib.request

        url = f"{self.base_url}{endpoint}"
        req = urllib.request.Request(url, method=method, headers=self.headers)
        if data:
            req.data = json.dumps(data).encode()

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            logger.error(f"Notion API error: {e.code} {e.reason}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Notion API failed: {e}")
            return {"error": str(e)}

    def search(self, query: str = "", page_size: int = 10) -> list[dict]:
        """搜索 Notion 工作区"""
        resp = self._request("/search", "POST", {"query": query, "page_size": page_size})
        return resp.get("results", [])

    def get_page_content(self, page_id: str) -> str:
        """获取页面内容（块级）"""
        resp = self._request(f"/blocks/{page_id}/children?page_size=100")
        blocks = resp.get("results", [])
        text_parts = []

        for block in blocks:
            block_type = block.get("type", "")
            if block_type == "paragraph":
                rich = block.get("paragraph", {}).get("rich_text", [])
                text_parts.append("".join(t.get("plain_text", "") for t in rich))
            elif block_type == "heading_1":
                rich = block.get("heading_1", {}).get("rich_text", [])
                text_parts.append("# " + "".join(t.get("plain_text", "") for t in rich))
            elif block_type == "heading_2":
                rich = block.get("heading_2", {}).get("rich_text", [])
                text_parts.append("## " + "".join(t.get("plain_text", "") for t in rich))
            elif block_type == "heading_3":
                rich = block.get("heading_3", {}).get("rich_text", [])
                text_parts.append("### " + "".join(t.get("plain_text", "") for t in rich))
            elif block_type == "bulleted_list_item":
                rich = block.get("bulleted_list_item", {}).get("rich_text", [])
                text_parts.append("- " + "".join(t.get("plain_text", "") for t in rich))
            elif block_type == "numbered_list_item":
                rich = block.get("numbered_list_item", {}).get("rich_text", [])
                text_parts.append("1. " + "".join(t.get("plain_text", "") for t in rich))
            elif block_type == "code":
                rich = block.get("code", {}).get("rich_text", [])
                lang = block.get("code", {}).get("language", "")
                text_parts.append(f"```{lang}\n" + "".join(t.get("plain_text", "") for t in rich) + "\n```")

        return "\n\n".join(text_parts)

    def list_databases(self, query: str = "") -> list[dict]:
        """列出可访问的数据库"""
        results = self.search(query=query, page_size=20)
        return [r for r in results if r.get("object") == "database"]

    def query_database(self, database_id: str, page_size: int = 10) -> list[dict]:
        """查询数据库条目"""
        resp = self._request(f"/databases/{database_id}/query", "POST", {"page_size": page_size})
        return resp.get("results", [])


# ══════════════════════════════════════════
# S3 连接器
# ══════════════════════════════════════════


class S3Connector:
    """S3 兼容存储连接器（AWS S3 / MinIO / 阿里云 OSS）。

    Usage:
        conn = S3Connector(endpoint="https://s3.amazonaws.com", bucket="my-bucket",
                          access_key="xxx", secret_key="xxx")
        files = conn.list_files(prefix="docs/")
        conn.download_file("docs/report.pdf", "/local/path/")
    """

    def __init__(self, endpoint: str = "", bucket: str = "",
                 access_key: str = "", secret_key: str = "", region: str = "us-east-1"):
        self.endpoint = endpoint or os.getenv("S3_ENDPOINT", "")
        self.bucket = bucket or os.getenv("S3_BUCKET", "")
        self.access_key = access_key or os.getenv("S3_ACCESS_KEY", "")
        self.secret_key = secret_key or os.getenv("S3_SECRET_KEY", "")
        self.region = region or os.getenv("S3_REGION", "us-east-1")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    "s3",
                    endpoint_url=self.endpoint or None,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region,
                )
            except ImportError:
                logger.warning("boto3 未安装，S3 功能不可用。pip install boto3")
                return None
            except Exception as e:
                logger.error(f"S3 客户端创建失败: {e}")
                return None
        return self._client

    def list_files(self, prefix: str = "", max_keys: int = 100) -> list[dict]:
        """列出 S3 桶中的文件"""
        if not self.client:
            return []
        try:
            resp = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix, MaxKeys=max_keys)
            return [{"key": obj["Key"], "size": obj["Size"], "modified": obj["LastModified"].isoformat()}
                    for obj in resp.get("Contents", [])
                    if not obj["Key"].endswith("/")]
        except Exception as e:
            logger.error(f"S3 list_files failed: {e}")
            return []

    def download_file(self, key: str, local_path: str) -> bool:
        """下载单个文件"""
        if not self.client:
            return False
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.client.download_file(self.bucket, key, local_path)
            logger.info(f"S3 download: {key} → {local_path}")
            return True
        except Exception as e:
            logger.error(f"S3 download failed: {e}")
            return False

    def sync_documents(self, prefix: str, target_dir: str, extensions: list[str] | None = None) -> int:
        """同步 S3 前缀下所有文档到本地目录"""
        files = self.list_files(prefix=prefix)
        if extensions:
            files = [f for f in files if any(f["key"].lower().endswith(e) for e in extensions)]

        count = 0
        for f in files:
            local = os.path.join(target_dir, os.path.basename(f["key"]))
            if not os.path.exists(local):
                if self.download_file(f["key"], local):
                    count += 1
        logger.info(f"S3 sync complete: {count} new files")
        return count


# ══════════════════════════════════════════
# Confluence 连接器
# ══════════════════════════════════════════

class ConfluenceConnector:
    """Confluence Wiki 数据源。

    Usage:
        conn = ConfluenceConnector(base_url="https://xxx.atlassian.net/wiki", token="...")
        pages = conn.search_pages("RAG")
    """

    def __init__(self, base_url: str = "", email: str = "", token: str = ""):
        self.base_url = (base_url or os.getenv("CONFLUENCE_URL", "")).rstrip("/")
        self.email = email or os.getenv("CONFLUENCE_EMAIL", "")
        self.token = token or os.getenv("CONFLUENCE_TOKEN", "")
        self._auth = None

    def _headers(self) -> dict:
        import base64
        creds = base64.b64encode(f"{self.email}:{self.token}".encode()).decode()
        return {"Authorization": f"Basic {creds}", "Accept": "application/json"}

    def search_pages(self, query: str = "", space: str = "", limit: int = 10) -> list[dict]:
        import json as _json
        import urllib.request
        cql = "type=page"
        if query: cql += f" AND text~\"{query}\""
        if space: cql += f" AND space=\"{space}\""
        url = f"{self.base_url}/rest/api/content/search?cql={urllib.parse.quote(cql)}&limit={limit}&expand=body.storage"
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return _json.loads(resp.read()).get("results", [])
        except Exception as e:
            logger.error(f"Confluence search failed: {e}")
            return []

    def get_page(self, page_id: str) -> str:
        import json as _json
        import urllib.request
        url = f"{self.base_url}/rest/api/content/{page_id}?expand=body.storage"
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = _json.loads(resp.read())
                return data.get("body", {}).get("storage", {}).get("value", "")
        except Exception as e:
            logger.error(f"Confluence page fetch failed: {e}")
            return ""


# ══════════════════════════════════════════
# Google Drive 连接器
# ══════════════════════════════════════════

class GoogleDriveConnector:
    """Google Drive 文件同步（使用 Service Account JSON Key）。

    Usage:
        conn = GoogleDriveConnector(keyfile="service-account.json")
        files = conn.list_files(folder_id="xxx", mime_types=["application/pdf"])
    """

    def __init__(self, keyfile: str = ""):
        self.keyfile = keyfile or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service-account.json")
        self._service = None

    def _get_service(self):
        if self._service is None:
            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build
                creds = service_account.Credentials.from_service_account_file(
                    self.keyfile, scopes=["https://www.googleapis.com/auth/drive.readonly"])
                self._service = build("drive", "v3", credentials=creds)
            except ImportError:
                logger.warning("google-api-python-client 未安装")
                return None
        return self._service

    def list_files(self, folder_id: str = "root", mime_types: list[str] | None = None, page_size: int = 50) -> list[dict]:
        svc = self._get_service()
        if not svc: return []

        query = f"'{folder_id}' in parents AND trashed=false"
        if mime_types:
            mime_q = " OR ".join(f"mimeType='{m}'" for m in mime_types)
            query += f" AND ({mime_q})"

        try:
            results = svc.files().list(q=query, pageSize=page_size, fields="files(id,name,mimeType,modifiedTime,size)").execute()
            return results.get("files", [])
        except Exception as e:
            logger.error(f"Google Drive list failed: {e}")
            return []

    def download_file(self, file_id: str, local_path: str) -> bool:
        svc = self._get_service()
        if not svc: return False
        try:

            from googleapiclient.http import MediaIoBaseDownload
            request = svc.files().get_media(fileId=file_id)
            with open(local_path, "wb") as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
            return True
        except Exception as e:
            logger.error(f"Google Drive download failed: {e}")
            return False


# ══════════════════════════════════════════
# WebDAV 连接器
# ══════════════════════════════════════════

class WebDAVConnector:
    """WebDAV 协议连接器（Nextcloud/OwnCloud/Seafile 等）。

    Usage:
        conn = WebDAVConnector("https://cloud.example.com/remote.php/dav", "user", "pass")
        files = conn.list_files("Documents/")
    """

    def __init__(self, url: str = "", username: str = "", password: str = ""):
        self.url = (url or os.getenv("WEBDAV_URL", "")).rstrip("/")
        self.username = username or os.getenv("WEBDAV_USER", "")
        self.password = password or os.getenv("WEBDAV_PASS", "")

    def list_files(self, path: str = "", depth: int = 1) -> list[dict]:
        import base64
        import urllib.request
        import xml.etree.ElementTree as ET

        full_url = f"{self.url}/{path.lstrip('/')}" if path else self.url
        req = urllib.request.Request(full_url, method="PROPFIND")
        req.add_header("Depth", str(depth))
        if self.username:
            creds = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            req.add_header("Authorization", f"Basic {creds}")

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                ns = {"d": "DAV:"}
                root = ET.fromstring(resp.read())
                files = []
                for resp_elem in root.findall("d:response", ns):
                    href = resp_elem.findtext("d:href", "", ns)
                    name = href.rstrip("/").split("/")[-1] if href else ""
                    if name and not href.endswith("/"):
                        size_str = resp_elem.findtext(".//d:getcontentlength", "0", ns)
                        files.append({"name": name, "href": href, "size": int(size_str) if size_str else 0})
                return files
        except Exception as e:
            logger.error(f"WebDAV list failed: {e}")
            return []

    def download_file(self, remote_path: str, local_path: str) -> bool:
        import base64
        import os as _os
        import urllib.request

        full_path = f"{self.url}/{remote_path.lstrip('/')}" if self.url not in remote_path else remote_path
        req = urllib.request.Request(full_path)
        if self.username:
            creds = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            req.add_header("Authorization", f"Basic {creds}")
        try:
            _os.makedirs(_os.path.dirname(local_path), exist_ok=True)
            with urllib.request.urlopen(req, timeout=30) as resp:
                with open(local_path, "wb") as f:
                    f.write(resp.read())
            return True
        except Exception as e:
            logger.error(f"WebDAV download failed: {e}")
            return False


# ══════════════════════════════════════════
# RSS 连接器
# ══════════════════════════════════════════

class RSSConnector:
    """RSS/Atom Feed 数据源。

    Usage:
        conn = RSSConnector()
        entries = conn.fetch("https://example.com/feed.xml")
    """

    def fetch(self, feed_url: str, max_entries: int = 20) -> list[dict]:
        import urllib.request
        import xml.etree.ElementTree as ET

        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "BrianRAG/2.4"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                root = ET.fromstring(resp.read())
        except Exception as e:
            logger.error(f"RSS fetch failed: {e}")
            return []

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = []

        for item in root.iter("item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            desc = item.findtext("description", "")
            pub = item.findtext("pubDate", "")
            entries.append({"title": title, "link": link, "content": desc, "published": pub})

        if not entries:
            for entry in root.findall("atom:entry", ns):
                title = entry.findtext("atom:title", "", ns)
                link_elem = entry.find("atom:link", ns)
                link = link_elem.get("href", "") if link_elem is not None else ""
                summary = entry.findtext("atom:summary", "", ns)
                entries.append({"title": title, "link": link, "content": summary})

        return entries[:max_entries]

    def fetch_and_index(self, feed_url: str, pipeline, max_entries: int = 10) -> int:
        entries = self.fetch(feed_url, max_entries)
        count = 0
        for entry in entries:
            text = f"# {entry['title']}\n\n{entry['content']}\n\n[来源]({entry['link']})"
            if pipeline and pipeline.retriever:
                try:
                    from langchain_core.documents import Document
                    pipeline.retriever.load_documents([Document(page_content=text, metadata={"source": entry.get("link", feed_url), "type": "rss"})])
                    count += 1
                except Exception:
                    pass
        return count


# ══════════════════════════════════════════
# 便捷函数
# ══════════════════════════════════════════


def auto_extract_toc(file_path: str) -> list[dict]:
    """自动识别文件类型并提取 TOC"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return extract_toc_from_pdf(file_path)
    elif ext in (".md", ".markdown"):
        with open(file_path, encoding="utf-8") as f:
            return extract_toc_from_markdown(f.read())


# ══════════════════════════════════════════
# 企业数据源连接器（Jira/Slack/Discord/GitLab/Dropbox/OneDrive/Asana/Trello/Airtable/钉钉/飞书/IMAP）
# ══════════════════════════════════════════

class _HTTPConnector:
    """Base class for simple HTTP API data sources."""
    base: str = ""
    _auth_headers: dict = {}

    def _get(self, path: str, params: dict = None) -> dict:
        import json as _json
        import urllib.parse
        import urllib.request
        url = f"{self.base}{path}"
        if params: url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={**self._auth_headers, "Accept": "application/json", "User-Agent": "BrianRAG/2.4"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return _json.loads(r.read())
        except Exception as e:
            logger.error(f"{self.__class__.__name__} request failed: {e}")
            return {}

    def _paginate(self, path: str, key: str = "values", max_items: int = 100) -> list[dict]:
        items = []
        start = 0
        while len(items) < max_items:
            data = self._get(f"{path}&startAt={start}" if "?" in path else f"{path}?startAt={start}")
            batch = data.get(key, [])
            if not batch: break
            items.extend(batch)
            start += len(batch)
        return items[:max_items]


# ── Jira ──

class JiraConnector(_HTTPConnector):
    def __init__(self, url: str = "", email: str = "", token: str = ""):
        self.base = (url or os.getenv("JIRA_URL", "")).rstrip("/")
        import base64
        creds = base64.b64encode(f"{(email or os.getenv('JIRA_EMAIL',''))}:{(token or os.getenv('JIRA_TOKEN',''))}".encode()).decode()
        self._auth_headers = {"Authorization": f"Basic {creds}"}

    def search_issues(self, jql: str = "order by created DESC", max_results: int = 50) -> list[dict]:
        return self._paginate(f"/rest/api/2/search?jql={jql.replace(' ','+')}", key="issues", max_items=max_results)

    def get_issue(self, key: str) -> dict:
        return self._get(f"/rest/api/2/issue/{key}?fields=summary,description,comment")


# ── Slack ──

class SlackConnector:
    def __init__(self, token: str = ""):
        self.token = token or os.getenv("SLACK_TOKEN", "")

    def list_channels(self) -> list[dict]:
        import json as _json
        import urllib.request
        req = urllib.request.Request("https://slack.com/api/conversations.list?limit=100", headers={"Authorization": f"Bearer {self.token}"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return _json.loads(r.read()).get("channels", [])
        except Exception: return []

    def fetch_messages(self, channel_id: str, limit: int = 50) -> list[dict]:
        import json as _json
        import urllib.request
        url = f"https://slack.com/api/conversations.history?channel={channel_id}&limit={limit}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.token}"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return _json.loads(r.read()).get("messages", [])
        except Exception: return []


# ── Discord ──

class DiscordConnector(_HTTPConnector):
    def __init__(self, token: str = ""):
        self.base = "https://discord.com/api/v10"
        self._auth_headers = {"Authorization": f"Bot {token or os.getenv('DISCORD_TOKEN','')}"}

    def fetch_guild_channels(self, guild_id: str) -> list[dict]:
        return self._get(f"/guilds/{guild_id}/channels")

    def fetch_messages(self, channel_id: str, limit: int = 50) -> list[dict]:
        return self._get(f"/channels/{channel_id}/messages?limit={limit}")


# ── GitLab ──

class GitLabConnector(_HTTPConnector):
    def __init__(self, url: str = "", token: str = ""):
        self.base = f"{(url or os.getenv('GITLAB_URL','https://gitlab.com'))}/api/v4"
        self._auth_headers = {"PRIVATE-TOKEN": token or os.getenv("GITLAB_TOKEN", "")}

    def list_projects(self) -> list[dict]: return self._get("/projects?membership=true")
    def list_files(self, project_id, path: str = "") -> list[dict]: return self._get(f"/projects/{project_id}/repository/tree?path={path}")
    def get_file(self, project_id, file_path: str) -> str:
        import base64
        import json as _json
        import urllib.request
        url = f"{self.base}/projects/{project_id}/repository/files/{urllib.parse.quote(file_path,'')}?ref=main"
        req = urllib.request.Request(url, headers=self._auth_headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                content = _json.loads(r.read()).get("content", "")
                return base64.b64decode(content).decode("utf-8", errors="replace")
        except Exception: return ""


# ── Dropbox ──

class DropboxConnector:
    def __init__(self, token: str = ""):
        self.token = token or os.getenv("DROPBOX_TOKEN", "")

    def _api(self, path: str, data: dict = None) -> dict:
        import json as _json
        import urllib.request
        url = "https://api.dropboxapi.com/2" + path
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}, method="POST")
        if data: req.data = _json.dumps(data).encode()
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return _json.loads(r.read())
        except Exception: return {}

    def list_folder(self, path: str = "") -> list[dict]:
        return self._api("/files/list_folder", {"path": path, "recursive": False}).get("entries", [])

    def download(self, path: str, local: str) -> bool:
        import urllib.request
        url = "https://content.dropboxapi.com/2/files/download"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.token}", "Dropbox-API-Arg": f'{{"path":"{path}"}}'})
        try:
            with urllib.request.urlopen(req, timeout=30) as r, open(local, "wb") as f:
                f.write(r.read())
            return True
        except Exception: return False


# ── OneDrive ──

class OneDriveConnector:
    def __init__(self, token: str = ""):
        self.token = token or os.getenv("ONEDRIVE_TOKEN", "")

    def _graph(self, path: str) -> dict:
        import json as _json
        import urllib.request
        req = urllib.request.Request(f"https://graph.microsoft.com/v1.0{path}", headers={"Authorization": f"Bearer {self.token}"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return _json.loads(r.read())
        except Exception: return {}

    def list_files(self, folder: str = "/me/drive/root") -> list[dict]:
        return self._graph(f"{folder}/children").get("value", [])

    def download(self, item_id: str, local: str) -> bool:
        import urllib.request
        req = urllib.request.Request(f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/content", headers={"Authorization": f"Bearer {self.token}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r, open(local, "wb") as f:
                f.write(r.read())
            return True
        except Exception: return False


# ── Asana ──

class AsanaConnector(_HTTPConnector):
    def __init__(self, token: str = ""):
        self.base = "https://app.asana.com/api/1.0"
        self._auth_headers = {"Authorization": f"Bearer {token or os.getenv('ASANA_TOKEN','')}"}

    def list_projects(self) -> list[dict]: return self._paginate("/projects", "data")
    def list_tasks(self, project_id: str) -> list[dict]: return self._paginate(f"/projects/{project_id}/tasks", "data")


# ── Trello ──

class TrelloConnector:
    def __init__(self, key: str = "", token: str = ""):
        self.key = key or os.getenv("TRELLO_KEY", "")
        self.token = token or os.getenv("TRELLO_TOKEN", "")

    def _get(self, path: str) -> dict:
        import json as _json
        import urllib.request
        url = f"https://api.trello.com/1{path}?key={self.key}&token={self.token}"
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                return _json.loads(r.read())
        except Exception: return {}

    def list_boards(self) -> list[dict]: return self._get("/members/me/boards")
    def list_cards(self, board_id: str) -> list[dict]: return self._get(f"/boards/{board_id}/cards")


# ── Airtable ──

class AirtableConnector(_HTTPConnector):
    def __init__(self, token: str = "", base_id: str = ""):
        self.base = f"https://api.airtable.com/v0/{base_id or os.getenv('AIRTABLE_BASE','')}"
        self._auth_headers = {"Authorization": f"Bearer {token or os.getenv('AIRTABLE_TOKEN','')}"}

    def list_records(self, table: str, max_records: int = 100) -> list[dict]:
        return self._paginate(f"/{table}?pageSize=100", "records", max_records)


# ── 钉钉 ──

class DingTalkConnector:
    def __init__(self, app_key: str = "", app_secret: str = ""):
        self.key = app_key or os.getenv("DINGTALK_APP_KEY", "")
        self.secret = app_secret or os.getenv("DINGTALK_APP_SECRET", "")
        self._token = None

    def _get_token(self) -> str:
        if self._token: return self._token
        import json as _json
        import urllib.request
        url = f"https://oapi.dingtalk.com/gettoken?appkey={self.key}&appsecret={self.secret}"
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                self._token = _json.loads(r.read()).get("access_token", "")
        except Exception: pass
        return self._token

    def list_departments(self) -> list[dict]:
        import json as _json
        import urllib.request
        token = self._get_token()
        url = f"https://oapi.dingtalk.com/topapi/v2/department/listsub?access_token={token}"
        req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return _json.loads(r.read()).get("result", [])
        except Exception: return []


# ── 飞书 ──

class FeishuConnector:
    def __init__(self, app_id: str = "", app_secret: str = ""):
        self.app_id = app_id or os.getenv("FEISHU_APP_ID", "")
        self.secret = app_secret or os.getenv("FEISHU_APP_SECRET", "")
        self._token = None

    def _get_token(self) -> str:
        if self._token: return self._token
        import json as _json
        import urllib.request
        data = _json.dumps({"app_id": self.app_id, "app_secret": self.secret}).encode()
        req = urllib.request.Request("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                self._token = _json.loads(r.read()).get("tenant_access_token", "")
        except Exception: pass
        return self._token

    def list_docs(self, page_size: int = 50) -> list[dict]:
        import json as _json
        import urllib.request
        token = self._get_token()
        url = f"https://open.feishu.cn/open-apis/drive/v1/files?page_size={page_size}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return _json.loads(r.read()).get("data", {}).get("files", [])
        except Exception: return []


# ── IMAP 邮件 ──

class IMAPConnector:
    def __init__(self, server: str = "", email: str = "", password: str = ""):
        self.server = server or os.getenv("IMAP_SERVER", "")
        self.email = email or os.getenv("IMAP_EMAIL", "")
        self.password = password or os.getenv("IMAP_PASS", "")

    def fetch_emails(self, folder: str = "INBOX", limit: int = 20) -> list[dict]:
        try:
            import email as _email
            import imaplib
            conn = imaplib.IMAP4_SSL(self.server)
            conn.login(self.email, self.password)
            conn.select(folder)
            _, ids = conn.search(None, "ALL")
            results = []
            for mid in ids[0].split()[-limit:]:
                _, data = conn.fetch(mid, "(RFC822)")
                msg = _email.message_from_bytes(data[0][1])
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                            break
                else: body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
                results.append({"subject": msg["subject"] or "", "from": msg["from"] or "", "date": msg["date"] or "", "body": body[:2000]})
            conn.logout()
            return results
        except Exception as e:
            logger.error(f"IMAP fetch failed: {e}")
            return []
