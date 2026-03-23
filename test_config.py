import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.config import get_settings
from app.database import engine
from sqlalchemy import text

settings = get_settings()

async def test_db_connection():
    print("=" * 50)
    print("配置检查")
    print("=" * 50)
    print(f"DATABASE_URL: {settings.DATABASE_URL}")
    print(f"REDIS_URL: {settings.REDIS_URL}")
    print(f"DEEPSEEK_API_KEY: {'已配置' if settings.DEEPSEEK_API_KEY else '未配置'}")
    print(f"VOLCANO_APP_ID: {'已配置' if settings.VOLCANO_APP_ID else '未配置'}")
    print(f"VOLCANO_ACCESS_TOKEN: {'已配置' if settings.VOLCANO_ACCESS_TOKEN else '未配置'}")
    print()
    
    print("=" * 50)
    print("测试数据库连接...")
    print("=" * 50)
    
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ MySQL 连接成功！")
            print(f"测试查询: SELECT 1 = {result.scalar()}")
            
            result = await conn.execute(text("SELECT VERSION()"))
            print(f"MySQL 版本: {result.scalar()}")
            
            result = await conn.execute(text("SELECT DATABASE()"))
            print(f"当前数据库: {result.scalar()}")
            
        print()
        print("=" * 50)
        print("✅ 所有检查通过！")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        print()
        print("请检查:")
        print("  1. MySQL 服务是否已启动")
        print("  2. 用户名、密码是否正确")
        print("  3. 数据库 'vibeing_code' 是否存在")
        print("  4. 用户 'root' 是否有访问权限")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_db_connection())
