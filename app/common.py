# -*- coding: utf-8 -*-
"""
MojingStudio Stable v2.0 Workbench
中文界面，DaVinci Resolve 式布局。

说明：
- 这是 v5 视觉壳 + 核心功能接入版。
- 保留轻量 JSON 元数据，不引入数据库。
- 云端接口按火山方舟 /contents/generations/tasks 异步任务流程写法。
- 若官方字段后续变化，可在 payload 构造处继续微调。
- 已修复：多任务并发提交时的 QThread 垃圾回收崩溃问题与下载文件抢占冲突。
"""

import os
import sys
import re
import json
import csv
import time
import base64
import shutil
import datetime
import urllib.request
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

try:
    import requests
except Exception:
    requests = None

try:
    import tos
except Exception:
    tos = None

try:
    import cv2
except Exception:
    cv2 = None

from PySide6.QtCore import Qt, QSize, QThread, Signal, QTimer, QRect, QEvent, QMimeData, QUrl
from PySide6.QtGui import QColor, QPainter, QFont, QLinearGradient, QPixmap, QIcon, QAction, QImage, QTextCharFormat, QTextCursor, QDrag, QDesktopServices, QTextImageFormat, QTextDocument
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QHBoxLayout, QVBoxLayout, QGridLayout, QScrollArea, QTextEdit,
    QLineEdit, QComboBox, QSlider, QSizePolicy, QStackedWidget,
    QSplitter, QButtonGroup, QGraphicsDropShadowEffect, QFileDialog,
    QDialog, QMessageBox, QSpinBox, QCheckBox, QListWidget,
    QListWidgetItem, QInputDialog, QTabWidget, QFormLayout, QMenu
)


# =========================================================
# 0. 常量 / 配置
# =========================================================

CONFIG_FILE = None
MODEL_PROFILES_FILE = None
PROMPT_LIBRARY_FILE = None
CLOUD_TASK_OVERRIDES_FILE = None
PERSONA_LIBRARY_FILE = None

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
VIDEO_EXTS = (".mp4", ".mov", ".m4v", ".avi")
AUDIO_EXTS = (".mp3", ".wav")

BASE_URL = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"


def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def app_root():
    return os.getcwd()


def data_root():
    return ensure_dir(os.path.join(app_root(), "data"))


def config_dir():
    return ensure_dir(os.path.join(data_root(), "config"))


def docs_dir():
    return ensure_dir(os.path.join(data_root(), "docs"))


def docs_official_dir():
    return ensure_dir(os.path.join(docs_dir(), "official"))


def docs_prompt_dir():
    return ensure_dir(os.path.join(docs_dir(), "prompts"))


def persona_preview_dir():
    return ensure_dir(os.path.join(data_root(), "persona_previews"))


CONFIG_FILE = os.path.join(config_dir(), "config.json")
MODEL_PROFILES_FILE = os.path.join(config_dir(), "model_profiles.json")
PROMPT_LIBRARY_FILE = os.path.join(config_dir(), "prompt_library.json")
CLOUD_TASK_OVERRIDES_FILE = os.path.join(config_dir(), "cloud_task_overrides.json")
PERSONA_LIBRARY_FILE = os.path.join(config_dir(), "persona_library.json")


