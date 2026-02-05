"""Clients page."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
    QLineEdit,
    QPushButton,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QMessageBox,
)
from PySide6.QtCore import Qt

from src.database.models import (
    get_all_clients,
    get_clients_count,
    add_client,
    update_client,
    delete_client,
)
from src.styles import theme


class ClientDialog(QDialog):
    """Dialog for adding or editing a client."""
    
    def __init__(self, parent=None, client=None):
        super().__init__(parent)
        self.client = client
        self.setup_ui()
        
        if client:
            self.setWindowTitle("Edit Client")
            self.first_name_input.setText(client["first_name"])
            self.last_name_input.setText(client["last_name"])
            self.address_input.setText(client.get("address", ""))
        else:
            self.setWindowTitle("Add Client")
    
    def setup_ui(self):
        """Setup the dialog UI."""
        self.setMinimumWidth(350)
        self.setStyleSheet(theme.dialog() + theme.line_edit_dialog())
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        self.first_name_input = QLineEdit()
        self.first_name_input.setPlaceholderText("Enter first name")
        form_layout.addRow("First Name:", self.first_name_input)
        
        self.last_name_input = QLineEdit()
        self.last_name_input.setPlaceholderText("Enter last name")
        form_layout.addRow("Last Name:", self.last_name_input)
        
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Enter address")
        form_layout.addRow("Address:", self.address_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(theme.button("cancel"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(theme.button("primary"))
        save_btn.clicked.connect(self.validate_and_accept)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def validate_and_accept(self):
        """Validate input and accept dialog."""
        first_name = self.first_name_input.text().strip()
        last_name = self.last_name_input.text().strip()
        
        if not first_name:
            QMessageBox.warning(self, "Validation Error", "First name is required.")
            self.first_name_input.setFocus()
            return
        
        if not last_name:
            QMessageBox.warning(self, "Validation Error", "Last name is required.")
            self.last_name_input.setFocus()
            return
        
        self.accept()
    
    def get_data(self):
        """Get the form data."""
        return {
            "first_name": self.first_name_input.text().strip(),
            "last_name": self.last_name_input.text().strip(),
            "address": self.address_input.text().strip(),
        }


class ClientsPage(QWidget):
    """Clients page content."""
    
    def __init__(self):
        super().__init__()
        self.all_clients = []  # Store all clients for filtering
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Setup the clients UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("👥 Clients")
        title.setStyleSheet(theme.page_title())
        header_layout.addWidget(title)
        
        layout.addLayout(header_layout)
        
        # Toolbar: Search and Action buttons
        toolbar_layout = QHBoxLayout()
        
        # Search bar
        search_label = QLabel("🔍")
        search_label.setStyleSheet("font-size: 18px;")
        toolbar_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search clients by name...")
        self.search_input.setStyleSheet(theme.search_input())
        self.search_input.textChanged.connect(self.filter_clients)
        toolbar_layout.addWidget(self.search_input)
        
        toolbar_layout.addSpacing(20)
        
        # Action buttons
        add_btn = QPushButton("➕ Add Client")
        add_btn.setStyleSheet(theme.button("success"))
        add_btn.clicked.connect(self.add_client)
        toolbar_layout.addWidget(add_btn)
        
        layout.addLayout(toolbar_layout)
        
        # Clients table
        self.clients_table = QTableWidget()
        self.clients_table.setStyleSheet(theme.table())
        self.clients_table.setAlternatingRowColors(True)
        self.clients_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.clients_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.clients_table.verticalHeader().setVisible(False)
        self.clients_table.verticalHeader().setDefaultSectionSize(50)
        self.clients_table.setColumnCount(5)
        self.clients_table.setHorizontalHeaderLabels(["ID", "First Name", "Last Name", "Address", "Actions"])
        self.clients_table.doubleClicked.connect(self.edit_client)
        
        layout.addWidget(self.clients_table)
    
    def load_data(self):
        """Load clients data from the database."""
        self.all_clients = get_all_clients()
        self.display_clients(self.all_clients)
    
    def filter_clients(self, search_text: str):
        """Filter clients based on search text."""
        search_text = search_text.lower().strip()
        
        if not search_text:
            filtered = self.all_clients
        else:
            filtered = [
                client for client in self.all_clients
                if search_text in client["first_name"].lower()
                or search_text in client["last_name"].lower()
                or search_text in f"{client['first_name']} {client['last_name']}".lower()
            ]
        
        self.display_clients(filtered)
    
    def display_clients(self, clients: list):
        """Display clients in the table."""
        # Populate table
        self.clients_table.setRowCount(len(clients))
        
        for row, client in enumerate(clients):
            id_item = QTableWidgetItem(str(client["id"]))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            id_item.setData(Qt.ItemDataRole.UserRole, client["id"])  # Store ID for reference
            self.clients_table.setItem(row, 0, id_item)
            
            self.clients_table.setItem(row, 1, QTableWidgetItem(client["first_name"]))
            self.clients_table.setItem(row, 2, QTableWidgetItem(client["last_name"]))
            self.clients_table.setItem(row, 3, QTableWidgetItem(client.get("address", "")))
            
            # Actions column with Edit and Delete buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 0, 2, 0)
            actions_layout.setSpacing(5)
            
            edit_btn = QPushButton("✏️")
            edit_btn.setStyleSheet(theme.button_icon("edit"))
            edit_btn.clicked.connect(lambda checked, c=client: self.edit_client_by_id(c["id"]))
            actions_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("🗑️")
            delete_btn.setStyleSheet(theme.button_icon("delete"))
            delete_btn.clicked.connect(lambda checked, c=client: self.delete_client_by_id(c["id"]))
            actions_layout.addWidget(delete_btn)
            
            self.clients_table.setCellWidget(row, 4, actions_widget)
        
        # Set column widths
        header = self.clients_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.clients_table.setColumnWidth(4, 100)
    
    def get_selected_client(self):
        """Get the currently selected client."""
        selected_rows = self.clients_table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        
        row = selected_rows[0].row()
        client_id = self.clients_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        first_name = self.clients_table.item(row, 1).text()
        last_name = self.clients_table.item(row, 2).text()
        address = self.clients_table.item(row, 3).text() if self.clients_table.item(row, 3) else ""
        
        return {
            "id": client_id,
            "first_name": first_name,
            "last_name": last_name,
            "address": address,
        }
    
    def add_client(self):
        """Open dialog to add a new client."""
        dialog = ClientDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            add_client(data["first_name"], data["last_name"], data["address"])
            self.load_data()
            self.search_input.clear()
    
    def edit_client(self):
        """Open dialog to edit the selected client."""
        client = self.get_selected_client()
        if not client:
            QMessageBox.warning(self, "No Selection", "Please select a client to edit.")
            return
        
        dialog = ClientDialog(self, client)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            update_client(client["id"], data["first_name"], data["last_name"], data["address"])
            self.load_data()
            self.filter_clients(self.search_input.text())
    
    def delete_client(self):
        """Delete the selected client."""
        client = self.get_selected_client()
        if not client:
            QMessageBox.warning(self, "No Selection", "Please select a client to delete.")
            return
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Delete")
        msg_box.setText(f"Are you sure you want to delete {client['first_name']} {client['last_name']}?")
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        msg_box.setStyleSheet(theme.message_box_confirm())
        
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            delete_client(client["id"])
            self.load_data()
            self.filter_clients(self.search_input.text())
    
    def edit_client_by_id(self, client_id: int):
        """Edit a client by ID (used by row action buttons)."""
        # Find the client in all_clients
        client = next((c for c in self.all_clients if c["id"] == client_id), None)
        if not client:
            return
        
        dialog = ClientDialog(self, client)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            update_client(client["id"], data["first_name"], data["last_name"], data["address"])
            self.load_data()
            self.filter_clients(self.search_input.text())
    
    def delete_client_by_id(self, client_id: int):
        """Delete a client by ID (used by row action buttons)."""
        # Find the client in all_clients
        client = next((c for c in self.all_clients if c["id"] == client_id), None)
        if not client:
            return
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Delete")
        msg_box.setText(f"Are you sure you want to delete {client['first_name']} {client['last_name']}?")
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        msg_box.setStyleSheet(theme.message_box_confirm())
        
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            delete_client(client_id)
            self.load_data()
            self.filter_clients(self.search_input.text())
