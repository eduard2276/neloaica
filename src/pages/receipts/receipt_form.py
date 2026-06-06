"""Receipt form page - Create or edit a receipt."""

import re

from PySide6.QtCore import QDate, QSize, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.database.models.cars import update_car_kilometers
from src.database.models.receipts import (
    add_receipt,
    get_receipt_by_id,
    get_receipt_by_plate_and_date,
    update_receipt,
)
from src.services import create_backup, generate_receipt_excel, template_exists
from src.styles import theme
from src.utils import show_critical, show_info, show_warning

from .billable_parts_section import BillablePartsSectionWidget
from .defects_section import DefectsSectionWidget
from .estimates_section import EstimatesSectionWidget
from .labor_section import LaborSectionWidget
from .parts_section import PartsSectionWidget
from .receipt_info import ReceiptInfoWidget

# --- Text-zoom support ------------------------------------------------------
# The receipt is a long form and a single job can carry a lot of data, so the
# user can scale the whole form up or down. Widget stylesheets hard-code their
# sizes in pixels, so a parent font would not cascade onto them; instead we
# rewrite every ``px`` dimension (font-size, padding, margin, min-height,
# border, ...) of the form's widgets on the fly. Scaling padding/margins too -
# not just the font - is what actually lets more rows fit on screen.

ZOOM_MIN = 0.5
ZOOM_MAX = 2.0
ZOOM_STEP = 0.1

# Compact style for the A- / A+ zoom buttons. The shared theme button has
# large horizontal padding which, at a fixed 44px width, clips the label to
# nothing - so these get their own zero-padding style with a big bold glyph.
_ZOOM_BTN_QSS = """
    QPushButton {
        background-color: #95a5a6;
        color: white;
        border: none;
        border-radius: 6px;
        font-size: 20px;
        font-weight: bold;
        padding: 0px;
    }
    QPushButton:hover { background-color: #7f8c8d; }
    QPushButton:pressed { background-color: #707b7c; }
"""

_PX_RE = re.compile(r"(\d+(?:\.\d+)?)px")

# Custom item-data role used to remember a list row's unscaled height so we
# can always derive the zoomed height from the original baseline.
_ROW_BASE_H_ROLE = int(Qt.ItemDataRole.UserRole) + 137

# Receipt sections that render rows in a QListWidget and expose ``_resize_list``.
_LIST_SECTION_ATTRS = (
    "defects_widget",
    "discovered_defects_widget",
    "parts_widget",
    "labor_widget",
    "billable_parts_widget",
)


def scale_pixel_sizes(qss: str, scale: float) -> str:
    """Return ``qss`` with every ``Npx`` dimension multiplied by ``scale``.

    This covers font-size, padding, margin, min-height, border width, etc., so
    scaling down actually compresses the layout (more rows on screen) instead
    of just shrinking the text. Sizes never drop below 1px. A stylesheet with
    no ``px`` value is returned unchanged. Pure helper - unit-testable without
    Qt.
    """
    if not qss:
        return qss

    def _repl(match: "re.Match") -> str:
        scaled = float(match.group(1)) * scale
        return f"{max(1, round(scaled))}px"

    return _PX_RE.sub(_repl, qss)


