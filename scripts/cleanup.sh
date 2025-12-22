#!/bin/bash
# 项目清理脚本
# 删除日志、缓存、临时文件等

set -e

echo "=========================================="
echo "Browser RPC - 项目清理"
echo "=========================================="

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# 1. 删除日志文件
echo ""
echo "1. 删除日志文件..."
find . -name "*.log" -type f -not -path "./.git/*" -delete
echo "   ✅ 日志文件已删除"

# 2. 删除 Python 缓存
echo ""
echo "2. 删除 Python 缓存..."
find . -type d -name "__pycache__" -not -path "./.git/*" -exec rm -r {} + 2>/dev/null || true
find . -name "*.pyc" -not -path "./.git/*" -delete 2>/dev/null || true
find . -name "*.pyo" -not -path "./.git/*" -delete 2>/dev/null || true
echo "   ✅ Python 缓存已删除"

# 3. 删除截图文件（保留 resources/stealth 中的文件）
echo ""
echo "3. 删除测试截图..."
find . -name "*.png" -type f -not -path "./.git/*" \
  -not -path "./resources/stealth/*" \
  -not -path "./static/*" \
  -delete 2>/dev/null || true
echo "   ✅ 测试截图已删除"

# 4. 删除其他临时文件
echo ""
echo "4. 删除临时文件..."
find . -name "*.tmp" -not -path "./.git/*" -delete 2>/dev/null || true
find . -name "*.bak" -not -path "./.git/*" -delete 2>/dev/null || true
find . -name "*.orig" -not -path "./.git/*" -delete 2>/dev/null || true
find . -name ".DS_Store" -not -path "./.git/*" -delete 2>/dev/null || true
echo "   ✅ 临时文件已删除"

# 5. 清理空的日志目录（保留目录结构）
echo ""
echo "5. 清理日志目录..."
if [ -d "log" ]; then
    find log -type f -name "*.log" -delete 2>/dev/null || true
    echo "   ✅ 日志目录已清理"
fi

echo ""
echo "=========================================="
echo "✅ 清理完成！"
echo "=========================================="
echo ""
echo "注意: 以下文件/目录已被 .gitignore 忽略，不会提交到 Git:"
echo "  - 所有 .log 文件"
echo "  - 所有 __pycache__ 目录"
echo "  - 所有 .png 截图文件（除了 resources/stealth/）"
echo ""

