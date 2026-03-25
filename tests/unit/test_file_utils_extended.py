# -*- coding: utf-8 -*-
"""FileUtils扩展单元测试"""
import pytest
import sys
import types
import importlib.util
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent / "backend"

# 先加载 base_manager
base_manager_path = backend_dir / "base_manager.py"
spec = importlib.util.spec_from_file_location("backend.base_manager", base_manager_path)
base_manager = importlib.util.module_from_spec(spec)
sys.modules["backend.base_manager"] = base_manager
spec.loader.exec_module(base_manager)

# 创建 backend 包
backend_mod = types.ModuleType("backend")
backend_mod.__path__ = [str(backend_dir)]
backend_mod.base_manager = base_manager
sys.modules["backend"] = backend_mod

# 手动加载 file_utils 并修复相对导入
file_utils_path = backend_dir / "file_utils.py"
file_utils_content = file_utils_path.read_text(encoding='utf-8')
file_utils_content = file_utils_content.replace(
    "from .base_manager import BaseManager",
    "# from .base_manager import BaseManager  # 被测试替换"
)

# 编译并执行模块
file_utils = types.ModuleType("file_utils")
file_utils.__file__ = str(file_utils_path)
sys.modules["file_utils"] = file_utils
exec(compile(file_utils_content, str(file_utils_path), 'exec'), file_utils.__dict__)

FileUtils = file_utils.FileUtils
TempFileManager = file_utils.TempFileManager
safe_file_operation = file_utils.safe_file_operation
get_temp_manager = file_utils.get_temp_manager


class TestFileUtilsExtended:
    """FileUtils扩展测试"""
    
    def test_sanitize_filename_with_unicode(self, temp_dir):
        """测试文件名清理（含Unicode字符）"""
        result = FileUtils.sanitize_filename("文件name.txt")
        assert "文件" in result  # 保留中文字符
        assert result.endswith(".txt")

    def test_sanitize_filename_only_dots(self, temp_dir):
        """测试只有点的文件名"""
        result = FileUtils.sanitize_filename("...")
        assert not result.startswith(".") or result == "file_"

    def test_sanitize_filename_with_spaces(self, temp_dir):
        """测试带空格的文件名"""
        result = FileUtils.sanitize_filename("  file name  .txt  ")
        assert result.strip() == result  # 前后空格应被处理

    def test_is_path_traversal_with_encoded(self, temp_dir):
        """测试编码路径遍历"""
        # 测试URL编码的路径遍历（如果实现支持的话）
        # 注意：当前实现可能不支持URL编码检测
        # 这里测试一般的路径遍历
        assert FileUtils.is_path_traversal("../etc/passwd") == True
        assert FileUtils.is_path_traversal("..\\..\\windows\\system32") == True

    def test_is_path_traversal_absolute_path(self, temp_dir):
        """测试绝对路径"""
        # 绝对路径不应该被视为路径遍历
        assert FileUtils.is_path_traversal("/absolute/path/file.pdf") == False

    def test_safe_join_with_traversal_in_middle(self, temp_dir):
        """测试路径遍历在中间"""
        base = str(temp_dir)
        result = FileUtils.safe_join(base, "subdir", "..", "..", "etc", "passwd", base_dir=base)
        assert result is None

    def test_safe_join_empty_paths(self, temp_dir):
        """测试空路径拼接"""
        result = FileUtils.safe_join()
        assert result is None

    def test_safe_join_single_path(self, temp_dir):
        """测试单一路径"""
        result = FileUtils.safe_join("/single/path")
        assert result is not None

    def test_validate_file_type_directory(self, temp_dir):
        """测试验证目录（非文件）"""
        test_dir = temp_dir / "testdir"
        test_dir.mkdir()
        
        valid, msg = FileUtils.validate_file_type(str(test_dir))
        assert valid is False
        assert "不是有效文件" in msg

    def test_validate_file_size_nonexistent(self, temp_dir):
        """测试验证不存在文件的大小"""
        valid, msg = FileUtils.validate_file_size(str(temp_dir / "nonexistent.pdf"))
        assert valid is False
        assert "不存在" in msg

    def test_validate_file_size_custom_max(self, temp_dir):
        """测试自定义最大文件大小"""
        test_file = temp_dir / "large.pdf"
        test_file.write_bytes(b"%PDF-1.4 " + b"x" * 1000)
        
        # 设置很小的最大大小
        valid, msg = FileUtils.validate_file_size(str(test_file), max_size=100)
        assert valid is False
        assert "文件过大" in msg

    def test_validate_file_with_traversal(self, temp_dir):
        """测试验证包含路径遍历的文件"""
        valid, errors = FileUtils.validate_file("../etc/passwd")
        assert valid is False
        assert any("非法路径" in e for e in errors)

    def test_temp_file_manager_init_with_custom_dir(self, temp_dir):
        """测试临时文件管理器使用自定义目录"""
        custom_dir = temp_dir / "custom_temp"
        custom_dir.mkdir()
        
        tm = TempFileManager(str(custom_dir))
        path = tm.create_temp_file()
        
        assert Path(path).exists()
        assert str(custom_dir) in path

    def test_temp_file_manager_cleanup_nonexistent(self, temp_dir):
        """测试清理不存在的文件"""
        tm = TempFileManager(str(temp_dir))
        
        # 清理不存在的文件不应该报错
        tm.cleanup_file(str(temp_dir / "nonexistent.txt"))

    def test_temp_file_manager_get_managed_files_empty(self, temp_dir):
        """测试获取空管理文件列表"""
        tm = TempFileManager(str(temp_dir))
        files = tm.get_managed_files()
        assert files == []

    def test_safe_file_operation_context(self, temp_dir):
        """测试安全文件操作上下文"""
        with safe_file_operation(str(temp_dir)) as ops:
            assert "temp_file" in ops
            assert "temp_dir" in ops
            assert "sanitize" in ops
            assert "safe_join" in ops
            assert "validate" in ops
            
            # 创建临时文件
            temp_path = ops["temp_file"](suffix=".txt")
            assert Path(temp_path).exists()

    def test_get_temp_manager_singleton(self):
        """测试全局临时文件管理器单例"""
        tm1 = get_temp_manager()
        tm2 = get_temp_manager()
        assert tm1 is tm2

    def test_temp_file_manager_context_exception(self, temp_dir):
        """测试上下文管理器处理异常"""
        temp_file_path = None
        try:
            with TempFileManager(str(temp_dir)) as tm:
                temp_file_path = tm.create_temp_file()
                assert Path(temp_file_path).exists()
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # 即使发生异常，文件也应该被清理
        if temp_file_path:
            assert not Path(temp_file_path).exists()

    def test_sanitize_filename_special_chars_all(self, temp_dir):
        """测试清理所有特殊字符"""
        special = 'file</\\:\\*?"<>|>.txt'
        result = FileUtils.sanitize_filename(special)
        assert '/' not in result
        assert '\\' not in result
        assert ':' not in result
        assert '*' not in result
        assert '?' not in result
        assert '"' not in result
        assert '<' not in result
        assert '>' not in result
        assert '|' not in result
