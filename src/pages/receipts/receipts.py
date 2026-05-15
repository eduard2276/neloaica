"""Receipts page - Table list of receipts with create/edit/delete via browser-like tabs."""

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.database.models.receipts import delete_receipt, get_all_receipts
from src.styles import theme
from src.widgets import NoScrollComboBox

from .receipt_form import ReceiptFormPage


class ReceiptsPage(QWidget):
    """Receipts page with a pinned list tab and dynamic form tabs."""

    def __init__(self):
        super().__init__()
        self.all_receipts = []
        self.active_status_filter = "All"
        self._open_receipt_tabs = {}
        self._next_new_counter = 0
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """Setup the receipts page with a QTabWidget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(theme.tab_widget())
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self._on_tab_close_requested)

        # --- Tab 0: Receipts list (pinned, not closable) ---
        self.list_page = QWidget()
        self._setup_list_page()
        self.tab_widget.addTab(self.list_page, "📋 Receipts List")

        # Hide the close button on the pinned list tab
        self.tab_widget.tabBar().setTabButton(
            0, self.tab_widget.tabBar().ButtonPosition.RightSide, None
        )

        layout.addWidget(self.tab_widget)

    def _setup_list_page(self):
        """Build the receipt list (table) page."""
        layout = QVBoxLayout(self.list_page)
        layout.setSpacing(20)

        header_layout = QHBoxLayout()
        title = QLabel("🧾 Receipts")
        title.setStyleSheet(theme.page_title())
        header_layout.addWidget(title)
        layout.addLayout(header_layout)

        toolbar_layout = QHBoxLayout()

        search_label = QLabel("🔍")
        search_label.setStyleSheet("font-size: 18px;")
        toolbar_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search receipts by client name...")
        self.search_input.setStyleSheet(theme.search_input())
        self.search_input.textChanged.connect(self.filter_receipts)
        toolbar_layout.addWidget(self.search_input)

        toolbar_layout.addSpacing(20)

        add_btn = QPushButton("➕ New Receipt")
        add_btn.setStyleSheet(theme.button("success"))
        add_btn.clicked.connect(self.create_new_receipt)
        toolbar_layout.addWidget(add_btn)

        self.filter_btn = QPushButton("🔽 Filters")
        self.filter_btn.setStyleSheet(theme.button("gray"))
        self.filter_btn.clicked.connect(self.open_filter_dialog)
        toolbar_layout.addWidget(self.filter_btn)

        toolbar_layout.addSpacing(20)

        sort_label = QLabel("Sort:")
        sort_label.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #555; margin-right: 2px;"
        )
        toolbar_layout.addWidget(sort_label)

        self.sort_combo = NoScrollComboBox()
        for opt in [
            "Date: Newest first",
            "Date: Oldest first",
            "Grand Total: High to low",
            "Grand Total: Low to high",
            "Client: A to Z",
            "Client: Z to A",
        ]:
            self.sort_combo.addItem(opt)
        self.sort_combo.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 28px 6px 10px;
                font-size: 13px;
                color: #2c3e50;
                min-height: 28px;
                min-width: 190px;
            }
            QComboBox:hover {
                border-color: #3498db;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #bdc3c7;
                color: #2c3e50;
                selection-background-color: #3498db;
                selection-color: #ffffff;
                padding: 2px;
            }
        """)
        self.sort_combo.currentIndexChanged.connect(self.apply_filters)
        toolbar_layout.addWidget(self.sort_combo)

        layout.addLayout(toolbar_layout)

        self.filter_indicator = QLabel()
        self.filter_indicator.setStyleSheet(
            "color: #e67e22; font-weight: bold; font-size: 13px; padding: 2px 0;"
        )
        self.filter_indicator.setVisible(False)
        layout.addWidget(self.filter_indicator)

        self.receipts_table = QTableWidget()
        self.receipts_table.setStyleSheet(theme.table())
        self.receipts_table.setAlternatingRowColors(True)
        self.receipts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.receipts_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.receipts_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.receipts_table.verticalHeader().setVisible(False)
        self.receipts_table.verticalHeader().setDefaultSectionSize(50)
        self.receipts_table.setColumnCount(7)
        self.receipts_table.setHorizontalHeaderLabels(
            [
                "ID",
                "Client",
                "Car",
                "Date",
                "Grand Total",
                "Status",
                "Actions",
            ]
        )
        self.receipts_table.doubleClicked.connect(self._on_table_double_click)

        layout.addWidget(self.receipts_table)

    def showEvent(self, event):
        """Reload data when the page becomes visible."""
        super().showEvent(event)
        if self.tab_widget.currentIndex() == 0:
            self.load_data()

    # ==================== Data / Filtering ====================

    def load_data(self):
        """Load receipts from the database."""
        self.all_receipts = get_all_receipts()
        self.apply_filters()

    def apply_filters(self):
        """Apply both search text and status filters."""
        search_text = self.search_input.text().lower().strip()
        filtered = self.all_receipts

        if self.active_status_filter != "All":
            filtered = [
                r for r in filtered if r.get("status", "Ongoing") == self.active_status_filter
            ]

        if search_text:
            filtered = [
                r
                for r in filtered
                if search_text in r.get("client_name", "").lower()
                or search_text in r.get("car_model", "").lower()
            ]

        # Sort according to the selected option in sort_combo.
        sort_text = (
            self.sort_combo.currentText() if hasattr(self, "sort_combo") else "Date: Newest first"
        )

        if sort_text.startswith("Date:"):
            descending = sort_text == "Date: Newest first"
            invalid_sentinel = datetime.min if descending else datetime.max

            def _date_key(r):
                try:
                    return datetime.strptime(r.get("date", ""), "%d.%m.%Y")
                except ValueError:
                    return invalid_sentinel

            filtered = sorted(filtered, key=_date_key, reverse=descending)

        elif sort_text == "Grand Total: High to low":
            filtered = sorted(
                filtered,
                key=lambda r: float(r.get("grand_total") or 0),
                reverse=True,
            )
        elif sort_text == "Grand Total: Low to high":
            filtered = sorted(
                filtered,
                key=lambda r: float(r.get("grand_total") or 0),
            )
        elif sort_text == "Client: A to Z":
            filtered = sorted(
                filtered,
                key=lambda r: r.get("client_name", "").lower(),
            )
        elif sort_text == "Client: Z to A":
            filtered = sorted(
                filtered,
                key=lambda r: r.get("client_name", "").lower(),
                reverse=True,
            )

        self.display_receipts(filtered)

    def filter_receipts(self, _search_text: str):
        """Called when the search input changes."""
        self.apply_filters()

    def open_filter_dialog(self):
        """Open the filter popup dialog."""
        dialog = FilterDialog(self, self.active_status_filter)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.active_status_filter = dialog.get_selected_status()
            self._update_filter_indicator()
            self.apply_filters()

    def _update_filter_indicator(self):
        """Show or hide the active filter indicator below the toolbar."""
        if self.active_status_filter == "All":
            self.filter_indicator.setVisible(False)
            self.filter_btn.setStyleSheet(theme.button("gray"))
        else:
            self.filter_indicator.setText(f"Filtering by status: {self.active_status_filter}")
            self.filter_indicator.setVisible(True)
            self.filter_btn.setStyleSheet(theme.button("primary"))

    def display_receipts(self, receipts: list):
        """Display receipts in the table."""
        self.receipts_table.setRowCount(len(receipts))

        for row, receipt in enumerate(receipts):
            receipt_id = receipt["id"]

            id_item = QTableWidgetItem(str(receipt_id))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            id_item.setData(Qt.ItemDataRole.UserRole, receipt_id)
            self.receipts_table.setItem(row, 0, id_item)

            self.receipts_table.setItem(row, 1, QTableWidgetItem(receipt.get("client_name", "")))
            self.receipts_table.setItem(row, 2, QTableWidgetItem(receipt.get("car_model", "")))
            self.receipts_table.setItem(row, 3, QTableWidgetItem(receipt.get("date", "")))

            grand_total = receipt.get("grand_total", 0.0)
            total_item = QTableWidgetItem(f"{self._format_price(grand_total)} Lei")
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.receipts_table.setItem(row, 4, total_item)

            status = receipt.get("status", "Ongoing")
            color = "#27ae60" if status == "Done" else "#e67e22"
            status_label = QLabel(status)
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_label.setStyleSheet(
                f"color: {color}; font-weight: bold; font-size: 14px;"
                " background-color: transparent;"
            )
            self.receipts_table.setCellWidget(row, 5, status_label)

            actions_widget = QWidget()
            actions_widget.setStyleSheet("background-color: transparent;")
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 0, 2, 0)
            actions_layout.setSpacing(5)

            edit_btn = QPushButton("✏️")
            edit_btn.setStyleSheet(theme.button_icon("edit"))
            edit_btn.setToolTip("Edit receipt")
            edit_btn.clicked.connect(lambda checked, rid=receipt_id: self.edit_receipt(rid))
            actions_layout.addWidget(edit_btn)

            delete_btn = QPushButton("🗑️")
            delete_btn.setStyleSheet(theme.button_icon("delete"))
            delete_btn.setToolTip("Delete receipt")
            delete_btn.clicked.connect(
                lambda checked, rid=receipt_id: self.delete_receipt_by_id(rid)
            )
            actions_layout.addWidget(delete_btn)

            self.receipts_table.setCellWidget(row, 6, actions_widget)

        header = self.receipts_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.receipts_table.setColumnWidth(6, 100)

    # ==================== Tab Management ====================

    def _make_tab_key(self, receipt_id=None):
        """Create a unique key for tracking open tabs."""
        if receipt_id is not None:
            return f"edit:{receipt_id}"
        self._next_new_counter += 1
        return f"new:{self._next_new_counter}"

    def _open_form_tab(self, receipt_id=None):
        """Open a new form tab or switch to an existing one for the given receipt_id."""
        if receipt_id is not None:
            existing_key = f"edit:{receipt_id}"
            if existing_key in self._open_receipt_tabs:
                tab_index = self.tab_widget.indexOf(self._open_receipt_tabs[existing_key])
                if tab_index != -1:
                    self.tab_widget.setCurrentIndex(tab_index)
                    return
                del self._open_receipt_tabs[existing_key]

        form = ReceiptFormPage()
        key = self._make_tab_key(receipt_id)
        self._open_receipt_tabs[key] = form

        form.receipt_saved.connect(self.load_data)
        form.close_requested.connect(lambda f=form: self._close_form_tab(f))
        form.tab_title_changed.connect(lambda title, f=form: self._update_tab_title(f, title))
        form.receipt_id_assigned.connect(lambda rid, k=key, f=form: self._remap_tab_key(k, rid, f))

        if receipt_id is not None:
            receipt = next((r for r in self.all_receipts if r["id"] == receipt_id), None)
            client_name = receipt.get("client_name", "") if receipt else ""
            tab_title = f"Receipt #{receipt_id}"
            if client_name:
                tab_title += f" - {client_name}"
            form.load_for_edit(receipt_id)
        else:
            tab_title = "New Receipt"
            form.load_for_new()

        tab_index = self.tab_widget.addTab(form, tab_title)
        self.tab_widget.setCurrentIndex(tab_index)

    def _update_tab_title(self, form_widget, title: str):
        """Update the tab text for a given form widget."""
        tab_index = self.tab_widget.indexOf(form_widget)
        if tab_index != -1:
            self.tab_widget.setTabText(tab_index, title)

    def _remap_tab_key(self, old_key: str, receipt_id: int, form_widget):
        """Remap a 'new:N' key to 'edit:<id>' once a receipt has been saved to the DB."""
        if old_key in self._open_receipt_tabs:
            del self._open_receipt_tabs[old_key]
        self._open_receipt_tabs[f"edit:{receipt_id}"] = form_widget

    def _close_form_tab(self, form_widget):
        """Close the tab containing the given form widget."""
        tab_index = self.tab_widget.indexOf(form_widget)
        if tab_index != -1:
            self._on_tab_close_requested(tab_index)

    def _on_tab_close_requested(self, index: int):
        """Handle a tab close request. Prevent closing the pinned list tab."""
        if index == 0:
            return

        widget = self.tab_widget.widget(index)

        if isinstance(widget, ReceiptFormPage) and widget.has_unsaved_changes:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Unsaved Changes")
            msg_box.setText(
                "This receipt has unsaved changes.\n" "Are you sure you want to close it?"
            )
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            msg_box.setDefaultButton(QMessageBox.StandardButton.No)
            msg_box.setStyleSheet(theme.message_box_confirm())
            if msg_box.exec() != QMessageBox.StandardButton.Yes:
                return

        keys_to_remove = [k for k, v in self._open_receipt_tabs.items() if v is widget]
        for k in keys_to_remove:
            del self._open_receipt_tabs[k]

        self.tab_widget.removeTab(index)
        widget.deleteLater()

        if self.tab_widget.count() == 1:
            self.tab_widget.setCurrentIndex(0)
            self.load_data()

    # ==================== Actions ====================

    def create_new_receipt(self):
        """Open a new form tab for creating a receipt."""
        self._open_form_tab()

    def edit_receipt(self, receipt_id: int):
        """Open or switch to the form tab for editing an existing receipt."""
        self._open_form_tab(receipt_id)

    def _on_table_double_click(self):
        """Handle double-click on a table row."""
        selected = self.receipts_table.selectionModel().selectedRows()
        if not selected:
            return
        row = selected[0].row()
        receipt_id = self.receipts_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.edit_receipt(receipt_id)

    def delete_receipt_by_id(self, receipt_id: int):
        """Delete a receipt after confirmation."""
        receipt = next((r for r in self.all_receipts if r["id"] == receipt_id), None)
        if not receipt:
            return

        client_name = receipt.get("client_name", "Unknown")
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Delete")
        msg_box.setText(
            f"Are you sure you want to delete receipt #{receipt_id} " f"for {client_name}?"
        )
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.setStyleSheet(theme.message_box_confirm())

        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            existing_key = f"edit:{receipt_id}"
            if existing_key in self._open_receipt_tabs:
                tab_index = self.tab_widget.indexOf(self._open_receipt_tabs[existing_key])
                if tab_index != -1:
                    self._on_tab_close_requested(tab_index)

            delete_receipt(receipt_id)
            self.load_data()

    # ==================== Utilities ====================

    @staticmethod
    def _format_price(value) -> str:
        """Format a number with thousand separators."""
        try:
            num = float(value)
        except (ValueError, TypeError):
            return "0.00"
        integer_part = int(num)
        decimal_part = f"{num:.2f}".split(".")[1]
        formatted = ""
        int_str = str(integer_part)
        for i, d in enumerate(reversed(int_str)):
            if i > 0 and i % 3 == 0:
                formatted = " " + formatted
            formatted = d + formatted
        return f"{formatted}.{decimal_part}"


