# -*- coding: utf-8 -*-
"""
Created on Thu May 15 15:06:43 2025

@author: simon
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QDialog, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QHBoxLayout, QFormLayout, QComboBox,
    QTreeWidget, QTreeWidgetItem, QSplitter, QWidget, QFileDialog,
    QProgressBar
)
from PyQt5.QtGui import QPixmap, QBrush, QColor, QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

import omero_connection
from pathlib import Path

OMERO_TOKEN_URL = "https://omero-cci-users.gu.se/oauth/sessiontoken"
APP_VERSION = "1.0.0"

# Default OMERO server settings
DEFAULT_HOST = "omero-cci-cli.gu.se"
DEFAULT_PORT = "4064"

class SettingsDialog(QDialog):
    def __init__(self, parent=None, host=DEFAULT_HOST, port=DEFAULT_PORT):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(300, 150)
        self.host = host
        self.port = port

        layout = QFormLayout()

        self.host_input = QLineEdit(self)
        self.host_input.setText(self.host)
        layout.addRow("Hostname:", self.host_input)

        self.port_input = QLineEdit(self)
        self.port_input.setText(str(self.port))
        layout.addRow("Port:", self.port_input)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        self.setLayout(layout)

    def accept(self):
        self.host = self.host_input.text().strip()
        self.port = self.port_input.text().strip()
        if not self.host or not self.port:
            QMessageBox.warning(self, "Invalid Input", "Please enter both hostname and port.")
            return
        super().accept()


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login to OMERO")
        self.token = None

        layout = QVBoxLayout()
        label = QLabel("Paste your OMERO session token below:")
        layout.addWidget(label)

        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Session token")
        layout.addWidget(self.token_input)

        link_label = QLabel(
            f'<a href="{OMERO_TOKEN_URL}">Get your token from OMERO</a>'
        )
        link_label.setOpenExternalLinks(True)
        layout.addWidget(link_label)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def accept(self):
        self.token = self.token_input.text().strip()
        if not self.token:
            QMessageBox.warning(self, "Missing Token", "Please enter a session token.")
            return
        super().accept()


class OmeroExplorerTree(QTreeWidget):
    itemDoubleClickedToTransfer = pyqtSignal(QTreeWidgetItem)  # Custom signal

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(1)
        self.setHeaderLabels(['OMERO Data'])
        self.itemDoubleClicked.connect(self._emit_double_clicked_item)

    def _emit_double_clicked_item(self, item):
        self.itemDoubleClickedToTransfer.emit(item)


class DownloadQueueTree(QTreeWidget):
    itemDoubleClickedToTransfer = pyqtSignal(QTreeWidgetItem)  # Custom signal
    
    def __init__(self, parent=None, conn=None):
        super().__init__(parent)
        self.conn = conn
        self.setColumnCount(1)
        self.setHeaderLabels(['Download Queue'])
        self._existing_projects = {}  # {project_id: QTreeWidgetItem}
        self.itemDoubleClicked.connect(self.remove_from_download_tree)

    def remove_from_download_tree(self, item, column):
        parent = item.parent()
        node_type, node_id = item.data(0, 1)
        if parent is None:
            self.takeTopLevelItem(self.indexOfTopLevelItem(item))
            if node_type == 'project' and node_id in self._existing_projects:
                del self._existing_projects[node_id]
        else:
            parent.removeChild(item)
        
        self.itemDoubleClickedToTransfer.emit(item)

    def add_omerohierarchy(self, omero_item):
        hierarchy = self._get_full_hierarchy(omero_item)
        for project_id, project_data in hierarchy.items():
            if project_id in self._existing_projects:
                project_node = self._existing_projects[project_id]
            else:
                project_node = QTreeWidgetItem(self)
                project_node.setText(0, project_data['name'])
                project_node.setData(0, 1, ('project', project_id))
                self._existing_projects[project_id] = project_node

            for dataset_id, dataset_data in project_data['datasets'].items():
                dataset_node = self._find_or_add_child(project_node, 'dataset', dataset_id, dataset_data['name'])
                for image_id, image_name in dataset_data['images'].items():
                    folder_name = self.conn.get_original_upload_folder(image_id)
                    if folder_name and folder_name.lower() != 'uploads':
                        folder_node = self._find_or_add_child(dataset_node, 'folder', folder_name, folder_name)
                        self._find_or_add_child(folder_node, 'image', image_id, image_name)
                    else:
                        self._find_or_add_child(dataset_node, 'image', image_id, image_name)

    def _find_or_add_child(self, parent, node_type, node_id, node_name):
        # node_id can be str for folder, int for others
        for i in range(parent.childCount()):
            child = parent.child(i)
            data = child.data(0, 1)
            if data and data[0] == node_type and data[1] == node_id:
                return child
        child = QTreeWidgetItem(parent)
        child.setText(0, node_name)
        child.setData(0, 1, (node_type, node_id))
        return child

    def _get_full_hierarchy(self, item):
        """Returns hierarchical data for the clicked item and its parents"""
        hierarchy = {}
        current_item = item

        # Traverse up to project level
        while current_item:
            node_type, node_id = current_item.data(0, 1)
            
            if node_type == 'project':
                hierarchy[node_id] = {
                    'name': current_item.text(0),
                    'datasets': self._get_child_datasets(current_item)
                }
                break
            elif node_type == 'dataset':
                parent_project = self._find_parent_project(current_item)
                if parent_project:
                    project_id = parent_project.data(0, 1)[1]
                    hierarchy[project_id] = {
                        'name': parent_project.text(0),
                        'datasets': {
                            node_id: {
                                'name': current_item.text(0),
                                'images': self._get_child_images(current_item)
                            }
                        }
                    }
                break
            elif node_type == 'image':
                parent_dataset = self._find_parent_dataset(current_item)
                parent_project = self._find_parent_project(parent_dataset)
                if parent_dataset and parent_project:
                    project_id = parent_project.data(0, 1)[1]
                    dataset_id = parent_dataset.data(0, 1)[1]
                    hierarchy[project_id] = {
                        'name': parent_project.text(0),
                        'datasets': {
                            dataset_id: {
                                'name': parent_dataset.text(0),
                                'images': {
                                    node_id: current_item.text(0)
                                }
                            }
                        }
                    }
                break
            current_item = current_item.parent()
        return hierarchy

    def _add_dataset(self, project_node, dataset_id, dataset_data):
        """Add dataset to project node if not already present"""
        for i in range(project_node.childCount()):
            existing_dataset = project_node.child(i)
            if existing_dataset.data(0, 1)[1] == dataset_id:
                return  # Dataset already exists

        dataset_node = QTreeWidgetItem(project_node)
        dataset_node.setText(0, dataset_data['name'])
        dataset_node.setData(0, 1, ('dataset', dataset_id))

        for image_id, image_name in dataset_data['images'].items():
            image_node = QTreeWidgetItem(dataset_node)
            image_node.setText(0, image_name)
            image_node.setData(0, 1, ('image', image_id))

    # Helper functions 
    def _find_parent_project(self, item):
        while item:
            data = item.data(0, 1)
            if data is not None and data[0] == 'project':
                return item
            item = item.parent()
        return None
    
    def _find_parent_dataset(self, item):
        while item:
            data = item.data(0, 1)
            if data is not None and data[0] == 'dataset':
                return item
            item = item.parent()
        return None

    def _get_child_datasets(self, project_item):
        datasets = {}
        for i in range(project_item.childCount()):
            dataset_item = project_item.child(i)
            dataset_id = dataset_item.data(0, 1)[1]
            datasets[dataset_id] = {
                'name': dataset_item.text(0),
                'images': self._get_child_images(dataset_item)
            }
        return datasets

    def _get_child_images(self, dataset_item):
        images = {}
        for i in range(dataset_item.childCount()):
            image_item = dataset_item.child(i)
            image_id = image_item.data(0, 1)[1]
            images[image_id] = image_item.text(0)
        return images




class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.color_partial = QColor("#FFBB66")  # soft amber-orange
        self.color_full = QColor("#66CC66")     # soft green
        self.setStyleSheet("""
                QMainWindow {
                    background-color: #f2f2f2;
                }
            
                QTreeWidget {
                    background-color: #ffffff;
                    border: 1px solid #ccc;
                    font-size: 13px;
                    padding: 5px;
                }
            
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border-radius: 5px;
                    padding: 5px 10px;
                    font-size: 15px;
                }
            
                QPushButton:hover {
                    background-color: #45a049;
                    font-size: 14px;
                }
            
                QComboBox, QLineEdit {
                    min-width: 150px;
                    padding: 5px;
                    border-radius: 4px;
                    border: 1px solid #ccc;
                    font-size: 15px;
                }
                
                QLabel{
                    font-size: 15px;
                }
            """)

        
        
        self.setWindowTitle("OMERO Downloader Client")
        self.setGeometry(200, 200, 800, 600)

        self.setWindowIcon(QIcon("icons/icon.png"))
        self.connected = False
        self.busy = False
        self.token = None
        self.host = DEFAULT_HOST
        self.port = DEFAULT_PORT

        # Initialize a timer for connection checks
        self.connection_timer = QTimer()
        self.connection_timer.setInterval(5000)  # Check every 5 seconds (adjust as needed)
        self.connection_timer.timeout.connect(self.check_connection)
        self.connection_timer.start()

        # Status icon
        self.status_icon = QLabel()
        self.update_status_icon()
        self.statusBar().addPermanentWidget(self.status_icon)
        
        self.spinner_label = QLabel()
        self.spinner_label.setText("")
        self.statusBar().addPermanentWidget(self.spinner_label)

        self._create_menu()
        
        # Add group/user toolbar
        self.group_toolbar = self.addToolBar("Groups")
        self.group_combo = QComboBox()
        self.group_combo.setEnabled(False)   
        self.group_combo.currentIndexChanged.connect(self._on_group_changed)
        self.group_toolbar.addWidget(QLabel("Current Group:"))
        self.group_toolbar.addWidget(self.group_combo)
        
        self.user_label = QLabel()
        self.group_toolbar.addWidget(self.user_label)
        
        self.user_combo = QComboBox()
        self.user_combo.setEnabled(False)
        self.user_combo.currentIndexChanged.connect(self._on_experimentor_changed)
        self.group_toolbar.addWidget(QLabel("  View Data of:"))
        self.group_toolbar.addWidget(self.user_combo)
        
        refresh_action = QAction(QIcon("icons/refresh_green_wb.svg"), "Refresh", self)
        refresh_action.triggered.connect(self.refresh)
        self.group_toolbar.addAction(refresh_action)
        
        central_widget = QWidget(self)
        main_layout = QVBoxLayout(central_widget)
        
        # 1. The splitter for the two trees (expands)
        splitter = QSplitter(Qt.Horizontal)
        self.omero_tree = OmeroExplorerTree()
        self.download_tree = DownloadQueueTree()
        splitter.addWidget(self.omero_tree)
        splitter.addWidget(self.download_tree)
        main_layout.addWidget(splitter)  # <-- expands vertically
        
        # 2. Bottom download layout (pinned)
        
        bottom_layout = QHBoxLayout()
        
        # Left side: path selector
        path_label = QLabel("Download to:")
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select download directory...")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_download_path)
        
        bottom_layout.addWidget(path_label)
        bottom_layout.addWidget(self.path_edit)
        bottom_layout.addWidget(browse_btn)
        
        # Spacer between path and download button
        bottom_layout.addStretch()
        
        # Right side: download button
        download_btn = QPushButton("Download")
        download_btn.clicked.connect(self.download_files)
        bottom_layout.addWidget(download_btn)
        
        main_layout.addLayout(bottom_layout)

        self.setCentralWidget(central_widget)
        
        # Connect signals
        self.omero_tree.itemDoubleClickedToTransfer.connect(
            self.download_tree.add_omerohierarchy)
        self.omero_tree.itemDoubleClickedToTransfer.connect(
            self.update_omero_tree_highlight)
        self.download_tree.itemDoubleClickedToTransfer.connect(
            lambda item: QTimer.singleShot(0, self.update_omero_tree_highlight))
        

    def download_files(self):
        download_path = self.get_download_path()
        if not download_path:
            QMessageBox.warning(self, "No Download Path", "Please select a download directory.")
            return
        self.progress_dialog = DownloadProgressDialog(self)
        self.progress_dialog.show()
        
        self.dm = DownloadManager(self.download_tree, self.conn, download_path)
        self.dm.progress_signals = self.progress_dialog  # Dialog handles set_* methods
    
        self.generator = self.dm.download_files_generator()
        self.busy = True
        self.update_status_icon()
        self.step_download()

    def step_download(self):
        try:
            next(self.generator)
            QTimer.singleShot(0, self.step_download)
        except StopIteration:
            self.progress_dialog.close()
            self.download_tree.clear()
            self.update_omero_tree_highlight()
            self.busy = False
            self.update_status_icon()

    def browse_download_path(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Download Directory")
        if directory:
            self.path_edit.setText(directory)
    
    def get_download_path(self):
        return self.path_edit.text()
    
    def refresh(self):
        if self.connected:
            self._on_experimentor_changed(self.user_combo.currentIndex())  
            self.update_omero_tree_highlight()
        

    def populate_full_tree(self):
        self.set_loading(True)
        self.tree_loader = self.populate_full_tree_generator()
        self.step_tree_loader()
    
    def step_tree_loader(self):
        try:
            next(self.tree_loader)
            QTimer.singleShot(0, self.step_tree_loader)
        except StopIteration:
            self.set_loading(False)


    def populate_full_tree_generator(self):
        projects = self.conn.get_user_projects()  # {project_id: project_name}
        for proj_id, proj_name in projects.items():
            proj_item = QTreeWidgetItem(self.omero_tree)
            proj_item.setText(0, proj_name)
            proj_item.setData(0, 1, ('project', proj_id))
            yield  # let UI breathe
    
            datasets = self.conn.get_dataset_from_projectID(proj_id)
            for ds_id, ds_name in datasets.items():
                ds_item = QTreeWidgetItem(proj_item)
                ds_item.setText(0, ds_name)
                ds_item.setData(0, 1, ('dataset', ds_id))
                yield
    
                images = self.conn.get_images_from_datasetID(ds_id)
                for img_id, img_name in images.items():
                    img_item = QTreeWidgetItem(ds_item)
                    img_item.setText(0, img_name)
                    img_item.setData(0, 1, ('image', img_id))
                    yield


    def _create_menu(self):
        menubar = self.menuBar()
        session_menu = menubar.addMenu("&Session")
        
        settings_menu = menubar.addMenu("&Settings")
        settings_action = QAction("Configure...", self)
        settings_action.triggered.connect(self.open_settings)
        settings_menu.addAction(settings_action)

        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        login_action = QAction("Login", self)
        login_action.triggered.connect(self.login)
        session_menu.addAction(login_action)

        disconnect_action = QAction("Disconnect", self)
        disconnect_action.triggered.connect(self.disconnect)
        session_menu.addAction(disconnect_action)

        session_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        session_menu.addAction(exit_action)
        
    def show_about_dialog(self):
        about_text = f"""
        <h3>OMERO Downloader Client</h3>
        <p><b>Version:</b> {APP_VERSION}</p>
        <p>This tool lets you explore and download data from an OMERO server.</p>
        <p><b>Latest version:</b> 
            <a href="https://example.com/omero-downloader">https://example.com/omero-downloader</a></p>
        <p>Created by Simon Leclerc at the Centre for Cellular Imaging, Gothenburg.<br>
        For support or feature requests, visit the download page.</p>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("About OMERO Downloader")
        msg.setTextFormat(Qt.RichText)
        msg.setText(about_text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def login(self):
        dlg = LoginDialog(self)
        try:
            if dlg.exec_() == QDialog.Accepted:
                self.token = dlg.token
                self.conn = omero_connection.OmeroConnection('omero-cci-cli.gu.se', '4064', self.token)
                self.download_tree.conn = self.conn
                self.connected = True
                self._update_groups_and_user()
                self.update_status_icon()
                QMessageBox.information(self, "Connected", "Successfully connected to OMERO.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to connect: {str(e)}")

    def disconnect(self):
        if self.connected:
            self.conn.kill_session()
            self.omero_tree.clear()
            self.download_tree.clear()
            self.group_combo.setEnabled(False)
            self.user_combo.setEnabled(False)   
            self.user_label.setText("")              
            
            self.conn = None
            self.connected = False

            self.token = None
            self.update_status_icon()
            QMessageBox.information(self, "Disconnected", "Disconnected from OMERO.")


    def open_settings(self):
        dlg = SettingsDialog(self, self.host, self.port)
        if dlg.exec_() == QDialog.Accepted:
            self.host = dlg.host
            self.port = dlg.port
            QMessageBox.information(
                self, "Settings Saved",
                f"Hostname: {self.host}\nPort: {self.port}"
            )
            
    def update_status_icon(self):
        if self.connected and not self.busy:
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.green)
            self.status_icon.setPixmap(pixmap)
            self.status_icon.setToolTip("Connected")
        elif self.connected and self.busy:
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.yellow)
            self.status_icon.setPixmap(pixmap)
            self.status_icon.setToolTip("Busy")            
        else:
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.red)
            self.status_icon.setPixmap(pixmap)
            self.status_icon.setToolTip("Disconnected")
            
            
    def set_loading(self, is_loading):
        if is_loading:
            self.busy = True
            self.spinner_label.setText("⏳ Loading...")  # or show a spinner gif
        else:
            self.spinner_label.setText("")
            self.busy = False
            
        self.update_status_icon()

    def _update_groups_and_user(self):
        """Populate group combo and user label after login"""
        try:
            groups = self.conn.get_user_group()
            current_group = self.conn.getDefaultOmeroGroup()
            self.user_name = self.conn.get_logged_in_user_name()
            
            self.group_combo.blockSignals(True)
            self.group_combo.clear()
            self.group_combo.addItems(groups)

            if current_group in groups:
                index = groups.index(current_group)
                self.group_combo.setCurrentIndex(index)
            else:
                index = 0
            
            self.group_combo.blockSignals(False)
            self.user_label.setText(f"  Logged in as: {self.user_name}")
            self.group_combo.setEnabled(True)
            self._on_group_changed(index)

        except AttributeError:
            self.user_label.setText("Not logged in")
            self.group_combo.setEnabled(False)

    def _on_group_changed(self, index):
        """Handle group selection changes"""
        group_name = self.group_combo.itemText(index)
        try:
            self.conn.setOmeroGroupName(group_name)
            self.load_experimentors()
            
            # Set experimentor combo to yourself
            self.user_combo.blockSignals(True)
            if self.user_name in self.members:
                user_index = list(self.members.keys()).index(self.user_name)
                self.user_combo.setCurrentIndex(user_index)
            self.user_combo.blockSignals(False)
    
            # Manually trigger experimentor change once
            self._on_experimentor_changed(self.user_combo.currentIndex())            
            
            self.omero_tree.clear()
            self.download_tree.clear()
            self.populate_full_tree()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to switch groups: {str(e)}")
            
    def load_experimentors(self):
        self.members = self.conn.get_members_of_group()
        self.user_combo.clear()
        for username in self.members.keys():
            self.user_combo.addItem(username)
        self.user_combo.setEnabled(True)
        
    def _on_experimentor_changed(self, index):
        self.omero_tree.clear()
        self.download_tree.clear()
        user_name = self.user_combo.itemText(index)
        if user_name == '':
            user_name = self.user_name
        self.conn.set_user(self.members[user_name])
        
        self.populate_full_tree()
        
    def update_omero_tree_highlight(self):
        for i in range(self.omero_tree.topLevelItemCount()):
            proj_item = self.omero_tree.topLevelItem(i)
            self._update_item_highlight_recursive(proj_item)

    def _update_item_highlight_recursive(self, item):
        if item.childCount() == 0:
            included = self._is_in_download_tree(item)
            self._set_item_color(item, Qt.green if included else Qt.white)
            return included
    
        total = item.childCount()
        included_count = 0
    
        for i in range(total):
            child = item.child(i)
            if self._update_item_highlight_recursive(child):
                included_count += 1
    
        if included_count == total:
            self._set_item_color(item, self.color_full)
            return True
        elif included_count > 0:
            self._set_item_color(item, self.color_partial) 
            return False
        else:
            self._set_item_color(item, Qt.white)
            return False
    
    def _set_item_color(self, item, color):
        brush = QBrush(color)
        item.setBackground(0, brush)
        
        
    def _is_in_download_tree(self, omero_item, verbose=False):
        o_type, o_id = omero_item.data(0, 1)
        if verbose: print(f"Checking if {o_type} {o_id} is in download tree")
    
        for i in range(self.download_tree.topLevelItemCount()):
            d_proj = self.download_tree.topLevelItem(i)
            if self._tree_item_match(d_proj, o_type, o_id):
                if verbose: print("Matched at project level")
                return True
            for j in range(d_proj.childCount()):
                d_ds = d_proj.child(j)
                if self._tree_item_match(d_ds, o_type, o_id):
                    if verbose: print("Matched at dataset level")
                    return True
                for k in range(d_ds.childCount()):
                    d_child = d_ds.child(k)
                    if self._tree_item_match(d_child, o_type, o_id):
                        if verbose: print("Matched at image/folder level")
                        return True
                    for l in range(d_child.childCount()):
                        d_img = d_child.child(l)
                        if self._tree_item_match(d_img, o_type, o_id):
                            if verbose: print("Matched at deep image level")
                            return True
        return False
    
    def _tree_item_match(self, item, o_type, o_id):
        d_type, d_id = item.data(0, 1)
        return (d_type == o_type and d_id == o_id)
    
    def check_connection(self):
        if not self.busy and self.connected:
            if not self.conn.is_connected():
                self.connected = False
                self.update_status_icon()
                QMessageBox.critical(self, "Error", "Lost the connection to the Omero server. \n Retry later.")


