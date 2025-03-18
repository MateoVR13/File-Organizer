import os
import shutil
import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QTextEdit, 
                             QMessageBox, QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

class WorkerThread(QThread):
    """Thread worker to move files without blocking the interface"""
    update_progress = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, main_folder):
        super().__init__()
        self.main_folder = main_folder

    def run(self):
        try:
            self.move_files_to_main_folder(self.main_folder)
            self.finished_signal.emit(True, "Operation completed successfully!")
        except Exception as e:
            self.finished_signal.emit(False, f"Error: {str(e)}")

    def move_files_to_main_folder(self, main_folder):
        # Recursively traverse the directory structure
        for root, dirs, files in os.walk(main_folder, topdown=False):
            # Skip the main folder itself
            if root == main_folder:
                continue
                
            # Move all files in the current folder to the main folder
            for file in files:
                file_path = os.path.join(root, file)
                destination = os.path.join(main_folder, file)
                
                # Handle duplicate filenames
                if os.path.exists(destination):
                    base, ext = os.path.splitext(file)
                    counter = 1
                    while os.path.exists(os.path.join(main_folder, f"{base}_{counter}{ext}")):
                        counter += 1
                    destination = os.path.join(main_folder, f"{base}_{counter}{ext}")
                
                shutil.move(file_path, destination)
                self.update_progress.emit(f"Moved: {file} → {destination}")
                
            # After moving all files, remove empty directories
            for dir_ in dirs:
                dir_path = os.path.join(root, dir_)
                if os.path.exists(dir_path) and not os.listdir(dir_path):  # Check if the folder is now empty
                    os.rmdir(dir_path)
                    self.update_progress.emit(f"Deleted empty folder: {dir_path}")
                    
        # Finally, check if the top-level subfolders are empty and delete them
        for subfolder in os.listdir(main_folder):
            subfolder_path = os.path.join(main_folder, subfolder)
            if os.path.isdir(subfolder_path) and not os.listdir(subfolder_path):
                os.rmdir(subfolder_path)
                self.update_progress.emit(f"Deleted empty folder: {subfolder_path}")


class FileOrganizerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        # Main window settings
        self.setWindowTitle("File Organizer")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Title
        title_label = QLabel("File Organizer")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Description
        description = QLabel("This application moves all files from subfolders to the main folder and deletes empty folders.")
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(description)
        
        # Folder select button
        self.folder_button = QPushButton("Select Folder")
        self.folder_button.setMinimumHeight(40)
        self.folder_button.clicked.connect(self.select_folder)
        main_layout.addWidget(self.folder_button)
        
        # Label to display the selected folder
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.folder_label)
        
        # Button to start the process
        self.start_button = QPushButton("Start Process")
        self.start_button.setMinimumHeight(40)
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_process)
        main_layout.addWidget(self.start_button)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimumHeight(20)
        main_layout.addWidget(self.progress_bar)
        
        # Text area to show progress
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        main_layout.addWidget(self.log_text)
        
        # Variables to store the selected folder
        self.selected_folder = None
        
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Main Folder")
        if folder:
            self.selected_folder = folder
            self.folder_label.setText(f"Select Folder: {folder}")
            self.start_button.setEnabled(True)
            
    def start_process(self):
        if not self.selected_folder:
            QMessageBox.warning(self, "Warning", "Please select a folder first.")
            return
        
        # Confirm before proceeding
        reply = QMessageBox.question(self, "Confirm", 
                                     "This operation will move all files from subfolders to the parent folder "
                                     "and delete empty folders. Do you want to continue?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # Disable buttons during the process
            self.folder_button.setEnabled(False)
            self.start_button.setEnabled(False)
            self.progress_bar.setRange(0, 0)  # Indeterminate mode
            
            # Clean log
            self.log_text.clear()
            self.log_text.append("Starting the organization process...")
            
            # Start worker thread
            self.worker = WorkerThread(self.selected_folder)
            self.worker.update_progress.connect(self.update_log)
            self.worker.finished_signal.connect(self.process_finished)
            self.worker.start()
    
    def update_log(self, message):
        self.log_text.append(message)
        # Auto-scroll
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def process_finished(self, success, message):
        # Reset the interface
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100 if success else 0)
        self.folder_button.setEnabled(True)
        self.start_button.setEnabled(True)
        
        # Show completion message
        self.update_log(message)
        
        if success:
            QMessageBox.information(self, "Success", "All files have been moved and empty folders deleted.")
        else:
            QMessageBox.critical(self, "Error", message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileOrganizerApp()
    window.show()
    sys.exit(app.exec())