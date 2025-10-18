#!/bin/bash
# 简单的数据库导入脚本

# MySQL 路径
MYSQL_PATH="/usr/local/mysql-9.4.0-macos15-x86_64/bin/mysql"
DB_SQL="/Users/kanyim/portsentinel/Database/db.sql"

echo "=========================================="
echo "PORTNET Database Import"
echo "=========================================="
echo ""

# 检查 MySQL 是否存在
if [ ! -f "$MYSQL_PATH" ]; then
    echo "❌ MySQL not found at: $MYSQL_PATH"
    exit 1
fi

echo "✓ Found MySQL: $MYSQL_PATH"

# 检查 db.sql 是否存在
if [ ! -f "$DB_SQL" ]; then
    echo "❌ db.sql not found at: $DB_SQL"
    exit 1
fi

echo "✓ Found db.sql"
echo ""

# 提示用户输入密码
echo "Please enter your MySQL root password:"
read -s MYSQL_PASSWORD
echo ""

# 测试连接
echo "Testing MySQL connection..."
if ! $MYSQL_PATH -u root -p"$MYSQL_PASSWORD" -e "SELECT 1;" &> /dev/null; then
    echo "❌ MySQL connection failed. Please check your password."
    exit 1
fi

echo "✓ MySQL connection successful"
echo ""

# 创建数据库
echo "Creating database 'portnet'..."
$MYSQL_PATH -u root -p"$MYSQL_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS portnet CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
echo "✓ Database created"
echo ""

# 导入数据
echo "Importing db.sql (this may take a minute)..."
$MYSQL_PATH -u root -p"$MYSQL_PASSWORD" portnet < "$DB_SQL"

if [ $? -eq 0 ]; then
    echo "✓ Import successful"
else
    echo "❌ Import failed"
    exit 1
fi
echo ""

# 验证
echo "Verifying import..."
TABLE_COUNT=$($MYSQL_PATH -u root -p"$MYSQL_PASSWORD" portnet -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'portnet';")
echo "✓ Found $TABLE_COUNT tables"
echo ""

# 显示表列表
echo "Tables in portnet database:"
$MYSQL_PATH -u root -p"$MYSQL_PASSWORD" portnet -e "SHOW TABLES;"
echo ""

echo "=========================================="
echo "✓ Import Complete!"
echo "=========================================="
echo ""
echo "Database connection info:"
echo "  Host: localhost"
echo "  Port: 3306"
echo "  Database: portnet"
echo "  User: root"
echo ""