def migrate_old_data_files():
    """把旧版根目录中的配置文件、文档和人像预览迁移到 data 目录。"""
    old_to_new = {
        os.path.join(app_root(), "config.json"): CONFIG_FILE,
        os.path.join(app_root(), "model_profiles.json"): MODEL_PROFILES_FILE,
        os.path.join(app_root(), "prompt_library.json"): PROMPT_LIBRARY_FILE,
        os.path.join(app_root(), "cloud_task_overrides.json"): CLOUD_TASK_OVERRIDES_FILE,
        os.path.join(app_root(), "persona_library.json"): PERSONA_LIBRARY_FILE,
    }
    for old_path, new_path in old_to_new.items():
        try:
            if os.path.exists(old_path) and not os.path.exists(new_path):
                ensure_dir(os.path.dirname(new_path))
                with open(old_path, "rb") as rf:
                    data = rf.read()
                with open(new_path, "wb") as wf:
                    wf.write(data)
        except Exception:
            pass

    # 迁移旧版 docs/official 与 docs/prompts
    old_docs = os.path.join(app_root(), "docs")
    docs_map = {
        os.path.join(old_docs, "official"): docs_official_dir(),
        os.path.join(old_docs, "prompts"): docs_prompt_dir(),
    }
    for old_folder, new_folder in docs_map.items():
        try:
            if os.path.isdir(old_folder):
                ensure_dir(new_folder)
                for name in os.listdir(old_folder):
                    src = os.path.join(old_folder, name)
                    dst = os.path.join(new_folder, name)
                    if os.path.isfile(src) and not os.path.exists(dst):
                        shutil.copy2(src, dst)
        except Exception:
            pass

    # 迁移旧版 persona_previews
    old_persona_previews = os.path.join(app_root(), "persona_previews")
    try:
        if os.path.isdir(old_persona_previews):
            new_preview_dir = persona_preview_dir()
            for name in os.listdir(old_persona_previews):
                src = os.path.join(old_persona_previews, name)
                dst = os.path.join(new_preview_dir, name)
                if os.path.isfile(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)
    except Exception:
        pass


def ensure_data_dirs():
    config_dir()
    docs_official_dir()
    docs_prompt_dir()
    persona_preview_dir()
    migrate_old_data_files()


def default_config():
    return {
        "api_key": "",
        "video_endpoint": "",
        "video_fast_endpoint": "",
        "doubao_seedance_1_0_pro_fast_endpoint": "",
        "custom_video_endpoint": "",
        "image_endpoint": "",
        "research_endpoint": "",
        "output_dir": os.path.join(app_root(), "outputs"),
        "last_project_name": "Baijin_Test",
        "last_shot_name": "S01",
        "poll_delay": 45,
        "poll_interval": 5,
        "enable_tos_upload": False,
        "tos_bucket": "",
        "tos_endpoint": "",
        "tos_access_key": "",
        "tos_secret_key": "",
    }


def load_config():
    if not os.path.exists(CONFIG_FILE):
        cfg = default_config()
        save_config(cfg)
        return cfg
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = default_config()
        cfg.update(data if isinstance(data, dict) else {})
        # 旧版本默认值为 3 / 6；升级后默认改为 45 / 5。
        if isinstance(data, dict) and data.get("poll_delay") == 3:
            cfg["poll_delay"] = 45
        if isinstance(data, dict) and data.get("poll_interval") == 6:
            cfg["poll_interval"] = 5
        return cfg
    except Exception:
        return default_config()


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_persona_library():
    if not os.path.exists(PERSONA_LIBRARY_FILE):
        data = {"items": []}
        save_persona_library(data)
        return data
    try:
        with open(PERSONA_LIBRARY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"items": []}
        data.setdefault("items", [])
        return data
    except Exception:
        return {"items": []}


