#!/bin/bash
#
# 导入 PORTNET 数据库脚本
#

set -e  # 遇到错误立即退出

echo "=========================================="
echo "PORTNET Database Import Script"
echo "=========================================="
echo ""

# 检查 MySQL 是否运行
if ! command -v mysql &> /dev/null; then
    echo "❌ 错误: MySQL 未安装或不在 PATH 中"
    echo "请先安装 MySQL: brew install mysql"
    exit 1
fi

# 检查 db.sql 文件是否存在
DB_SQL_PATH="/Users/kanyim/portsentinel/Database/db.sql"
if [ ! -f "$DB_SQL_PATH" ]; then
    echo "❌ 错误: db.sql 文件不存在"
    echo "路径: $DB_SQL_PATH"
    exit 1
fi

echo "✓ 找到 db.sql 文件"
echo "文件大小: $(ls -lh "$DB_SQL_PATH" | awk '{print $5}')"
echo ""

# 提示用户输入 MySQL 密码
echo "请输入 MySQL root 密码:"
read -s MYSQL_PASSWORD
echo ""

# 测试 MySQL 连接
echo "测试 MySQL 连接..."
if ! mysql -u root -p"$MYSQL_PASSWORD" -e "SELECT 1;" &> /dev/null; then
    echo "❌ 错误: MySQL 连接失败"
    echo "请检查密码是否正确，或 MySQL 服务是否运行"
    echo ""
    echo "检查 MySQL 状态:"
    echo "  brew services list | grep mysql"
    echo ""
    echo "启动 MySQL:"
    echo "  brew services start mysql"
    exit 1
fi

echo "✓ MySQL 连接成功"
echo ""

# 创建数据库
echo "创建数据库 'portnet'..."
mysql -u root -p"$MYSQL_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS portnet CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>&1

if [ $? -eq 0 ]; then
    echo "✓ 数据库创建成功"
else
    echo "⚠ 数据库可能已存在"
fi
echo ""

# 导入 SQL 文件
echo "导入 db.sql..."
mysql -u root -p"$MYSQL_PASSWORD" portnet < "$DB_SQL_PATH" 2>&1

if [ $? -eq 0 ]; then
    echo "✓ SQL 文件导入成功"
else
    echo "❌ SQL 文件导入失败"
    exit 1
fi
echo ""

# 验证导入
echo "验证导入结果..."
TABLE_COUNT=$(mysql -u root -p"$MYSQL_PASSWORD" portnet -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'portnet';" 2>&1)

echo "✓ 数据库中共有 $TABLE_COUNT 个表"
echo ""

# 显示表列表
echo "表列表:"
mysql -u root -p"$MYSQL_PASSWORD" portnet -e "SHOW TABLES;" 2>&1
echo ""

# 显示一些统计信息
echo "数据统计:"
mysql -u root -p"$MYSQL_PASSWORD" portnet -e "
SELECT
    table_name AS 'Table',
    table_rows AS 'Rows'
FROM information_schema.tables
WHERE table_schema = 'portnet'
ORDER BY table_name;
" 2>&1

echo ""
echo "=========================================="
echo "✓ 数据库导入完成!"
echo "=========================================="
echo ""
echo "数据库连接信息:"
echo "  Host: localhost"
echo "  Port: 3306"
echo "  Database: portnet"
echo "  User: root"
echo ""
echo "测试连接:"
echo "  mysql -u root -p portnet"
echo ""
