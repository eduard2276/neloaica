"""Receipt information section - Customer and car data."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QGroupBox,
)
from PySide6.QtCore import Qt, Signal

from src.database.models import (
    get_all_clients,
    get_all_cars,
)
from src.widgets import NoScrollComboBox
from src.styles import theme


class ReceiptInfoWidget(QWidget):
    """Widget for receipt information (client and car data)."""
    
    # Signals to notify parent when data changes
    data_changed = Signal(dict)  # Emits updated receipt info data
    
    def __init__(self):
        super().__init__()
        self.all_clients = []
        self.all_cars = []
        self.saved_client_id = None
        self.saved_car_id = None
        self.saved_kilometers = ""
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Setup the receipt information UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Form container
        form_group = QGroupBox("Receipt Information")
        form_group.setStyleSheet(theme.groupbox())
        
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Client dropdown
        self.client_combo = NoScrollComboBox()
        self.client_combo.setPlaceholderText("Select a client")
        self.client_combo.currentIndexChanged.connect(self.on_client_changed)
        self.client_combo.setStyleSheet(theme.combobox())
        form_layout.addRow("Client:", self.client_combo)
        
        # Car dropdown
        self.car_combo = NoScrollComboBox()
        self.car_combo.setPlaceholderText("Select a car")
        self.car_combo.setEnabled(False)
        self.car_combo.currentIndexChanged.connect(self.on_car_changed)
        self.car_combo.setStyleSheet(theme.combobox())
        form_layout.addRow("Car:", self.car_combo)
        
        # Car details (read-only except kilometers)
        self.plate_input = QLineEdit()
        self.plate_input.setReadOnly(True)
        self.plate_input.setPlaceholderText("Plate number")
        
        self.vin_input = QLineEdit()
        self.vin_input.setReadOnly(True)
        self.vin_input.setPlaceholderText("VIN")
        
        self.model_input = QLineEdit()
        self.model_input.setReadOnly(True)
        self.model_input.setPlaceholderText("Model")
        
        self.km_input = QLineEdit()
        self.km_input.setPlaceholderText("Kilometers")
        self.km_input.textChanged.connect(self.on_km_changed)
        
        # Styling for inputs
        input_style = theme.line_edit()
        
        self.plate_input.setStyleSheet(input_style)
        self.vin_input.setStyleSheet(input_style)
        self.model_input.setStyleSheet(input_style)
        self.km_input.setStyleSheet(input_style)
        
        form_layout.addRow("Plate Number:", self.plate_input)
        form_layout.addRow("VIN:", self.vin_input)
        form_layout.addRow("Model:", self.model_input)
        form_layout.addRow("Kilometers:", self.km_input)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
    
    def load_data(self, restore_state=False):
        """Load clients and cars from database."""
        if restore_state:
            self.save_form_state()
        
        self.all_clients = get_all_clients()
        self.all_cars = get_all_cars()
        
        self.client_combo.blockSignals(True)
        
        # Populate client dropdown
        self.client_combo.clear()
        self.client_combo.addItem("Select a client", None)
        for client in self.all_clients:
            display_text = f"{client['first_name']} {client['last_name']}"
            self.client_combo.addItem(display_text, client['id'])
        
        if restore_state and self.saved_client_id is not None:
            self.restore_form_state()
        
        self.client_combo.blockSignals(False)
    
    def save_form_state(self):
        """Save current form state."""
        self.saved_client_id = self.client_combo.currentData()
        self.saved_car_id = self.car_combo.currentData()
        self.saved_kilometers = self.km_input.text()
    
    def restore_form_state(self):
        """Restore previously saved form state."""
        if self.saved_client_id is not None:
            for i in range(self.client_combo.count()):
                if self.client_combo.itemData(i) == self.saved_client_id:
                    self.client_combo.setCurrentIndex(i)
                    break
        
        if self.saved_car_id is not None:
            for i in range(self.car_combo.count()):
                if self.car_combo.itemData(i) == self.saved_car_id:
                    self.car_combo.setCurrentIndex(i)
                    break
        
        if self.saved_kilometers and self.km_input.text() != self.saved_kilometers:
            self.km_input.setText(self.saved_kilometers)
    
    def on_client_changed(self, index):
        """Handle client selection change."""
        self.car_combo.clear()
        self.car_combo.addItem("Select a car", None)
        
        if index <= 0:
            self.car_combo.setEnabled(False)
            self.clear_car_details()
            self.emit_data_changed()
            return
        
        client_id = self.client_combo.currentData()
        if client_id is None:
            self.car_combo.setEnabled(False)
            self.clear_car_details()
            self.emit_data_changed()
            return
        
        # Filter cars for selected client
        client_cars = [car for car in self.all_cars if car['client_id'] == client_id]
        
        if client_cars:
            self.car_combo.setEnabled(True)
            for car in client_cars:
                display_text = f"{car['model']} ({car['vin']})"
                self.car_combo.addItem(display_text, car['id'])
        else:
            self.car_combo.setEnabled(False)
        
        self.clear_car_details()
        self.emit_data_changed()
    
    def on_car_changed(self, index):
        """Handle car selection change."""
        if index <= 0:
            self.clear_car_details()
            self.emit_data_changed()
            return
        
        car_id = self.car_combo.currentData()
        if car_id is None:
            self.clear_car_details()
            self.emit_data_changed()
            return
        
        # Find the selected car
        selected_car = next((car for car in self.all_cars if car['id'] == car_id), None)
        
        if selected_car:
            self.plate_input.setText(selected_car['plate_number'])
            self.vin_input.setText(selected_car['vin'])
            self.model_input.setText(selected_car['model'])
            self.km_input.setText(str(selected_car.get('kilometers', 0)))
        
        self.emit_data_changed()
    
    def on_km_changed(self):
        """Handle kilometers input change."""
        self.emit_data_changed()
    
    def clear_car_details(self):
        """Clear all car detail inputs."""
        self.plate_input.clear()
        self.vin_input.clear()
        self.model_input.clear()
        self.km_input.clear()
    
    def get_data(self) -> dict:
        """Get current form data."""
        # Get client name and address
        client_id = self.client_combo.currentData()
        client_name = ""
        client_address = ""
        
        if client_id is not None:
            client = next((c for c in self.all_clients if c['id'] == client_id), None)
            if client:
                client_name = f"{client['first_name']} {client['last_name']}"
                client_address = client.get('address', '')
        
        return {
            'client_id': client_id,
            'client_name': client_name,
            'client_address': client_address,
            'car_id': self.car_combo.currentData(),
            'plate_number': self.plate_input.text(),
            'vin': self.vin_input.text(),
            'model': self.model_input.text(),
            'kilometers': self.km_input.text(),
        }
    
    def emit_data_changed(self):
        """Emit signal with current data."""
        self.data_changed.emit(self.get_data())
