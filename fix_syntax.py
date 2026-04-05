#!/usr/bin/env python3
"""
修复Python文件中的语法错误。
"""

import ast
import sys

def check_file(filepath):
    """检查文件的语法并报告问题。"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 移除BOM（如果存在）
        if content.startswith('\ufeff'):
            content = content[1:]
        
        # 尝试解析
        ast.parse(content)
        print(f"✅ {filepath}: 语法正确")
        return True
    except SyntaxError as e:
        print(f"❌ {filepath}: 语法错误")
        print(f"   行号: {e.lineno}, 列号: {e.offset}")
        print(f"   错误: {e.msg}")
        
        # 读取有问题的行
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if e.lineno <= len(lines):
            problem_line = lines[e.lineno-1].rstrip()
            print(f"   问题行: {problem_line}")
            
            # 高亮问题字符位置
            if e.offset and e.offset <= len(problem_line):
                indent = " " * (11 + len(str(e.lineno)) + 2)
                marker = indent + " " * (e.offset-1) + "^"
                print(f"   位置: {marker}")
        
        return False
    except Exception as e:
        print(f"⚠️  {filepath}: 检查时出错 - {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    print("检查Python文件语法...")
    files_to_check = [
        "src/models/session.py",
        "src/storage/file_manager.py",
        "src/ai/recommendation_templates.py"
    ]
    
    all_passed = True
    for filepath in files_to_check:
        if not check_file(filepath):
            all_passed = False
    
    if all_passed:
        print("\n✅ 所有语法检查通过！")
        sys.exit(0)
    else:
        print("\n❌ 发现有语法错误，请修复。")
        sys.exit(1)