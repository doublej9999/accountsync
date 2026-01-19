#!/bin/bash
# AccountSync项目离线安装脚本
# 使用方法: chmod +x install.sh && ./install.sh

echo "开始离线安装AccountSync项目依赖..."

# 检查Python版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "当前Python版本: $python_version"

# 创建虚拟环境（可选）
read -p "是否创建虚拟环境？(y/n): " create_venv
if [ "$create_venv" = "y" ] || [ "$create_venv" = "Y" ]; then
    python3 -m venv venv
    source venv/bin/activate
    echo "虚拟环境已创建并激活"
fi

# 离线安装依赖
echo "安装依赖包..."
pip install --no-index --find-links=./packages -r requirements.txt

# 验证安装
echo "验证安装..."
python3 -c "import django; print(f'Django版本: {django.VERSION}')"

echo "依赖安装完成！"
echo ""
echo "后续步骤："
echo "1. 配置数据库连接"
echo "2. 运行 python manage.py migrate"
echo "3. 创建超级用户: python manage.py createsuperuser"
echo "4. 启动开发服务器: python manage.py runserver"