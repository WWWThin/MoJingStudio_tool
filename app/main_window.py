from .common import *
from .widgets import *
from .workers import *
from .dialogs import *

# =========================================================
# 4. 主窗口
# =========================================================

class SeedanceV5Workbench(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("墨境片场 Stable v2.0")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self._window_drag_pos = None
        self.resize(1580, 940)
        self.setMinimumSize(1280, 780)
        self.setStyleSheet(APP_QSS)

        self.cfg = load_config()
        ensure_dir(self.cfg.get("output_dir", "outputs"))
        self.profiles = load_model_profiles()
        self.assets: List[AssetItem] = []
        self.current_asset: Optional[AssetItem] = None
        self.persona_library = load_persona_library()
        self.current_persona = None
        self.current_worker = None
        self.active_workers = [] # <--- 新增的活跃线程池
        self.cloud_tasks = []
        self.current_cloud_task = None
        self.cloud_input_mode = "auto"

        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        main.addWidget(self.build_topbar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self.build_sidebar())

        self.stack = QStackedWidget()
        self.stack.addWidget(self.build_shot_page())
        self.stack.addWidget(self.build_image_page())
        self.stack.addWidget(self.build_cloud_page())
        self.stack.addWidget(self.build_vault_page())
        self.stack.addWidget(self.build_library_page())
        self.stack.addWidget(self.build_persona_page())
        body.addWidget(self.stack, 1)

        main.addLayout(body, 1)
        main.addWidget(self.build_statusbar())

        self.setAcceptDrops(True)
        QTimer.singleShot(300, self.update_shot_path_label)
        QTimer.singleShot(700, self.refresh_vault)
        QTimer.singleShot(1100, lambda: self.log(self.stability_report_text()))

    def toggle_max_restore(self):
        if self.isMaximized():
            self.showNormal()
            if hasattr(self, "max_btn"):
                self.max_btn.setText("□")
        else:
            self.showMaximized()
            if hasattr(self, "max_btn"):
                self.max_btn.setText("❐")

    def mouseDoubleClickEvent(self, event):
        try:
            y = event.position().y()
        except Exception:
            y = event.y()
        if y <= 104:
            self.toggle_max_restore()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        try:
            pos = event.globalPosition().toPoint()
            y = event.position().y()
        except Exception:
            pos = event.globalPos()
            y = event.y()
        if event.button() == Qt.LeftButton and y <= 104:
            self._window_drag_pos = pos - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._window_drag_pos is not None and event.buttons() & Qt.LeftButton and not self.isMaximized():
            try:
                pos = event.globalPosition().toPoint()
            except Exception:
                pos = event.globalPos()
            self.move(pos - self._window_drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._window_drag_pos = None
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            fw = QApplication.focusWidget()
            if isinstance(fw, (QLineEdit, QTextEdit)):
                return super().keyPressEvent(event)
            if getattr(self, "current_asset", None):
                name = self.current_asset.display_name or self.current_asset.tag
                self.delete_asset(self.current_asset)
                self.set_status(f"已删除素材：{name}")
                event.accept()
                return
        super().keyPressEvent(event)

    def dropEvent(self, event):
        added = 0
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                fp = url.toLocalFile()
                if not fp:
                    continue
                if os.path.isfile(fp) and fp.lower().endswith(IMAGE_EXTS + VIDEO_EXTS + AUDIO_EXTS):
                    self.add_asset(fp, kind=asset_kind(fp))
                    added += 1
        elif event.mimeData().hasText():
            raw = event.mimeData().text().strip()
            urls = re.findall(r"https?://[^\s]+|asset://[^\s]+", raw)
            for u in urls:
                kind = asset_kind(u)
                d = detect_url_asset(u) if u.startswith(("http://", "https://", "asset://")) else {}
                self.add_asset(u, kind=kind, display_name=short_url_label(u), detection=d)
                added += 1

        if added:
            self.update_asset_usage()
            self.refresh_assets()
            self.set_status(f"已拖入 {added} 个素材。")
            event.acceptProposedAction()
        else:
            event.ignore()

    # ---------- 基础布局 ----------

    def build_topbar(self):
        bar = QFrame()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(104)
        root = QVBoxLayout(bar)
        root.setContentsMargins(18, 8, 18, 8)
        root.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(14)
        top.addWidget(ui_label("墨境片场", 15, True))
        top.addWidget(Pill("完整工作台", Theme.CYAN))
        top.addSpacing(12)

        top.addWidget(ui_label("项目", 11, True, True))
        self.project_in = QLineEdit(self.cfg.get("last_project_name", "Baijin_Test"))
        self.project_in.setFixedWidth(180)
        top.addWidget(self.project_in)

        confirm_project = GlowButton("确认项目", primary=True)
        confirm_project.clicked.connect(self.confirm_project_settings)
        top.addWidget(confirm_project)

        top.addWidget(ui_label("镜头", 11, True, True))
        self.shot_in = QLineEdit(self.cfg.get("last_shot_name", "S01"))
        self.shot_in.setFixedWidth(105)
        top.addWidget(self.shot_in)

        new_shot = GlowButton("新建镜头")
        new_shot.clicked.connect(self.create_next_shot)
        top.addWidget(new_shot)

        top.addStretch()
        self_check = GlowButton("功能自检")
        self_check.clicked.connect(self.show_stability_check)
        top.addWidget(self_check)

        settings = GlowButton("管线设置")
        settings.clicked.connect(self.open_settings)
        top.addWidget(settings)

        start = GlowButton("提交生成", primary=True)
        start.clicked.connect(self.run_video_task)
        top.addWidget(start)

        stop = GlowButton("停止", danger=True)
        stop.clicked.connect(self.cancel_current_task)
        top.addWidget(stop)

        top.addSpacing(8)
        minimize_btn = GlowButton("—")
        minimize_btn.setFixedWidth(34)
        minimize_btn.clicked.connect(self.showMinimized)
        top.addWidget(minimize_btn)

        self.max_btn = GlowButton("□")
        self.max_btn.setFixedWidth(34)
        self.max_btn.clicked.connect(self.toggle_max_restore)
        top.addWidget(self.max_btn)

        close_btn = GlowButton("×", danger=True)
        close_btn.setFixedWidth(34)
        close_btn.clicked.connect(self.close)
        top.addWidget(close_btn)

        root.addLayout(top)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        path_row.addWidget(ui_label("输出根目录", 11, True, True))

        self.out_dir_label = QLineEdit(self.cfg.get("output_dir", "outputs"))
        self.out_dir_label.setPlaceholderText("选择项目输出根目录")
        self.out_dir_label.setMinimumWidth(260)
        self.out_dir_label.textChanged.connect(self.on_output_dir_changed)
        path_row.addWidget(self.out_dir_label, 2)

        pick_path = GlowButton("选择")
        pick_path.clicked.connect(self.pick_output_root)
        path_row.addWidget(pick_path)

        path_row.addSpacing(10)
        path_row.addWidget(ui_label("当前镜头路径", 11, True, True))

        self.shot_path_label = QLineEdit()
        self.shot_path_label.setReadOnly(True)
        self.shot_path_label.setPlaceholderText("当前镜头完整路径")
        path_row.addWidget(self.shot_path_label, 3)

        open_path = GlowButton("打开")
        open_path.clicked.connect(lambda: safe_open_path(self.current_shot_dir(create=True)))
        path_row.addWidget(open_path)
        root.addLayout(path_row)

        self.project_in.textChanged.connect(self.update_shot_path_label)
        self.shot_in.textChanged.connect(self.update_shot_path_label)
        return bar

    def build_sidebar(self):
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(210)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(14, 18, 14, 18)
        lay.setSpacing(8)

        items = [
            ("镜头生成", 0),
            ("画面生成", 1),
            ("云端任务", 2),
            ("渲染金库", 3),
            ("资料库", 4),
            ("人像库", 5),
        ]
        self.nav_buttons = []
        for i, (name, idx) in enumerate(items):
            b = QPushButton(name)
            b.setCheckable(True)
            b.setFixedHeight(44)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding-left: 16px;
                background: transparent;
                border: 1px solid transparent;
                color: #8F9AAF;
                border-radius: 12px;
                font-weight: 800;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.045);
                color: #EEF3FA;
                border: 1px solid rgba(145,160,184,0.14);
            }
            QPushButton:checked {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #162235, stop:0.56 #111A28, stop:1 #1C2634);
                color: #F3F5F8;
                border-top: 1px solid rgba(255,255,255,0.10);
                border-left: 3px solid #C8924A;
                border-right: 1px solid rgba(0,0,0,0.45);
                border-bottom: 1px solid rgba(0,0,0,0.55);
            }
            """)
            b.clicked.connect(lambda checked, p=idx: self.switch_page(p))
            lay.addWidget(b)
            self.nav_buttons.append(b)
            if i == 1:
                lay.addWidget(ui_label("管理", 9, True, True))
            if i == 3:
                lay.addWidget(ui_label("资料", 9, True, True))
        self.nav_buttons[0].setChecked(True)
        lay.addStretch()
        lay.addWidget(ui_label("状态", 10, True, True))
        lay.addWidget(Pill("引擎就绪", Theme.GREEN))
        return side

    def switch_page(self, idx):
        self.stack.setCurrentIndex(idx)
        for i, b in enumerate(self.nav_buttons):
            b.setChecked(i == idx)
        if idx == 3:
            QTimer.singleShot(80, self.refresh_vault)

    def build_statusbar(self):
        bar = QFrame()
        bar.setObjectName("StatusBar")
        bar.setFixedHeight(42)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)
        self.status_pill = Pill("READY", Theme.GREEN)
        lay.addWidget(self.status_pill)
        self.status_label = ui_label("无活动任务。", 11, False, True)
        lay.addWidget(self.status_label)
        lay.addStretch()
        progress_btn = GlowButton("任务进度器", ghost=True)
        progress_btn.clicked.connect(self.show_task_progress)
        lay.addWidget(progress_btn)

        log_btn = GlowButton("展开日志", ghost=True)
        log_btn.clicked.connect(self.toggle_log)
        lay.addWidget(log_btn)
        return bar

    def toggle_log(self):
        self.log_box.setVisible(not self.log_box.isVisible())

    def show_task_progress(self):
        if not hasattr(self, "progress_dialog") or self.progress_dialog is None:
            self.progress_dialog = TaskProgressDialog(self)
            self.progress_dialog.append_log("当前没有正在显示的任务。")
        self.progress_dialog.show()
        self.progress_dialog.raise_()
        self.progress_dialog.activateWindow()

    def set_status(self, text):
        self.status_label.setText(text)

    # ---------- 镜头生成页 ----------

    def build_shot_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(12)

        controls = ProPanel("镜头规格", "模型、模式、比例与基础参数")
        cl = QHBoxLayout()
        self.video_model = QComboBox()
        self.video_model.addItems([p.get("name") for p in self.profiles.get("video", [])])
        self.video_model.setCurrentText(default_profile(self.profiles, "video").get("name", ""))
        self.video_model.currentTextChanged.connect(self.apply_video_model_profile)

        self.video_mode = SegmentedControl(["普通生成", "视频编辑", "视频延长", "前序生成", "轨道补全"], 2)
        self.video_mode.changed.connect(self.apply_video_mode_template)
        self.video_res = SegmentedControl(["720p", "1080p"], 0)
        self.video_ratio = QComboBox()
        self.video_ratio.addItems(["16:9", "9:16", "21:9", "4:3", "1:1", "3:4", "adaptive"])
        self.video_duration = QComboBox()
        self.video_duration.addItems([str(i) for i in range(4, 16)])
        self.video_duration.setCurrentText("5")
        self.video_service_tier = QComboBox()
        self.video_service_tier.addItems(["在线推理", "离线推理"])
        self.video_service_tier.setCurrentText("在线推理")
        self.video_service_tier.setToolTip("在线推理：出结果更快。离线推理：价格更低，但等待时间更长，仅部分模型支持。")

        cl.addWidget(InspectorRow("视频模型", self.video_model))
        cl.addWidget(InspectorRow("生成模式", self.video_mode), 2)
        cl.addWidget(InspectorRow("清晰度", self.video_res))
        cl.addWidget(InspectorRow("比例", self.video_ratio))
        cl.addWidget(InspectorRow("时长", self.video_duration))
        cl.addWidget(InspectorRow("推理层级", self.video_service_tier))
        controls.body.addLayout(cl)
        outer.addWidget(controls)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        split.addWidget(self.build_asset_pool())
        split.addWidget(self.build_prompt_studio())
        split.addWidget(self.build_video_inspector())
        split.setSizes([330, 780, 340])

        self.shot_body_split = QSplitter(Qt.Horizontal)
        self.shot_body_split.setChildrenCollapsible(False)
        self.shot_body_split.addWidget(split)
        self.project_video_panel = self.build_project_video_panel()
        self.shot_body_split.addWidget(self.project_video_panel)
        self.shot_body_split.setSizes([1180, 320])
        outer.addWidget(self.shot_body_split, 1)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setVisible(False)
        self.log_box.setFixedHeight(160)
        self.log_box.setStyleSheet("font-family:Consolas, 'Cascadia Mono'; color:#8FF6B3;")
        outer.addWidget(self.log_box)
        return page

    # ---------- 项目 / 镜头路径 ----------

    def safe_name(self, text, fallback):
        s = re.sub(r"[^\w\u4e00-\u9fa5-]+", "_", (text or "").strip())
        return s or fallback

    def output_root(self):
        if hasattr(self, "out_dir_label"):
            return self.out_dir_label.text().strip() or self.cfg.get("output_dir", "outputs")
        return self.cfg.get("output_dir", "outputs")

    def current_project_dir(self, create=False):
        path = os.path.join(self.output_root(), self.safe_name(self.project_in.text(), "Project"))
        if create:
            ensure_dir(path)
        return path

    def current_shot_dir(self, image=False, create=False):
        shot = self.safe_name(self.shot_in.text(), "S01")
        if image:
            shot = shot + "_IMG"
        path = os.path.join(self.current_project_dir(create=create), shot)
        if create:
            ensure_dir(path)
        return path

    def update_shot_path_label(self):
        if hasattr(self, "project_in") and hasattr(self, "shot_in"):
            self.cfg["last_project_name"] = self.project_in.text().strip()
            self.cfg["last_shot_name"] = self.shot_in.text().strip()
            save_config(self.cfg)
            
        if hasattr(self, "shot_path_label"):
            self.shot_path_label.setText(self.current_shot_dir(create=False))
        QTimer.singleShot(160, self.refresh_project_videos)

    def confirm_project_settings(self):
        project_dir = self.current_project_dir(create=True)
        shot_dir = self.current_shot_dir(create=True)
        self.cfg["output_dir"] = self.output_root()
        self.cfg["last_project_name"] = self.project_in.text().strip() or "Project"
        self.cfg["last_shot_name"] = self.shot_in.text().strip() or "S01"
        save_config(self.cfg)
        self.update_shot_path_label()
        self.refresh_project_videos()
        self.refresh_vault()
        self.set_status(f"项目已确认：{project_dir}")
        QMessageBox.information(self, "项目已确认", f"已创建 / 确认项目路径：\n{project_dir}\n\n当前镜头路径：\n{shot_dir}")

    def on_output_dir_changed(self):
        self.cfg["output_dir"] = self.out_dir_label.text().strip()
        save_config(self.cfg)
        self.update_shot_path_label()
        self.refresh_vault()

    def pick_output_root(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出根目录", self.output_root())
        if d:
            self.out_dir_label.setText(d)
            self.confirm_project_settings()

    def create_next_shot(self):
        project_dir = ensure_dir(self.current_project_dir(create=True))
        nums = []
        for name in os.listdir(project_dir):
            full = os.path.join(project_dir, name)
            if os.path.isdir(full):
                m = re.match(r"^[sS]?(\d+)", name)
                if m:
                    nums.append(int(m.group(1)))
        next_num = (max(nums) + 1) if nums else 1
        shot = f"S{next_num:02d}"
        self.shot_in.setText(shot)
        ensure_dir(self.current_shot_dir(create=True))
        self.update_shot_path_label()
        self.set_status(f"已创建新镜头：{shot}")

    def video_mode_template(self, mode):
        templates = {
            "普通生成": "根据提示词生成电影级写实视频，画面自然、光影真实、运动连贯。",
            "视频编辑": "以 [@视频1] 为基础进行视频编辑，保持原视频镜头运动、空间关系、透视、光影方向和物理一致性，只修改提示词中指定的内容。",
            "视频延长": "将 [@视频1] 向后延长，保持原视频的人物状态、主体运动、镜头运动、空间关系、光影方向与画面风格连续，自然生成后续画面。",
            "前序生成": "为 [@视频1] 生成前序画面，保持原视频的人物状态、空间关系、光影方向与画面风格一致，生成发生在视频开头之前的内容，并自然衔接到原视频开头。",
            "轨道补全": "按顺序参考 [@视频1]、[@视频2]、[@视频3]，生成它们之间连贯的过渡画面，补全空间运动轨迹、镜头连接和视觉节奏，使多个片段形成一个完整连续镜头。"
        }
        return templates.get(mode, "")

    def apply_video_mode_template(self, mode):
        if not hasattr(self, "video_prompt"):
            return
        tpl = self.video_mode_template(mode)
        if not tpl:
            return
        current = self.video_prompt.toPlainText().strip()
        if tpl in current:
            return
        known = [self.video_mode_template(m) for m in ["普通生成", "视频编辑", "视频延长", "前序生成", "轨道补全"]]
        if not current or current in known:
            self.video_prompt.setText(tpl)
        else:
            self.video_prompt.setText(tpl + "\n\n" + current)
        self.update_asset_usage()

    # ---------- 项目视频侧栏 ----------

    def build_project_video_panel(self):
        panel = ProPanel("项目视频", "扫描项目目录与子目录，按镜头号分组")
        top = QHBoxLayout()
        scan = GlowButton("扫描")
        scan.clicked.connect(self.refresh_project_videos)
        info = GlowButton("信息")
        info.clicked.connect(self.show_project_video_summary)
        self.project_video_toggle = GlowButton("收起")
        self.project_video_toggle.clicked.connect(self.toggle_project_video_panel)
        top.addWidget(scan)
        top.addWidget(info)
        top.addWidget(self.project_video_toggle)
        top.addStretch()
        panel.body.addLayout(top)

        slider_row, self.project_video_thumb_slider = self.make_thumb_slider_row("视频缩略图大小", 64, 180, 88, lambda _v: self.refresh_project_videos())
        panel.body.addLayout(slider_row)

        self.project_video_scroll = QScrollArea()
        self.project_video_scroll.setWidgetResizable(True)
        self.project_video_host = QWidget()
        self.project_video_list = QVBoxLayout(self.project_video_host)
        self.project_video_list.setContentsMargins(2, 2, 8, 2)
        self.project_video_list.setSpacing(10)
        self.project_video_scroll.setWidget(self.project_video_host)
        panel.body.addWidget(self.project_video_scroll, 1)

        self.project_video_meta = QTextEdit()
        self.project_video_meta.setReadOnly(True)
        self.project_video_meta.setFixedHeight(170)
        self.project_video_meta.setPlaceholderText("选中项目视频后显示元数据。")
        panel.body.addWidget(self.project_video_meta)

        btns = QHBoxLayout()
        copy = GlowButton("复制 Prompt")
        copy.clicked.connect(self.copy_project_video_prompt)
        fill = GlowButton("填入当前 Prompt", primary=True)
        fill.clicked.connect(self.fill_project_video_prompt)
        btns.addWidget(copy)
        btns.addWidget(fill)
        panel.body.addLayout(btns)
        QTimer.singleShot(300, self.refresh_project_videos)
        return panel

    def toggle_project_video_panel(self):
        if not hasattr(self, "project_video_panel"):
            return
        hidden = not self.project_video_panel.isVisible()
        self.project_video_panel.setVisible(hidden)
        self.project_video_toggle.setText("收起" if hidden else "展开")

    def show_project_video_summary(self):
        root = self.current_project_dir()
        ensure_dir(root)
        files = []
        total_seconds = 0.0
        total_cost = 0.0
        for base, _, names in os.walk(root):
            for name in names:
                fp = os.path.join(base, name)
                if fp.lower().endswith(VIDEO_EXTS):
                    files.append(fp)
                    meta = load_sidecar(fp)
                    try:
                        total_seconds += float(meta.get("duration") or 0)
                    except Exception:
                        pass
                    cost_text = estimate_cost(meta, self.profiles) if meta else ""
                    m = re.search(r"¥([0-9.]+)", cost_text)
                    if m:
                        try:
                            total_cost += float(m.group(1))
                        except Exception:
                            pass
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        cost_line = f"¥{total_cost:.2f}" if total_cost > 0 else "暂无可计算费用"
        QMessageBox.information(
            self,
            "项目视频信息",
            f"项目名称：{self.project_in.text().strip()}\n"
            f"镜头号：{self.shot_in.text().strip()}\n"
            f"视频数量：{len(files)}\n"
            f"视频总时长：{minutes:02d}:{seconds:02d}\n"
            f"镜头费用总计：{cost_line}"
        )

    def shot_group_name_for_path(self, fp):
        root = os.path.abspath(self.current_project_dir())
        full = os.path.abspath(fp)
        try:
            rel = os.path.relpath(full, root)
        except Exception:
            return "未分类"
        parts = rel.split(os.sep)
        if len(parts) >= 2:
            return parts[0]
        name = os.path.basename(fp)
        m = re.search(r"([sS]\d{1,4})", name)
        if m:
            return m.group(1).upper()
        return "项目根目录"

    def shot_sort_key(self, shot_name):
        m = re.search(r"(\d+)", shot_name or "")
        return (int(m.group(1)) if m else 999999, shot_name or "")

    def make_project_video_group_header(self, shot_name, files):
        header = QFrame()
        header.setStyleSheet(f"""
        QFrame {{
            background: rgba(255,255,255,0.035);
            border: 1px solid {Theme.BORDER};
            border-radius: 12px;
        }}
        """)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(10, 7, 10, 7)
        lay.setSpacing(8)

        total_seconds = 0.0
        total_cost = 0.0
        for fp in files:
            meta = load_sidecar(fp)
            try:
                total_seconds += float(meta.get("duration") or 0)
            except Exception:
                pass
            cost_text = estimate_cost(meta, self.profiles) if meta else ""
            m = re.search(r"¥([0-9.]+)", cost_text)
            if m:
                try:
                    total_cost += float(m.group(1))
                except Exception:
                    pass
        mm = int(total_seconds // 60)
        ss = int(total_seconds % 60)
        cost = f"¥{total_cost:.2f}" if total_cost > 0 else "费用待计算"

        lay.addWidget(ui_label(str(shot_name), 12, True))
        lay.addStretch()
        lay.addWidget(ui_label(f"{len(files)} 个视频", 10, False, True))
        lay.addWidget(ui_label(f"总时长 {mm:02d}:{ss:02d}", 10, False, True))
        lay.addWidget(ui_label(cost, 10, False, True))
        return header

    def refresh_project_videos(self):
        if not hasattr(self, "project_video_list"):
            return
        self.clear_layout(self.project_video_list)
        root = self.current_project_dir()
        ensure_dir(root)

        grouped = {}
        for base, _, names in os.walk(root):
            for name in names:
                fp = os.path.join(base, name)
                if fp.lower().endswith(VIDEO_EXTS):
                    group = self.shot_group_name_for_path(fp)
                    grouped.setdefault(group, []).append(fp)

        if not grouped:
            empty = QTextEdit()
            empty.setReadOnly(True)
            empty.setFixedHeight(90)
            empty.setText("当前项目目录和子目录中没有扫描到视频。\n会扫描：项目根目录 / S01 / S02 / 任意子目录。")
            self.project_video_list.addWidget(empty)
            self.project_video_list.addStretch(1)
            return

        for shot_name in sorted(grouped.keys(), key=self.shot_sort_key):
            files = grouped[shot_name]
            files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            self.project_video_list.addWidget(self.make_project_video_group_header(shot_name, files))
            for fp in files[:40]:
                c = ResultCard(fp, self.current_project_video_thumb_size())
                c.clicked.connect(self.show_project_video_meta)
                c.double_clicked.connect(lambda card: safe_open_path(card.path))
                self.project_video_list.addWidget(c)

        self.project_video_list.addStretch(1)

    def show_project_video_meta(self, card):
        self.current_project_video_path = card.path
        meta = load_sidecar(card.path)
        if not meta:
            self.project_video_meta.setText(f"文件：{os.path.basename(card.path)}\n暂无元数据。")
            return
        prompt = meta.get("prompt", "")
        if len(prompt) > 520:
            prompt_show = prompt[:520] + "..."
        else:
            prompt_show = prompt
        self.project_video_meta.setText(
            f"文件：{os.path.basename(card.path)}\n"
            f"任务 ID：{meta.get('task_id','')}\n"
            f"模式：{meta.get('video_mode', meta.get('mode',''))}\n"
            f"清晰度：{meta.get('resolution','')}｜比例：{meta.get('ratio','')}｜时长：{meta.get('duration','')}\n"
            f"Seed：{meta.get('seed','')}｜用时：{meta.get('elapsed_seconds','')}s\n\n"
            f"Prompt：\n{prompt_show}"
        )

    def current_project_video_prompt(self):
        p = getattr(self, "current_project_video_path", "")
        if not p:
            return ""
        return load_sidecar(p).get("prompt", "")

    def copy_project_video_prompt(self):
        prompt = self.current_project_video_prompt()
        if prompt:
            QApplication.clipboard().setText(prompt)
            self.set_status("已复制项目视频 Prompt。")

    def fill_project_video_prompt(self):
        prompt = self.current_project_video_prompt()
        if prompt:
            self.video_prompt.setText(prompt)
            self.set_status("已填入项目视频 Prompt，可继续二次编辑。")

    def make_thumb_slider_row(self, label_text, min_v, max_v, default_v, callback):
        row = QHBoxLayout()
        row.addWidget(ui_label(label_text, 11, True, True))
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_v, max_v)
        slider.setValue(default_v)
        value_label = ui_label(str(default_v), 11, False, True)
        value_label.setFixedWidth(42)
        slider.valueChanged.connect(lambda v: value_label.setText(str(v)))
        slider.valueChanged.connect(callback)
        row.addWidget(slider, 1)
        row.addWidget(value_label)
        return row, slider

    def current_asset_thumb_size(self):
        return self.asset_thumb_slider.value() if hasattr(self, "asset_thumb_slider") else 150

    def current_project_video_thumb_size(self):
        return self.project_video_thumb_slider.value() if hasattr(self, "project_video_thumb_slider") else 88

    def current_vault_thumb_size(self):
        return self.vault_thumb_slider.value() if hasattr(self, "vault_thumb_slider") else 88

    def current_cloud_thumb_size(self):
        return self.cloud_thumb_slider.value() if hasattr(self, "cloud_thumb_slider") else 112

    def build_asset_pool(self):
        panel = ProPanel("素材池", "参考视频 / 图片 / 音频")
        row = QHBoxLayout()
        self.asset_search = QLineEdit()
        self.asset_search.setPlaceholderText("搜索素材")
        self.asset_search.textChanged.connect(self.refresh_assets)
        row.addWidget(self.asset_search, 1)

        import_local = GlowButton("导入本地")
        import_local.clicked.connect(self.import_local_assets)
        row.addWidget(import_local)

        import_url = GlowButton("URL / Asset")
        import_url.clicked.connect(self.import_url_asset)
        row.addWidget(import_url)

        add_persona = GlowButton("虚拟人像库")
        add_persona.clicked.connect(self.show_add_virtual_persona_asset_menu)
        row.addWidget(add_persona)
        panel.body.addLayout(row)

        self.asset_filter = SegmentedControl(["全部", "视频", "图片", "音频", "URL"], 0)
        self.asset_filter.changed.connect(lambda _: self.refresh_assets())
        panel.body.addWidget(self.asset_filter)

        slider_row, self.asset_thumb_slider = self.make_thumb_slider_row("素材缩略图大小", 64, 150, 92, lambda _v: self.refresh_assets())
        panel.body.addLayout(slider_row)

        self.asset_scroll = QScrollArea()
        self.asset_scroll.setAcceptDrops(True)
        self.asset_scroll.setWidgetResizable(True)
        self.asset_grid_host = QWidget()
        self.asset_grid_host.setAcceptDrops(True)
        self.asset_grid = QGridLayout(self.asset_grid_host)
        self.asset_grid.setContentsMargins(2, 2, 8, 2)
        self.asset_grid.setSpacing(10)
        self.asset_scroll.setWidget(self.asset_grid_host)
        panel.body.addWidget(self.asset_scroll, 1)

        self.asset_detail = QTextEdit()
        self.asset_detail.setReadOnly(True)
        self.asset_detail.setFixedHeight(125)
        self.asset_detail.setPlaceholderText("选中素材后显示详情。支持拖入本地素材，也可以把素材卡片拖到 Prompt 指定位置创建引用图标。")
        panel.body.addWidget(self.asset_detail)
        return panel

    def build_prompt_studio(self):
        clear_prompt_btn = GlowButton("清空 Prompt", danger=True)
        clear_prompt_btn.clicked.connect(lambda: self.video_prompt.clear() if hasattr(self, "video_prompt") else None)

        insert_persona_btn = GlowButton("插入虚拟人像")
        insert_persona_btn.clicked.connect(self.show_insert_virtual_persona_menu)

        web_expand_btn = GlowButton("联网扩写")
        web_expand_btn.clicked.connect(self.expand_prompt_with_web_search)

        check_prompt_btn = GlowButton("提示词体检")
        check_prompt_btn.clicked.connect(self.check_prompt_quality)

        normalize_prompt_btn = GlowButton("整理文本")
        normalize_prompt_btn.clicked.connect(self.normalize_prompt_editor_plain_text)

        panel = ProPanel("Prompt Studio", "导演提示词、结构控制与负面约束",
                         actions=[insert_persona_btn, web_expand_btn, check_prompt_btn, normalize_prompt_btn, clear_prompt_btn])
        row = QHBoxLayout()
        self.prompt_style_segment = SegmentedControl(["自由提示词", "结构化"], 0)
        self.prompt_style_segment.changed.connect(self.on_prompt_style_changed)
        row.addWidget(self.prompt_style_segment, 1)
        self.asset_bound_pill = Pill("0 个素材", Theme.AMBER)
        row.addWidget(self.asset_bound_pill)
        self.audio_sync_chk = QCheckBox("音频节奏同步")
        self.audio_sync_chk.setChecked(True)
        row.addWidget(self.audio_sync_chk)
        self.web_search_chk = QCheckBox("生成任务启用 web_search")
        row.addWidget(self.web_search_chk)
        panel.body.addLayout(row)

        template_row = QHBoxLayout()
        template_row.setSpacing(8)
        template_row.addWidget(ui_label("Prompt 模板", 12, False, True))
        self.prompt_template_combo = QComboBox()
        self.reload_prompt_template_combo()
        template_row.addWidget(self.prompt_template_combo, 1)

        save_template_btn = GlowButton("保存为模板", ghost=True)
        save_template_btn.clicked.connect(self.save_current_prompt_as_template)
        template_row.addWidget(save_template_btn)

        delete_template_btn = GlowButton("删除自定义", ghost=True)
        delete_template_btn.clicked.connect(self.delete_selected_custom_template)
        template_row.addWidget(delete_template_btn)

        insert_template_btn = GlowButton("插入模板")
        insert_template_btn.clicked.connect(self.insert_selected_prompt_template)
        template_row.addWidget(insert_template_btn)

        replace_template_btn = GlowButton("替换为模板", ghost=True)
        replace_template_btn.clicked.connect(self.replace_with_selected_prompt_template)
        template_row.addWidget(replace_template_btn)

        panel.body.addLayout(template_row)

        self.video_prompt = AssetPromptEdit(lambda: self.assets, self)
        self.video_prompt.setAcceptRichText(False)
        self.video_prompt.setLineWrapMode(QTextEdit.WidgetWidth)
        self.video_prompt.setPlaceholderText("输入 @ 选择素材，素材会显示成一个可视化小标签。也兼容手写 [@视频1] / [@图片1] / [@音频1]。")
        self.video_prompt.setMinimumHeight(270)
        self.video_prompt.textChanged.connect(self.update_asset_usage)
        self.video_prompt.setStyleSheet("""
        QTextEdit {
            font-size: 16px;
            padding: 16px;
            border-radius: 16px;
            background-color: #09111D;
        }
        """)
        panel.body.addWidget(self.video_prompt, 2)

        self.video_negative = QTextEdit()
        self.video_negative.setPlaceholderText("负面提示词：畸形手、闪烁脸、破碎几何、错误文字、过度锐化...")
        self.video_negative.setFixedHeight(112)
        panel.body.addWidget(self.video_negative)

        self.prompt_report = QTextEdit()
        self.prompt_report.setReadOnly(True)
        self.prompt_report.setFixedHeight(86)
        self.prompt_report.setText("提示词体检：等待检查。")
        panel.body.addWidget(self.prompt_report)

        return panel

    # ---------- Prompt 模板 ----------

    def builtin_prompt_template_names(self):
        return ["镜头生成", "连续镜头", "素材驱动", "概念出场"]

    def custom_prompt_templates(self):
        raw = load_prompt_library()
        items = []
        if isinstance(raw, list):
            for i, x in enumerate(raw, 1):
                if isinstance(x, dict):
                    title = x.get("title") or f"自定义模板 {i}"
                    content = x.get("content") or ""
                else:
                    content = str(x)
                    title = content.splitlines()[0][:22] if content.strip() else f"自定义模板 {i}"
                if content.strip():
                    items.append({"title": title, "content": content})
        return items

    def reload_prompt_template_combo(self):
        if not hasattr(self, "prompt_template_combo"):
            return
        cur = self.prompt_template_combo.currentText()
        self.prompt_template_combo.clear()
        self.prompt_template_combo.addItems(self.builtin_prompt_template_names())
        customs = self.custom_prompt_templates()
        if customs:
            self.prompt_template_combo.insertSeparator(self.prompt_template_combo.count())
            for item in customs:
                self.prompt_template_combo.addItem("自定义｜" + item["title"], item["content"])
        if cur:
            self.prompt_template_combo.setCurrentText(cur)

    def selected_prompt_template_name(self):
        if hasattr(self, "prompt_template_combo"):
            return self.prompt_template_combo.currentText()
        return "镜头生成"

    def prompt_template_text(self, name):
        if hasattr(self, "prompt_template_combo"):
            data = self.prompt_template_combo.currentData()
            if data:
                return str(data)
        templates = {
            "镜头生成": """【本镜目标】\n生成一个电影级写实镜头，画面自然、主体清晰、运动连贯。\n\n【场景与角色】\n场景：____。\n角色：____。\n当前状态：____。\n\n【镜头与光影】\n景别：____。\n机位与运镜：____。\n光源方向与色调：____。\n\n【动作】\n角色动作：____。\n环境变化：____。\n\n【生成约束】\n保持主体身份、服装材质、空间关系和光影方向稳定。避免变形、闪烁、背景突变、错误文字。""",
            "连续镜头": """【连续性】\n本镜与上一镜保持同一角色、同一场景、同一光影方向和同一情绪基调。\n上一镜参考：[@视频1]\n\n【本镜目标】\n继续上一镜内容，生成自然连贯的后续镜头。\n\n【本镜新增变化】\n本镜只新增：____。\n\n【镜头与动作】\n镜头运动：____。\n角色动作：____。\n环境变化：____。\n\n【生成约束】\n保持人物身份、服装材质、空间关系、镜头语言和光影方向稳定。避免换脸、服装突变、场景跳变、镜头突然切换、多余角色和错误文字。""",
            "素材驱动": """【参考素材】\n角色参考：[@图片1]\n场景参考：[@图片2]\n虚拟人像参考：[@虚拟人像1]\n\n【本镜目标】\n基于参考素材生成一个电影级写实镜头，优先保持角色身份和场景空间一致。\n\n【场景与角色】\n场景空间：____。\n角色状态：____。\n角色动作：____。\n\n【镜头与光影】\n景别与机位：____。\n运镜方式：____。\n光影氛围：____。\n\n【生成约束】\n优先遵循参考素材中的角色外观、服装材质、空间关系和视觉风格。避免换脸、五官漂移、服装突变、场景跳变、错误文字。""",
            "概念出场": """【镜头功能】\n完成主角出场，并建立诡异、压迫的气氛。\n\n【连续性】\n角色、场景、光影方向和情绪基调保持统一。\n角色参考：[@图片1]\n场景参考：[@图片2]\n\n【镜头设计】\n先建立环境压迫感，再逐步揭示主体。镜头运动缓慢、克制，不突然切换机位。\n\n【场景与光影】\n场景：____。\n光源方向：____。\n阴影形态：____。\n\n【角色与动作】\n角色从：____ 出现。\n角色最终状态：____。\n本镜唯一关键事件：____。\n\n【生成约束】\n不要新增无关角色、地点或重大剧情事件。保持主体身份、服装材质、场景空间和光影关系稳定，避免背景抢戏、换脸、变形和错误文字。"""
        }
        return templates.get(name, templates["镜头生成"])

    def save_current_prompt_as_template(self):
        if not hasattr(self, "video_prompt"):
            return
        content = self.video_prompt.toPlainText().strip()
        if not content:
            QMessageBox.information(self, "没有内容", "当前 Prompt 为空，无法保存为模板。")
            return
        title, ok = QInputDialog.getText(self, "保存自定义模板", "模板名称：")
        if not ok:
            return
        title = title.strip() or content.splitlines()[0][:22]
        data = self.custom_prompt_templates()
        data.append({"title": title, "content": content, "created_at": now_str()})
        save_prompt_library(data)
        self.reload_prompt_template_combo()
        self.prompt_template_combo.setCurrentText("自定义｜" + title)
        self.set_status(f"已保存自定义 Prompt 模板：{title}")

    def delete_selected_custom_template(self):
        if not hasattr(self, "prompt_template_combo"):
            return
        text_label = self.prompt_template_combo.currentText()
        if not text_label.startswith("自定义｜"):
            QMessageBox.information(self, "不是自定义模板", "当前选择的是内置模板，不能删除。")
            return
        title = text_label.replace("自定义｜", "", 1)
        data = [x for x in self.custom_prompt_templates() if x.get("title") != title]
        save_prompt_library(data)
        self.reload_prompt_template_combo()
        self.set_status(f"已删除自定义 Prompt 模板：{title}")

    def insert_selected_prompt_template(self):
        if not hasattr(self, "video_prompt"):
            return
        name = self.selected_prompt_template_name()
        content = self.prompt_template_text(name)
        cursor = self.video_prompt.textCursor()
        if self.video_prompt.toPlainText().strip():
            cursor.insertText("\n\n" + content)
        else:
            cursor.insertText(content)
        self.video_prompt.setTextCursor(cursor)
        self.video_prompt.setFocus()
        self.update_asset_usage()
        self.set_status(f"已插入 Prompt 模板：{name}")

    def replace_with_selected_prompt_template(self):
        if not hasattr(self, "video_prompt"):
            return
        name = self.selected_prompt_template_name()
        self.video_prompt.setPlainText(self.prompt_template_text(name))
        cursor = self.video_prompt.textCursor()
        cursor.movePosition(QTextCursor.Start)
        self.video_prompt.setTextCursor(cursor)
        self.video_prompt.setFocus()
        self.update_asset_usage()
        self.set_status(f"已替换为 Prompt 模板：{name}")

    # ---------- Prompt Studio 功能 ----------

    def normalize_prompt_editor_plain_text(self):
        if not hasattr(self, "video_prompt"):
            return
        raw = self.video_prompt.toPlainText()
        self.video_prompt.clear()
        self.video_prompt.setPlainText(raw)
        cursor = self.video_prompt.textCursor()
        cursor.movePosition(QTextCursor.Start)
        self.video_prompt.setTextCursor(cursor)
        self.video_prompt.setFocus()
        self.update_asset_usage()
        self.set_status("Prompt 已整理为纯文本，可从第一行正常编辑。")

    def current_prompt_plain(self):
        return self.prompt_text_for_api() if hasattr(self, "video_prompt") else ""

    def set_prompt_plain(self, content):
        self.video_prompt.setPlainText(content)
        self.update_asset_usage()

    def on_prompt_style_changed(self, style):
        if style == "结构化":
            self.convert_prompt_to_structured()
        else:
            self.set_status("已切换到自由提示词模式。")

    def convert_prompt_to_structured(self):
        raw = self.current_prompt_plain().strip()
        if not raw:
            raw = "请描述镜头主体、动作、场景、光影、镜头运动与风格。"
        if "【镜头目标】" in raw and "【质量要求】" in raw:
            self.set_status("当前 Prompt 已是结构化格式。")
            return

        mode = self.video_mode.current_text() if hasattr(self, "video_mode") else "普通生成"
        refs = []
        for a in self.assets:
            refs.append(f"{a.tag}：{a.display_name or a.path}")
        refs_text = "\n".join(refs) if refs else "无参考素材"

        structured = (
            f"【生成模式】\n{mode}\n\n"
            f"【镜头目标】\n{raw}\n\n"
            f"【参考素材】\n{refs_text}\n\n"
            "【主体与动作】\n"
            "保持主体身份、姿态、运动方向和动作逻辑稳定；避免面部、肢体和服装突变。\n\n"
            "【场景与空间】\n"
            "保持空间关系、透视关系、前中后景层次和物体位置连续。\n\n"
            "【光影与色彩】\n"
            "保持原始光源方向、阴影关系、曝光、色温与画面风格一致。\n\n"
            "【镜头语言】\n"
            "镜头运动自然，速度均匀，无突然跳切；如需延长或编辑，保持与原片首尾连贯。\n\n"
            "【质量要求】\n"
            "电影感、真实物理光影、细节稳定、无闪烁、无变形、无错误文字。"
        )
        self.set_prompt_plain(structured)
        self.prompt_report.setText("结构化完成：已按生成模式、参考素材、主体、空间、光影、镜头语言整理。")
        self.set_status("已转换为结构化 Prompt。")

    def expand_prompt_with_web_search(self):
        raw = self.current_prompt_plain().strip()
        if not raw:
            QMessageBox.information(self, "缺少提示词", "请先写一段基础提示词，再使用联网扩写。")
            return

        self.web_search_chk.setChecked(True)
        research_block = (
            "\n\n【联网前置调研 / web_search】\n"
            "提交任务时启用 web_search。请在生成前检索提示词中涉及的真实品牌、车型、建筑、服装、地域、历史时期、自然地貌或专业视觉元素，"
            "提取最新且可视化明确的外观细节，再将其转化为强约束视觉描述。"
            "\n要求：只补充有助于画面生成的形态、材质、比例、颜色、结构、光学细节；不要输出网页文字、引用链接或解释性段落。"
        )
        if "【联网前置调研 / web_search】" not in raw:
            self.set_prompt_plain(raw + research_block)
        self.prompt_report.setText(
            "联网扩写已准备：已勾选“生成任务启用 web_search”，并在 Prompt 中加入联网前置调研约束。\n"
            "说明：真正联网发生在提交云端生成任务时；本按钮不直接浏览网页。"
        )
        self.set_status("已启用 web_search 扩写约束。")

    def check_prompt_quality(self):
        raw = self.current_prompt_plain().strip()
        neg = self.video_negative.toPlainText().strip() if hasattr(self, "video_negative") else ""
        issues = []
        suggestions = []

        if not raw:
            issues.append("缺少正向提示词。")
        if len(raw) < 80:
            issues.append("提示词偏短，画面约束不足。")
            suggestions.append("补充主体、动作、场景、镜头、光影、风格与质量要求。")
        if not any(k in raw for k in ["镜头", "运镜", "推近", "拉远", "跟随", "航拍", "固定", "手持", "camera"]):
            issues.append("缺少镜头运动或机位描述。")
        if not any(k in raw for k in ["光", "阴影", "曝光", "色温", "冷暖", "雾", "lighting"]):
            issues.append("缺少光影 / 色彩约束。")
        if not any(k in raw for k in ["保持", "一致", "连续", "稳定", "连贯"]):
            issues.append("缺少连续性约束，视频编辑 / 延长时容易跳变。")
        if self.assets and not any(f"[@{a.tag}]" in raw for a in self.assets):
            issues.append("素材池中有素材，但 Prompt 未引用任何素材。")
        if not neg:
            issues.append("负面提示词为空。")
            suggestions.append("建议加入：闪烁、变形、错误文字、低清、过度锐化、人物崩坏、肢体异常。")
        if self.web_search_chk.isChecked() and "web_search" not in raw and "联网" not in raw:
            suggestions.append("已勾选 web_search，可加入联网前置调研约束，让模型先检索真实视觉细节。")

        score = 100
        score -= min(60, len(issues) * 12)
        score = max(40 if raw else 0, score)

        report = [f"提示词体检评分：{score}/100"]
        if issues:
            report.append("\n发现问题：")
            report.extend([f"- {x}" for x in issues])
        else:
            report.append("\n未发现明显问题。")
        if suggestions:
            report.append("\n优化建议：")
            report.extend([f"- {x}" for x in suggestions])
        report.append("\n当前状态：可继续编辑，或点击“结构化 / 联网扩写”补强。")

        self.prompt_report.setText("\n".join(report))
        self.set_status("提示词体检完成。")

    def check_main_ui_integrity(self):
        checks = [
            ("顶部项目名", hasattr(self, "project_in")),
            ("顶部镜头号", hasattr(self, "shot_in")),
            ("顶部输出目录", hasattr(self, "out_dir_label")),
            ("视频模型", hasattr(self, "video_model")),
            ("生成模式", hasattr(self, "video_mode")),
            ("素材池", hasattr(self, "asset_grid")),
            ("素材拖拽编辑器", hasattr(self, "video_prompt") and hasattr(self.video_prompt, "dropEvent")),
            ("Prompt 编辑器", hasattr(self, "video_prompt")),
            ("结构化切换", hasattr(self, "prompt_style_segment")),
            ("联网扩写按钮逻辑", hasattr(self, "expand_prompt_with_web_search")),
            ("提示词体检按钮逻辑", hasattr(self, "check_prompt_quality")),
            ("负面提示词", hasattr(self, "video_negative")),
            ("费用估算", hasattr(self, "estimated_cost_box")),
            ("项目视频扫描", hasattr(self, "project_video_list")),
            ("画面生成", hasattr(self, "image_prompt")),
            ("云端任务", hasattr(self, "cloud_grid")),
            ("渲染金库", hasattr(self, "vault_list")),
            ("资料库", hasattr(self, "official_doc_list")),
            ("人像库", hasattr(self, "persona_library")),
            ("管线设置入口", hasattr(self, "open_settings")),
            ("任务提交逻辑", hasattr(self, "run_video_task")),
        ]
        missing = [name for name, ok in checks if not ok]
        return missing

    def show_add_virtual_persona_asset_menu(self):
        items = [x for x in self.persona_items("virtual") if x.get("uri")]
        if not items:
            QMessageBox.information(self, "暂无虚拟人像", "请先在人像库导入 asset ID / URI。")
            return
        popup = PersonaDropdown(
            self,
            items,
            "从虚拟人像库导入",
            lambda item: self.add_persona_to_assets(item, insert_prompt=False)
        )
        sender = self.sender()
        if isinstance(sender, QWidget):
            popup.move(sender.mapToGlobal(sender.rect().bottomLeft()))
        else:
            popup.move(QApplication.cursor().pos())
        popup.exec()

    def show_insert_virtual_persona_menu(self):
        items = [x for x in self.persona_items("virtual") if x.get("uri")]
        if not items:
            QMessageBox.information(self, "暂无虚拟人像", "请先在人像库导入 asset ID / URI。")
            return
        popup = PersonaDropdown(
            self,
            items,
            "插入虚拟人像到 Prompt",
            lambda item: self.add_persona_to_assets(item, insert_prompt=True)
        )
        sender = self.sender()
        if isinstance(sender, QWidget):
            popup.move(sender.mapToGlobal(sender.rect().bottomLeft()))
        else:
            popup.move(QApplication.cursor().pos())
        popup.exec()

    def build_video_inspector(self):
        panel = ProPanel("Inspector", "参数、费用与提交")
        self.video_seed = QLineEdit("-1")
        self.video_seed.setPlaceholderText("-1 表示随机")
        self.cost_input = SegmentedControl(["自动", "不含视频", "含视频"], 0)

        panel.body.addWidget(InspectorRow("Seed", self.video_seed))
        panel.body.addWidget(InspectorRow("计费输入类型", self.cost_input))

        path_hint = QLabel("路径在顶部统一管理：输出根目录 / 项目名称 / 镜头号 会自动组合成当前镜头路径。")
        path_hint.setWordWrap(True)
        path_hint.setStyleSheet(f"""
        QLabel {{
            background: {Theme.SURFACE_2};
            border: 1px solid {Theme.BORDER};
            border-radius: 12px;
            padding: 10px;
            color: {Theme.MUTED};
            line-height: 1.4;
        }}
        """)
        panel.body.addWidget(path_hint)

        self.estimated_cost_box = QTextEdit()
        self.estimated_cost_box.setReadOnly(True)
        self.estimated_cost_box.setFixedHeight(115)
        self.estimated_cost_box.setText("费用估算会在任务完成并返回 usage 后显示。")
        panel.body.addWidget(self.estimated_cost_box)

        panel.body.addStretch()
        submit = GlowButton("提交镜头生成", primary=True)
        submit.clicked.connect(self.run_video_task)
        panel.body.addWidget(submit)
        stop = GlowButton("停止任务", danger=True)
        stop.clicked.connect(self.cancel_current_task)
        panel.body.addWidget(stop)
        return panel

    # ---------- 画面生成页 ----------

    def build_image_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(12)

        controls = ProPanel("画面规格", "生图模型、比例、清晰度")
        row = QHBoxLayout()
        self.image_model = QComboBox()
        self.image_model.addItems([p.get("name") for p in self.profiles.get("image", [])])
        self.image_model.setCurrentText(default_profile(self.profiles, "image").get("name", ""))
        self.image_res = QComboBox(); self.image_res.addItems(["1k", "2k", "4k"]); self.image_res.setCurrentText("2k")
        self.image_ratio = QComboBox(); self.image_ratio.addItems(["16:9", "9:16", "4:3", "3:4", "1:1", "21:9"])
        self.image_seed = QLineEdit("-1")
        row.addWidget(InspectorRow("生图模型", self.image_model))
        row.addWidget(InspectorRow("清晰度", self.image_res))
        row.addWidget(InspectorRow("比例", self.image_ratio))
        row.addWidget(InspectorRow("Seed", self.image_seed))
        controls.body.addLayout(row)
        outer.addWidget(controls)

        split = QSplitter(Qt.Horizontal)
        split.addWidget(self.build_image_ref_pool())
        split.addWidget(self.build_image_prompt_panel())
        split.setSizes([340, 900])
        outer.addWidget(split, 1)
        return page

    def build_image_ref_pool(self):
        panel = ProPanel("参考图", "角色 / 场景 / 风格图")
        row = QHBoxLayout()
        b1 = GlowButton("导入本地")
        b1.clicked.connect(lambda: self.import_local_assets(image_only=True))
        b2 = GlowButton("图片 URL")
        b2.clicked.connect(lambda: self.import_url_asset(image_only=True))
        row.addWidget(b1)
        row.addWidget(b2)
        row.addStretch()
        panel.body.addLayout(row)
        self.image_asset_list = QListWidget()
        self.image_asset_list.itemClicked.connect(self.show_image_asset_detail)
        panel.body.addWidget(self.image_asset_list, 1)
        self.image_asset_detail = QTextEdit()
        self.image_asset_detail.setReadOnly(True)
        self.image_asset_detail.setFixedHeight(100)
        panel.body.addWidget(self.image_asset_detail)
        return panel

    def build_image_prompt_panel(self):
        panel = ProPanel("Image Prompt Studio", "画面提示词与负面约束")
        self.image_prompt = QTextEdit()
        self.image_prompt.setPlaceholderText("输入生图提示词。引用参考图用 [@图片1]。")
        self.image_prompt.setMinimumHeight(340)
        self.image_prompt.setStyleSheet("font-size:16px; padding:16px;")
        panel.body.addWidget(self.image_prompt)
        self.image_negative = QTextEdit()
        self.image_negative.setFixedHeight(110)
        self.image_negative.setPlaceholderText("负面提示词...")
        panel.body.addWidget(self.image_negative)
        submit = GlowButton("提交生图生成", primary=True)
        submit.clicked.connect(self.run_image_task)
        panel.body.addWidget(submit)
        return panel

    # ---------- 云端任务 ----------

    def build_cloud_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(12)

        top = ProPanel("云端任务", "查询、扫描、费用补全与下载")
        row = QHBoxLayout()
        self.query_task_id = QLineEdit()
        self.query_task_id.setPlaceholderText("粘贴 Task ID")
        row.addWidget(self.query_task_id, 1)
        qbtn = GlowButton("查询任务")
        qbtn.clicked.connect(self.query_cloud_task)
        row.addWidget(qbtn)
        sbtn = GlowButton("扫描已完成")
        sbtn.clicked.connect(self.scan_cloud_tasks)
        row.addWidget(sbtn)
        top.body.addLayout(row)
        slider_row, self.cloud_thumb_slider = self.make_thumb_slider_row("云端缩略图大小", 80, 220, 112, lambda _v: self.refresh_cloud_grid())
        top.body.addLayout(slider_row)
        outer.addWidget(top)

        split = QSplitter(Qt.Horizontal)
        task_panel = ProPanel("Task Grid", "云端已完成任务")
        self.cloud_scroll = QScrollArea()
        self.cloud_scroll.setWidgetResizable(True)
        self.cloud_host = QWidget()
        self.cloud_grid = QVBoxLayout(self.cloud_host)
        self.cloud_grid.setContentsMargins(2, 2, 8, 2)
        self.cloud_grid.setSpacing(10)
        self.cloud_scroll.setWidget(self.cloud_host)
        task_panel.body.addWidget(self.cloud_scroll)
        split.addWidget(task_panel)

        ins = ProPanel("Task Inspector", "状态、URL、计费与原始 JSON")
        self.cloud_thumb = QLabel("NO PREVIEW")
        self.cloud_thumb.setAlignment(Qt.AlignCenter)
        self.cloud_thumb.setFixedHeight(170)
        self.cloud_thumb.setStyleSheet("background:#09111D; border:1px solid rgba(126,150,190,0.22); border-radius:14px; color:#91A4C7; font-weight:800;")
        ins.body.addWidget(self.cloud_thumb)
        self.cloud_status = QTextEdit(); self.cloud_status.setReadOnly(True); self.cloud_status.setFixedHeight(120)
        ins.body.addWidget(self.cloud_status)
        mode_row = QHBoxLayout()
        mode_row.addWidget(ui_label("计费类型", 11, True, True))
        self.cloud_cost_mode = SegmentedControl(["自动", "不含视频", "含视频"], 0)
        self.cloud_cost_mode.changed.connect(lambda _: self.save_cloud_override_quick())
        mode_row.addWidget(self.cloud_cost_mode, 1)
        ins.body.addLayout(mode_row)
        note_row = QHBoxLayout()
        self.cloud_note = QLineEdit()
        self.cloud_note.setPlaceholderText("任务备注，例如：视频延长，使用了视频输入 + 音频")
        note_row.addWidget(self.cloud_note, 1)
        save_note = GlowButton("保存备注")
        save_note.clicked.connect(self.save_cloud_note)
        note_row.addWidget(save_note)
        ins.body.addLayout(note_row)
        btn_row = QHBoxLayout()
        copy_url = GlowButton("复制 URL")
        copy_url.clicked.connect(lambda: QApplication.clipboard().setText(self.current_cloud_task.get("url", "") if self.current_cloud_task else ""))
        download = GlowButton("下载结果")
        download.clicked.connect(self.download_cloud_result)
        btn_row.addWidget(copy_url)
        btn_row.addWidget(download)
        ins.body.addLayout(btn_row)
        self.cloud_raw = QTextEdit(); self.cloud_raw.setReadOnly(True)
        ins.body.addWidget(self.cloud_raw, 1)
        split.addWidget(ins)
        split.setSizes([740, 520])
        outer.addWidget(split, 1)
        return page

    # ---------- 渲染金库 ----------

    def build_vault_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(12)

        header = ProPanel("渲染金库", "本地结果、元数据、复刻与发送到工作台")
        row = QHBoxLayout()
        self.vault_search = QLineEdit()
        self.vault_search.setPlaceholderText("搜索项目 / 镜头 / Task ID / 文件名")
        self.vault_search.textChanged.connect(self.refresh_vault)
        self.vault_filter = QComboBox()
        self.vault_filter.addItems(["全部", "视频", "图片", "今天", "有元数据", "可复刻"])
        self.vault_filter.currentTextChanged.connect(self.refresh_vault)
        refresh = GlowButton("刷新")
        refresh.clicked.connect(self.refresh_vault)
        row.addWidget(self.vault_filter)
        row.addWidget(self.vault_search, 1)
        row.addWidget(refresh)
        header.body.addLayout(row)
        slider_row, self.vault_thumb_slider = self.make_thumb_slider_row("缩略图大小", 64, 180, 88, lambda _v: self.refresh_vault())
        header.body.addLayout(slider_row)
        outer.addWidget(header)

        split = QSplitter(Qt.Horizontal)
        self.vault_panel = ProPanel("Result Grid", "生成结果")
        self.vault_scroll = QScrollArea(); self.vault_scroll.setWidgetResizable(True)
        self.vault_host = QWidget()
        self.vault_list = QVBoxLayout(self.vault_host)
        self.vault_list.setContentsMargins(2, 2, 8, 2)
        self.vault_list.setSpacing(10)
        self.vault_scroll.setWidget(self.vault_host)
        self.vault_panel.body.addWidget(self.vault_scroll)
        split.addWidget(self.vault_panel)

        meta_panel = ProPanel("Metadata Inspector", "Prompt、Seed、费用与复刻")
        self.vault_meta = QTextEdit(); self.vault_meta.setReadOnly(True)
        meta_panel.body.addWidget(self.vault_meta, 1)
        open_btn = GlowButton("打开文件")
        open_btn.clicked.connect(lambda: safe_open_path(getattr(self, "current_vault_path", "")))
        folder_btn = GlowButton("打开文件夹")
        folder_btn.clicked.connect(lambda: safe_open_path(os.path.dirname(getattr(self, "current_vault_path", ""))))
        rep_btn = GlowButton("完整复刻到工作台")
        rep_btn.clicked.connect(self.replicate_current_vault)
        meta_panel.body.addWidget(open_btn)
        meta_panel.body.addWidget(folder_btn)
        meta_panel.body.addWidget(rep_btn)
        split.addWidget(meta_panel)
        split.setSizes([760, 440])
        outer.addWidget(split, 1)
        return page

    # ---------- 资料库 ----------

    def open_browser_url(self, url):
        QDesktopServices.openUrl(QUrl(url))

    def build_persona_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self.build_virtual_persona_tab(), "虚拟人像库")
        tabs.addTab(self.build_real_persona_tab(), "真人授权追踪")
        tabs.addTab(self.build_persona_guide_tab(), "官方流程说明")
        outer.addWidget(tabs, 1)
        return page

    def build_virtual_persona_tab(self):
        page = QWidget()
        root = QHBoxLayout(page)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(12)

        left = ProPanel("虚拟人像入库", "主流程：复制 / 批量导入 Asset ID，然后直接用于生成")

        top_links = QHBoxLayout()
        exp_btn_big = GlowButton("打开我的方舟体验中心", primary=True)
        exp_btn_big.clicked.connect(lambda: self.open_browser_url("https://console.volcengine.com/ark/region:ark+cn-beijing/experience/vision?modelId=doubao-seedance-2-0-260128&tab=GenVideo"))
        doc_btn_big = GlowButton("打开虚拟人像库说明")
        doc_btn_big.clicked.connect(lambda: self.open_browser_url("https://www.volcengine.com/docs/82379/2223965"))
        top_links.addWidget(exp_btn_big)
        top_links.addWidget(doc_btn_big)
        left.body.addLayout(top_links)

        self.virtual_persona_name = QLineEdit()
        self.virtual_persona_name.setPlaceholderText("人像名称，例如：阳光男大学生")
        self.virtual_persona_asset = QLineEdit()
        self.virtual_persona_asset.setPlaceholderText("asset-xxxx 或 asset://asset-xxxx")
        self.virtual_persona_desc = QTextEdit()
        self.virtual_persona_desc.setPlaceholderText("标签 / 小传 / 外形描述，例如：青年男性，180cm，阳光，运动感")
        self.virtual_persona_desc.setFixedHeight(92)
        self.virtual_persona_preview = QLineEdit()
        self.virtual_persona_preview.setPlaceholderText("可选：本地预览图路径或公网图片 URL")
        pick_preview = GlowButton("选择预览图")
        pick_preview.clicked.connect(lambda: self.pick_persona_preview(self.virtual_persona_preview))
        paste_preview = GlowButton("粘贴预览")
        paste_preview.clicked.connect(self.paste_preview_to_virtual_form)

        self.virtual_persona_preview.setVisible(False)
        self.virtual_persona_preview_label = QLabel("粘贴截图\n作为人像预览")
        self.virtual_persona_preview_label.setAlignment(Qt.AlignCenter)
        self.virtual_persona_preview_label.setFixedHeight(210)
        self.virtual_persona_preview_label.setStyleSheet(f"""
        QLabel {{
            background: #09111D;
            border: 1px solid {Theme.BORDER};
            border-radius: 16px;
            color: {Theme.MUTED};
            font-weight: 800;
            line-height: 1.6;
        }}
        """)
        left.body.addWidget(self.virtual_persona_preview_label)

        preview_actions = QHBoxLayout()
        preview_actions.addWidget(paste_preview)
        preview_actions.addWidget(pick_preview)
        url_preview_form = GlowButton("图片URL")
        url_preview_form.clicked.connect(self.set_virtual_form_preview_from_url)
        preview_actions.addWidget(url_preview_form)
        left.body.addLayout(preview_actions)

        left.body.addWidget(InspectorRow("名称", self.virtual_persona_name))
        left.body.addWidget(InspectorRow("Asset URI", self.virtual_persona_asset))
        left.body.addWidget(InspectorRow("描述 / 标签 / 小传", self.virtual_persona_desc))

        save_btn = GlowButton("保存虚拟人像", primary=True)
        save_btn.clicked.connect(lambda: self.save_persona_item("virtual"))
        left.body.addWidget(save_btn)

        batch_box = QTextEdit()
        batch_box.setPlaceholderText(
            "批量导入：从体验中心复制多个 asset ID / asset:// URI / 示例 JSON 粘贴到这里。\n"
            "软件会自动识别 asset-xxxx 与 asset://asset-xxxx。"
        )
        batch_box.setFixedHeight(58)
        self.virtual_persona_batch = batch_box
        left.body.addWidget(InspectorRow("批量识别 ID", batch_box))

        batch_btns = QHBoxLayout()
        scan_clip = GlowButton("扫描剪贴板")
        scan_clip.clicked.connect(self.scan_clipboard_virtual_assets)
        import_batch = GlowButton("批量导入", primary=True)
        import_batch.clicked.connect(self.import_virtual_assets_batch)
        batch_btns.addWidget(scan_clip)
        batch_btns.addWidget(import_batch)
        left.body.addLayout(batch_btns)

        guide = QLabel(
            "软件内部操作指南：\n"
            "1. 顶部按钮会打开你的方舟体验中心 Seedance 2.0 视频生成页。\n"
            "2. 在 Seedance 2.0 页面点击“虚拟人像库”，复制 asset ID / URI。\n"
            "3. 复制官网人像截图，点“粘贴预览”。\n"
            "4. 填写名称、Asset URI、描述后保存。\n"
            "5. 回到镜头生成，在素材池点击“虚拟人像库”导入。"
        )
        guide.setWordWrap(True)
        guide.setStyleSheet(f"""
        QLabel {{
            background: rgba(255,255,255,0.035);
            border: 1px solid {Theme.BORDER};
            border-radius: 12px;
            padding: 10px;
            color: {Theme.MUTED};
            line-height: 1.5;
        }}
        """)
        left.body.addWidget(guide)

        left.body.addStretch()
        root.addWidget(left, 1)

        right = self.build_persona_list_panel("virtual")
        root.addWidget(right, 2)
        return page

    def build_real_persona_tab(self):
        page = QWidget()
        root = QHBoxLayout(page)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(12)

        left = ProPanel("真人授权追踪", "临时保留：记录资产组与二维码，不做复杂入库设计")
        self.real_group_name = QLineEdit()
        self.real_group_name.setPlaceholderText("资产组名称 / 艺人名称，例如：演员A_古装造型")
        self.real_group_status = QComboBox()
        self.real_group_status.addItems(["二维码已生成", "等待艺人认证", "艺人已上传", "等待接收", "已接收可用", "一致性失败", "已拒绝"])
        self.real_group_qr = QLineEdit()
        self.real_group_qr.setPlaceholderText("二维码截图路径，可选")
        pick_qr = GlowButton("选择二维码")
        pick_qr.clicked.connect(lambda: self.pick_persona_preview(self.real_group_qr))
        self.real_group_note = QTextEdit()
        self.real_group_note.setPlaceholderText("备注：授权有效期、艺人联系方式、妆造说明、接收状态等")
        self.real_group_note.setFixedHeight(110)

        left.body.addWidget(InspectorRow("资产组", self.real_group_name))
        left.body.addWidget(InspectorRow("状态", self.real_group_status))
        qr_row = QWidget()
        qr_lay = QHBoxLayout(qr_row)
        qr_lay.setContentsMargins(0, 0, 0, 0)
        qr_lay.setSpacing(6)
        qr_lay.addWidget(self.real_group_qr, 1)
        qr_lay.addWidget(pick_qr)
        left.body.addWidget(InspectorRow("二维码截图", qr_row))
        left.body.addWidget(InspectorRow("备注", self.real_group_note))

        save_group = GlowButton("保存资产组状态", primary=True)
        save_group.clicked.connect(self.save_real_asset_group)
        left.body.addWidget(save_group)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"color:{Theme.BORDER};")
        left.body.addWidget(line)

        left.body.addWidget(ui_label("已接收后登记可用 Asset URI", 12, True))
        self.real_persona_name = QLineEdit()
        self.real_persona_name.setPlaceholderText("可用人像名称")
        self.real_persona_asset = QLineEdit()
        self.real_persona_asset.setPlaceholderText("已接收的人像素材 asset://asset-xxxx")
        self.real_persona_status = QComboBox()
        self.real_persona_status.addItems(["已接收可用", "待接收", "已拒绝", "一致性待确认"])
        self.real_persona_auth = QLineEdit()
        self.real_persona_auth.setPlaceholderText("授权备注")
        self.real_persona_desc = QTextEdit()
        self.real_persona_desc.setPlaceholderText("妆造、服装、表演方向说明")
        self.real_persona_desc.setFixedHeight(72)
        self.real_persona_preview = QLineEdit()
        self.real_persona_preview.setPlaceholderText("可选预览图路径")
        pick_preview = GlowButton("选择预览图")
        pick_preview.clicked.connect(lambda: self.pick_persona_preview(self.real_persona_preview))

        left.body.addWidget(InspectorRow("名称", self.real_persona_name))
        left.body.addWidget(InspectorRow("Asset URI", self.real_persona_asset))
        left.body.addWidget(InspectorRow("授权状态", self.real_persona_status))
        left.body.addWidget(InspectorRow("授权备注", self.real_persona_auth))
        left.body.addWidget(InspectorRow("描述", self.real_persona_desc))
        preview_row = QWidget()
        preview_lay = QHBoxLayout(preview_row)
        preview_lay.setContentsMargins(0, 0, 0, 0)
        preview_lay.setSpacing(6)
        preview_lay.addWidget(self.real_persona_preview, 1)
        preview_lay.addWidget(pick_preview)
        left.body.addWidget(InspectorRow("预览图", preview_row))
        save_btn = GlowButton("保存可用真人资产", primary=True)
        save_btn.clicked.connect(lambda: self.save_persona_item("real"))
        left.body.addWidget(save_btn)

        root.addWidget(left, 1)

        right_panel = ProPanel("真人资产组与可用资产", "资产组只做状态记录；真正生成仍使用已接收的 asset://")
        self.real_group_list = QTextEdit()
        self.real_group_list.setReadOnly(True)
        self.real_group_list.setFixedHeight(180)
        right_panel.body.addWidget(self.real_group_list)

        right_panel.body.addWidget(ui_label("已登记可用真人资产", 12, True))
        real_list = self.build_persona_list_panel("real")
        right_panel.body.addWidget(real_list, 1)
        QTimer.singleShot(200, self.refresh_real_group_list)
        root.addWidget(right_panel, 2)
        return page

    def parse_asset_uris_from_text(self, raw):
        raw = raw or ""
        found = []
        for m in re.findall(r"asset://asset-[A-Za-z0-9_-]+", raw):
            found.append(normalize_asset_uri(m))
        for m in re.findall(r"\basset-[A-Za-z0-9_-]+\b", raw):
            found.append(normalize_asset_uri(m))
        seen = set()
        result = []
        for u in found:
            if u not in seen:
                seen.add(u)
                result.append(u)
        return result

    def scan_clipboard_virtual_assets(self):
        txt = QApplication.clipboard().text()
        self.virtual_persona_batch.setText(txt)
        uris = self.parse_asset_uris_from_text(txt)
        self.set_status(f"剪贴板中识别到 {len(uris)} 个 Asset URI。")

    def import_virtual_assets_batch(self):
        raw = self.virtual_persona_batch.toPlainText()
        uris = self.parse_asset_uris_from_text(raw)
        if not uris:
            QMessageBox.information(self, "未识别到资产", "没有识别到 asset-xxxx 或 asset://asset-xxxx。")
            return

        data = load_persona_library()
        data.setdefault("items", [])
        added = 0
        for uri in uris:
            if any(x.get("uri") == uri for x in data["items"]):
                continue
            idx = len([x for x in data["items"] if x.get("type") == "virtual"]) + 1
            data["items"].append({
                "id": f"virtual_{int(time.time()*1000)}_{idx}",
                "type": "virtual",
                "name": f"虚拟人像 {idx}",
                "uri": uri,
                "desc": "批量导入的虚拟人像资产。",
                "preview": "",
                "status": "可用",
                "auth": "",
                "created_at": now_str()
            })
            added += 1
        save_persona_library(data)
        self.persona_library = data
        self.refresh_persona_list("virtual")
        self.set_status(f"已批量导入 {added} 个虚拟人像。")

    def save_real_asset_group(self):
        name = self.real_group_name.text().strip()
        if not name:
            QMessageBox.warning(self, "缺少资产组名称", "请填写资产组名称或艺人名称。")
            return
        data = load_persona_library()
        data.setdefault("items", [])
        item = {
            "id": f"real_group_{int(time.time()*1000)}",
            "type": "real_group",
            "name": name,
            "status": self.real_group_status.currentText(),
            "qr": self.real_group_qr.text().strip(),
            "note": self.real_group_note.toPlainText().strip(),
            "updated_at": now_str()
        }
        old = next((x for x in data["items"] if x.get("type") == "real_group" and x.get("name") == name), None)
        if old:
            old.update(item)
        else:
            data["items"].append(item)
        save_persona_library(data)
        self.persona_library = data
        self.refresh_real_group_list()
        self.set_status(f"已保存真人资产组状态：{name}")

    def refresh_real_group_list(self):
        if not hasattr(self, "real_group_list"):
            return
        groups = [x for x in load_persona_library().get("items", []) if x.get("type") == "real_group"]
        if not groups:
            self.real_group_list.setText("暂无真人资产组记录。你已经创建了资产组和二维码，可以先在左侧记录。")
            return
        lines = []
        for g in groups:
            lines.append(
                f"资产组：{g.get('name','')}\n"
                f"状态：{g.get('status','')}\n"
                f"二维码：{g.get('qr','') or '未记录'}\n"
                f"备注：{g.get('note','')}\n"
                f"更新时间：{g.get('updated_at','')}\n"
                "------------------------------"
            )
        self.real_group_list.setText("\n".join(lines))

    def build_persona_guide_tab(self):
        page = QWidget()
        root = QHBoxLayout(page)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(12)

        virtual = ProPanel("虚拟人像使用", "根据官方文档落地到软件")
        link_row = QHBoxLayout()
        exp_btn = GlowButton("打开我的方舟体验中心")
        exp_btn.clicked.connect(lambda: self.open_browser_url("https://console.volcengine.com/ark/region:ark+cn-beijing/experience/vision?modelId=doubao-seedance-2-0-260128&tab=GenVideo"))
        doc_btn = GlowButton("打开虚拟人像库说明")
        doc_btn.clicked.connect(lambda: self.open_browser_url("https://www.volcengine.com/docs/82379/2223965"))
        link_row.addWidget(exp_btn)
        link_row.addWidget(doc_btn)
        link_row.addStretch()
        virtual.body.addLayout(link_row)

        vtxt = QTextEdit()
        vtxt.setReadOnly(True)
        vtxt.setText(
            "1. 打开我的方舟体验中心的 Seedance 2.0 视频生成界面。\n"
            "2. 在输入框下方点击“虚拟人像库”页签。\n"
            "3. 在虚拟人像库中检索人像，可按自然语言、性别、年龄、国籍等条件筛选。\n"
            "4. 查看详情，复制 Asset ID 或 URI。\n"
            "5. 回到本软件的人像库登记 asset://asset_id。\n"
            "6. 点击“加入素材池”或“插入 Prompt”，生成时会作为 reference_image 传入。\n\n"
            "说明：官方文档指出每个虚拟人对应一个资产 ID，API 中可使用 asset://asset_id 的 URI 传入模型。"
        )
        virtual.body.addWidget(vtxt)
        root.addWidget(virtual)

        real = ProPanel("真人人像录入", "合规录入流程提醒")
        rtxt = QTextEdit()
        rtxt.setReadOnly(True)
        rtxt.setText(
            "1. 使用方在方舟体验中心：我的 > 真人人像 > 管理素材 > 创建资产组。\n"
            "2. 设置授权有效期并生成邀约二维码。\n"
            "3. 授权人扫码登录火山账号，完成真人认证、上传素材并授权。\n"
            "4. 使用方在真人人像库中接收授权素材。\n"
            "5. 复制已接收可用素材的 Asset ID / URI，登记到本软件。\n\n"
            "素材要求摘要：图片小于 30MB；视频 mp4/mov 且不超过 50MB，时长 2-15 秒；音频 mp3/wav 且小于 15MB。"
            "\n注意：真人认证和一致性校验可能因光线、角度、侧脸、多人等原因失败。"
        )
        real.body.addWidget(rtxt)
        root.addWidget(real)
        return page

    def build_persona_list_panel(self, persona_type):
        title = "虚拟人像预览库" if persona_type == "virtual" else "已登记人像"
        subtitle = "主要显示人像信息；预览图在左侧入库区补录" if persona_type == "virtual" else "可加入素材池或插入 Prompt 使用"
        panel = ProPanel(title, subtitle)
        row = QHBoxLayout()
        search = QLineEdit()
        search.setPlaceholderText("搜索名称 / Asset ID / 描述")
        search.textChanged.connect(lambda: self.refresh_persona_list(persona_type))
        if persona_type == "virtual":
            self.virtual_persona_search = search
        else:
            self.real_persona_search = search
        row.addWidget(search, 1)
        refresh = GlowButton("刷新")
        refresh.clicked.connect(lambda: self.refresh_persona_list(persona_type))
        row.addWidget(refresh)
        panel.body.addLayout(row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        lay = QVBoxLayout(host)
        lay.setContentsMargins(2, 2, 8, 2)
        lay.setSpacing(10)
        scroll.setWidget(host)
        panel.body.addWidget(scroll, 1)

        detail = QTextEdit()
        detail.setReadOnly(True)
        detail.setFixedHeight(150 if persona_type == "virtual" else 135)
        detail.setPlaceholderText("选中人像后显示详情。")
        panel.body.addWidget(detail)

        if persona_type == "virtual":
            usage = QLabel(
                "固定使用方式：先在左侧粘贴截图保存预览，再保存 Asset URI。\n"
                "镜头生成页可从“素材池 > 虚拟人像库”导入；Prompt Studio 可直接插入虚拟人像。"
            )
            usage.setWordWrap(True)
            usage.setStyleSheet(f"""
            QLabel {{
                background: rgba(255,255,255,0.035);
                border: 1px solid {Theme.BORDER};
                border-radius: 12px;
                padding: 10px;
                color: {Theme.MUTED};
                line-height: 1.5;
            }}
            """)
            panel.body.addWidget(usage)

        actions = QHBoxLayout()
        add_btn = GlowButton("加入素材池", primary=True)
        insert_btn = GlowButton("插入 Prompt")
        copy_btn = GlowButton("复制 URI")
        set_preview_btn = GlowButton("设置预览图")
        paste_preview_btn = GlowButton("粘贴预览")
        url_preview_btn = GlowButton("图片URL")
        del_btn = GlowButton("删除", danger=True)
        actions.addWidget(add_btn)
        actions.addWidget(insert_btn)
        actions.addWidget(copy_btn)
        actions.addWidget(set_preview_btn)
        actions.addWidget(paste_preview_btn)
        actions.addWidget(url_preview_btn)
        actions.addWidget(del_btn)
        panel.body.addLayout(actions)

        if persona_type == "virtual":
            self.virtual_persona_list = lay
            self.virtual_persona_detail = detail
            self.virtual_persona_add_btn = add_btn
            self.virtual_persona_insert_btn = insert_btn
            self.virtual_persona_copy_btn = copy_btn
            self.virtual_persona_set_preview_btn = set_preview_btn
            self.virtual_persona_paste_preview_btn = paste_preview_btn
            self.virtual_persona_url_preview_btn = url_preview_btn
            self.virtual_persona_del_btn = del_btn
            paste_preview_btn.setVisible(True)
            QTimer.singleShot(150, lambda: self.refresh_persona_list("virtual"))
        else:
            self.real_persona_list = lay
            self.real_persona_detail = detail
            self.real_persona_add_btn = add_btn
            self.real_persona_insert_btn = insert_btn
            self.real_persona_copy_btn = copy_btn
            self.real_persona_set_preview_btn = set_preview_btn
            self.real_persona_paste_preview_btn = paste_preview_btn
            self.real_persona_url_preview_btn = url_preview_btn
            self.real_persona_del_btn = del_btn
            set_preview_btn.setVisible(False)
            paste_preview_btn.setVisible(False)
            url_preview_btn.setVisible(False)
            QTimer.singleShot(150, lambda: self.refresh_persona_list("real"))
        return panel

    def set_virtual_form_preview_value(self, preview):
        self.virtual_persona_preview.setText(preview or "")
        if not hasattr(self, "virtual_persona_preview_label"):
            return
        if preview and os.path.isfile(str(preview)):
            pix = QPixmap(str(preview))
            if not pix.isNull():
                self.virtual_persona_preview_label.setPixmap(
                    pix.scaled(self.virtual_persona_preview_label.width(), self.virtual_persona_preview_label.height(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                )
                return
        if preview and str(preview).startswith(("http://", "https://")):
            self.virtual_persona_preview_label.setPixmap(remote_pixmap(preview, 280, 190, "image"))
            return
        self.virtual_persona_preview_label.setText("粘贴截图\n作为人像预览")
        self.virtual_persona_preview_label.setPixmap(QPixmap())

    def pick_persona_preview(self, target_lineedit):
        fp, _ = QFileDialog.getOpenFileName(self, "选择人像预览图", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if fp:
            target_lineedit.setText(fp)
            if target_lineedit is getattr(self, "virtual_persona_preview", None):
                self.set_virtual_form_preview_value(fp)

    def paste_preview_to_virtual_form(self):
        cb = QApplication.clipboard()
        pix = cb.pixmap()
        if pix.isNull():
            img = cb.image()
            if img.isNull():
                QMessageBox.information(self, "剪贴板无图片", "请先复制一张截图或图片。")
                return
            pix = QPixmap.fromImage(img)
        uri = normalize_asset_uri(self.virtual_persona_asset.text().strip())
        key = safe_persona_preview_name(uri or f"virtual_preview_{int(time.time())}")
        dst = os.path.join(persona_preview_dir(), key + ".png")
        if pix.save(dst, "PNG"):
            self.set_virtual_form_preview_value(dst)
            self.set_status("已从剪贴板粘贴虚拟人像预览图。")
        else:
            QMessageBox.warning(self, "预览图保存失败", "无法保存剪贴板图片。")

    def set_virtual_form_preview_from_url(self):
        url, ok = QInputDialog.getText(self, "输入预览图 URL", "图片 URL：")
        if not ok:
            return
        url = url.strip()
        if not url:
            return
        if not url.startswith(("http://", "https://")):
            QMessageBox.warning(self, "URL 格式不正确", "请输入 http:// 或 https:// 开头的图片地址。")
            return
        self.set_virtual_form_preview_value(url)

    def save_persona_item(self, persona_type):
        if persona_type == "virtual":
            name = self.virtual_persona_name.text().strip()
            uri = normalize_asset_uri(self.virtual_persona_asset.text())
            desc = self.virtual_persona_desc.toPlainText().strip()
            preview = self.virtual_persona_preview.text().strip()
            status = "可用"
            auth = ""
        else:
            name = self.real_persona_name.text().strip()
            uri = normalize_asset_uri(self.real_persona_asset.text())
            desc = self.real_persona_desc.toPlainText().strip()
            preview = self.real_persona_preview.text().strip()
            status = self.real_persona_status.currentText()
            auth = self.real_persona_auth.text().strip()

        if not name or not uri:
            QMessageBox.warning(self, "缺少信息", "请至少填写名称和 Asset ID / URI。")
            return
        if not uri.startswith("asset://"):
            QMessageBox.warning(self, "Asset URI 格式不正确", "请填写 asset-xxxx 或 asset://asset-xxxx。")
            return

        item = {
            "id": f"{persona_type}_{int(time.time()*1000)}",
            "type": persona_type,
            "name": name,
            "uri": uri,
            "desc": desc,
            "preview": preview,
            "status": status,
            "auth": auth,
            "created_at": now_str()
        }
        data = load_persona_library()
        data.setdefault("items", [])
        old = next((x for x in data["items"] if x.get("uri") == uri), None)
        if old:
            old.update(item)
        else:
            data["items"].append(item)
        save_persona_library(data)
        self.persona_library = data
        self.refresh_persona_list(persona_type)
        self.set_status(f"已保存人像：{name}")

    def persona_items(self, persona_type=None):
        items = load_persona_library().get("items", [])
        if persona_type:
            items = [x for x in items if x.get("type") == persona_type]
        return items

    def refresh_persona_list(self, persona_type):
        lay = self.virtual_persona_list if persona_type == "virtual" else self.real_persona_list
        detail = self.virtual_persona_detail if persona_type == "virtual" else self.real_persona_detail
        search = self.virtual_persona_search if persona_type == "virtual" else self.real_persona_search

        self.clear_layout(lay)
        q = search.text().strip().lower()
        for item in self.persona_items(persona_type):
            hay = f"{item.get('name','')} {item.get('uri','')} {item.get('desc','')} {item.get('status','')}".lower()
            if q and q not in hay:
                continue
            card = ResultCardLike(
                item.get("name", "未命名人像"),
                f"{item.get('status','')}｜{item.get('uri','')}",
                item.get("preview", ""),
                item.get("preview", "") or item.get("uri", ""),
                104
            )
            card.clicked.connect(lambda it=item, typ=persona_type: self.select_persona(it, typ))
            lay.addWidget(card)
        lay.addStretch(1)
        detail.setText("请选择一个人像资产。")

    def safe_disconnect_button(self, btn):
        try:
            btn.clicked.disconnect()
        except Exception:
            pass

    def select_persona(self, item, persona_type):
        self.current_persona = item
        detail = self.virtual_persona_detail if persona_type == "virtual" else self.real_persona_detail
        preview = item.get("preview", "")
        preview_line = preview if preview else "未设置预览图，可点击“设置预览图 / 粘贴预览 / 图片URL”。"
        if persona_type == "virtual":
            detail.setText(
                f"名称：{item.get('name','')}\n"
                f"Asset URI：{item.get('uri','')}\n"
                f"状态：{item.get('status','')}\n"
                f"预览图：{preview_line}\n"
                f"描述 / 标签 / 小传：\n{item.get('desc','')}"
            )
        else:
            detail.setText(
                f"名称：{item.get('name','')}\n"
                f"类型：真人人像\n"
                f"状态：{item.get('status','')}\n"
                f"Asset URI：{item.get('uri','')}\n"
                f"预览图：{preview_line}\n"
                f"授权备注：{item.get('auth','')}\n"
                f"描述：{item.get('desc','')}"
            )

        add_btn = self.virtual_persona_add_btn if persona_type == "virtual" else self.real_persona_add_btn
        insert_btn = self.virtual_persona_insert_btn if persona_type == "virtual" else self.real_persona_insert_btn
        copy_btn = self.virtual_persona_copy_btn if persona_type == "virtual" else self.real_persona_copy_btn
        set_preview_btn = self.virtual_persona_set_preview_btn if persona_type == "virtual" else self.real_persona_set_preview_btn
        paste_preview_btn = self.virtual_persona_paste_preview_btn if persona_type == "virtual" else self.real_persona_paste_preview_btn
        url_preview_btn = self.virtual_persona_url_preview_btn if persona_type == "virtual" else self.real_persona_url_preview_btn
        del_btn = self.virtual_persona_del_btn if persona_type == "virtual" else self.real_persona_del_btn

        self.safe_disconnect_button(add_btn)
        self.safe_disconnect_button(insert_btn)
        self.safe_disconnect_button(copy_btn)
        self.safe_disconnect_button(set_preview_btn)
        self.safe_disconnect_button(paste_preview_btn)
        self.safe_disconnect_button(url_preview_btn)
        self.safe_disconnect_button(del_btn)

        add_btn.clicked.connect(lambda: self.add_persona_to_assets(item, insert_prompt=False))
        insert_btn.clicked.connect(lambda: self.add_persona_to_assets(item, insert_prompt=True))
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(item.get("uri", "")))
        set_preview_btn.clicked.connect(lambda: self.set_persona_preview_from_file(item, persona_type))
        paste_preview_btn.clicked.connect(lambda: self.set_persona_preview_from_clipboard(item, persona_type))
        url_preview_btn.clicked.connect(lambda: self.set_persona_preview_from_url(item, persona_type))
        del_btn.clicked.connect(lambda: self.delete_persona_item(item, persona_type))

    def update_persona_item_preview(self, item, persona_type, preview_value):
        data = load_persona_library()
        updated = None
        for x in data.get("items", []):
            if x.get("id") == item.get("id") or x.get("uri") == item.get("uri"):
                x["preview"] = preview_value
                updated = x
                break
        save_persona_library(data)
        self.persona_library = data
        self.refresh_persona_list(persona_type)
        if updated:
            self.select_persona(updated, persona_type)
        self.set_status("已更新虚拟人像预览图。")

    def set_persona_preview_from_file(self, item, persona_type):
        fp, _ = QFileDialog.getOpenFileName(self, "选择虚拟人像预览图", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if not fp:
            return
        ext = os.path.splitext(fp)[1].lower() or ".png"
        dst = os.path.join(persona_preview_dir(), safe_persona_preview_name(item.get("uri") or item.get("id")) + ext)
        try:
            shutil.copy2(fp, dst)
            self.update_persona_item_preview(item, persona_type, dst)
        except Exception as e:
            QMessageBox.warning(self, "预览图保存失败", str(e))

    def set_persona_preview_from_clipboard(self, item, persona_type):
        cb = QApplication.clipboard()
        pix = cb.pixmap()
        if pix.isNull():
            img = cb.image()
            if img.isNull():
                QMessageBox.information(self, "剪贴板无图片", "请先复制一张截图或图片。")
                return
            pix = QPixmap.fromImage(img)
        dst = os.path.join(persona_preview_dir(), safe_persona_preview_name(item.get("uri") or item.get("id")) + ".png")
        if pix.save(dst, "PNG"):
            self.update_persona_item_preview(item, persona_type, dst)
        else:
            QMessageBox.warning(self, "预览图保存失败", "无法保存剪贴板图片。")

    def set_persona_preview_from_url(self, item, persona_type):
        url, ok = QInputDialog.getText(self, "输入预览图 URL", "图片 URL：", text=item.get("preview", "") if str(item.get("preview","")).startswith(("http://","https://")) else "")
        if not ok:
            return
        url = url.strip()
        if not url:
            return
        if not url.startswith(("http://", "https://")):
            QMessageBox.warning(self, "URL 格式不正确", "请输入 http:// 或 https:// 开头的图片地址。")
            return
        self.update_persona_item_preview(item, persona_type, url)

    def delete_persona_item(self, item, persona_type):
        data = load_persona_library()
        data["items"] = [x for x in data.get("items", []) if x.get("id") != item.get("id")]
        save_persona_library(data)
        self.persona_library = data
        self.refresh_persona_list(persona_type)
        self.set_status("已删除人像登记。")

    def add_persona_to_assets(self, item, insert_prompt=False):
        uri = item.get("uri", "")
        if not uri:
            return
        existing = next((a for a in self.assets if a.path == uri), None)
        if existing:
            asset = existing
        else:
            prefix = "虚拟人像" if item.get("type") == "virtual" else "真人人像"
            asset = self.add_asset(
                uri,
                kind="image",
                display_name=f"{prefix}｜{item.get('name','未命名')}",
                note=item.get("desc", ""),
                detection={"message": "可信人像资产，按 asset:// URI 引用。", "persona_type": item.get("type"), "persona_status": item.get("status"), "preview": item.get("preview", "")}
            )
        if insert_prompt and hasattr(self, "video_prompt"):
            if hasattr(self.video_prompt, "insert_asset_chip"):
                self.video_prompt.insert_asset_chip(asset)
            else:
                self.video_prompt.insertPlainText(f"[@{asset.tag}] ")
            self.update_asset_usage()
        self.set_status(f"人像已加入素材池：{item.get('name','未命名')}")

    def build_library_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(16, 14, 16, 14)
        tabs = QTabWidget()
        tabs.addTab(self.build_doc_tab("official"), "官方文档")
        tabs.addTab(self.build_doc_tab("prompts"), "自用提示词")
        tabs.addTab(self.build_temp_tab(), "临时资料")
        lay.addWidget(tabs)
        return page

    def ensure_doc_dirs(self):
        docs_official_dir()
        docs_prompt_dir()
        return docs_dir()

    def build_doc_tab(self, kind):
        self.ensure_doc_dirs()
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(12, 12, 12, 12)
        top = QHBoxLayout()
        top.addWidget(ui_label("官方文档" if kind == "official" else "自用提示词", 14, True))
        upload = GlowButton("上传")
        upload.clicked.connect(lambda: self.upload_doc(kind))
        delete = GlowButton("删除", danger=True)
        delete.clicked.connect(lambda: self.delete_doc(kind))
        refresh = GlowButton("刷新")
        refresh.clicked.connect(lambda: self.refresh_doc_list(kind))
        top.addWidget(upload)
        top.addWidget(delete)
        top.addWidget(refresh)
        if kind == "prompts":
            insert = GlowButton("插入到当前 Prompt")
            insert.clicked.connect(lambda: self.insert_text_to_current_prompt(self.prompt_doc_view.toPlainText()))
            top.addWidget(insert)
        top.addStretch()
        root.addLayout(top)

        split = QSplitter(Qt.Horizontal)
        lst = QListWidget()
        viewer = QTextEdit()
        viewer.setPlaceholderText("选择或上传文档后显示内容。PDF 暂作为附件记录。")
        split.addWidget(lst)
        split.addWidget(viewer)
        split.setSizes([280, 880])
        root.addWidget(split, 1)

        if kind == "official":
            self.official_doc_list = lst; self.official_doc_view = viewer
        else:
            self.prompt_doc_list = lst; self.prompt_doc_view = viewer
        lst.itemClicked.connect(lambda item, k=kind: self.open_doc_item(k, item))
        QTimer.singleShot(0, lambda k=kind: self.refresh_doc_list(k))
        return w

    def build_temp_tab(self):
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(12, 12, 12, 12)
        top = QHBoxLayout()
        top.addWidget(ui_label("临时资料台", 14, True))
        top.addStretch()
        copy = GlowButton("复制")
        clear = GlowButton("清空", danger=True)
        insert = GlowButton("插入到当前 Prompt")
        top.addWidget(copy)
        top.addWidget(insert)
        top.addWidget(clear)
        root.addLayout(top)
        self.temp_doc_view = QTextEdit()
        self.temp_doc_view.setPlaceholderText("临时粘贴官方说明、报错、接口返回或灵感片段。")
        root.addWidget(self.temp_doc_view, 1)
        copy.clicked.connect(lambda: QApplication.clipboard().setText(self.temp_doc_view.toPlainText()))
        clear.clicked.connect(self.temp_doc_view.clear)
        insert.clicked.connect(lambda: self.insert_text_to_current_prompt(self.temp_doc_view.toPlainText()))
        return w

    # ---------- 素材操作 ----------

    def next_tag(self, kind):
        prefix = {"video": "视频", "image": "图片", "audio": "音频"}.get(kind, "素材")
        nums = []
        for a in self.assets:
            if a.tag.startswith(prefix):
                m = re.search(r"(\d+)", a.tag)
                if m:
                    nums.append(int(m.group(1)))
        n = 1
        while n in nums:
            n += 1
        return f"{prefix}{n}"

    def add_asset(self, path, kind=None, display_name="", note="", detection=None):
        kind = kind or asset_kind(path)
        tag = self.next_tag(kind)
        name = display_name or (os.path.basename(path) if not str(path).startswith(("http://", "https://", "asset://")) else short_url_label(path))
        a = AssetItem(tag=tag, path=path, kind=kind, display_name=name, note=note, detection=detection or {})
        self.assets.append(a)
        self.refresh_assets()
        return a

    def import_local_assets(self, image_only=False):
        if image_only:
            filt = "Images (*.png *.jpg *.jpeg *.webp)"
        else:
            filt = "Assets (*.png *.jpg *.jpeg *.webp *.mp4 *.mov *.m4v *.avi *.mp3 *.wav)"
        files, _ = QFileDialog.getOpenFileNames(self, "导入素材", "", filt)
        for fp in files:
            self.add_asset(fp, kind=asset_kind(fp))
            if image_only:
                item = QListWidgetItem(f"{self.next_tag('image')} - {os.path.basename(fp)}")
                item.setData(Qt.UserRole, fp)
                self.image_asset_list.addItem(item)
        self.update_asset_usage()

    def import_url_asset(self, image_only=False):
        dlg = UrlImportDialog(allow_video=not image_only, allow_audio=not image_only, parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        d = dlg.data()
        if not d.get("url"):
            return
        a = self.add_asset(d["url"], d["kind"], d["display_name"], d["note"], d["detection"])
        if image_only:
            item = QListWidgetItem(f"{a.tag} - {a.display_name}")
            item.setData(Qt.UserRole, a.path)
            self.image_asset_list.addItem(item)

    def clear_layout(self, lay):
        while lay.count():
            it = lay.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

    def refresh_assets(self):
        if not hasattr(self, "asset_grid"):
            return
        self.clear_layout(self.asset_grid)
        f = self.asset_filter.current_text() if hasattr(self, "asset_filter") else "全部"
        q = self.asset_search.text().strip().lower() if hasattr(self, "asset_search") else ""
        shown = []
        for a in self.assets:
            if f == "视频" and a.kind != "video": continue
            if f == "图片" and a.kind != "image": continue
            if f == "音频" and a.kind != "audio": continue
            if f == "URL" and not str(a.path).startswith(("http://", "https://", "asset://")): continue
            hay = f"{a.tag} {a.display_name} {a.path}".lower()
            if q and q not in hay: continue
            shown.append(a)
        for i, a in enumerate(shown):
            size = self.current_asset_thumb_size()
            card = AssetCard(a, size)
            card.clicked.connect(self.select_asset_card)
            card.request_menu.connect(self.show_asset_menu)
            self.asset_grid.addWidget(card, i, 0)
        self.asset_grid.setColumnStretch(0, 1)
        self.asset_grid.setRowStretch(99, 1)
        self.asset_bound_pill.setText(f"{len(self.assets)} 个素材")

    def select_asset_card(self, card):
        self.current_asset = card.asset
        a = card.asset
        risk = "；".join(a.detection.get("risk", [])) if isinstance(a.detection, dict) else ""
        det = a.detection.get("message", "") if isinstance(a.detection, dict) else ""
        self.asset_detail.setText(
            f"标签：{a.tag}\n类型：{a.kind}\n名称：{a.display_name}\n路径/URL：{a.path}\n备注：{a.note}\n检测：{det}\n风险：{risk}"
        )

    def show_asset_menu(self, card):
        a = card.asset
        menu = QMenuLike(self, [
            ("插入到 Prompt", lambda: self.video_prompt.insert_asset_chip(a) if hasattr(self.video_prompt, "insert_asset_chip") else self.video_prompt.insertPlainText(f"[@{a.tag}] ")),
            ("复制引用 Token", lambda: QApplication.clipboard().setText(f"[@{a.tag}]")),
            ("复制路径 / URL", lambda: QApplication.clipboard().setText(a.path)),
            ("重命名显示名", lambda: self.rename_asset(a)),
            ("重命名图片文件", lambda: self.rename_image_file(a)),
            ("检测链接", lambda: self.detect_asset(a)),
            ("删除素材", lambda: self.delete_asset(a)),
        ])
        menu.exec()

    def rename_asset(self, a):
        name, ok = QInputDialog.getText(self, "重命名素材", "显示名不会改变引用标签：", text=a.display_name)
        if ok:
            a.display_name = name.strip()
            self.refresh_assets()

    def rename_image_file(self, a):
        if a.kind != "image":
            QMessageBox.information(self, "仅支持图片", "重命名图片文件只适用于本地图片素材。")
            return
        if str(a.path).startswith(("http://", "https://", "asset://")) or not os.path.exists(a.path):
            QMessageBox.information(self, "无法重命名", "URL / asset:// 图片没有本地文件名，不能在素材池里重命名文件。")
            return
        base = os.path.splitext(os.path.basename(a.path))[0]
        ext = os.path.splitext(a.path)[1]
        name, ok = QInputDialog.getText(self, "重命名图片文件", "新文件名，不需要扩展名：", text=base)
        if not ok:
            return
        name = re.sub(r'[\\/:*?"<>|]+', "_", name.strip())
        if not name:
            return
        new_path = os.path.join(os.path.dirname(a.path), name + ext)
        if os.path.abspath(new_path) == os.path.abspath(a.path):
            return
        if os.path.exists(new_path):
            QMessageBox.warning(self, "文件已存在", "目标文件名已存在，请换一个名字。")
            return
        try:
            os.rename(a.path, new_path)
            a.path = new_path
            a.display_name = name + ext
            self.refresh_assets()
            self.update_asset_usage()
            self.set_status(f"图片文件已重命名：{a.display_name}")
        except Exception as e:
            QMessageBox.warning(self, "重命名失败", str(e))

    def detect_asset(self, a):
        if not str(a.path).startswith(("http://", "https://", "asset://")):
            QMessageBox.information(self, "本地素材", "本地素材无需 URL 检测。")
            return
        a.detection = detect_url_asset(a.path)
        self.refresh_assets()
        self.asset_detail.setText(json.dumps(a.detection, ensure_ascii=False, indent=2))

    def delete_asset(self, a):
        self.assets = [x for x in self.assets if x is not a]
        self.current_asset = None
        self.refresh_assets()
        self.update_asset_usage()

    def prompt_text_for_api(self):
        if hasattr(self, "video_prompt") and hasattr(self.video_prompt, "api_prompt_text"):
            return self.video_prompt.api_prompt_text().strip()
        return self.video_prompt.toPlainText().strip() if hasattr(self, "video_prompt") else ""

    def update_asset_usage(self):
        api_prompt = self.prompt_text_for_api() if hasattr(self, "video_prompt") else ""
        for a in self.assets:
            a.used = api_prompt.count(f"[@{a.tag}]")
        self.refresh_assets()

    def collect_refs(self, mode="video"):
        prompt_text = self.prompt_text_for_api() if mode == "video" and hasattr(self, "video_prompt") else ""
        if mode == "image":
            return [a.__dict__ for a in self.assets if a.kind == "image"]
        refs = [a.__dict__ for a in self.assets]
        p = self.current_video_profile() if hasattr(self, "current_video_profile") else {}
        return filter_refs_for_video_profile(refs, p, prompt_text)

    # ---------- 运行任务 ----------

    def log(self, msg):
        if hasattr(self, "log_box"):
            self.log_box.append(msg)
        self.set_status(msg)

    def current_video_profile(self):
        name = self.video_model.currentText()
        for p in self.profiles.get("video", []):
            if p.get("name") == name:
                return p
        return default_profile(self.profiles, "video")

    def current_image_profile(self):
        name = self.image_model.currentText()
        for p in self.profiles.get("image", []):
            if p.get("name") == name:
                return p
        return default_profile(self.profiles, "image")

    def apply_video_model_profile(self):
        p = self.current_video_profile()
        caps = []
        if p.get("supports_reference_video"): caps.append("视频参考")
        if p.get("supports_reference_audio"): caps.append("音频参考")
        if p.get("supports_web_search"): caps.append("web_search")
        if p.get("supports_offline_inference"): caps.append("离线推理")
        modes = " / ".join(profile_supported_video_modes(p))
        if p.get("name") == "Doubao-Seedance-1.0-pro-fast":
            effective_endpoint = p.get("endpoint") or self.cfg.get("doubao_seedance_1_0_pro_fast_endpoint") or "未配置"
        elif p.get("name") == "Seedance 2.0 Fast":
            effective_endpoint = p.get("endpoint") or self.cfg.get("video_fast_endpoint") or "未配置"
        elif p.get("name") == "自定义视频模型":
            effective_endpoint = p.get("endpoint") or self.cfg.get("custom_video_endpoint") or "未配置"
        else:
            effective_endpoint = p.get("endpoint") or self.cfg.get("video_endpoint") or "未配置"
        if hasattr(self, "video_service_tier") and self.video_service_tier.currentText() == "离线推理" and not profile_supports_offline_inference(p):
            self.video_service_tier.setCurrentText("在线推理")
        cap_text = " / ".join(caps) if caps else "仅文本/首帧图生视频"
        tier_text = self.video_service_tier.currentText() if hasattr(self, "video_service_tier") else "在线推理"
        self.set_status(f"当前模型：{p.get('name')}｜Endpoint：{effective_endpoint}｜能力：{cap_text}｜支持模式：{modes}｜当前推理：{tier_text}")

    def build_task(self, mode):
        if mode == "video":
            p = self.current_video_profile()
            current_video_mode = self.video_mode.current_text()
            if not profile_supports_video_mode(p, current_video_mode):
                raise ValueError(f"{p.get('name')} 不支持当前生成模式：{current_video_mode}")
            seed = int(self.video_seed.text().strip()) if self.video_seed.text().strip().lstrip("-").isdigit() else -1
            prompt = self.prompt_text_for_api()
            refs = self.collect_refs("video")
            if self.audio_sync_chk.isChecked() and any(a.get("kind") == "audio" for a in refs):
                prompt += "\n请分析参考音频的节奏、重音、BPM 和情绪变化，使画面运动、光影闪烁和粒子爆发与音频自然同步。"

            if p.get("name") == "Doubao-Seedance-1.0-pro-fast":
                endpoint = p.get("endpoint") or self.cfg.get("doubao_seedance_1_0_pro_fast_endpoint") or ""
                enable_web_search = False
            elif p.get("name") == "Seedance 2.0 Fast":
                endpoint = p.get("endpoint") or self.cfg.get("video_fast_endpoint") or ""
                enable_web_search = bool(self.web_search_chk.isChecked())
            elif p.get("name") == "自定义视频模型":
                endpoint = p.get("endpoint") or self.cfg.get("custom_video_endpoint") or ""
                enable_web_search = bool(self.web_search_chk.isChecked()) and bool(p.get("supports_web_search"))
            else:
                endpoint = p.get("endpoint") or self.cfg.get("video_endpoint") or ""
                enable_web_search = bool(self.web_search_chk.isChecked()) and bool(p.get("supports_web_search"))

            service_tier = "flex" if (hasattr(self, "video_service_tier") and self.video_service_tier.currentText() == "离线推理") else "default"
            if service_tier == "flex" and not profile_supports_offline_inference(p):
                raise ValueError(f"{p.get('name')} 暂不支持离线推理。请切换为在线推理，或改用支持离线推理的模型。")

            return {
                "mode": "video",
                "project": self.project_in.text().strip(),
                "shot": self.shot_in.text().strip(),
                "endpoint": endpoint,
                "model_profile": p.get("name"),
                "prompt": prompt,
                "negative_prompt": self.video_negative.toPlainText().strip(),
                "refs": refs,
                "seed": seed,
                "ratio": self.video_ratio.currentText(),
                "resolution": self.video_res.current_text(),
                "duration": int(self.video_duration.currentText()),
                "video_mode": current_video_mode,
                "output_dir": self.current_shot_dir(create=True),
                "enable_web_search": enable_web_search,
                "service_tier": service_tier,
                "execution_expires_after": 172800,
                "supports_offline_inference": bool(p.get("supports_offline_inference")),
            }
        else:
            p = self.current_image_profile()
            seed = int(self.image_seed.text().strip()) if self.image_seed.text().strip().lstrip("-").isdigit() else -1
            return {
                "mode": "image",
                "project": self.project_in.text().strip(),
                "shot": self.shot_in.text().strip() + "_IMG",
                "endpoint": p.get("endpoint") or self.cfg.get("image_endpoint"),
                "model_profile": p.get("name"),
                "prompt": self.image_prompt.toPlainText().strip(),
                "negative_prompt": self.image_negative.toPlainText().strip(),
                "refs": self.collect_refs("image"),
                "seed": seed,
                "ratio": self.image_ratio.currentText(),
                "resolution": self.image_res.currentText(),
                "duration": "",
                "output_dir": self.current_shot_dir(image=True, create=True),
            }

    def task_has_local_refs(self, task):
        for ref in task.get("refs", []):
            p = str(ref.get("path", ""))
            if p and not p.startswith(("http://", "https://", "asset://")):
                return True
        return False

    def tos_ready_for_local_upload(self):
        cfg = load_config()
        if not cfg.get("enable_tos_upload"):
            return False, "未启用 TOS 本地上传"
        for k in ["tos_bucket", "tos_endpoint", "tos_access_key", "tos_secret_key"]:
            if not cfg.get(k):
                return False, "TOS 配置不完整"
        return True, "TOS 已配置"

    def check_local_refs_before_submit(self, task):
        if not self.task_has_local_refs(task):
            return True
        ok, msg = self.tos_ready_for_local_upload()
        if ok:
            return True
        QMessageBox.warning(
            self,
            "本地素材需要 TOS",
            f"{msg}。\n\n当前任务引用了本地文件，火山云端无法直接读取你的电脑路径。\n"
            "解决方式：\n"
            "1. 在管线设置 > TOS 上传中开启并填写 Bucket / Endpoint / AK / SK；\n"
            "2. 或把素材换成公网 URL / asset:// 官方素材 / 虚拟人像。"
        )
        return False

    def run_video_task(self):
        try:
            task = self.build_task("video")
        except ValueError as e:
            QMessageBox.warning(self, "当前模型不支持", str(e))
            return
        if not task["prompt"]:
            QMessageBox.warning(self, "缺少提示词", "请先输入镜头提示词。")
            return
        if not self.check_local_refs_before_submit(task):
            return
        self.start_worker(task)

    def run_image_task(self):
        task = self.build_task("image")
        if not task["prompt"]:
            QMessageBox.warning(self, "缺少提示词", "请先输入生图提示词。")
            return
        if not self.check_local_refs_before_submit(task):
            return
        self.start_worker(task)

    def start_worker(self, task):
        self.cfg = load_config()
        worker = APIRenderWorker(task, self.cfg)
        self.active_workers.append(worker)
        self.current_worker = worker

        if not hasattr(self, "progress_dialog") or self.progress_dialog is None:
            self.progress_dialog = TaskProgressDialog(self)
        self.progress_dialog.log_view.clear()
        self.progress_dialog.title.setText("云端任务正在运行")
        self.progress_dialog.append_log("任务已启动。关闭窗口不会影响任务运行。")
        self.progress_dialog.show()
        self.progress_dialog.raise_()
        self.progress_dialog.activateWindow()

        worker.log.connect(self.log)
        worker.log.connect(self.progress_dialog.append_log)
        worker.done.connect(self.on_render_done)
        worker.finished.connect(lambda w=worker: self.cleanup_worker(w))
        worker.start()
        self.log("任务已启动。")

    def cleanup_worker(self, worker):
        if worker in self.active_workers:
            self.active_workers.remove(worker)
        worker.deleteLater()

    def cancel_current_task(self):
        # 仅停止最后一个发起的任务（主要作用是停止前端的本地轮询等待）。
        if self.current_worker:
            self.current_worker.cancelled = True
            self.log("已请求停止本地轮询。云端 running 状态不一定可取消。")

    def on_render_done(self, result):
        if result.get("ok"):
            msg = f"完成：{result.get('path')}"
            self.log(msg)
            if hasattr(self, "progress_dialog") and self.progress_dialog:
                self.progress_dialog.mark_done(True, msg)
            self.refresh_vault()
            self.refresh_project_videos()
        else:
            msg = f"失败：{result.get('msg')}"
            self.log(msg)
            if hasattr(self, "progress_dialog") and self.progress_dialog:
                self.progress_dialog.mark_done(False, msg)
            QMessageBox.warning(self, "任务失败", result.get("msg", "未知错误"))

    # ---------- 云端 ----------

    def query_cloud_task(self):
        cfg = load_config()
        tid = self.query_task_id.text().strip()
        if not tid:
            QMessageBox.warning(self, "缺少 Task ID", "请先输入 Task ID。")
            return
        self.query_worker = QueryWorker(cfg.get("api_key"), tid)
        self.query_worker.done.connect(self.on_query_done)
        self.query_worker.start()
        self.set_status("正在查询云端任务...")

    def on_query_done(self, data):
        if not data.get("ok"):
            self.cloud_raw.setText(data.get("msg", "查询失败"))
            return
        task = {
            "task_id": self.query_task_id.text().strip(),
            "status": data.get("status"),
            "url": data.get("url"),
            "thumb": data.get("thumb"),
            "usage_total_tokens": data.get("usage_total_tokens"),
            "model": data.get("model"),
            "raw": data.get("raw")
        }
        self.current_cloud_task = task
        self.show_cloud_task(task)

    def scan_cloud_tasks(self):
        cfg = load_config()
        if not cfg.get("api_key"):
            QMessageBox.warning(self, "缺少 API Key", "请先在管线设置里配置 API Key。")
            return
        self.scan_worker = ScanCloudWorker(cfg.get("api_key"), 32)
        self.scan_worker.done.connect(self.on_scan_done)
        self.scan_worker.start()
        self.set_status("正在扫描云端已完成任务...")

    def on_scan_done(self, data):
        if not data.get("ok"):
            self.cloud_raw.setText(data.get("msg", "扫描失败"))
            return
        self.cloud_tasks = data.get("tasks", [])
        self.refresh_cloud_grid()
        self.set_status(f"扫描完成：{len(self.cloud_tasks)} 个任务。")

    def refresh_cloud_grid(self):
        self.clear_layout(self.cloud_grid)
        for t in self.cloud_tasks:
            card = ResultCardLike(
                f"任务 {t.get('task_id')[:16]}",
                f"{t.get('status')}｜用时 {t.get('elapsed_seconds') or '-'}s",
                t.get("thumb", ""),
                t.get("url", ""),
                self.current_cloud_thumb_size()
            )
            card.clicked.connect(lambda tt=t: self.show_cloud_task(tt))
            self.cloud_grid.addWidget(card)
        self.cloud_grid.addStretch(1)

    def cloud_input_mode_value(self):
        txt = self.cloud_cost_mode.current_text()
        if "含视频" in txt:
            return "with_video"
        if "不含视频" in txt:
            return "no_video"
        return "auto"

    def set_cloud_cost_mode(self, mode):
        self.cloud_cost_mode.set_current_text({"with_video": "含视频", "no_video": "不含视频"}.get(mode, "自动"))

    def show_cloud_task(self, task):
        self.current_cloud_task = task
        tid = task.get("task_id", "")
        overrides = load_overrides()
        o = overrides.get(tid, {})
        self.set_cloud_cost_mode(o.get("input_mode", "auto"))
        self.cloud_note.setText(o.get("note", ""))
        thumb_url = task.get("thumb") or ""
        media_url = task.get("url") or ""
        fallback_kind = "image" if guess_ext_from_url(media_url, "") in {"png", "jpg", "jpeg", "webp"} else "video"
        preview_url = thumb_url or (media_url if fallback_kind == "image" else "")
        detail_w = max(260, self.current_cloud_thumb_size() * 3)
        detail_h = max(140, int(detail_w * 0.45))
        self.cloud_thumb.setFixedHeight(detail_h + 10)
        self.cloud_thumb.setPixmap(remote_pixmap(preview_url, detail_w, detail_h, fallback_kind))
        cost = estimate_cost(task, self.profiles, o.get("input_mode", "auto"))
        self.cloud_status.setText(f"任务 ID：{tid}\n状态：{task.get('status')}\nURL：{task.get('url')}\n{cost}")
        self.cloud_raw.setText(task.get("raw", ""))

    def save_cloud_override_quick(self):
        if not self.current_cloud_task:
            return
        tid = self.current_cloud_task.get("task_id")
        data = load_overrides()
        old = data.get(tid, {})
        data[tid] = {
            "input_mode": self.cloud_input_mode_value(),
            "note": old.get("note", ""),
            "updated_at": now_str()
        }
        save_overrides(data)
        self.show_cloud_task(self.current_cloud_task)

    def save_cloud_note(self):
        if not self.current_cloud_task:
            return
        tid = self.current_cloud_task.get("task_id")
        data = load_overrides()
        old = data.get(tid, {})
        data[tid] = {
            "input_mode": old.get("input_mode", self.cloud_input_mode_value()),
            "note": self.cloud_note.text().strip(),
            "updated_at": now_str()
        }
        save_overrides(data)
        self.show_cloud_task(self.current_cloud_task)

    def download_cloud_result(self):
        if not self.current_cloud_task or not self.current_cloud_task.get("url"):
            QMessageBox.warning(self, "缺少 URL", "当前任务没有可下载 URL。")
            return
        url = self.current_cloud_task["url"]
        ext = guess_ext_from_url(url)
        fp = get_next_path(self.cfg.get("output_dir"), "Cloud", self.current_cloud_task.get("task_id", "Task")[:10], ext)
        try:
            urllib.request.urlretrieve(url, fp)
            meta = dict(self.current_cloud_task)
            meta.update({"mode": "video" if ext in {"mp4", "mov", "m4v", "avi"} else "image", "created_at": now_str()})
            write_sidecar(fp, meta)
            self.refresh_vault()
            QMessageBox.information(self, "下载完成", fp)
        except Exception as e:
            QMessageBox.warning(self, "下载失败", str(e))

    # ---------- 金库 ----------

    def refresh_vault(self):
        if not hasattr(self, "vault_list"):
            return
        self.clear_layout(self.vault_list)
        out = self.cfg.get("output_dir", "outputs")
        ensure_dir(out)
        files = []
        for root, _, names in os.walk(out):
            for name in names:
                if name.lower().endswith(IMAGE_EXTS + VIDEO_EXTS):
                    files.append(os.path.join(root, name))
        files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

        q = self.vault_search.text().strip().lower() if hasattr(self, "vault_search") else ""
        mode = self.vault_filter.currentText() if hasattr(self, "vault_filter") else "全部"

        for fp in files[:250]:
            meta = load_sidecar(fp)
            is_video = fp.lower().endswith(VIDEO_EXTS)
            is_image = fp.lower().endswith(IMAGE_EXTS)
            if mode == "视频" and not is_video: continue
            if mode == "图片" and not is_image: continue
            if mode == "有元数据" and not meta: continue
            if mode == "可复刻" and not meta.get("prompt"): continue
            if mode == "今天" and datetime.datetime.fromtimestamp(os.path.getmtime(fp)).date() != datetime.date.today():
                continue
            hay = " ".join([os.path.basename(fp), str(meta.get("project","")), str(meta.get("shot","")), str(meta.get("task_id",""))]).lower()
            if q and q not in hay:
                continue
            c = ResultCard(fp, self.current_vault_thumb_size())
            c.clicked.connect(self.show_vault_meta)
            c.double_clicked.connect(lambda card: safe_open_path(card.path))
            c.request_menu.connect(self.show_vault_menu)
            self.vault_list.addWidget(c)
        self.vault_list.addStretch(1)

    def show_vault_meta(self, card):
        self.current_vault_path = card.path
        meta = card.meta
        if not meta:
            self.vault_meta.setText("暂无元数据。\n旧结果可以打开，但不能完整复刻。")
            return
        prompt = (meta.get("prompt") or "").replace("\n", " ")
        if len(prompt) > 420:
            prompt = prompt[:420] + "..."
        self.vault_meta.setText(
            f"文件：{os.path.basename(card.path)}\n"
            f"任务 ID：{meta.get('task_id','')}\n"
            f"模式：{meta.get('mode','')}｜模型：{meta.get('model_profile','')}｜用时：{meta.get('elapsed_seconds','')}s\n"
            f"Seed：{meta.get('seed','')}｜比例：{meta.get('ratio','')}｜清晰度：{meta.get('resolution','')}\n"
            f"{estimate_cost(meta, self.profiles)}\n\n"
            f"Prompt：{prompt}"
        )

    def show_vault_menu(self, card):
        menu = QMenuLike(self, [
            ("打开文件", lambda: safe_open_path(card.path)),
            ("打开所在文件夹", lambda: safe_open_path(os.path.dirname(card.path))),
            ("完整复刻到工作台", lambda: self.replicate_vault(card.path)),
            ("发送到视频延长工作台", lambda: self.send_to_video_mode(card.path, "视频延长")),
            ("发送到前序生成工作台", lambda: self.send_to_video_mode(card.path, "前序生成")),
            ("发送到轨道补全工作台", lambda: self.send_to_video_mode(card.path, "轨道补全")),
        ])
        menu.exec()

    def replicate_current_vault(self):
        p = getattr(self, "current_vault_path", "")
        if p:
            self.replicate_vault(p)

    def replicate_vault(self, path):
        meta = load_sidecar(path)
        if not meta:
            QMessageBox.warning(self, "无法复刻", "没有找到元数据 JSON。")
            return
        self.switch_page(0 if meta.get("mode") == "video" else 1)
        if meta.get("mode") == "video":
            self.video_prompt.setText(meta.get("prompt", ""))
            self.video_negative.setText(meta.get("negative_prompt", ""))
            self.video_seed.setText(str(meta.get("seed", -1)))
            self.project_in.setText(meta.get("project", "Project"))
            self.shot_in.setText(meta.get("shot", "Shot"))
            self.assets = []
            for ref in meta.get("refs", []):
                self.add_asset(ref.get("path", ""), ref.get("kind") or asset_kind(ref.get("path", ""), ref.get("tag", "")), ref.get("display_name", ""))
            self.update_asset_usage()
        else:
            self.image_prompt.setText(meta.get("prompt", ""))
            self.image_negative.setText(meta.get("negative_prompt", ""))
            self.image_seed.setText(str(meta.get("seed", -1)))
        QMessageBox.information(self, "已复刻", "已把参数、Prompt 与素材恢复到工作台。")

    def send_to_video_mode(self, path, mode):
        self.switch_page(0)
        self.video_mode.set_current_text(mode)
        self.assets = []
        a = self.add_asset(path, "video", os.path.basename(path))
        templates = {
            "视频延长": "将 [@视频1] 向后延长，保持原视频的人物状态、主体运动、镜头运动、空间关系、光影方向与画面风格连续，自然生成后续画面。",
            "前序生成": "为 [@视频1] 生成前序画面，保持原视频的人物状态、空间关系、光影方向与画面风格一致，生成发生在视频开头之前的内容，并自然衔接到原视频开头。",
            "轨道补全": "以 [@视频1] 作为第一段参考，继续添加其他视频素材后，按顺序生成它们之间连贯的过渡画面，补全空间运动轨迹、镜头连接和视觉节奏。"
        }
        self.video_prompt.setText(templates.get(mode, ""))
        self.update_asset_usage()

    # ---------- 资料库 ----------

    def refresh_doc_list(self, kind):
        self.ensure_doc_dirs()
        folder = docs_official_dir() if kind == "official" else docs_prompt_dir()
        lst = self.official_doc_list if kind == "official" else self.prompt_doc_list
        lst.clear()
        for name in sorted(os.listdir(folder)):
            fp = os.path.join(folder, name)
            if os.path.isfile(fp):
                it = QListWidgetItem(name)
                it.setData(Qt.UserRole, fp)
                lst.addItem(it)

    def upload_doc(self, kind):
        files, _ = QFileDialog.getOpenFileNames(self, "上传文档", "", "Documents (*.txt *.md *.json *.csv *.pdf);;All Files (*.*)")
        if not files:
            return
        folder = docs_official_dir() if kind == "official" else docs_prompt_dir()
        for fp in files:
            try:
                shutil.copy2(fp, os.path.join(folder, os.path.basename(fp)))
            except Exception as e:
                QMessageBox.warning(self, "上传失败", str(e))
        self.refresh_doc_list(kind)

    def delete_doc(self, kind):
        lst = self.official_doc_list if kind == "official" else self.prompt_doc_list
        it = lst.currentItem()
        if not it: return
        try:
            os.remove(it.data(Qt.UserRole))
            self.refresh_doc_list(kind)
        except Exception as e:
            QMessageBox.warning(self, "删除失败", str(e))

    def read_doc(self, path):
        if path.lower().endswith(".pdf"):
            return f"PDF 附件：{os.path.basename(path)}\n\n当前版本不解析 PDF 正文，可转成 txt / md 后上传。"
        for enc in ["utf-8", "utf-8-sig", "gbk", "shift_jis"]:
            try:
                with open(path, "r", encoding=enc) as f:
                    return f.read()
            except Exception:
                pass
        return "无法读取文档。"

    def open_doc_item(self, kind, item):
        content = self.read_doc(item.data(Qt.UserRole))
        if kind == "official":
            self.official_doc_view.setText(content)
        else:
            self.prompt_doc_view.setText(content)

    def insert_text_to_current_prompt(self, text):
        text = (text or "").strip()
        if not text:
            return
        if self.stack.currentIndex() == 1:
            self.image_prompt.insertPlainText("\n" + text)
        else:
            self.video_prompt.insertPlainText("\n" + text)

    # ---------- 稳定版自检 ----------

    def run_stability_check(self):
        cfg = load_config()
        profiles = load_model_profiles()
        results = []

        def add(name, ok, detail=""):
            results.append((name, bool(ok), detail))

        add("API Key", bool(cfg.get("api_key")), "已配置" if cfg.get("api_key") else "未配置")
        add("视频 Endpoint", bool(cfg.get("video_endpoint") or default_profile(profiles, "video").get("endpoint")),
            cfg.get("video_endpoint") or default_profile(profiles, "video").get("endpoint", "") or "未配置")
        add("生图 Endpoint", bool(cfg.get("image_endpoint") or default_profile(profiles, "image").get("endpoint")),
            cfg.get("image_endpoint") or default_profile(profiles, "image").get("endpoint", "") or "未配置")
        out = cfg.get("output_dir") or self.output_root()
        try:
            ensure_dir(out)
            writable = os.access(out, os.W_OK)
        except Exception:
            writable = False
        add("输出目录可写", writable, out)

        tos_enabled = bool(cfg.get("enable_tos_upload"))
        tos_complete = all(cfg.get(k) for k in ["tos_bucket", "tos_endpoint", "tos_access_key", "tos_secret_key"])
        if tos_enabled:
            add("TOS 本地上传", tos_complete, "已启用且配置完整" if tos_complete else "已启用但配置不完整")
        else:
            add("TOS 本地上传", True, "未启用；仅使用公网 URL / asset:// 时不需要")

        video_names = [p.get("name") for p in profiles.get("video", [])]
        image_names = [p.get("name") for p in profiles.get("image", [])]
        add("Seedance 2.0 模型预设", "Seedance 2.0" in video_names, "存在" if "Seedance 2.0" in video_names else "缺失")
        fast_profile = profile_by_name(profiles, "video", "Seedance 2.0 Fast")
        add("Seedance 2.0 Fast 模型预设", "Seedance 2.0 Fast" in video_names, "存在" if "Seedance 2.0 Fast" in video_names else "缺失")
        add("Seedance 2.0 Fast Endpoint", bool((fast_profile or {}).get("endpoint") or cfg.get("video_fast_endpoint")), (fast_profile or {}).get("endpoint") or cfg.get("video_fast_endpoint") or "未配置")
        add("Seedream Image 模型预设", "Seedream Image" in image_names, "存在" if "Seedream Image" in image_names else "缺失")

        missing_ui = self.check_main_ui_integrity() if hasattr(self, "check_main_ui_integrity") else ["自检函数缺失"]
        add("主界面控件完整性", not missing_ui, "完整" if not missing_ui else "缺失：" + "、".join(missing_ui))
        add("Prompt 结构化逻辑", hasattr(self, "convert_prompt_to_structured"), "已绑定" if hasattr(self, "convert_prompt_to_structured") else "缺失")
        add("联网扩写逻辑", hasattr(self, "expand_prompt_with_web_search"), "已绑定" if hasattr(self, "expand_prompt_with_web_search") else "缺失")
        add("提示词体检逻辑", hasattr(self, "check_prompt_quality"), "已绑定" if hasattr(self, "check_prompt_quality") else "缺失")
        add("素材拖拽到 Prompt", hasattr(AssetPromptEdit, "dropEvent"), "已启用" if hasattr(AssetPromptEdit, "dropEvent") else "缺失")
        add("虚拟人像库", os.path.exists(PERSONA_LIBRARY_FILE) or bool(getattr(self, "persona_library", None) is not None), PERSONA_LIBRARY_FILE)

        add("首次轮询延迟", int(cfg.get("poll_delay", 45)) >= 0, f"{cfg.get('poll_delay', 45)} 秒")
        add("轮询间隔", int(cfg.get("poll_interval", 5)) >= 1, f"{cfg.get('poll_interval', 5)} 秒")

        return results

    def stability_report_text(self):
        results = self.run_stability_check()
        ok_count = sum(1 for _, ok, _ in results if ok)
        lines = [f"稳定版自检：{ok_count}/{len(results)} 项通过", ""]
        for name, ok, detail in results:
            mark = "✅" if ok else "⚠️"
            lines.append(f"{mark} {name}：{detail}")
        lines.append("")
        lines.append("说明：⚠️ 不一定代表软件不能打开，通常表示生成前需要补配置。")
        return "\n".join(lines)

    def show_stability_check(self):
        text = self.stability_report_text()
        if hasattr(self, "log_box"):
            self.log(text)
        QMessageBox.information(self, "功能自检", text)

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.cfg = load_config()
            self.profiles = load_model_profiles()
            self.out_dir_label.setText(self.cfg.get("output_dir", "outputs"))
            self.update_shot_path_label()
            self.refresh_vault()
            self.refresh_project_videos()
            self.apply_video_model_profile()
            self.set_status(
                "管线设置已更新｜"
                f"Seedance 2.0：{self.cfg.get('video_endpoint') or '未配置'}｜"
                f"Fast：{self.cfg.get('video_fast_endpoint') or '未配置'}｜"
                f"生图：{self.cfg.get('image_endpoint') or '未配置'}"
            )

    def show_image_asset_detail(self, item):
        self.image_asset_detail.setText(f"路径：{item.data(Qt.UserRole)}")


class ResultCardLike(QFrame):
    clicked = Signal()

    def __init__(self, title, subtitle, thumb_url="", media_url="", thumb_w=112):
        super().__init__()
        self.thumb_url = thumb_url or ""
        self.media_url = media_url or ""
        self.thumb_w = int(thumb_w)
        self.thumb_h = max(52, int(self.thumb_w * 0.59))
        self.setFixedHeight(max(92, self.thumb_h + 26))
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
        QFrame {{
            background: {Theme.SURFACE_2};
            border: 1px solid {Theme.BORDER};
            border-radius: 14px;
        }}
        QFrame:hover {{
            border-color: {Theme.BORDER_HI};
            background: #142036;
        }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 10, 12, 10)
        lay.setSpacing(10)

        fallback = "image" if guess_ext_from_url(self.media_url, "") in {"png", "jpg", "jpeg", "webp"} else "video"
        preview_url = self.thumb_url or (self.media_url if fallback == "image" else "")
        thumb = QLabel()
        thumb.setFixedSize(self.thumb_w, self.thumb_h)
        thumb.setAlignment(Qt.AlignCenter)
        thumb.setStyleSheet("background:#09111D; border-radius:10px; color:#91A4C7; font-weight:800;")
        if preview_url and os.path.isfile(str(preview_url)):
            pix = QPixmap(str(preview_url))
            if not pix.isNull():
                thumb.setPixmap(pix.scaled(self.thumb_w, self.thumb_h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
            else:
                thumb.setPixmap(make_placeholder_pixmap(fallback, self.thumb_w, self.thumb_h))
        else:
            thumb.setPixmap(remote_pixmap(preview_url, self.thumb_w, self.thumb_h, fallback))
        lay.addWidget(thumb)

        info = QVBoxLayout()
        info.setSpacing(5)
        info.addWidget(ui_label(title, 12, True))
        info.addWidget(ui_label(subtitle, 11, False, True))
        if self.thumb_url:
            info.addWidget(ui_label("缩略图：已获取", 10, False, True))
        elif self.media_url:
            info.addWidget(ui_label("缩略图：尝试首帧预览", 10, False, True))
        else:
            info.addWidget(ui_label("缩略图：占位预览", 10, False, True))
        lay.addLayout(info, 1)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class PersonaDropdownItem(QFrame):
    clicked = Signal(object)

    def __init__(self, item):
        super().__init__()
        self.item = item
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(86)
        self.setStyleSheet(f"""
        QFrame {{
            background: {Theme.SURFACE_2};
            border: 1px solid {Theme.BORDER};
            border-radius: 13px;
        }}
        QFrame:hover {{
            background: #142036;
            border-color: {Theme.BORDER_HI};
        }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)
        
        thumb = QLabel()
        thumb.setFixedSize(66, 66)
        thumb.setStyleSheet("background:#09111D; border-radius:8px;")
        thumb.setAlignment(Qt.AlignCenter)
        preview = item.get("preview", "")
        if preview and os.path.isfile(str(preview)):
            pix = QPixmap(str(preview))
            if not pix.isNull():
                thumb.setPixmap(pix.scaled(66, 66, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        elif preview and str(preview).startswith(("http://", "https://")):
            thumb.setPixmap(remote_pixmap(preview, 66, 66, "image"))
        else:
            thumb.setText("无预览")
        lay.addWidget(thumb)

        info = QVBoxLayout()
        info.setSpacing(4)
        info.addWidget(ui_label(item.get("name", "未命名"), 12, True))
        info.addWidget(ui_label(item.get("uri", ""), 10, False, True))
        desc = item.get("desc", "").replace("\n", " ")
        if len(desc) > 20: desc = desc[:19] + "..."
        info.addWidget(ui_label(desc, 10, False, True))
        lay.addLayout(info, 1)

    def mousePressEvent(self, event):
        self.clicked.emit(self.item)
        super().mousePressEvent(event)


class PersonaDropdown(QDialog):
    def __init__(self, parent, items, title, on_select):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.items = items
        self.on_select = on_select
        self.resize(320, 400)
        
        root = QFrame(self)
        root.setGeometry(self.rect())
        root.setStyleSheet(f"""
        QFrame {{
            background: {Theme.SURFACE};
            border: 1px solid {Theme.BORDER_HI};
            border-radius: 12px;
        }}
        """)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        
        lay.addWidget(ui_label(title, 12, True))
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索人像...")
        self.search.textChanged.connect(self.refresh_list)
        lay.addWidget(self.search)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        host = QWidget()
        self.list_lay = QVBoxLayout(host)
        self.list_lay.setContentsMargins(0, 0, 0, 0)
        self.list_lay.setSpacing(8)
        scroll.setWidget(host)
        lay.addWidget(scroll, 1)
        self.refresh_list()

    def refresh_list(self):
        while self.list_lay.count():
            it = self.list_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        q = self.search.text().strip().lower()
        count = 0
        for item in self.items:
            hay = f"{item.get('name','')} {item.get('uri','')} {item.get('desc','')}".lower()
            if q and q not in hay:
                continue
            card = PersonaDropdownItem(item)
            card.clicked.connect(self.handle_select)
            self.list_lay.addWidget(card)
            count += 1
        if count == 0:
            empty = QTextEdit()
            empty.setReadOnly(True)
            empty.setFixedHeight(88)
            empty.setText("没有匹配的人像。")
            self.list_lay.addWidget(empty)
        self.list_lay.addStretch(1)

    def handle_select(self, item):
        if self.on_select:
            self.on_select(item)
        self.close()


class QMenuLike:
    def __init__(self, parent, actions):
        from PySide6.QtWidgets import QMenu
        self.menu = QMenu(parent)
        self.menu.setStyleSheet(APP_QSS)
        for name, fn in actions:
            act = QAction(name, parent)
            act.triggered.connect(fn)
            self.menu.addAction(act)

    def exec(self):
        from PySide6.QtGui import QCursor
        self.menu.exec(QCursor.pos())
