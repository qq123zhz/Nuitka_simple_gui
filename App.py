import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                            QCheckBox, QLineEdit, QTextEdit, QMessageBox,
                            QListWidget, QInputDialog, QGroupBox, QComboBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import subprocess

class BuildThread(QThread):
    output_ready = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd
        
    def run(self):
        try:
            # 使用subprocess.PIPE来捕获输出
            process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                shell=True,
                bufsize=1
            )
            
            # 创建两个线程分别处理stdout和stderr
            def read_output(pipe, is_error=False):
                for line in iter(pipe.readline, ''):
                    if line:
                        if is_error:
                            self.output_ready.emit(f"错误: {line.strip()}")
                        else:
                            self.output_ready.emit(line.strip())
                pipe.close()
            
            # 启动输出处理线程
            import threading
            stdout_thread = threading.Thread(target=read_output, args=(process.stdout, False))
            stderr_thread = threading.Thread(target=read_output, args=(process.stderr, True))
            
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            
            stdout_thread.start()
            stderr_thread.start()
            
            # 等待进程完成
            process.wait()
            
            # 等待输出处理线程完成
            stdout_thread.join()
            stderr_thread.join()
            
            # 检查打包结果
            if process.returncode == 0:
                self.finished.emit(True, "打包完成！")
            else:
                self.finished.emit(False, "打包失败，请查看日志了解详情。")
                
        except Exception as e:
            self.output_ready.emit(f"错误: {str(e)}")
            self.finished.emit(False, f"打包过程出错：{str(e)}")

class NuitkaGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nuitka打包工具")
        self.setMinimumSize(800, 600)
        
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # 文件选择区域
        file_layout = QHBoxLayout()
        self.file_label = QLabel("Python文件:")
        self.file_path = QLineEdit()
        self.file_path.setReadOnly(True)
        self.browse_btn = QPushButton("浏览")
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.file_path)
        file_layout.addWidget(self.browse_btn)
        layout.addLayout(file_layout)
        
        # 打包选项区域
        options_layout = QVBoxLayout()
        
        # 基本选项组
        basic_group = QGroupBox("基本选项")
        basic_layout = QVBoxLayout()
        
        # 编译模式选择
        mode_layout = QHBoxLayout()
        mode_label = QLabel("编译模式:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["standalone", "onefile", "module", "package"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        basic_layout.addLayout(mode_layout)
        
        # 其他基本选项
        self.standalone = QCheckBox("生成独立文件夹 (--standalone)")
        self.standalone.setChecked(True)
        self.onefile = QCheckBox("生成单个文件 (--onefile)")
        self.onefile.setChecked(False)
        self.windows_icon = QCheckBox("使用Windows图标")
        self.windows_icon.setChecked(False)
        self.show_progress = QCheckBox("显示编译进度 (--show-progress)")
        self.show_progress.setChecked(True)
        self.follow_imports = QCheckBox("自动包含导入的模块 (--follow-imports)")
        self.follow_imports.setChecked(True)
        self.remove_output = QCheckBox("打包完成后删除临时文件 (--remove-output)")
        self.remove_output.setChecked(False)
        
        basic_layout.addWidget(self.standalone)
        basic_layout.addWidget(self.onefile)
        basic_layout.addWidget(self.windows_icon)
        basic_layout.addWidget(self.show_progress)
        basic_layout.addWidget(self.follow_imports)
        basic_layout.addWidget(self.remove_output)
        basic_group.setLayout(basic_layout)
        options_layout.addWidget(basic_group)
        
        # 图标选择
        icon_layout = QHBoxLayout()
        self.icon_label = QLabel("图标文件:")
        self.icon_path = QLineEdit()
        self.icon_path.setReadOnly(True)
        self.icon_browse_btn = QPushButton("浏览")
        self.icon_browse_btn.clicked.connect(self.browse_icon)
        icon_layout.addWidget(self.icon_label)
        icon_layout.addWidget(self.icon_path)
        icon_layout.addWidget(self.icon_browse_btn)
        options_layout.addLayout(icon_layout)
        
        # 输出目录选择
        output_layout = QHBoxLayout()
        self.output_label = QLabel("输出目录:")
        self.output_path = QLineEdit()
        self.output_path.setReadOnly(True)
        self.output_browse_btn = QPushButton("浏览")
        self.output_browse_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(self.output_browse_btn)
        options_layout.addLayout(output_layout)
        
        # 资源文件夹选择
        data_dir_layout = QHBoxLayout()
        self.data_dir_label = QLabel("资源文件夹:")
        self.data_dir_path = QLineEdit()
        self.data_dir_path.setReadOnly(True)
        self.data_dir_browse_btn = QPushButton("浏览")
        self.data_dir_browse_btn.clicked.connect(self.browse_data_dir)
        data_dir_layout.addWidget(self.data_dir_label)
        data_dir_layout.addWidget(self.data_dir_path)
        data_dir_layout.addWidget(self.data_dir_browse_btn)
        options_layout.addLayout(data_dir_layout)
        
        # 包含包选择区域
        packages_layout = QVBoxLayout()
        packages_label = QLabel("包含的包:")
        self.packages_list = QListWidget()
        packages_buttons_layout = QHBoxLayout()
        self.add_package_btn = QPushButton("添加包")
        self.add_package_btn.clicked.connect(self.add_package)
        self.remove_package_btn = QPushButton("删除包")
        self.remove_package_btn.clicked.connect(self.remove_package)
        packages_buttons_layout.addWidget(self.add_package_btn)
        packages_buttons_layout.addWidget(self.remove_package_btn)
        packages_layout.addWidget(packages_label)
        packages_layout.addWidget(self.packages_list)
        packages_layout.addLayout(packages_buttons_layout)
        options_layout.addLayout(packages_layout)
        
        # 高级选项
        self.advanced_options = QTextEdit()
        self.advanced_options.setPlaceholderText("其他高级选项 (每行一个，例如: --windows-disable-console)")
        self.advanced_options.setMaximumHeight(100)
        options_layout.addWidget(QLabel("其他高级选项:"))
        options_layout.addWidget(self.advanced_options)
        
        layout.addLayout(options_layout)
        
        # 日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(QLabel("打包日志:"))
        layout.addWidget(self.log_text)
        
        # 打包按钮
        self.build_btn = QPushButton("开始打包")
        self.build_btn.clicked.connect(self.start_build)
        layout.addWidget(self.build_btn)
        
        # 初始化变量
        self.python_file = ""
        self.icon_file = ""
        self.output_dir = ""
        self.data_dir = ""
        self.build_thread = None
        
    def on_mode_changed(self, mode):
        if mode == "standalone":
            self.standalone.setChecked(True)
            self.onefile.setChecked(False)
        elif mode == "onefile":
            self.standalone.setChecked(True)
            self.onefile.setChecked(True)
        elif mode == "module":
            self.standalone.setChecked(False)
            self.onefile.setChecked(False)
        elif mode == "package":
            self.standalone.setChecked(False)
            self.onefile.setChecked(False)
            
    def browse_data_dir(self):
        dir = QFileDialog.getExistingDirectory(self, "选择资源文件夹")
        if dir:
            self.data_dir = dir
            self.data_dir_path.setText(dir)
            
    def add_package(self):
        package, ok = QInputDialog.getText(self, "添加包", "请输入要包含的包名:")
        if ok and package:
            self.packages_list.addItem(package)
            
    def remove_package(self):
        current_item = self.packages_list.currentItem()
        if current_item:
            self.packages_list.takeItem(self.packages_list.row(current_item))
            
    def browse_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "选择Python文件", "", "Python Files (*.py)")
        if file:
            self.python_file = file
            self.file_path.setText(file)
            
    def browse_icon(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "选择图标文件", "", "Icon Files (*.ico)")
        if file:
            self.icon_file = file
            self.icon_path.setText(file)
            
    def browse_output(self):
        dir = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir:
            self.output_dir = dir
            self.output_path.setText(dir)
            
    def start_build(self):
        if not self.python_file:
            QMessageBox.warning(self, "警告", "请选择Python文件！")
            return
            
        if not self.output_dir:
            QMessageBox.warning(self, "警告", "请选择输出目录！")
            return
            
        # 禁用打包按钮，防止重复点击
        self.build_btn.setEnabled(False)
        self.build_btn.setText("打包中...")
        
        # 构建Nuitka命令
        cmd = ["python", "-m", "nuitka"]
        
        # 添加编译模式
        mode = self.mode_combo.currentText()
        if mode == "standalone":
            cmd.append("--standalone")
        elif mode == "onefile":
            cmd.append("--onefile")
        elif mode == "module":
            cmd.append("--module")
        elif mode == "package":
            cmd.append("--package")
        
        # 添加基本选项（避免重复添加模式选项）
        if self.windows_icon.isChecked() and self.icon_file:
            cmd.append(f"--windows-icon-from-ico={self.icon_file}")
        if self.show_progress.isChecked():
            cmd.append("--show-progress")
        if self.follow_imports.isChecked():
            cmd.append("--follow-imports")
        if self.remove_output.isChecked():
            cmd.append("--remove-output")
            
        # 添加输出目录
        cmd.append(f"--output-dir={self.output_dir}")
        
        # 添加资源文件夹
        if self.data_dir:
            # 获取资源文件夹的名称作为目标路径
            data_dir_name = os.path.basename(self.data_dir)
            cmd.append(f"--include-data-dir={self.data_dir}={data_dir_name}")
        
        # 添加包含的包
        for i in range(self.packages_list.count()):
            package = self.packages_list.item(i).text()
            cmd.append(f"--include-package={package}")
        
        # 添加高级选项
        advanced_opts = self.advanced_options.toPlainText().strip()
        if advanced_opts:
            cmd.extend(advanced_opts.split("\n"))
            
        # 添加Python文件
        cmd.append(self.python_file)
        
        # 打印命令用于调试
        print("执行命令:", " ".join(cmd))
        
        # 清空日志
        self.log_text.clear()
        
        # 创建并启动打包线程
        self.build_thread = BuildThread(" ".join(cmd))
        self.build_thread.output_ready.connect(self.update_log)
        self.build_thread.finished.connect(self.build_finished)
        self.build_thread.start()
        
    def update_log(self, text):
        self.log_text.append(text)
        # 滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
        
    def build_finished(self, success, message):
        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.warning(self, "信息", message)
        # 恢复打包按钮状态
        self.build_btn.setEnabled(True)
        self.build_btn.setText("开始打包")

def main():
    app = QApplication(sys.argv)
    window = NuitkaGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
