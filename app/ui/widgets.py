from ..common import *

# =========================================================
# 1. 主题 / UI 组件
# =========================================================

class Theme:
    BG = "#070A10"
    SURFACE = "#0C111B"
    SURFACE_2 = "#101827"
    PANEL = "#0D1421"
    BORDER = "rgba(126, 150, 190, 0.22)"
    BORDER_HI = "rgba(88, 201, 255, 0.55)"
    TEXT = "#EAF1FF"
    MUTED = "#91A4C7"
    FAINT = "#5F718F"
    BLUE = "#31A8FF"
    CYAN = "#42E8FF"
    GREEN = "#42D392"
    RED = "#FF4D5E"
    AMBER = "#F8B84E"


APP_QSS = f"""
QMainWindow {{ background: {Theme.BG}; }}
QWidget {{
    background: transparent;
    color: {Theme.TEXT};
    font-family: "Microsoft YaHei UI", "PingFang SC", "Segoe UI", Arial;
    font-size: 13px;
}}
QFrame#Sidebar {{
    background: #060A11;
    border-right: 1px solid {Theme.BORDER};
}}
QFrame#TopBar {{
    background: {Theme.SURFACE};
    border-bottom: 1px solid {Theme.BORDER};
}}
QFrame#StatusBar {{
    background: #080D15;
    border-top: 1px solid {Theme.BORDER};
}}
QFrame[panel="true"] {{
    background-color: {Theme.PANEL};
    border: 1px solid {Theme.BORDER};
    border-radius: 16px;
}}
QLabel[muted="true"] {{ color: {Theme.MUTED}; }}
QLabel[faint="true"] {{ color: {Theme.FAINT}; }}
QLineEdit, QTextEdit, QComboBox, QSpinBox {{
    background-color: #0A101A;
    border: 1px solid {Theme.BORDER};
    color: {Theme.TEXT};
    border-radius: 10px;
    padding: 8px 10px;
    selection-background-color: {Theme.BLUE};
}}
QTextEdit {{ line-height: 1.7; }}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
    border: 1px solid {Theme.BORDER_HI};
}}
QComboBox {{
    padding-right: 34px;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 30px;
    border-left: 1px solid rgba(126, 150, 190, 0.22);
    background: #111A2B;
    border-top-right-radius: 10px;
    border-bottom-right-radius: 10px;
}}
QComboBox::drop-down:hover {{
    background: #17243A;
}}
QComboBox::down-arrow {{
    image: none;
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #BFD7FF;
    margin-right: 9px;
}}
QComboBox QAbstractItemView {{
    show-decoration-selected: 1;
}}
QComboBox QAbstractItemView {{
    background-color: #0A101A;
    color: #EAF1FF;
    border: 1px solid rgba(88, 201, 255, 0.45);
    border-radius: 10px;
    padding: 6px;
    outline: none;
    selection-background-color: #1B2A44;
    selection-color: #FFFFFF;
}}
QComboBox QAbstractItemView::item {{
    min-height: 30px;
    padding: 6px 10px;
    border-radius: 8px;
}}
QPushButton {{
    background-color: #111A2B;
    color: {Theme.TEXT};
    border: 1px solid rgba(126, 150, 190, 0.28);
    border-radius: 10px;
    padding: 8px 13px;
    font-weight: 700;
}}
QPushButton:hover {{
    background-color: #17243A;
    border: 1px solid {Theme.BORDER_HI};
}}
QPushButton[primary="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1677FF, stop:1 #39D5FF);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 12px 18px;
    font-size: 14px;
}}
QPushButton[danger="true"] {{
    background-color: rgba(255, 77, 94, 0.16);
    color: #FFD8DD;
    border: 1px solid rgba(255, 77, 94, 0.42);
}}
QPushButton[ghost="true"] {{
    background-color: transparent;
    border: 1px solid transparent;
    color: {Theme.MUTED};
}}
QPushButton[ghost="true"]:hover {{
    background-color: rgba(255,255,255,0.05);
    border: 1px solid {Theme.BORDER};
    color: {Theme.TEXT};
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: #26344D;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 14px;
    height: 14px;
    margin: -5px 0;
    background: {Theme.CYAN};
    border-radius: 7px;
}}
QScrollArea {{
    border: none;
}}
QTabWidget::pane {{
    border: 1px solid {Theme.BORDER};
    border-radius: 14px;
    top: -1px;
    background: {Theme.PANEL};
}}
QTabBar::tab {{
    background: #111827;
    color: #9FB2D8;
    border: 1px solid rgba(119, 147, 196, 0.22);
    padding: 9px 20px;
    margin-right: 6px;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
    font-weight: 700;
}}
QTabBar::tab:selected {{
    background: #1A2A44;
    color: #FFFFFF;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 9px;
}}
QScrollBar::handle:vertical {{
    background: rgba(145,164,199,0.28);
    border-radius: 4px;
    min-height: 40px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""


def ui_label(text, size=13, bold=False, muted=False):
    w = QLabel(text)
    w.setFont(QFont("Microsoft YaHei UI", size, QFont.Bold if bold else QFont.Normal))
    if muted:
        w.setProperty("muted", True)
    return w


class GlowButton(QPushButton):
    def __init__(self, text, primary=False, danger=False, ghost=False):
        super().__init__(text)
        self.setCursor(Qt.PointingHandCursor)
        if primary:
            self.setProperty("primary", True)
            eff = QGraphicsDropShadowEffect(self)
            eff.setColor(QColor(49, 168, 255, 90))
            eff.setBlurRadius(22)
            eff.setOffset(0, 8)
            self.setGraphicsEffect(eff)
        if danger:
            self.setProperty("danger", True)
        if ghost:
            self.setProperty("ghost", True)


class Pill(QLabel):
    def __init__(self, text, color=Theme.BLUE):
        super().__init__(text)
        c = QColor(color)
        self.setAlignment(Qt.AlignCenter)
        self.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        self.setStyleSheet(f"""
        QLabel {{
            color: white;
            background: rgba({c.red()}, {c.green()}, {c.blue()}, 0.18);
            border: 1px solid rgba({c.red()}, {c.green()}, {c.blue()}, 0.45);
            border-radius: 11px;
            padding: 3px 8px;
        }}
        """)


class ProPanel(QFrame):
    def __init__(self, title, subtitle="", actions=None):
        super().__init__()
        self.setProperty("panel", True)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 13, 14, 14)
        root.setSpacing(10)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(ui_label(title, 13, True))
        if subtitle:
            titles.addWidget(ui_label(subtitle, 11, False, True))
        header.addLayout(titles, 1)
        for a in actions or []:
            header.addWidget(a)
        root.addLayout(header)
        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        root.addLayout(self.body, 1)


class SegmentedControl(QFrame):
    changed = Signal(str)

    def __init__(self, items, current=0):
        super().__init__()
        self.items = items
        self.setStyleSheet(f"""
        QFrame {{
            background: #080E17;
            border: 1px solid {Theme.BORDER};
            border-radius: 12px;
        }}
        QPushButton {{
            background: transparent;
            border: none;
            border-radius: 9px;
            color: {Theme.MUTED};
            padding: 7px 12px;
        }}
        QPushButton:checked {{
            background: #1B2A44;
            color: #FFFFFF;
        }}
        """)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        for i, t in enumerate(items):
            b = QPushButton(t)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setChecked(i == current)
            self.group.addButton(b, i)
            lay.addWidget(b)
        self.group.idClicked.connect(lambda idx: self.changed.emit(self.items[idx]))

    def current_text(self):
        idx = self.group.checkedId()
        return self.items[idx] if 0 <= idx < len(self.items) else self.items[0]

    def set_current_text(self, text):
        for b in self.group.buttons():
            if b.text() == text:
                b.setChecked(True)
                return


@dataclass
class AssetItem:
    tag: str
    path: str
    kind: str
    display_name: str = ""
    note: str = ""
    detection: Dict[str, Any] = field(default_factory=dict)
    used: int = 0


class AssetPromptEdit(QTextEdit):
    def __init__(self, asset_getter, parent=None):
        super().__init__(parent)
        self.asset_getter = asset_getter
        self.setAcceptDrops(True)
        self.setAcceptRichText(False)
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        self.setTabChangesFocus(False)

    def icon_for_asset(self, a):
        if getattr(a, "kind", "") == "video": return "🎞"
        if getattr(a, "kind", "") == "image": return "🖼"
        if getattr(a, "kind", "") == "audio": return "♪"
        return "◆"

    def chip_text_for_asset(self, a):
        return f"{self.icon_for_asset(a)} {a.tag}"

    def chip_resource_name(self, a):
        return f"mojing-chip://{a.tag}"

    def make_chip_pixmap(self, a):
        tag = getattr(a, "tag", "素材")
        label = f"{self.icon_for_asset(a)} {tag}"
        fm = QFont("Microsoft YaHei UI", 10, QFont.Bold)
        tmp = QPixmap(1, 1)
        painter = QPainter(tmp)
        painter.setFont(fm)
        width = max(70, painter.fontMetrics().horizontalAdvance(label) + 24)
        painter.end()

        height = 26
        pix = QPixmap(width, height)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(fm)

        if getattr(a, "kind", "") == "video":
            bg = QColor("#1D4F78"); border = QColor("#3AA2FF")
        elif getattr(a, "kind", "") == "image":
            bg = QColor("#174E5D"); border = QColor("#39D5FF")
        elif getattr(a, "kind", "") == "audio":
            bg = QColor("#5A3E12"); border = QColor("#F4B65F")
        else:
            bg = QColor("#293247"); border = QColor("#91A4C7")

        p.setPen(border)
        p.setBrush(bg)
        p.drawRoundedRect(0, 0, width - 1, height - 1, 9, 9)
        p.setPen(QColor("#FFFFFF"))
        p.drawText(10, 18, label)
        p.end()
        return pix

    def register_chip_resource(self, a):
        name = self.chip_resource_name(a)
        self.document().addResource(QTextDocument.ImageResource, QUrl(name), self.make_chip_pixmap(a))
        return name

    def api_prompt_text(self):
        out = []
        doc = self.document()
        block = doc.begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                if frag.isValid():
                    fmt = frag.charFormat()
                    if fmt.isImageFormat():
                        img = fmt.toImageFormat()
                        name = img.name()
                        if name.startswith("mojing-chip://"):
                            tag = name.replace("mojing-chip://", "", 1)
                            out.append(f"[@{tag}]")
                        else:
                            out.append(frag.text())
                    else:
                        out.append(frag.text())
                it += 1
            if block.next().isValid():
                out.append("\n")
            block = block.next()

        txt = "".join(out)
        for a in self.asset_getter() or []:
            txt = txt.replace(self.chip_text_for_asset(a), f"[@{a.tag}]")
        return txt

    def show_asset_popup(self):
        menu = QMenu(self)
        menu.setStyleSheet(APP_QSS)
        assets = list(self.asset_getter() or [])
        if not assets:
            act = QAction("暂无素材：请先拖入或导入素材", self)
            act.setEnabled(False)
            menu.addAction(act)
        else:
            for a in assets:
                label = f"{self.icon_for_asset(a)}  {a.tag}    {a.display_name or a.path}"
                act = QAction(label, self)
                act.triggered.connect(lambda _=False, aa=a: self.insert_asset_chip(aa))
                menu.addAction(act)
        rect = self.cursorRect()
        menu.exec(self.mapToGlobal(rect.bottomLeft()))

    def insert_asset_chip(self, a):
        cursor = self.textCursor()
        name = self.register_chip_resource(a)
        fmt = QTextImageFormat()
        fmt.setName(name)
        fmt.setWidth(self.make_chip_pixmap(a).width())
        fmt.setHeight(self.make_chip_pixmap(a).height())
        cursor.insertImage(fmt)
        cursor.insertText(" ")

        normal_fmt = QTextCharFormat()
        normal_fmt.setForeground(QColor("#EAF2FF"))
        normal_fmt.setBackground(Qt.transparent)
        normal_fmt.setFontWeight(QFont.Normal)
        self.setTextCursor(cursor)
        self.setCurrentCharFormat(normal_fmt)
        self.textChanged.emit()

    def asset_by_tag(self, tag):
        for a in self.asset_getter() or []:
            if getattr(a, "tag", "") == tag:
                return a
        return None

    def canInsertFromMimeData(self, source):
        if source.hasFormat("application/x-mojing-asset-tag"): return True
        if source.hasText(): return True
        return False

    def insertFromMimeData(self, source):
        if source.hasFormat("application/x-mojing-asset-tag"):
            tag = bytes(source.data("application/x-mojing-asset-tag")).decode("utf-8", errors="ignore")
            asset = self.asset_by_tag(tag)
            if asset:
                self.insert_asset_chip(asset)
            return
        if source.hasText():
            self.insertPlainText(source.text())
            return

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-mojing-asset-tag"):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-mojing-asset-tag"):
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-mojing-asset-tag"):
            tag = bytes(event.mimeData().data("application/x-mojing-asset-tag")).decode("utf-8", errors="ignore")
            asset = self.asset_by_tag(tag)
            if asset:
                try:
                    pos = event.position().toPoint()
                except Exception:
                    pos = event.pos()
                cursor = self.cursorForPosition(pos)
                self.setTextCursor(cursor)
                self.insert_asset_chip(asset)
                event.acceptProposedAction()
                return
        event.ignore()

    def keyPressEvent(self, event):
        if event.text() == "@":
            self.show_asset_popup()
            return
        if event.text():
            normal_fmt = QTextCharFormat()
            normal_fmt.setForeground(QColor("#EAF2FF"))
            normal_fmt.setBackground(Qt.transparent)
            normal_fmt.setFontWeight(QFont.Normal)
            self.setCurrentCharFormat(normal_fmt)
        super().keyPressEvent(event)


class AssetCard(QFrame):
    clicked = Signal(object)
    request_menu = Signal(object)

    def __init__(self, asset: AssetItem, thumb_w=92):
        super().__init__()
        self.asset = asset
        self.thumb_w = int(thumb_w)
        self.thumb_h = max(56, int(self.thumb_w * 0.62))
        self.setMinimumHeight(max(82, self.thumb_h + 22))
        self._drag_start_pos = None
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda _pos: self.request_menu.emit(self))
        self.setStyleSheet(f"""
        QFrame {{ background: {Theme.SURFACE_2}; border: 1px solid {Theme.BORDER}; border-radius: 14px; }}
        QFrame:hover {{ border-color: {Theme.BORDER_HI}; background: #142036; }}
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        self.thumb = QLabel()
        self.thumb.setFixedSize(self.thumb_w, self.thumb_h)
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setStyleSheet("background:#09111D; border-radius:10px; color:#91A4C7; font-weight:800;")
        self.thumb.setPixmap(self.make_asset_thumb(self.thumb_w, self.thumb_h))
        lay.addWidget(self.thumb)

        info = QVBoxLayout()
        info.setSpacing(3)
        top = QHBoxLayout()
        top.addWidget(ui_label(self.asset.tag, 12, True))
        top.addStretch()
        type_text = {"video": "视频", "image": "图片", "audio": "音频"}.get(self.asset.kind, "素材")
        top.addWidget(Pill(type_text, Theme.BLUE if self.asset.kind == "video" else (Theme.CYAN if self.asset.kind == "image" else Theme.AMBER)))
        info.addLayout(top)

        name = self.asset.display_name or (os.path.basename(self.asset.path) if not str(self.asset.path).startswith(("http://", "https://", "asset://")) else short_url_label(self.asset.path, 42))
        info.addWidget(ui_label(name, 11, False, True))

        src = "URL素材" if str(self.asset.path).startswith(("http://", "https://", "asset://")) else "本地素材"
        risk = "｜风险链接" if isinstance(self.asset.detection, dict) and self.asset.detection.get("risk") else ""
        info.addWidget(ui_label(f"{src}{risk}", 10, False, True))

        used = f"已引用 {self.asset.used}" if self.asset.used else "未引用"
        used_label = ui_label(used, 10, True)
        used_label.setStyleSheet("color:#42D392;" if self.asset.used else "color:#F8B84E;")
        info.addWidget(used_label)

        lay.addLayout(info, 1)

    def make_asset_thumb(self, width, height):
        path = self.asset.path or ""
        kind = self.asset.kind or asset_kind(path)
        if kind == "image" and isinstance(path, str) and os.path.isfile(path):
            pix = QPixmap(path)
            if not pix.isNull():
                return pix.scaled(width, height, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        if kind == "video" and isinstance(path, str) and os.path.isfile(path):
            return video_first_frame(path, width, height)
        if isinstance(path, str) and path.startswith(("http://", "https://")):
            return remote_pixmap(path, width, height, kind)
        if isinstance(path, str) and path.startswith("asset://"):
            preview = ""
            if isinstance(self.asset.detection, dict):
                preview = self.asset.detection.get("preview", "")
            if preview:
                if os.path.isfile(str(preview)):
                    pix = QPixmap(str(preview))
                    if not pix.isNull():
                        return pix.scaled(width, height, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                if str(preview).startswith(("http://", "https://")):
                    return remote_pixmap(preview, width, height, "image")
            return make_placeholder_pixmap("video" if kind == "video" else ("image" if kind == "image" else "audio"), width, height)
        return make_placeholder_pixmap("audio" if kind == "audio" else ("image" if kind == "image" else "video"), width, height)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            try:
                self._drag_start_pos = event.position().toPoint()
            except Exception:
                self._drag_start_pos = event.pos()
        self.clicked.emit(self)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton): return super().mouseMoveEvent(event)
        if self._drag_start_pos is None: return super().mouseMoveEvent(event)
        try: pos = event.position().toPoint()
        except Exception: pos = event.pos()
        if (pos - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance(): return super().mouseMoveEvent(event)

        mime = QMimeData()
        mime.setData("application/x-mojing-asset-tag", self.asset.tag.encode("utf-8"))
        mime.setText(f"[@{self.asset.tag}]")

        drag = QDrag(self)
        drag.setMimeData(mime)
        pix = self.thumb.pixmap()
        if pix and not pix.isNull():
            drag.setPixmap(pix.scaled(80, 54, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        drag.exec(Qt.CopyAction)


class ResultCard(QFrame):
    clicked = Signal(object)
    double_clicked = Signal(object)
    request_menu = Signal(object)

    def __init__(self, path, thumb_w=88):
        super().__init__()
        self.path = path
        self.meta = load_sidecar(path)
        self.thumb_w = int(thumb_w)
        self.thumb_h = max(46, int(self.thumb_w * 0.68))
        self.setFixedHeight(max(90, self.thumb_h + 28))
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
        QFrame {{ background: {Theme.SURFACE_2}; border: 1px solid {Theme.BORDER}; border-radius: 14px; }}
        QFrame:hover {{ border-color: {Theme.BORDER_HI}; background: #142036; }}
        """)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda _pos: self.request_menu.emit(self))

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 10, 12, 10)
        lay.setSpacing(10)

        thumb = QLabel()
        thumb.setAlignment(Qt.AlignCenter)
        thumb.setFixedSize(self.thumb_w, self.thumb_h)
        if path.lower().endswith(IMAGE_EXTS):
            pix = QPixmap(path)
            if not pix.isNull():
                thumb.setPixmap(pix.scaled(self.thumb_w, self.thumb_h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                thumb.setText("IMAGE")
        else:
            thumb.setPixmap(video_first_frame(path, self.thumb_w, self.thumb_h))
        thumb.setStyleSheet("background:#0A101A; border-radius:10px; color:white; font-weight:800;")
        lay.addWidget(thumb)

        info = QVBoxLayout()
        f = os.path.basename(path)
        if len(f) > 32: f = f[:31] + "..."
        info.addWidget(ui_label(f, 12, True))
        elapsed = self.meta.get("elapsed_seconds")
        e = f"｜用时 {int(elapsed)}s" if isinstance(elapsed, (int, float)) else ""
        info.addWidget(ui_label(f"{time.strftime('%m-%d %H:%M', time.localtime(os.path.getmtime(path)))}{e}", 11, False, True))
        cost = estimate_cost(self.meta) if self.meta else "暂无元数据"
        info.addWidget(ui_label(cost[:48], 10, False, True))
        lay.addLayout(info, 1)

    def mousePressEvent(self, event):
        self.clicked.emit(self)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit(self)
        super().mouseDoubleClickEvent(event)


class InspectorRow(QWidget):
    def __init__(self, name, widget):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)
        lay.addWidget(ui_label(name, 11, True, True))
        lay.addWidget(widget)


