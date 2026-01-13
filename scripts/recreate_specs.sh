#!/bin/bash

# LeanSpec 规范重新创建脚本
# 此脚本使用 lean-spec 工具重新创建所有规范

set -e

cd "$(dirname "$0")/.."

echo "🚀 开始重新创建 LeanSpec 规范..."
echo ""

# 检查 lean-spec 是否可用
if ! command -v lean-spec &> /dev/null; then
    echo "❌ lean-spec 命令未找到，尝试使用 npx..."
    LEAN_SPEC_CMD="npx -y lean-spec"
else
    LEAN_SPEC_CMD="lean-spec"
fi

echo "使用命令: $LEAN_SPEC_CMD"
echo ""

# 1. 创建核心 RPC 服务规范
echo "📝 创建 browser-rpc-core 规范..."
$LEAN_SPEC_CMD create browser-rpc-core --tags core,rpc,browser-automation --priority high
# 获取实际的规范名称
CORE_SPEC=$(ls specs | grep "browser-rpc-core" | head -n 1)
echo "✅ browser-rpc-core 创建为: $CORE_SPEC"
echo ""

# 2. 创建分布式架构规范
echo "📝 创建 distributed-architecture 规范..."
$LEAN_SPEC_CMD create distributed-architecture --tags architecture,gateway,load-balancing --priority medium
ARCH_SPEC=$(ls specs | grep "distributed-architecture" | head -n 1)
echo "✅ distributed-architecture 创建为: $ARCH_SPEC"
sleep 1
$LEAN_SPEC_CMD link "$ARCH_SPEC" --depends-on "$CORE_SPEC" || echo "⚠️  链接失败，可能需要手动链接"
echo ""

# 3. 创建监控规范
echo "📝 创建 monitoring-observability 规范..."
$LEAN_SPEC_CMD create monitoring-observability --tags monitoring,prometheus,observability --priority medium
MONITOR_SPEC=$(ls specs | grep "monitoring-observability" | head -n 1)
echo "✅ monitoring-observability 创建为: $MONITOR_SPEC"
sleep 1
$LEAN_SPEC_CMD link "$MONITOR_SPEC" --depends-on "$CORE_SPEC" || echo "⚠️  链接失败"
$LEAN_SPEC_CMD link "$MONITOR_SPEC" --depends-on "$ARCH_SPEC" || echo "⚠️  链接失败"
echo ""

# 4. 创建地域路由规范
echo "📝 创建 region-aware-routing 规范..."
$LEAN_SPEC_CMD create region-aware-routing --tags routing,region,zone --priority low
ROUTING_SPEC=$(ls specs | grep "region-aware-routing" | head -n 1)
echo "✅ region-aware-routing 创建为: $ROUTING_SPEC"
sleep 1
$LEAN_SPEC_CMD link "$ROUTING_SPEC" --depends-on "$ARCH_SPEC" || echo "⚠️  链接失败"
echo ""

# 5. 创建 K8s 部署规范
echo "📝 创建 kubernetes-deployment 规范..."
$LEAN_SPEC_CMD create kubernetes-deployment --tags k8s,deployment,infrastructure --priority medium
K8S_SPEC=$(ls specs | grep "kubernetes-deployment" | head -n 1)
echo "✅ kubernetes-deployment 创建为: $K8S_SPEC"
sleep 1
$LEAN_SPEC_CMD link "$K8S_SPEC" --depends-on "$ARCH_SPEC" || echo "⚠️  链接失败"
$LEAN_SPEC_CMD link "$K8S_SPEC" --depends-on "$MONITOR_SPEC" || echo "⚠️  链接失败"
echo ""

# 6. 更新已完成规范的状态
echo "📝 更新规范状态为 complete..."
$LEAN_SPEC_CMD update "$CORE_SPEC" --status complete
$LEAN_SPEC_CMD update "$ARCH_SPEC" --status complete
$LEAN_SPEC_CMD update "$MONITOR_SPEC" --status complete
$LEAN_SPEC_CMD update "$ROUTING_SPEC" --status complete
$LEAN_SPEC_CMD update "$K8S_SPEC" --status complete
echo "✅ 所有规范状态已更新"
echo ""

# 7. 验证
echo "📊 验证创建结果..."
echo ""
echo "规范列表:"
$LEAN_SPEC_CMD list
echo ""
echo "项目看板:"
$LEAN_SPEC_CMD board
echo ""

echo "✅ 所有规范创建完成！"
echo ""
echo "💡 提示: 现在可以使用以下命令查看规范:"
echo "   - lean-spec board  # 查看项目看板"
echo "   - lean-spec list    # 列出所有规范"
echo "   - lean-spec view <name>  # 查看特定规范"