class ReceiptFormPage(QWidget):
    """Form page for creating or editing a receipt."""

    close_requested = Signal()
    receipt_saved = Signal()
    tab_title_changed = Signal(str)
    receipt_id_assigned = Signal(int)  # fired once when a new receipt gets its DB id

    def __init__(self):
        super().__init__()
        self.receipt_data = {}
        self.editing_receipt_id = None
        self._dirty = False
        self._font_scale = 1.0
        # Zoom controls are excluded from scaling so they stay a fixed size.
        self._zoom_chrome: set = set()
        self.setup_ui()

        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.on_save_clicked)

        for seq, slot in (
            ("Ctrl++", self.zoom_in),
            ("Ctrl+=", self.zoom_in),
            ("Ctrl+-", self.zoom_out),
            ("Ctrl+0", self.zoom_reset),
        ):
            shortcut = QShortcut(QKeySequence(seq), self)
            shortcut.activated.connect(slot)

    def setup_ui(self):
        """Setup the receipt form UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_layout = QHBoxLayout()

        self.title_label = QLabel("🧾 New Receipt")
        self.title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()
        self._build_zoom_controls(header_layout)
        content_layout.addLayout(header_layout)

        # Receipt information section
        self.receipt_info_widget = ReceiptInfoWidget()
        self.receipt_info_widget.data_changed.connect(self.on_receipt_info_changed)
        content_layout.addWidget(self.receipt_info_widget)

        # Estimates section
        self.estimates_widget = EstimatesSectionWidget("Estimates")
        self.estimates_widget.estimates_changed.connect(self.on_estimates_changed)
        content_layout.addWidget(self.estimates_widget)
        self.on_estimates_changed(
            self.estimates_widget.get_estimate_cost(),
            self.estimates_widget.get_estimated_final_date(),
        )

        # Defects section
        self.defects_widget = DefectsSectionWidget("Defects by the Client")
        self.defects_widget.defects_changed.connect(self.on_defects_changed)
        content_layout.addWidget(self.defects_widget)

        # Discovered Defects section
        self.discovered_defects_widget = DefectsSectionWidget("Discovered Defects")
        self.discovered_defects_widget.defects_changed.connect(self.on_discovered_defects_changed)
        content_layout.addWidget(self.discovered_defects_widget)

        # Parts section
        self.parts_widget = PartsSectionWidget("Parts received from client")
        self.parts_widget.parts_changed.connect(self.on_parts_changed)
        content_layout.addWidget(self.parts_widget)

        # Labor section
        self.labor_widget = LaborSectionWidget("Labor Services")
        self.labor_widget.labor_changed.connect(self.on_labor_changed)
        content_layout.addWidget(self.labor_widget)

        # Billable parts section
        self.billable_parts_widget = BillablePartsSectionWidget("Parts Used")
        self.billable_parts_widget.parts_changed.connect(self.on_billable_parts_changed)
        content_layout.addWidget(self.billable_parts_widget)

        # Grand Total section
        grand_total_group = QGroupBox("Grand Total")
        grand_total_group.setStyleSheet(theme.groupbox() + theme.form_label())
        grand_total_layout = QHBoxLayout()
        grand_total_layout.setSpacing(10)

        grand_total_label = QLabel("Total (Labor + Parts):")
        grand_total_label.setStyleSheet(theme.form_label())
        grand_total_layout.addWidget(grand_total_label)

        self.grand_total_value = QLabel("0.00 Lei")
        self.grand_total_value.setStyleSheet(theme.form_label())
        grand_total_layout.addWidget(self.grand_total_value)

        grand_total_layout.addStretch()
        grand_total_group.setLayout(grand_total_layout)
        content_layout.addWidget(grand_total_group)

        # Buttons section
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 20, 0, 0)
        button_layout.addStretch()

        self.reset_button = QPushButton("🔄 Reset Form")
        self.reset_button.setStyleSheet(theme.button("gray"))
        self.reset_button.setMinimumHeight(50)
        self.reset_button.setMinimumWidth(180)
        self.reset_button.clicked.connect(self.on_reset_clicked)
        button_layout.addWidget(self.reset_button)

        self.save_button = QPushButton("💾 Save Receipt")
        self.save_button.setStyleSheet(theme.button("primary"))
        self.save_button.setMinimumHeight(50)
        self.save_button.setMinimumWidth(180)
        self.save_button.clicked.connect(self.on_save_clicked)
        button_layout.addWidget(self.save_button)

        self.generate_button = QPushButton("📄 Generate & Finish")
        self.generate_button.setStyleSheet(theme.button("success"))
        self.generate_button.setMinimumHeight(50)
        self.generate_button.setMinimumWidth(200)
        self.generate_button.clicked.connect(self.on_generate_clicked)
        button_layout.addWidget(self.generate_button)

        button_layout.addStretch()
        content_layout.addLayout(button_layout)

        content_layout.addStretch()

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

    # ------------------------------------------------------------------ zoom
    def _build_zoom_controls(self, header_layout: QHBoxLayout):
        """Build the text-size (zoom) controls on the right of the header."""
        caption = QLabel("Text size:")
        caption.setStyleSheet("color: #2c3e50; font-weight: bold;")
        header_layout.addWidget(caption)

        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.setStyleSheet(_ZOOM_BTN_QSS)
        self.zoom_out_btn.setFixedSize(44, 34)
        self.zoom_out_btn.setToolTip("Decrease text size (Ctrl+-)")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        header_layout.addWidget(self.zoom_out_btn)

        self.zoom_level_label = QLabel("100%")
        self.zoom_level_label.setFixedWidth(52)
        self.zoom_level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_level_label.setStyleSheet("color: #2c3e50; font-weight: bold;")
        header_layout.addWidget(self.zoom_level_label)

        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setStyleSheet(_ZOOM_BTN_QSS)
        self.zoom_in_btn.setFixedSize(44, 34)
        self.zoom_in_btn.setToolTip("Increase text size (Ctrl++)")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        header_layout.addWidget(self.zoom_in_btn)

        self.zoom_reset_btn = QPushButton("Reset")
        self.zoom_reset_btn.setStyleSheet(theme.button("gray"))
        self.zoom_reset_btn.setFixedHeight(34)
        self.zoom_reset_btn.setToolTip("Reset text size (Ctrl+0)")
        self.zoom_reset_btn.clicked.connect(self.zoom_reset)
        header_layout.addWidget(self.zoom_reset_btn)

        self._zoom_chrome = {
            caption,
            self.zoom_out_btn,
            self.zoom_level_label,
            self.zoom_in_btn,
            self.zoom_reset_btn,
        }

    def zoom_in(self):
        """Increase the receipt text size by one step."""
        self._set_font_scale(self._font_scale + ZOOM_STEP)

    def zoom_out(self):
        """Decrease the receipt text size by one step."""
        self._set_font_scale(self._font_scale - ZOOM_STEP)

    def zoom_reset(self):
        """Reset the receipt text size to 100%."""
        self._set_font_scale(1.0)

    def _set_font_scale(self, scale: float):
        """Clamp ``scale`` to the allowed range and re-apply it to the form."""
        scale = max(ZOOM_MIN, min(ZOOM_MAX, round(scale, 2)))
        self._font_scale = scale
        if hasattr(self, "zoom_level_label"):
            self.zoom_level_label.setText(f"{round(scale * 100)}%")
        self._apply_font_scale()

    def _apply_font_scale(self, only_new: bool = False):
        """Rewrite ``font-size`` of every form widget to match the zoom level.

        Each widget's original stylesheet is cached once (``_base_qss``) so the
        scaled value is always derived from the unscaled baseline. ``QListWidget``
        instances manage their own stylesheet (item count toggles the style), so
        they are skipped; their child rows are scaled instead. When ``only_new``
        is set, already-cached widgets are left untouched - used after rows are
        added so only the fresh widgets get scaled.
        """
        for w in self.findChildren(QWidget):
            if w in self._zoom_chrome or isinstance(w, QListWidget):
                continue
            base = w.property("_base_qss")
            if base is None:
                base = w.styleSheet()
                w.setProperty("_base_qss", base)
            elif only_new:
                continue
            if base and "px" in base:
                w.setStyleSheet(scale_pixel_sizes(base, self._font_scale))

        self._scale_list_rows(only_new=only_new)

    def _scale_list_rows(self, only_new: bool = False):
        """Scale the height and inner margins of every list row.

        List rows set their height (``setSizeHint``) and content margins in
        Python, not via a stylesheet, so the stylesheet rewrite cannot touch
        them - they have to be scaled here. After scaling, each section is asked
        to recompute its list height so no empty gap is left behind.
        """
        for attr in _LIST_SECTION_ATTRS:
            section = getattr(self, attr, None)
            if section is None:
                continue
            changed = False
            for lw in section.findChildren(QListWidget):
                for i in range(lw.count()):
                    if self._scale_one_row(lw, lw.item(i), only_new):
                        changed = True
            if changed and hasattr(section, "_resize_list"):
                section._resize_list()

    def _scale_one_row(self, lw: QListWidget, item, only_new: bool) -> bool:
        """Scale one list row's height + its widget margins. Returns True if touched."""
        base_h = item.data(_ROW_BASE_H_ROLE)
        if base_h is None:
            base_h = item.sizeHint().height()
            item.setData(_ROW_BASE_H_ROLE, base_h)
        elif only_new:
            return False

        sh = item.sizeHint()
        item.setSizeHint(QSize(sh.width(), max(1, round(base_h * self._font_scale))))

        widget = lw.itemWidget(item)
        if widget is not None:
            self._scale_layout_margins(widget)
        return True

    def _scale_layout_margins(self, widget: QWidget):
        """Scale a row widget's outer layout margins/spacing from their baseline."""
        layout = widget.layout()
        if layout is None:
            return
        base = widget.property("_base_margins")
        if base is None:
            m = layout.contentsMargins()
            base = (m.left(), m.top(), m.right(), m.bottom(), layout.spacing())
            widget.setProperty("_base_margins", base)
        left, top, right, bottom, spacing = base
        s = self._font_scale
        layout.setContentsMargins(
            round(left * s), round(top * s), round(right * s), round(bottom * s)
        )
        if spacing and spacing > 0:
            layout.setSpacing(max(0, round(spacing * s)))

    def _rescale_new_widgets(self):
        """Scale rows added after a zoom was applied (no-op at 100%)."""
        if self._font_scale != 1.0:
            self._apply_font_scale(only_new=True)

    def load_for_new(self):
        """Prepare the form for creating a new receipt."""
        self.editing_receipt_id = None
        self.receipt_data = {}
        self.title_label.setText("🧾 New Receipt")
        self._reload_all_data(restore_state=False)

        self.estimates_widget.estimate_cost_input.clear()
        self.estimates_widget._selected_date = QDate.currentDate()
        self.estimates_widget.date_display.setText(
            self.estimates_widget._selected_date.toString("dd.MM.yyyy")
        )
        self.estimates_widget.emit_estimates_changed()
        self.grand_total_value.setText("0.00 Lei")
        self._dirty = False

    def load_for_edit(self, receipt_id: int):
        """Load an existing receipt into the form for editing."""
        self.editing_receipt_id = receipt_id
        receipt = get_receipt_by_id(receipt_id)
        if not receipt:
            show_warning(self, "Error", "Receipt not found.")
            self.close_requested.emit()
            return

        self.title_label.setText(f"🧾 Edit Receipt #{receipt_id}")
        self.receipt_data = {}

        self.receipt_info_widget.set_data(
            {
                "client_id": receipt.get("client_id"),
                "car_id": receipt.get("car_id"),
                "kilometers": receipt.get("kilometers", ""),
                "executant_name": receipt.get("executant_name", ""),
                "date": receipt.get("date", ""),
            }
        )

        self.estimates_widget.set_data(
            receipt.get("estimate_cost", 0.0),
            receipt.get("estimated_final_date", ""),
        )

        self.defects_widget.set_data(receipt.get("defects", []))
        self.discovered_defects_widget.set_data(receipt.get("discovered_defects", []))
        self.parts_widget.set_data(receipt.get("parts", []))
        self.labor_widget.set_data(
            receipt.get("labor", []),
            receipt.get("total_labor_cost", 0.0),
        )
        self.billable_parts_widget.set_data(receipt.get("billable_parts", []))

        self.update_grand_total()
        self._dirty = False

    def _reload_all_data(self, restore_state=True):
        """Reload all section data from the database."""
        self.receipt_info_widget.load_data(restore_state=restore_state)
        self.defects_widget.load_data(restore_state=restore_state)
        self.discovered_defects_widget.load_data(restore_state=restore_state)
        self.parts_widget.load_data(restore_state=restore_state)
        self.labor_widget.load_data(restore_state=restore_state)
        self.billable_parts_widget.load_data(restore_state=restore_state)

    def showEvent(self, event):
        """Reload catalog dropdowns when the tab is switched back to this form.

        Preserves all in-progress selections (restore_state=True) so the user
        does not lose unsaved work.  This ensures that services or parts added
        in other pages appear in the combo boxes without having to open a new
        receipt tab.
        """
        super().showEvent(event)
        if hasattr(self, "labor_widget"):
            self._reload_all_data(restore_state=True)

    def on_receipt_info_changed(self, data: dict):
        """Handle receipt information data change."""
        self.receipt_data.update(data)
        self._dirty = True

    def on_defects_changed(self, defect_ids: list):
        """Handle defects list change."""
        self.receipt_data["defects"] = defect_ids
        self._dirty = True
        self._rescale_new_widgets()

    def on_estimates_changed(self, estimate_cost: float, estimated_final_date: str):
        """Handle estimates section data change."""
        self.receipt_data["estimate_cost"] = estimate_cost
        self.receipt_data["estimated_final_date"] = estimated_final_date
        self._dirty = True

    def on_discovered_defects_changed(self, defect_ids: list):
        """Handle discovered defects list change."""
        self.receipt_data["discovered_defects"] = defect_ids
        self._dirty = True
        self._rescale_new_widgets()

    def on_parts_changed(self, part_ids: list):
        """Handle parts list change."""
        self.receipt_data["parts"] = part_ids
        self._dirty = True
        self._rescale_new_widgets()

    def on_labor_changed(self, labor_ids: list, total_cost: float):
        """Handle labor list change."""
        self.receipt_data["labor"] = labor_ids
        self.receipt_data["total_labor_cost"] = total_cost
        self._dirty = True
        self.update_grand_total()
        self._rescale_new_widgets()

    def on_billable_parts_changed(self, parts_list: list, total_cost: float):
        """Handle billable parts list change."""
        self.receipt_data["billable_parts"] = parts_list
        self.receipt_data["total_parts_cost"] = total_cost
        self._dirty = True
        self.update_grand_total()
        self._rescale_new_widgets()

    def update_grand_total(self):
        """Update the grand total label (Labor + Parts)."""
        labor_cost = self.receipt_data.get("total_labor_cost", 0.0)
        parts_cost = self.receipt_data.get("total_parts_cost", 0.0)
        grand_total = labor_cost + parts_cost
        self.receipt_data["grand_total"] = grand_total
        self.grand_total_value.setText(f"{self.format_price(grand_total)} Lei")

    def format_price(self, value) -> str:
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

    def _collect_save_data(self) -> dict:
        """Collect all form data for saving."""
        data = dict(self.receipt_data)
        data["grand_total"] = data.get("total_labor_cost", 0.0) + data.get("total_parts_cost", 0.0)
        return data

    def on_save_clicked(self):
        """Save the receipt to the database without generating Excel."""
        if not self.receipt_data.get("client_id"):
            show_warning(
                self,
                "Missing Information",
                "Please select a client before saving the receipt.",
            )
            return

        plate = self.receipt_data.get("plate_number", "")
        date = self.receipt_data.get("date", "")
        existing = get_receipt_by_plate_and_date(plate, date, exclude_id=self.editing_receipt_id)
        if existing:
            show_warning(
                self,
                "Duplicate Receipt",
                f"A receipt for plate '{existing['plate_number']}' on {existing['date']} "
                f"already exists (Receipt #{existing['id']}).",
            )
            return

        data = self._collect_save_data()
        data["status"] = "Ongoing"

        if self.editing_receipt_id:
            update_receipt(self.editing_receipt_id, data)
            show_info(self, "Saved", f"Receipt #{self.editing_receipt_id} has been updated.")
        else:
            new_id = add_receipt(data)
            self.editing_receipt_id = new_id
            self.title_label.setText(f"🧾 Edit Receipt #{new_id}")
            self.receipt_id_assigned.emit(new_id)
            show_info(self, "Saved", f"Receipt #{new_id} has been created.")

        self._dirty = False
        self.receipt_saved.emit()
        self._emit_tab_title()

    def on_reset_clicked(self):
        """Reset the entire receipt form to a blank state."""
        self.receipt_data = {}
        self._reload_all_data(restore_state=False)

        self.estimates_widget.estimate_cost_input.clear()
        self.estimates_widget._selected_date = QDate.currentDate()
        self.estimates_widget.date_display.setText(
            self.estimates_widget._selected_date.toString("dd.MM.yyyy")
        )
        self.estimates_widget.emit_estimates_changed()
        self.grand_total_value.setText("0.00 Lei")

        show_info(self, "Reset", "All fields have been cleared.")

    @property
    def has_unsaved_changes(self) -> bool:
        """Whether the form has unsaved modifications."""
        return self._dirty

    def on_close_clicked(self):
        """Request to close this tab."""
        self.close_requested.emit()

    def _emit_tab_title(self):
        """Emit the updated tab title based on current receipt data."""
        client_name = self.receipt_data.get("client_name", "")
        if self.editing_receipt_id:
            title = f"Receipt #{self.editing_receipt_id}"
            if client_name:
                title += f" - {client_name}"
        else:
            title = "New Receipt"
        self.tab_title_changed.emit(title)

    def on_generate_clicked(self):
        """Save the receipt, generate Excel, and mark as Done."""
        try:
            self._do_generate()
        except Exception:
            import traceback

            show_critical(
                self,
                "Error",
                f"Failed to generate receipt:\n{traceback.format_exc()}",
            )

    def _do_generate(self):
        """Internal receipt generation logic."""
        if not template_exists():
            show_warning(
                self,
                "Template Not Found",
                "The Excel template was not found.\n\n"
                "Please reinstall the application or contact support.",
            )
            return

        if not self.receipt_data.get("client_id"):
            show_warning(
                self,
                "Missing Information",
                "Please select a client before generating the receipt.",
            )
            return

        create_backup("pre-receipt")
        plate = self.receipt_data.get("plate_number", "")
        date = self.receipt_data.get("date", "")
        existing = get_receipt_by_plate_and_date(plate, date, exclude_id=self.editing_receipt_id)
        if existing:
            show_warning(
                self,
                "Duplicate Receipt",
                f"A receipt for plate '{existing['plate_number']}' on {existing['date']} "
                f"already exists (Receipt #{existing['id']}).",
            )
            return
        car_id = self.receipt_data.get("car_id")
        kilometers = self.receipt_data.get("kilometers", "")
        if car_id and kilometers:
            try:
                update_car_kilometers(car_id, int(kilometers))
            except ValueError:
                pass

        output_path, warnings = generate_receipt_excel(self.receipt_data)

        data = self._collect_save_data()
        data["status"] = "Done"

        if self.editing_receipt_id:
            update_receipt(self.editing_receipt_id, data)
        else:
            new_id = add_receipt(data)
            self.editing_receipt_id = new_id
            self.receipt_id_assigned.emit(new_id)

        self._dirty = False
        self.receipt_saved.emit()
        self._emit_tab_title()

        message = f"Receipt has been generated successfully!\n\nFile saved to:\n{output_path}"
        if warnings:
            message += "\n\n" + "\n".join(warnings)

        show_info(self, "Receipt Generated", message)

        import os

        os.startfile(output_path)