def save_persona_library(data):
    with open(PERSONA_LIBRARY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_asset_uri(asset_text):
    s = str(asset_text or "").strip()
    if not s:
        return ""
    if s.startswith("asset://"):
        return s
    if s.startswith("asset-"):
        return "asset://" + s
    return s


def persona_asset_kind(uri):
    return "image"



def safe_persona_preview_name(uri_or_id):
    s = normalize_asset_uri(uri_or_id).replace("asset://", "")
    s = re.sub(r"[^\w\-]+", "_", s or f"persona_{int(time.time())}")
    return s


def default_model_profiles():
    cfg = load_config()
    return {
        "video": [
            {
                "name": "Seedance 2.0",
                "provider": "ark_seedance",
                "endpoint": cfg.get("video_endpoint", ""),
                "default": True,
                "default_resolution": "720p",
                "supported_resolutions": ["480p", "720p", "1080p"],
                "supported_ratios": ["adaptive", "16:9", "9:16", "21:9", "4:3", "1:1", "3:4"],
                "duration_range": [4, 15],
                "supports_reference_image": True,
                "supports_reference_video": True,
                "supports_reference_audio": True,
                "supports_web_search": True,
                "supports_return_last_frame": True,
                "supports_offline_inference": False,
                "supported_video_modes": ["普通生成", "视频编辑", "视频延长", "前序生成", "轨道补全"],
                "pricing": {
                    "no_video_input_per_million_tokens": 46.0,
                    "with_video_input_per_million_tokens": 28.0
                }
            },
            {
                "name": "Seedance 2.0 Fast",
                "provider": "ark_seedance",
                "endpoint": cfg.get("video_fast_endpoint", ""),
                "default": False,
                "default_resolution": "720p",
                "supported_resolutions": ["480p", "720p"],
                "supported_ratios": ["adaptive", "16:9", "9:16", "21:9", "4:3", "1:1", "3:4"],
                "duration_range": [4, 15],
                "supports_reference_image": True,
                "supports_reference_video": True,
                "supports_reference_audio": True,
                "supports_web_search": True,
                "supports_return_last_frame": True,
                "supports_offline_inference": False,
                "supported_video_modes": ["普通生成", "视频编辑", "视频延长", "前序生成", "轨道补全"],
                "pricing": {
                    "no_video_input_per_million_tokens": 37.0,
                    "with_video_input_per_million_tokens": 22.0
                }
            },
            {
                "name": "Doubao-Seedance-1.0-pro-fast",
                "provider": "ark_seedance",
                "endpoint": cfg.get("doubao_seedance_1_0_pro_fast_endpoint", ""),
                "default": False,
                "default_resolution": "720p",
                "supported_resolutions": ["480p", "720p", "1080p"],
                "supported_ratios": ["adaptive", "16:9", "9:16", "21:9", "4:3", "1:1", "3:4"],
                "duration_range": [4, 10],
                "supports_reference_image": True,
                "supports_reference_video": False,
                "supports_reference_audio": False,
                "supports_web_search": False,
                "supports_return_last_frame": False,
                "supports_offline_inference": True,
                "supported_video_modes": ["普通生成"],
                "pricing": {
                    "no_video_input_per_million_tokens": 4.2,
                    "with_video_input_per_million_tokens": 0.0,
                    "offline_no_video_input_per_million_tokens": 2.1,
                    "offline_with_video_input_per_million_tokens": 0.0
                }
            },
            {
                "name": "自定义视频模型",
                "provider": "custom_video",
                "endpoint": cfg.get("custom_video_endpoint", ""),
                "default": False,
                "default_resolution": "720p",
                "supported_resolutions": ["480p", "720p", "1080p"],
                "supported_ratios": ["adaptive", "16:9", "9:16", "21:9", "4:3", "1:1", "3:4"],
                "duration_range": [4, 15],
                "supports_reference_image": True,
                "supports_reference_video": True,
                "supports_reference_audio": False,
                "supports_web_search": False,
                "supports_return_last_frame": False,
                "supports_offline_inference": False,
                "supported_video_modes": ["普通生成", "视频编辑", "视频延长", "前序生成", "轨道补全"],
                "pricing": {
                    "no_video_input_per_million_tokens": 0.0,
                    "with_video_input_per_million_tokens": 0.0
                }
            }
        ],
        "image": [
            {
                "name": "Seedream Image",
                "provider": "ark_seedream",
                "endpoint": cfg.get("image_endpoint", ""),
                "default": True,
                "default_resolution": "2k",
                "supported_resolutions": ["1k", "2k", "4k"],
                "supported_ratios": ["16:9", "9:16", "4:3", "3:4", "1:1", "21:9"],
                "supports_reference_image": True,
                "supports_seed": True,
                "pricing": {}
            },
            {
                "name": "自定义生图模型",
                "provider": "custom_image",
                "endpoint": "",
                "default": False,
                "default_resolution": "2k",
                "supported_resolutions": ["1k", "2k", "4k"],
                "supported_ratios": ["16:9", "9:16", "4:3", "3:4", "1:1", "21:9"],
                "supports_reference_image": True,
                "supports_seed": True,
                "pricing": {}
            }
        ]
    }


def _merge_profile_fields(existing_profile, default_profile):
    existing_profile = dict(existing_profile or {})
    changed = False
    for k, v in (default_profile or {}).items():
        if k not in existing_profile:
            existing_profile[k] = v
            changed = True
    return existing_profile, changed


def _merge_missing_profiles(existing_items, default_items):
    existing_items = existing_items or []
    default_items = default_items or []

    default_map = {}
    for it in default_items:
        if isinstance(it, dict):
            name = str(it.get("name", "")).strip()
            if name:
                default_map[name] = it

    merged = []
    changed = False
    seen_names = set()

    for it in existing_items:
        if not isinstance(it, dict):
            merged.append(it)
            continue
        name = str(it.get("name", "")).strip()
        seen_names.add(name)
        if name and name in default_map:
            merged_item, item_changed = _merge_profile_fields(it, default_map[name])
            merged.append(merged_item)
            changed = changed or item_changed
        else:
            merged.append(it)

    for name, it in default_map.items():
        if name not in seen_names:
            merged.append(it)
            changed = True

    return merged, changed


def load_model_profiles():
    if not os.path.exists(MODEL_PROFILES_FILE):
        data = default_model_profiles()
        save_model_profiles(data)
        return data
    try:
        with open(MODEL_PROFILES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("bad model_profiles")

        defaults = default_model_profiles()
        changed = False

        if "video" not in data or not isinstance(data.get("video"), list):
            data["video"] = defaults["video"]
            changed = True
        else:
            data["video"], add_changed = _merge_missing_profiles(data["video"], defaults["video"])
            changed = changed or add_changed

        if "image" not in data or not isinstance(data.get("image"), list):
            data["image"] = defaults["image"]
            changed = True
        else:
            data["image"], add_changed = _merge_missing_profiles(data["image"], defaults["image"])
            changed = changed or add_changed

        if changed:
            save_model_profiles(data)
        return data
    except Exception:
        return default_model_profiles()


def save_model_profiles(data):
    with open(MODEL_PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def default_profile(profiles, kind):
    items = profiles.get(kind, [])
    for it in items:
        if it.get("default"):
            return it
    return items[0] if items else {}


def profile_by_name(profiles, kind, name):
    for it in profiles.get(kind, []):
        if it.get("name") == name:
            return it
    return None


def update_profile_endpoint(profiles, kind, name, endpoint):
    p = profile_by_name(profiles, kind, name)
    if p is not None:
        p["endpoint"] = endpoint or ""


def profile_supported_video_modes(profile):
    if not isinstance(profile, dict):
        return ["普通生成"]
    modes = profile.get("supported_video_modes")
    return list(modes) if isinstance(modes, list) and modes else ["普通生成"]

def profile_supports_video_mode(profile, video_mode):
    return str(video_mode or "普通生成") in profile_supported_video_modes(profile)


def profile_supports_offline_inference(profile):
    return bool((profile or {}).get("supports_offline_inference"))

def filter_refs_for_video_profile(refs, profile, prompt_text=""):
    """
    按模型能力过滤参考素材。
    - 只保留 Prompt 中实际引用到的素材（未引用的不提交）
    - 不支持视频/音频时自动剔除
    - Doubao-Seedance-1.0-pro-fast 仅保留 1 张图片参考，避免被服务端识别为参考视频/复杂模式
    """
    refs = refs or []
    prompt_text = str(prompt_text or "")
    supports_video = bool(profile.get("supports_reference_video"))
    supports_audio = bool(profile.get("supports_reference_audio"))
    supports_image = bool(profile.get("supports_reference_image", True))

    filtered = []
    image_count = 0
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        tag = str(ref.get("tag") or "").strip()
        if tag and f"[@{tag}]" not in prompt_text:
            continue
        kind = ref.get("kind") or asset_kind(ref.get("path", ""), tag)
        if kind == "video" and not supports_video:
            continue
        if kind == "audio" and not supports_audio:
            continue
        if kind == "image" and not supports_image:
            continue
        if profile.get("name") == "Doubao-Seedance-1.0-pro-fast" and kind == "image":
            if image_count >= 1:
                continue
            image_count += 1
        filtered.append(ref)
    return filtered


def endpoint_from_profile_or_cfg(profiles, kind, name, cfg_key, cfg=None):
    cfg = cfg or load_config()
    val = (cfg.get(cfg_key) or "").strip()
    if val:
        return val
    p = profile_by_name(profiles, kind, name)
    return (p.get("endpoint") or "").strip() if p else ""


def load_overrides():
    if not os.path.exists(CLOUD_TASK_OVERRIDES_FILE):
        return {}
    try:
        with open(CLOUD_TASK_OVERRIDES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_overrides(data):
    with open(CLOUD_TASK_OVERRIDES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_prompt_library():
    if not os.path.exists(PROMPT_LIBRARY_FILE):
        data = [
            "电影级写实质感，保持原视频构图与镜头运动，主体替换自然，光影方向一致。",
            "保持人物面部身份一致，自然皮肤纹理，可见毛孔，避免过度磨皮。",
            "中式异世界幻想，精细服饰层次，体积光，真实材质，电影海报级构图。",
            "避免畸形手、闪烁面部、破碎几何、错误文字、塑料质感、过度锐化。"
        ]
        with open(PROMPT_LIBRARY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data
    try:
        with open(PROMPT_LIBRARY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_prompt_library(data):
    with open(PROMPT_LIBRARY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def sidecar_path(media_path):
    return os.path.splitext(media_path)[0] + ".json"


def load_sidecar(media_path):
    p = sidecar_path(media_path)
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def write_sidecar(media_path, data):
    try:
        with open(sidecar_path(media_path), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def safe_open_path(path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)
        elif sys.platform == "darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')
    except Exception:
        pass


def asset_kind(path, tag=""):
    raw = str(path or "").lower()
    clean = raw.split("?")[0]
    if "音频" in tag or clean.endswith(AUDIO_EXTS) or "mime_type=audio" in raw:
        return "audio"
    if "视频" in tag or clean.endswith(VIDEO_EXTS) or "mime_type=video" in raw or "__vid=" in raw:
        return "video"
    return "image"


def guess_ext_from_url(url, fallback="mp4"):
    clean = str(url or "").split("?")[0]
    ext = os.path.splitext(clean)[1].lower().strip(".")
    if ext in {"mp4", "mov", "m4v", "avi", "png", "jpg", "jpeg", "webp"}:
        return "jpg" if ext == "jpeg" else ext
    if "mime_type=video" in str(url).lower():
        return "mp4"
    if "mime_type=image" in str(url).lower():
        return "png"
    return fallback


def get_next_path(out_dir, project, shot, ext):
    ensure_dir(out_dir)
    safe_project = re.sub(r"[^\w\u4e00-\u9fa5-]+", "_", project or "Project")
    safe_shot = re.sub(r"[^\w\u4e00-\u9fa5-]+", "_", shot or "Shot")
    base = f"{safe_project}_{safe_shot}"
    n = 1
    while True:
        fp = os.path.join(out_dir, f"{base}_v{n:03d}.{ext}")
        if not os.path.exists(fp):
            return fp
        n += 1


def extract_url(data):
    if isinstance(data, dict):
        c = data.get("content")
        if isinstance(c, dict):
            for key in ["video_url", "image_url", "url"]:
                if isinstance(c.get(key), str) and c.get(key).startswith("http"):
                    return c.get(key)
        for key in ["video_url", "image_url", "url", "download_url"]:
            if isinstance(data.get(key), str) and data.get(key).startswith("http"):
                return data.get(key)
        for v in data.values():
            u = extract_url(v)
            if u:
                return u
    elif isinstance(data, list):
        for v in data:
            u = extract_url(v)
            if u:
                return u
    return ""


def extract_thumb(data):
    keys = ["last_frame_url", "thumbnail_url", "thumb_url", "poster_url", "cover_url", "preview_url", "image_url", "first_frame_url", "screenshot_url"]
    if isinstance(data, dict):
        c = data.get("content")
        if isinstance(c, dict):
            for k in keys:
                if isinstance(c.get(k), str) and c.get(k).startswith("http"):
                    return c.get(k)
        for k in keys:
            if isinstance(data.get(k), str) and data.get(k).startswith("http"):
                return data.get(k)
        for v in data.values():
            u = extract_thumb(v)
            if u:
                return u
    elif isinstance(data, list):
        for v in data:
            u = extract_thumb(v)
            if u:
                return u
    return ""


def get_usage_tokens(data):
    try:
        usage = data.get("usage", {})
        return int(usage.get("total_tokens") or usage.get("completion_tokens") or 0)
    except Exception:
        return 0


def infer_has_video_input(meta):
    refs = meta.get("refs") or []
    for r in refs:
        if isinstance(r, dict) and (r.get("kind") == "video" or asset_kind(r.get("path"), r.get("tag")) == "video"):
            return True
    raw = str(meta.get("raw", ""))
    if "reference_video" in raw or '"type": "video_url"' in raw:
        return True
    return False


def find_video_profile(model_name, profiles):
    if not profiles:
        return {}
    for p in profiles.get("video", []):
        if model_name and (model_name == p.get("name") or model_name == p.get("endpoint") or model_name == p.get("model_id")):
            return p
    return default_profile(profiles, "video")


def estimate_cost(meta, profiles=None, input_mode="auto"):
    tokens = int(meta.get("usage_total_tokens") or meta.get("total_tokens") or 0)
    if not tokens and isinstance(meta.get("raw"), str):
        try:
            tokens = get_usage_tokens(json.loads(meta.get("raw")))
        except Exception:
            tokens = 0
    if tokens <= 0:
        return "费用估算：不可用｜置信度：低｜缺少 usage.total_tokens"

    profile = find_video_profile(meta.get("model_profile") or meta.get("model") or meta.get("model_id"), profiles or load_model_profiles())
    pricing = profile.get("pricing") or {}
    service_tier = str(meta.get("service_tier") or "").strip().lower()
    if not service_tier and isinstance(meta.get("raw"), str):
        raw_text = str(meta.get("raw") or "")
        if '"service_tier": "flex"' in raw_text or '"service_tier":"flex"' in raw_text:
            service_tier = "flex"
    if service_tier not in {"default", "flex"}:
        service_tier = "default"

    if input_mode == "with_video":
        has_video = True
    elif input_mode == "no_video":
        has_video = False
    else:
        has_video = infer_has_video_input(meta)

    if service_tier == "flex":
        no_rate = float(pricing.get("offline_no_video_input_per_million_tokens") or pricing.get("no_video_input_per_million_tokens") or 0)
        yes_rate = float(pricing.get("offline_with_video_input_per_million_tokens") or pricing.get("with_video_input_per_million_tokens") or 0)
        tier_label = "离线推理"
    else:
        no_rate = float(pricing.get("no_video_input_per_million_tokens") or 0)
        yes_rate = float(pricing.get("with_video_input_per_million_tokens") or 0)
        tier_label = "在线推理"

    model_name = profile.get("name") or meta.get("model") or "未知模型"
    if has_video is True and yes_rate:
        cost = tokens / 1_000_000 * yes_rate
        return f"费用估算：¥{cost:.2f}｜置信度：高｜{model_name}｜{tier_label}｜含视频输入｜{tokens:,} tokens"
    if has_video is False and no_rate:
        cost = tokens / 1_000_000 * no_rate
        return f"费用估算：¥{cost:.2f}｜置信度：高｜{model_name}｜{tier_label}｜不含视频输入｜{tokens:,} tokens"
    if no_rate and yes_rate:
        low = min(tokens / 1_000_000 * no_rate, tokens / 1_000_000 * yes_rate)
        high = max(tokens / 1_000_000 * no_rate, tokens / 1_000_000 * yes_rate)
        return f"费用估算：约 ¥{low:.2f} - ¥{high:.2f}｜置信度：中｜{model_name}｜{tier_label}｜无法判断输入类型｜{tokens:,} tokens"
    return f"费用估算：不可用｜置信度：低｜模型未配置价格｜{model_name}｜{tier_label}｜{tokens:,} tokens"

def short_url_label(url, max_len=32):
    s = str(url or "")
    if s.startswith("asset://"):
        return s if len(s) <= max_len else s[:max_len - 3] + "..."
    try:
        from urllib.parse import urlparse
        u = urlparse(s)
        host = u.netloc.replace("www.", "")
        path = os.path.basename(u.path.rstrip("/")) or "url"
        lab = f"{host}/{path}"
    except Exception:
        lab = s
    return lab if len(lab) <= max_len else lab[:max_len - 3] + "..."


def detect_url_asset(url, timeout=10):
    result = {"ok": False, "kind": asset_kind(url), "content_type": "", "content_length": "", "risk": [], "message": ""}
    s = str(url or "")
    low = s.lower()
    if any(k in low for k in ["expire", "signature", "token", "webid", "dy_q", "auth"]):
        result["risk"].append("疑似临时/鉴权链接")
    if any(h in low for h in ["douyinvod", "snssdk", "ixigua", "bilibili", "xiaohongshu"]):
        result["risk"].append("疑似短视频平台防盗链")
    if s.startswith("asset://"):
        result.update({"ok": True, "message": "asset:// 素材 ID，由平台侧校验。"})
        return result
    if requests is None:
        result["message"] = "缺少 requests，无法检测。"
        return result
    try:
        sess = requests.Session()
        resp = sess.head(s, allow_redirects=True, timeout=timeout)
        if resp.status_code >= 400 or not resp.headers.get("content-type"):
            resp = sess.get(s, stream=True, timeout=timeout, headers={"Range": "bytes=0-1024"})
        ctype = resp.headers.get("content-type", "")
        clen = resp.headers.get("content-length", "")
        result["content_type"] = ctype
        result["content_length"] = clen
        if "video" in ctype:
            result["kind"] = "video"
        elif "audio" in ctype:
            result["kind"] = "audio"
        elif "image" in ctype:
            result["kind"] = "image"
        result["ok"] = resp.status_code < 400
        result["message"] = f"HTTP {resp.status_code}｜{ctype or '未知类型'}"
    except Exception as e:
        result["message"] = f"检测失败：{e}"
    return result


def video_first_frame(path, width=96, height=60):
    if cv2 is not None:
        try:
            cap = cv2.VideoCapture(path)
            ret, frame = cap.read()
            cap.release()
            if ret:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
                return QPixmap.fromImage(qimg).scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except Exception:
            pass
    return make_placeholder_pixmap("video", width, height)


def make_placeholder_pixmap(kind="video", width=160, height=92):
    pix = QPixmap(width, height)
    if kind == "image":
        c1, c2, label = QColor("#126B80"), QColor("#1C2340"), "IMAGE"
    elif kind == "audio":
        c1, c2, label = QColor("#5A2C86"), QColor("#1C2340"), "AUDIO"
    else:
        c1, c2, label = QColor("#174C88"), QColor("#1C2340"), "VIDEO"
    pix.fill(c2)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, width, height)
    grad.setColorAt(0, c1)
    grad.setColorAt(1, c2)
    p.setBrush(grad)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(0, 0, width, height, 12, 12)
    p.setPen(QColor("#FFFFFF"))
    p.setFont(QFont("Microsoft YaHei UI", max(10, int(width * 0.09)), QFont.Bold))
    p.drawText(pix.rect(), Qt.AlignCenter, label)
    p.end()
    return pix


def remote_pixmap(url, width=160, height=92, fallback_kind="video"):
    if not url:
        return make_placeholder_pixmap(fallback_kind, width, height)

    low = str(url).lower()
    is_video_url = fallback_kind == "video" or low.split("?")[0].endswith(VIDEO_EXTS) or "mime_type=video" in low
    if is_video_url and cv2 is not None:
        try:
            cap = cv2.VideoCapture(url)
            ret, frame = cap.read()
            cap.release()
            if ret:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
                return QPixmap.fromImage(qimg).scaled(width, height, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        except Exception:
            pass

    try:
        if requests is None:
            return make_placeholder_pixmap(fallback_kind, width, height)
        r = requests.get(url, timeout=12)
        if r.status_code >= 400:
            return make_placeholder_pixmap(fallback_kind, width, height)
        pix = QPixmap()
        if pix.loadFromData(r.content):
            return pix.scaled(width, height, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    except Exception:
        pass
    return make_placeholder_pixmap(fallback_kind, width, height)
