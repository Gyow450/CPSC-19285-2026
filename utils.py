import os
import sys

def resource_path(relative_path: str) -> str:
    """
    兼容开发环境和 Nuitka 编译后的资源路径。
    Nuitka standalone/onefile 模式下，sys.executable 指向 exe 所在目录。
    """
    if getattr(sys, "frozen", False):
        # Nuitka 编译后：exe 所在目录就是根目录
        base_path = os.path.dirname(sys.executable)
    else:
        # 开发环境：从 src/utils.py 回溯到项目根目录
        base_path = os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(base_path) == "src":
            base_path = os.path.dirname(base_path)
    
    return os.path.join(base_path, relative_path)