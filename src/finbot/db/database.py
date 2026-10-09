import asyncpg
import logging
from datetime import datetime

db_pool = None

async def init_db_pool(database_url: str):
    global db_pool
    db_pool = await asyncpg.create_pool(database_url)
    await init_tables()
    return db_pool

async def init_tables():
    async with db_pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS financial_records (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                period DATE NOT NULL,
                revenue DECIMAL(15, 2) DEFAULT 0,
                fixed_costs DECIMAL(15, 2) DEFAULT 0,
                variable_costs DECIMAL(15, 2) DEFAULT 0,
                taxes DECIMAL(15, 2) DEFAULT 0,
                marketing_budget DECIMAL(15, 2) DEFAULT 0,
                new_customers INTEGER DEFAULT 0,
                inventory_value DECIMAL(15, 2) DEFAULT 0,
                UNIQUE(user_id, period)
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS product_sales (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                period DATE NOT NULL,
                product_name VARCHAR(255) NOT NULL,
                quantity_sold INTEGER DEFAULT 0,
                product_revenue DECIMAL(15, 2) DEFAULT 0,
                product_cost DECIMAL(15, 2) DEFAULT 0,
                stock_qty INTEGER DEFAULT 0,
                UNIQUE(user_id, period, product_name)
            );
        ''')
        
        try:
            await conn.execute('ALTER TABLE product_sales ADD COLUMN stock_qty INTEGER DEFAULT 0;')
        except asyncpg.exceptions.DuplicateColumnError:
            pass
            
        logging.info("Таблицы БД успешно проверены/созданы!")

async def add_user(telegram_id: int, username: str):
    async with db_pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (telegram_id, username) 
            VALUES ($1, $2) 
            ON CONFLICT (telegram_id) DO NOTHING
        ''', telegram_id, username)

async def insert_financial_records(telegram_id: int, records: list):
    async with db_pool.acquire() as conn:
        user_id = await conn.fetchval('SELECT id FROM users WHERE telegram_id = $1', telegram_id)
        if not user_id:
            return
        
        query = '''
            INSERT INTO financial_records 
            (user_id, period, revenue, fixed_costs, variable_costs, taxes, marketing_budget, new_customers, inventory_value)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (user_id, period) DO UPDATE SET
                revenue = EXCLUDED.revenue,
                fixed_costs = EXCLUDED.fixed_costs,
                variable_costs = EXCLUDED.variable_costs,
                taxes = EXCLUDED.taxes,
                marketing_budget = EXCLUDED.marketing_budget,
                new_customers = EXCLUDED.new_customers,
                inventory_value = EXCLUDED.inventory_value
        '''
        args = [(user_id,) + r for r in records]
        await conn.executemany(query, args)

async def insert_product_sales(telegram_id: int, records: list):
    async with db_pool.acquire() as conn:
        user_id = await conn.fetchval('SELECT id FROM users WHERE telegram_id = $1', telegram_id)
        if not user_id:
            return
        
        query = '''
            INSERT INTO product_sales 
            (user_id, period, product_name, quantity_sold, product_revenue, product_cost, stock_qty)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (user_id, period, product_name) DO UPDATE SET
                quantity_sold = EXCLUDED.quantity_sold,
                product_revenue = EXCLUDED.product_revenue,
                product_cost = EXCLUDED.product_cost,
                stock_qty = EXCLUDED.stock_qty
        '''
        args = [(user_id,) + r for r in records]
        await conn.executemany(query, args)

async def get_financial_records(telegram_id: int):
    async with db_pool.acquire() as conn:
        user_id = await conn.fetchval('SELECT id FROM users WHERE telegram_id = $1', telegram_id)
        if not user_id:
            return []
        
        return await conn.fetch('''
            SELECT period, revenue, fixed_costs, variable_costs, taxes, marketing_budget, new_customers, inventory_value
            FROM financial_records WHERE user_id = $1 ORDER BY period ASC
        ''', user_id)

async def get_product_sales(telegram_id: int):
    async with db_pool.acquire() as conn:
        user_id = await conn.fetchval('SELECT id FROM users WHERE telegram_id = $1', telegram_id)
        if not user_id:
            return []
        
        return await conn.fetch('''
            SELECT period, product_name, quantity_sold, product_revenue, product_cost, stock_qty
            FROM product_sales WHERE user_id = $1 ORDER BY period ASC
        ''', user_id)

async def add_micro_transaction(telegram_id: int, amount: float, category: str):
    
    allowed_categories = ["revenue", "fixed_costs", "variable_costs", "marketing_budget"]
    if category not in allowed_categories:
        logging.error(f"Недопустимая категория: {category}")
        return

    now = datetime.now()
    current_period = now.date().replace(day=1)

    async with db_pool.acquire() as conn:
        user_id = await conn.fetchval('SELECT id FROM users WHERE telegram_id = $1', telegram_id)
        if not user_id:
            return

        query = f'''
            INSERT INTO financial_records (user_id, period, {category}) 
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, period) DO UPDATE SET 
                {category} = financial_records.{category} + EXCLUDED.{category}
        '''
        await conn.execute(query, user_id, current_period, amount)

async def clear_user_data(telegram_id: int):
    async with db_pool.acquire() as conn:
        user_id = await conn.fetchval('SELECT id FROM users WHERE telegram_id = $1', telegram_id)
        if user_id:
            await conn.execute('DELETE FROM financial_records WHERE user_id = $1', user_id)
            await conn.execute('DELETE FROM product_sales WHERE user_id = $1', user_id)

async def get_all_users():
    async with db_pool.acquire() as conn:
        return await conn.fetch('SELECT telegram_id FROM users')
