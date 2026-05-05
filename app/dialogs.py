from .common import *
from .widgets import *

# =========================================================
# 3. 对话框
# =========================================================

class TaskProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("任务进度查看器")
        self.resize(720, 420)
        self.setMinimumSize(720, 420)
        self.setMaximumSize(720, 420)
        self.setStyleSheet(APP_QSS)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        self.title = ui_label("云端任务正在运行", 16, True)
        root.addWidget(self.title)

        self.status = ui_label("等待云端返回状态...", 12, False, True)
        root.addWidget(self.status)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QTextEdit.WidgetWidth)
        try:
            self.log_view.setWordWrapMode(QTextOption.WrapAnywhere)
        except Exception:
            pass
        try:
            self.log_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        except Exception:
            pass
        self.log_view.setPlaceholderText("任务日志会显示在这里。关闭窗口不会影响任务运行。")
        root.addWidget(self.log_view, 1)

        row = QHBoxLayout()
        row.addWidget(ui_label("关闭这个窗口不会停止任务。需要停止轮询请使用主界面的“停止”按钮。", 10, False, True))
        row.addStretch()
        close_btn = GlowButton("关闭查看器")
        close_btn.clicked.connect(self.hide)
        row.addWidget(close_btn)
        root.addLayout(row)

    def append_log(self, msg):
        text = str(msg)
        self.log_view.append(text)
        self.status.setText(text)

    def mark_done(self, ok, msg):
        text = str(msg)
        self.title.setText("任务完成" if ok else "任务失败")
        self.status.setText(text)
        self.log_view.append(text)



