from ..common import *
from .widgets import *

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SeedanceV5Workbench()
    win.show()
    sys.exit(app.exec())