class FilterDialog(QDialog):
    """Popup dialog for receipt filters."""

    STATUS_OPTIONS = ["All", "Ongoing", "Done"]

    def __init__(self, parent=None, current_status: str = "All"):
        super().__init__(parent)
        self.setWindowTitle("Filter Receipts")
        self.setMinimumWidth(350)
        self.setStyleSheet(theme.dialog() + theme.line_edit_dialog())
        self._build_ui(current_status)

    def _build_ui(self, current_status: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.status_combo = NoScrollComboBox()
        self.status_combo.setStyleSheet(theme.combobox())
        for option in self.STATUS_OPTIONS:
            self.status_combo.addItem(option)
        idx = (
            self.STATUS_OPTIONS.index(current_status)
            if current_status in self.STATUS_OPTIONS
            else 0
        )
        self.status_combo.setCurrentIndex(idx)
        form_layout.addRow("Status:", self.status_combo)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        clear_btn = QPushButton("Clear Filters")
        clear_btn.setStyleSheet(theme.button("cancel"))
        clear_btn.clicked.connect(self._clear_filters)
        btn_layout.addWidget(clear_btn)

        apply_btn = QPushButton("Apply")
        apply_btn.setStyleSheet(theme.button("primary"))
        apply_btn.clicked.connect(self.accept)
        btn_layout.addWidget(apply_btn)

        layout.addLayout(btn_layout)

    def _clear_filters(self):
        """Reset all filters to defaults and accept."""
        self.status_combo.setCurrentIndex(0)
        self.accept()

    def get_selected_status(self) -> str:
        """Return the currently selected status option."""
        return self.status_combo.currentText()