class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("管线设置")
        self.resize(760, 680)
        self.setStyleSheet(APP_QSS)
        self.cfg = load_config()

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        tabs = QTabWidget()
        root.addWidget(tabs, 1)

        cfg_page = QWidget()
        form = QFormLayout(cfg_page)
        form.setSpacing(12)

        self.api_key = QLineEdit(self.cfg.get("api_key", ""))
        self.api_key.setEchoMode(QLineEdit.Password)

        profiles = load_model_profiles()

        self.video_ep = QLineEdit(endpoint_from_profile_or_cfg(profiles, "video", "Seedance 2.0", "video_endpoint", self.cfg))
        self.video_ep.setPlaceholderText("Seedance 2.0 Endpoint，例如 ep-xxxx")
        self.video_fast_ep = QLineEdit(endpoint_from_profile_or_cfg(profiles, "video", "Seedance 2.0 Fast", "video_fast_endpoint", self.cfg))
        self.video_fast_ep.setPlaceholderText("Seedance 2.0 Fast Endpoint，例如 ep-xxxx")
        self.seedance1_fast_ep = QLineEdit(endpoint_from_profile_or_cfg(profiles, "video", "Doubao-Seedance-1.0-pro-fast", "doubao_seedance_1_0_pro_fast_endpoint", self.cfg))
        self.seedance1_fast_ep.setPlaceholderText("Doubao-Seedance-1.0-pro-fast Endpoint，例如 ep-xxxx")
        self.custom_video_ep = QLineEdit(endpoint_from_profile_or_cfg(profiles, "video", "自定义视频模型", "custom_video_endpoint", self.cfg))
        self.custom_video_ep.setPlaceholderText("自定义视频模型 Endpoint，可留空")
        self.image_ep = QLineEdit(endpoint_from_profile_or_cfg(profiles, "image", "Seedream Image", "image_endpoint", self.cfg))
        self.image_ep.setPlaceholderText("生图 Endpoint，例如 ep-xxxx")
        self.research_ep = QLineEdit(self.cfg.get("research_endpoint", ""))
        self.research_ep.setPlaceholderText("可选：联网扩写独立 Endpoint；不填则跟随视频生成")

        self.output_dir = QLineEdit(self.cfg.get("output_dir", ""))
        browse = GlowButton("选择目录")
        browse.clicked.connect(self.pick_output_dir)
        out_row = QHBoxLayout()
        out_row.addWidget(self.output_dir, 1)
        out_row.addWidget(browse)

        self.poll_delay = QSpinBox(); self.poll_delay.setRange(0, 300); self.poll_delay.setValue(int(self.cfg.get("poll_delay", 45)))
        self.poll_interval = QSpinBox(); self.poll_interval.setRange(1, 120); self.poll_interval.setValue(int(self.cfg.get("poll_interval", 5)))

        form.addRow("API Key", self.api_key)
        form.addRow("Seedance 2.0 Endpoint", self.video_ep)
        form.addRow("Seedance 2.0 Fast Endpoint", self.video_fast_ep)
        form.addRow("Doubao-Seedance-1.0-pro-fast Endpoint", self.seedance1_fast_ep)
        form.addRow("自定义视频 Endpoint", self.custom_video_ep)
        form.addRow("生图 Endpoint", self.image_ep)
        form.addRow("联网扩写 Endpoint", self.research_ep)
        form.addRow("输出目录", out_row)
        form.addRow("首次轮询延迟", self.poll_delay)
        form.addRow("轮询间隔", self.poll_interval)
        tabs.addTab(cfg_page, "基础")

        tos_page = QWidget()
        tform = QFormLayout(tos_page)
        self.enable_tos = QCheckBox("启用本地素材上传到 TOS")
        self.enable_tos.setChecked(bool(self.cfg.get("enable_tos_upload", False)))
        tos_tip = QLabel("说明：仅当你拖入本地视频 / 图片 / 音频并希望自动上传给火山访问时才需要 TOS。\n如果使用公网 URL、asset:// 官方素材或虚拟人像，这里可以全部留空。")
        tos_tip.setWordWrap(True)
        tos_tip.setProperty("muted", True)

        self.bucket = QLineEdit(self.cfg.get("tos_bucket", ""))
        self.bucket.setPlaceholderText("可选：仅启用本地上传时填写，例如 your-bucket")
        self.tos_ep = QLineEdit(self.cfg.get("tos_endpoint", ""))
        self.tos_ep.setPlaceholderText("可选：仅启用本地上传时填写，例如 tos-cn-beijing.volces.com")
        self.ak = QLineEdit(self.cfg.get("tos_access_key", "")); self.ak.setEchoMode(QLineEdit.Password)
        self.ak.setPlaceholderText("可选：仅启用本地上传时填写")
        self.sk = QLineEdit(self.cfg.get("tos_secret_key", "")); self.sk.setEchoMode(QLineEdit.Password)
        self.sk.setPlaceholderText("可选：仅启用本地上传时填写")

        tform.addRow("", self.enable_tos)
        tform.addRow("说明", tos_tip)
        tform.addRow("Bucket", self.bucket)
        tform.addRow("Endpoint", self.tos_ep)
        tform.addRow("AccessKey", self.ak)
        tform.addRow("SecretKey", self.sk)
        tabs.addTab(tos_page, "TOS 上传")

        btns = QHBoxLayout()
        open_profiles = GlowButton("打开模型预设", ghost=True)
        open_profiles.clicked.connect(lambda: safe_open_path(os.path.abspath(MODEL_PROFILES_FILE)))
        btns.addWidget(open_profiles)

        self_check = GlowButton("功能自检")
        self_check.clicked.connect(lambda: parent.show_stability_check() if parent and hasattr(parent, "show_stability_check") else None)
        btns.addWidget(self_check)

        btns.addStretch()
        save = GlowButton("保存设置", primary=True)
        save.clicked.connect(self.save)
        btns.addWidget(save)
        root.addLayout(btns)

    def fill_endpoint_combo(self, combo, profiles, prefix, current_endpoint=""):
        combo.clear()
        combo.setMaxVisibleItems(10)
        current_endpoint = (current_endpoint or "").strip()

        if current_endpoint:
            combo.addItem(f"{prefix}｜当前已保存｜{current_endpoint}", current_endpoint)
        else:
            combo.addItem(f"{prefix}｜当前未配置｜手动输入 Endpoint", "")

        seen_names = set()
        added_keys = set()
        for p in profiles:
            name = (p.get("name") or "未命名模型").strip()
            ep = (p.get("endpoint") or "").strip()
            seen_names.add(name)

            if prefix in {"视频", "联网"} and name == "Seedance 2.0":
                shown_ep = current_endpoint or ep
            elif prefix == "生图" and name == "Seedream Image":
                shown_ep = current_endpoint or ep
            else:
                shown_ep = ep

            state = shown_ep if shown_ep else "未配置 Endpoint"
            key = (name, shown_ep)
            if key in added_keys:
                continue
            added_keys.add(key)
            combo.addItem(f"{prefix}｜{name}｜{state}", shown_ep)

        if prefix in {"视频", "联网"}:
            for name in ["Seedance 2.0", "Seedance 2.0 Fast"]:
                if name not in seen_names:
                    state = current_endpoint if name == "Seedance 2.0" and current_endpoint else "未配置 Endpoint"
                    combo.addItem(f"{prefix}｜{name}｜{state}", current_endpoint if name == "Seedance 2.0" else "")

        if prefix == "生图" and "Seedream Image" not in seen_names:
            state = current_endpoint if current_endpoint else "未配置 Endpoint"
            combo.addItem(f"{prefix}｜Seedream Image｜{state}", current_endpoint)

        for i in range(1, 4):
            combo.addItem(f"{prefix}｜自定义接入点 {i}｜直接输入 Endpoint", "")

    def set_endpoint_combo_value(self, combo, endpoint):
        endpoint = (endpoint or "").strip()
        if not endpoint:
            combo.setCurrentIndex(0)
            return
        for i in range(combo.count()):
            if combo.itemData(i) == endpoint and "当前已保存" in combo.itemText(i):
                combo.setCurrentIndex(i)
                return
        for i in range(combo.count()):
            if combo.itemData(i) == endpoint:
                combo.setCurrentIndex(i)
                return
        combo.setCurrentText(endpoint)

    def endpoint_from_combo(self, combo):
        if isinstance(combo, QLineEdit):
            return combo.text().strip()
        data = combo.currentData()
        if data:
            return str(data).strip()
        text = combo.currentText().strip()
        if "｜" in text:
            candidate = text.split("｜")[-1].strip()
            if candidate and candidate not in {"未配置 Endpoint", "直接输入 Endpoint", "留空 / 手动输入"}:
                return candidate
            return ""
        if "未配置 Endpoint" in text or "直接输入 Endpoint" in text or "留空" in text:
            return ""
        return text

    def pick_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录", self.output_dir.text())
        if d:
            self.output_dir.setText(d)

    def clean_ep(self, x):
        x = str(x or "").strip()
        if "|" in x:
            x = x.split("|", 1)[1].strip()
        return "" if (x.startswith("空槽位") or "留空" in x or x.startswith("▼ [")) else x

    def save(self):
        video_endpoint = self.video_ep.text().strip()
        video_fast_endpoint = self.video_fast_ep.text().strip()
        seedance1_fast_endpoint = self.seedance1_fast_ep.text().strip()
        custom_video_endpoint = self.custom_video_ep.text().strip()
        image_endpoint = self.image_ep.text().strip()
        research_endpoint = self.research_ep.text().strip()

        self.cfg.update({
            "api_key": self.api_key.text().strip(),
            "video_endpoint": video_endpoint,
            "video_fast_endpoint": video_fast_endpoint,
            "doubao_seedance_1_0_pro_fast_endpoint": seedance1_fast_endpoint,
            "custom_video_endpoint": custom_video_endpoint,
            "image_endpoint": image_endpoint,
            "research_endpoint": research_endpoint,
            "output_dir": self.output_dir.text().strip(),
            "poll_delay": self.poll_delay.value(),
            "poll_interval": self.poll_interval.value(),
            "enable_tos_upload": self.enable_tos.isChecked(),
            "tos_bucket": self.bucket.text().strip(),
            "tos_endpoint": self.tos_ep.text().strip(),
            "tos_access_key": self.ak.text().strip(),
            "tos_secret_key": self.sk.text().strip(),
        })
        save_config(self.cfg)

        profiles = load_model_profiles()
        update_profile_endpoint(profiles, "video", "Seedance 2.0", video_endpoint)
        update_profile_endpoint(profiles, "video", "Seedance 2.0 Fast", video_fast_endpoint)
        update_profile_endpoint(profiles, "video", "Doubao-Seedance-1.0-pro-fast", seedance1_fast_endpoint)
        update_profile_endpoint(profiles, "video", "自定义视频模型", custom_video_endpoint)
        update_profile_endpoint(profiles, "image", "Seedream Image", image_endpoint)
        save_model_profiles(profiles)

        QMessageBox.information(
            self,
            "设置已保存",
            "管线配置已更新。\n\n"
            f"Seedance 2.0：{video_endpoint or '未配置'}\n"
            f"Seedance 2.0 Fast：{video_fast_endpoint or '未配置'}\n"
            f"Doubao-Seedance-1.0-pro-fast：{seedance1_fast_endpoint or '未配置'}\n"
            f"自定义视频模型：{custom_video_endpoint or '未配置'}\n"
            f"生图 Endpoint：{image_endpoint or '未配置'}\n"
            f"联网扩写 Endpoint：{research_endpoint or '未配置，跟随视频生成'}\n"
            f"首次轮询延迟：{self.cfg.get('poll_delay')} 秒\n"
            f"轮询间隔：{self.cfg.get('poll_interval')} 秒\n"
            f"TOS 本地上传：{'已启用' if self.cfg.get('enable_tos_upload') else '未启用，公网 URL / asset:// 可正常使用'}"
        )
        self.accept()


