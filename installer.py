import PyInstaller.__main__

if __name__ == '__main__':
    PyInstaller.__main__.run([
        "--onedir",
        "--windowed",
        "--name", "SurveyCTO Convertor",
        "--icon", "assets/icon.ico",
        "main.py"
    ])