class DownloadManager:
    def __init__(self, download_tree, conn, base_path):
        self.download_tree = download_tree
        self.conn = conn
        self.base_path = Path(base_path)
        self.downloaded_filesets = set()  # Track downloaded fileset IDs
        self.progress_signals = None
    
    def update_overall_progress(self, current, total):
        if self.progress_signals:
            self.progress_signals.set_overall_max(total)
            self.progress_signals.set_overall_value(current)

    def update_file_progress(self, current, total):
        if self.progress_signals:
            self.progress_signals.set_file_max(total)
            self.progress_signals.set_file_value(current)
                    
    def _collect_fileset_ids(self):
        fileset_set = set()
        for i in range(self.download_tree.topLevelItemCount()):
            project_item = self.download_tree.topLevelItem(i)
            for j in range(project_item.childCount()):
                dataset_item = project_item.child(j)
                for k in range(dataset_item.childCount()):
                    child_item = dataset_item.child(k)
                    if child_item is None:
                        continue
                    data = child_item.data(0, 1)
                    if data is None:
                        continue
                    node_type, node_id = data
                    if node_type == 'folder':
                        for l in range(child_item.childCount()):
                            image_item = child_item.child(l)
                            if image_item is None:
                                continue
                            image_data = image_item.data(0, 1)
                            if image_data is None:
                                continue
                            node_type, image_id = image_data
                            fileset = self.conn.get_fileset_from_imageID(image_id)
                            if fileset:
                                fileset_set.add(fileset.getId())
                    elif node_type == 'image':
                        image_id = node_id
                        fileset = self.conn.get_fileset_from_imageID(image_id)
                        if fileset:
                            fileset_set.add(fileset.getId())
        return list(fileset_set)
        
    def download_files_generator(self):
        if not self.base_path.exists():
            self.base_path.mkdir(parents=True, exist_ok=True)
    
        all_fileset_ids = self._collect_fileset_ids()
        self.total_files = len(all_fileset_ids)
        self.files_downloaded = 0
        self.update_overall_progress(self.files_downloaded, self.total_files)
    
        for i in range(self.download_tree.topLevelItemCount()):
            project_item = self.download_tree.topLevelItem(i)
            yield from self._download_project_generator(project_item, self.base_path)
    
        yield "done"
    
    
    def _download_project_generator(self, project_item, current_path):
        project_name = project_item.text(0)
        project_path = current_path / project_name
        project_path.mkdir(exist_ok=True)
    
        for i in range(project_item.childCount()):
            dataset_item = project_item.child(i)
            yield from self._download_dataset_generator(dataset_item, project_path)
    
    
    def _download_dataset_generator(self, dataset_item, current_path):
        dataset_name = dataset_item.text(0)
        dataset_path = current_path / dataset_name
        dataset_path.mkdir(exist_ok=True)
    
        for i in range(dataset_item.childCount()):
            child_item = dataset_item.child(i)
            node_type, node_id = child_item.data(0, 1)
            if node_type == 'folder':
                folder_name = child_item.text(0)
                folder_path = dataset_path / folder_name
                folder_path.mkdir(exist_ok=True)
                for j in range(child_item.childCount()):
                    image_item = child_item.child(j)
                    yield from self._download_image_generator(image_item, folder_path)
            elif node_type == 'image':
                yield from self._download_image_generator(child_item, dataset_path)
    
    
    def _download_image_generator(self, image_item, current_path):
        image_name = image_item.text(0)
        node_type, image_id = image_item.data(0, 1)
    
        fileset = self.conn.get_fileset_from_imageID(image_id)
        if fileset is None:
            print(f"No fileset for image {image_name} (ID: {image_id})")
            return
    
        fileset_id = fileset.getId()
        if fileset_id in self.downloaded_filesets:
            return
    
        for orig_file in fileset.listFiles():
            file_name = orig_file.getName()
            file_path = current_path / file_name
            file_size = orig_file.getSize()
            self.update_file_progress(0, file_size)
    
            with open(file_path, 'wb') as f:
                bytes_written = 0
                for chunk in orig_file.getFileInChunks():
                    f.write(chunk)
                    bytes_written += len(chunk)
                    self.update_file_progress(bytes_written, file_size)
                    yield
    
            self.downloaded_filesets.add(fileset_id)
            self.files_downloaded += 1
            self.update_overall_progress(self.files_downloaded, self.total_files)
            yield        


class DownloadProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Download Progress")
        self.setWindowModality(Qt.ApplicationModal)  # Modal window
        self.setFixedSize(400, 120)

        self.overall_progress = QProgressBar()
        self.overall_progress.setFormat("Overall Progress: %v/%m files")
        self.overall_progress.setAlignment(Qt.AlignCenter)

        self.file_progress = QProgressBar()
        self.file_progress.setFormat("Current File Progress: %p%")
        self.file_progress.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.overall_progress)
        layout.addWidget(self.file_progress)
        self.setLayout(layout)

    def set_overall_max(self, max_files):
        self.overall_progress.setMaximum(max_files)

    def set_overall_value(self, value):
        self.overall_progress.setValue(value)

    def set_file_max(self, max_bytes):
        self.file_progress.setMaximum(max_bytes)

    def set_file_value(self, value):
        self.file_progress.setValue(value)




if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("icons/icon.png"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