class UrlImportDialog(QDialog):
    def __init__(self, allow_video=True, allow_audio=True, parent=None):
        super().__init__(parent)
        self.setWindowTitle("URL / Asset 导入器")
        self.resize(700, 430)
        self.setStyleSheet(APP_QSS)
        self.allow_video = allow_video
        self.allow_audio = allow_audio
        self.detection = {}

        root = QVBoxLayout(self)
        root.addWidget(ui_label("URL / asset://", 12, True))
        self.url_in = QLineEdit()
        self.url_in.setPlaceholderText("粘贴公网 URL、TOS/CDN 链接，或 asset://素材ID")
        root.addWidget(self.url_in)

        row = QHBoxLayout()
        row.addWidget(ui_label("素材类型", 11, True, True))
        self.kind = QComboBox()
        kinds = ["自动识别", "图片"]
        if allow_video: kinds.append("视频")
        if allow_audio: kinds.append("音频")
        self.kind.addItems(kinds)
        row.addWidget(self.kind)
        row.addWidget(ui_label("显示名称", 11, True, True))
        self.name = QLineEdit()
        self.name.setPlaceholderText("可选，例如：老人包饺子参考")
        row.addWidget(self.name, 1)
        root.addLayout(row)

        self.note = QLineEdit()
        self.note.setPlaceholderText("来源备注：例如 抖音临时链接 / TOS / 官方素材库")
        root.addWidget(self.note)

        self.status = QTextEdit()
        self.status.setReadOnly(True)
        self.status.setMaximumHeight(140)
        self.status.setPlaceholderText("点击「检测链接」后显示检测结果。")
        root.addWidget(self.status)

        btns = QHBoxLayout()
        detect = GlowButton("检测链接")
        detect.clicked.connect(self.detect)
        btns.addWidget(detect)
        btns.addStretch()
        cancel = GlowButton("取消", ghost=True)
        cancel.clicked.connect(self.reject)
        add = GlowButton("添加素材", primary=True)
        add.clicked.connect(self.accept)
        btns.addWidget(cancel)
        btns.addWidget(add)
        root.addLayout(btns)

    def detect(self):
        u = self.url_in.text().strip()
        if not u:
            self.status.setText("请先粘贴 URL。")
            return
        d = detect_url_asset(u)
        self.detection = d
        risk = "；".join(d.get("risk") or []) or "无明显风险"
        self.status.setText(
            f"检测结果：{d.get('message')}\n"
            f"识别类型：{d.get('kind')}\n"
            f"Content-Type：{d.get('content_type') or '未知'}\n"
            f"Content-Length：{d.get('content_length') or '未知'}\n"
            f"风险提示：{risk}\n\n"
            "提示：短视频平台临时链接可能本地能打开，但方舟服务器无法访问；更稳的方式是下载到本地后上传 TOS。"
        )
        if self.kind.currentText() == "自动识别":
            if d.get("kind") == "video" and self.allow_video:
                self.kind.setCurrentText("视频")
            elif d.get("kind") == "audio" and self.allow_audio:
                self.kind.setCurrentText("音频")
            elif d.get("kind") == "image":
                self.kind.setCurrentText("图片")

    def data(self):
        m = {"图片": "image", "视频": "video", "音频": "audio"}
        kind = m.get(self.kind.currentText()) or self.detection.get("kind") or asset_kind(self.url_in.text())
        return {
            "url": self.url_in.text().strip(),
            "kind": kind,
            "display_name": self.name.text().strip(),
            "note": self.note.text().strip(),
            "detection": self.detection
        }
