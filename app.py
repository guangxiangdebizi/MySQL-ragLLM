"""
Web应用模块 (app.py)
==================

该模块提供了基于Flask的Web服务，实现了数据库查询的RESTful API接口和Web界面。主要功能包括：

核心功能：
    1. Web界面服务：提供现代化的用户交互界面
    2. RESTful API：处理数据库连接和查询请求
    3. AI查询集成：连接AI模型实现自然语言查询
    4. 实时数据处理：处理查询结果并生成响应
    5. 会话管理：使用Flask会话维护对话历史

主要组件：
    - create_connection(): 创建数据库连接
    - index(): 提供主页面路由
    - test_connection(): 测试数据库连接API
    - query(): 处理查询请求API
    - stream_query(): 支持流式响应的查询API

API端点：
    - GET  /: 返回主页面
    - POST /api/test-connection: 测试数据库连接
    - POST /api/stream-query: 流式执行AI辅助查询

工作流程：
    1. Web界面交互
       - 提供HTML页面
       - 处理用户输入
       - 展示查询结果
       - 显示AI解释

    2. 数据库连接管理
       - 验证连接参数
       - 建立数据库连接
       - 获取数据库列表
       - 处理连接错误

    3. 查询处理
       - 接收查询请求
       - 生成SQL语句
       - 执行数据库查询
       - 格式化返回结果

技术特点：
    - 基于Flask框架构建
    - RESTful API设计
    - JSON数据交换
    - 完整的错误处理
    - 支持CORS跨域请求
    - 异步查询处理
    - 流式输出支持
    - 会话历史管理

依赖项：
    - flask: Web框架
    - mysql.connector: MySQL数据库连接
    - llm_interaction: AI模型交互
    - flask_cors: CORS支持
"""

from flask import Flask, render_template, request, jsonify, session, Response, stream_with_context
import mysql.connector
import json
import uuid
import time
import threading
from functools import wraps
from llm_interaction import generate_sql, generate_answer, stream_generate_answer
from db.utils import get_enhanced_database_structure, analyze_table_relationships
import re
import logging
import sys
from io import StringIO
from flask_cors import CORS  # 导入CORS支持
import datetime
import decimal

app = Flask(__name__)
# 启用CORS，允许所有来源的跨域请求
CORS(app)
app.secret_key = 'mysql_ai_tool_secret_key'  # 用于会话加密

# 全局变量存储活跃的数据库连接
active_connections = {}
# 全局变量存储对话历史
conversation_histories = {}
# 连接锁，防止并发问题
connection_lock = threading.Lock()

# 创建内存日志处理器用于捕获日志
class MemoryHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.logs = StringIO()
    
    def emit(self, record):
        self.logs.write(self.format(record) + '\n')
    
    def get_logs(self):
        return self.logs.getvalue()
    
    def clear(self):
        self.logs = StringIO()

# 创建内存日志处理器
memory_handler = MemoryHandler()
memory_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
memory_handler.setLevel(logging.INFO)

# 配置根日志记录器
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(memory_handler)

# 确保日志输出到控制台
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
console_handler.setLevel(logging.INFO)
root_logger.addHandler(console_handler)

# 添加文件日志处理器
try:
    file_handler = logging.FileHandler('mysql_ai_tool.log')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    app.logger.info("日志文件处理器已添加")
except Exception as e:
    app.logger.warning(f"无法创建日志文件: {str(e)}")

# 配置Flask应用日志记录器
app.logger.setLevel(logging.INFO)
if not app.debug:
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    stream_handler.setLevel(logging.INFO)
    app.logger.addHandler(stream_handler)

app.logger.info("应用启动 - 日志系统初始化完成")

def get_session_id():
    """获取或创建会话ID"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

def with_error_handling(f):
    """API错误处理装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            app.logger.error(f"API错误: {str(e)}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    return decorated_function

def create_connection(config):
    """创建数据库连接"""
    try:
        connection = mysql.connector.connect(
            user=config['username'],
            password=config['password'],
            host=config['host'],
            port=int(config['port']),
            database=config.get('database'),
            connect_timeout=10  # 添加连接超时
        )
        return connection
    except Exception as e:
        raise Exception(f"数据库连接失败: {str(e)}")

def get_or_create_connection(config):
    """获取或创建数据库连接，管理连接池"""
    session_id = get_session_id()
    connection_key = json.dumps({k: v for k, v in config.items() if k != 'password'})
    
    with connection_lock:
        # 检查是否已有此连接
        if session_id in active_connections and connection_key in active_connections[session_id]:
            connection = active_connections[session_id][connection_key]
            # 验证连接是否还活着
            if connection.is_connected():
                return connection
            else:
                # 如果断开，删除旧连接
                del active_connections[session_id][connection_key]
        
        # 创建新连接
        connection = create_connection(config)
        
        # 存储连接
        if session_id not in active_connections:
            active_connections[session_id] = {}
        active_connections[session_id][connection_key] = connection
        
        return connection

def get_conversation_history(session_id):
    """获取当前会话的对话历史"""
    if session_id not in conversation_histories:
        conversation_histories[session_id] = []
    return conversation_histories[session_id]

def add_to_conversation_history(session_id, user_question, sql_query):
    """添加对话到历史记录"""
    if session_id not in conversation_histories:
        conversation_histories[session_id] = []
    
    # 限制历史长度为10条
    if len(conversation_histories[session_id]) >= 10:
        conversation_histories[session_id] = conversation_histories[session_id][-9:]
    
    conversation_histories[session_id].append({
        "user": user_question,
        "response": sql_query
    })

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/test-connection', methods=['POST'])
@with_error_handling
def test_connection():
    """测试数据库连接，返回可用的数据库列表"""
    connection = None
    cursor = None
    
    try:
        app.logger.info("=====================")
        app.logger.info("收到 /api/test-connection 请求")
        config = request.json
        
        if not config:
            app.logger.warning("Test Connection - 缺少配置参数")
            return jsonify({'success': False, 'error': '缺少数据库配置'}), 400
            
        try:
            # 直接创建新连接
            app.logger.info("Test Connection - 正在创建新的数据库连接...")
            connection = mysql.connector.connect(
                user=config['username'],
                password=config['password'],
                host=config['host'],
                port=int(config['port']),
                database=config.get('database'),
                connect_timeout=30
            )
            
            if not connection.is_connected():
                raise Exception("无法建立数据库连接")
                
            app.logger.info("Test Connection - 数据库连接成功")
        except Exception as e:
            app.logger.error(f"Test Connection - 连接失败: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
        
        try:
            # 获取所有数据库
            cursor = connection.cursor()
            cursor.execute("SHOW DATABASES")
            databases = [db[0] for db in cursor.fetchall() 
                        if db[0] not in ['information_schema', 'performance_schema', 'mysql', 'sys']]
            
            app.logger.info(f"Test Connection - 成功获取数据库列表，共 {len(databases)} 个数据库")
            
            return jsonify({
                'success': True,
                'databases': databases
            })
        except Exception as e:
            app.logger.error(f"Test Connection - 获取数据库列表失败: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'获取数据库列表失败: {str(e)}'
            })
            
    finally:
        # 确保资源释放
        if cursor:
            try:
                cursor.close()
                app.logger.info("Test Connection - 游标已关闭")
            except Exception as e:
                app.logger.error(f"Test Connection - 关闭游标失败: {str(e)}")
                
        if connection and connection.is_connected():
            try:
                connection.close()
                app.logger.info("Test Connection - 数据库连接已关闭")
            except Exception as e:
                app.logger.error(f"Test Connection - 关闭连接失败: {str(e)}")

@app.route('/api/nl-query', methods=['POST'])
@with_error_handling
def natural_language_query():
    """处理自然语言查询请求，生成并执行SQL"""
    try:
        app.logger.info("=====================")
        app.logger.info("收到 /api/nl-query 请求")
        data = request.json
        user_question = data.get('question')
        config = data.get('config', {})

        app.logger.info(f"自然语言问题: {user_question}")

        if not config or not user_question:
            app.logger.warning("NL Query - 缺少必要参数")
            return jsonify({'error': '缺少配置或问题参数'}), 400

        # 创建数据库连接
        try:
            connection = get_or_create_connection(config)
            app.logger.info("NL Query - 数据库连接成功")
        except Exception as e:
            app.logger.error(f"NL Query - 数据库连接失败: {str(e)}")
            return jsonify({'error': f'数据库连接失败: {str(e)}'}), 500

        # 获取会话历史 (如果需要上下文)
        session_id = get_session_id()
        conversation_history = get_conversation_history(session_id)

        # 调用优化后的 SQL 生成函数
        sql_query = None
        try:
            sql_query = generate_sql(user_question, conversation_history, connection)
            app.logger.info(f"NL Query - SQL生成成功: {sql_query}")
        except (ValueError, RuntimeError, ConnectionError) as e:
            # Catch specific errors from generate_sql
            app.logger.error(f"NL Query - SQL生成失败: {str(e)}")
            return jsonify({'error': f'SQL生成失败: {str(e)}'}), 500
        except Exception as e:
            # Catch any other unexpected errors
            app.logger.error(f"NL Query - SQL生成过程中发生未知错误: {str(e)}", exc_info=True)
            return jsonify({'error': f'SQL生成过程中发生未知错误: {str(e)}'}), 500

        # 执行查询
        results = []
        try:
            app.logger.info(f"NL Query - 开始执行生成的SQL: {sql_query}")
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sql_query)
            if cursor.description:
                results = cursor.fetchall()
            else:
                connection.commit() # Commit if it was a modification
                results = [{"status": "success", "rows_affected": cursor.rowcount}]
            cursor.close()
            app.logger.info(f"NL Query - 查询执行成功，返回 {len(results)} 条记录 (或状态)")
        except mysql.connector.Error as e:
            app.logger.error(f"NL Query - MySQL查询执行错误: {str(e)}")
            try: connection.rollback() 
            except: pass
            return jsonify({'error': f'查询执行错误: {str(e)}'}), 500
        except Exception as e:
            app.logger.error(f"NL Query - 查询执行过程中发生未知错误: {str(e)}", exc_info=True)
            return jsonify({'error': f'查询执行错误: {str(e)}'}), 500

        # 添加到对话历史
        add_to_conversation_history(session_id, user_question, sql_query)

        # 生成回答 (可选，非流式)
        answer = "AI已生成并执行SQL。"
        try:
            app.logger.info("NL Query - 开始生成回答")
            # Pass the original question and results
            answer = generate_answer(user_question, results) 
            app.logger.info("NL Query - 回答生成成功")
        except Exception as e:
            app.logger.error(f"NL Query - 回答生成失败: {str(e)}")
            answer = f"SQL已执行，但无法生成解释。错误: {str(e)}"

        # 构建成功响应
        response_data = {
            'sql': sql_query,
            'results': results,
            'answer': answer
        }
        app.logger.info("NL Query - 请求处理完成")
        return jsonify(response_data)

    except Exception as e:
        app.logger.error(f"处理 NL Query 时发生顶层错误: {str(e)}", exc_info=True)
        return jsonify({'error': f'处理自然语言查询时发生内部错误: {str(e)}'}), 500

@app.route('/api/direct-sql', methods=['POST'])
@with_error_handling
def direct_sql_execution():
    """处理直接 SQL 执行请求"""
    connection = None  # 初始化连接
    cursor = None      # 初始化游标
    try:
        app.logger.info("=====================")
        app.logger.info("收到 /api/direct-sql 请求")
        data = request.json
        sql_query = data.get('sql')
        config = data.get('config', {})

        app.logger.info(f"Direct SQL: {sql_query}")

        if not config or not sql_query:
            app.logger.warning("Direct SQL - 缺少必要参数")
            return jsonify({'error': '缺少配置或SQL参数'}), 400

        # 基本安全性检查
        sql_lower = sql_query.lower().strip()
        if ';' in sql_lower[:-1]: 
             app.logger.warning(f"Direct SQL - 检测到多语句，已拒绝: {sql_query}")
             return jsonify({'error': '不支持执行多个SQL语句'}), 400

        # 创建全新的数据库连接 - 不使用连接池
        try:
            # 直接创建新连接，不使用get_or_create_connection
            app.logger.info("Direct SQL - 正在创建全新的数据库连接...")
            connection = mysql.connector.connect(
                user=config['username'],
                password=config['password'],
                host=config['host'],
                port=int(config['port']),
                database=config.get('database'),
                connect_timeout=30,  # 增加连接超时
                autocommit=False     # 明确设置手动提交事务
            )
            if not connection.is_connected():
                raise Exception("无法建立数据库连接")
                
            app.logger.info("Direct SQL - 已创建新的数据库连接")
        except Exception as e:
            app.logger.error(f"Direct SQL - 创建数据库连接失败: {str(e)}")
            return jsonify({'error': f'数据库连接失败: {str(e)}'}), 500

        # 执行查询
        results = []
        start_time = time.time()
        try:
            app.logger.info(f"Direct SQL - 开始执行: {sql_query}")
            cursor = connection.cursor(dictionary=True)
            
            # 测试连接是否真正可用
            app.logger.info("Direct SQL - 执行测试查询确认连接可用...")
            try:
                test_cursor = connection.cursor()
                test_cursor.execute("SELECT 1")
                test_cursor.fetchall()
                test_cursor.close()
                app.logger.info("Direct SQL - 测试查询成功，连接有效")
            except Exception as test_e:
                app.logger.error(f"Direct SQL - 测试查询失败，连接无效: {str(test_e)}")
                raise Exception(f"数据库连接测试失败: {str(test_e)}")
            
            # 执行实际查询
            cursor.execute(sql_query)
            
            if cursor.description: # 处理 SELECT, SHOW 等返回结果的查询
                results = cursor.fetchall()
                app.logger.info(f"Direct SQL - 查询成功 (有结果集)，返回 {len(results)} 条记录")
            else: # 处理 INSERT, UPDATE, DELETE 等不返回结果的查询
                connection.commit() # 提交事务
                results = [{"status": "success", "rows_affected": cursor.rowcount}]
                app.logger.info(f"Direct SQL - 查询成功 (无结果集)，影响 {cursor.rowcount} 行")

            execution_time = time.time() - start_time
            app.logger.info(f"Direct SQL - 执行耗时: {execution_time:.4f} 秒")

        except mysql.connector.Error as e:
            execution_time = time.time() - start_time
            app.logger.error(f"Direct SQL - MySQL执行错误 (耗时 {execution_time:.4f} 秒): {str(e)}")
            try:
                if connection and connection.is_connected():
                    connection.rollback()
                    app.logger.info("Direct SQL - 事务已回滚")
            except Exception as rb_err:
                app.logger.error(f"Direct SQL - 回滚失败: {str(rb_err)}")
            
            return jsonify({'error': f'SQL执行错误: {str(e)}'}), 500
        
        except Exception as e:
            execution_time = time.time() - start_time
            app.logger.error(f"Direct SQL - 执行过程中发生异常 (耗时 {execution_time:.4f} 秒): {str(e)}")
            try:
                if connection and connection.is_connected():
                    connection.rollback()
            except: pass
            return jsonify({'error': f'执行SQL时发生错误: {str(e)}'}), 500

        finally:
            # 始终确保关闭游标和连接
            if cursor:
                try:
                    cursor.close()
                    app.logger.info("Direct SQL - 游标已关闭")
                except Exception as cur_err:
                    app.logger.error(f"Direct SQL - 关闭游标失败: {str(cur_err)}")
            
            # 现在总是关闭连接，不再保留在连接池中
            if connection:
                try:
                    if connection.is_connected():
                        connection.close()
                        app.logger.info("Direct SQL - 数据库连接已关闭")
                except Exception as conn_err:
                    app.logger.error(f"Direct SQL - 关闭连接失败: {str(conn_err)}")

        # 构建成功响应
        response_data = {
            'sql': sql_query,
            'results': results,
            'answer': 'SQL已直接执行。'
        }
        app.logger.info("Direct SQL - 请求处理完成")
        return jsonify(response_data)

    except Exception as e: # 捕获函数顶层的意外错误
        app.logger.error(f"处理 Direct SQL 时发生顶层错误: {str(e)}", exc_info=True)
        return jsonify({'error': f'处理请求时发生内部服务器错误: {str(e)}'}), 500

@app.route('/api/stream-query', methods=['POST'])
@with_error_handling
def stream_query():
    """流式API，支持逐步返回生成的结果"""
    # 增强日志记录
    app.logger.info("=====================")
    app.logger.info("收到/api/stream-query请求")
    data = request.json
    user_question = data.get('question')
    config = data.get('config', {})
    
    app.logger.info(f"用户问题: {user_question}")
    app.logger.info(f"数据库配置: 用户名={config.get('username')}, 主机={config.get('host')}, 端口={config.get('port')}, 数据库={config.get('database')}")
    
    if not config or not user_question:
        app.logger.error("缺少必要参数")
        return jsonify({'error': '缺少必要参数'}), 400
    
    # 获取会话ID和历史
    session_id = get_session_id()
    conversation_history = get_conversation_history(session_id)
    
    try:
        # 发送准备阶段状态
        def generate():
            # 首先发送准备状态
            app.logger.info("开始流式生成")
            yield json.dumps({
                'type': 'status',
                'data': '准备中'
            }) + '\n'
            
            try:
                # 创建数据库连接
                app.logger.info(f"开始创建数据库连接: {config}")
                connection = get_or_create_connection(config)
                
                # 发送SQL解析阶段状态
                yield json.dumps({
                    'type': 'status',
                    'data': '解析SQL'
                }) + '\n'
                
                # 生成SQL
                app.logger.info(f"开始生成SQL: {user_question}")
                sql_query = generate_sql(user_question, conversation_history, connection=connection)
                app.logger.info(f"生成的SQL: {sql_query}")
                
                # 返回SQL结果
                yield json.dumps({
                    'type': 'sql',
                    'data': sql_query
                }) + '\n'
                
                # 发送查询执行阶段状态
                yield json.dumps({
                    'type': 'status',
                    'data': '执行查询'
                }) + '\n'
                
                # 执行查询
                app.logger.info(f"开始执行SQL查询")
                cursor = connection.cursor(dictionary=True)
                cursor.execute(sql_query)
                results = cursor.fetchall()
                app.logger.info(f"查询执行完成，返回 {len(results)} 条记录")
                
                # 发送结果处理阶段状态
                yield json.dumps({
                    'type': 'status',
                    'data': '处理结果'
                }) + '\n'
                
                # 返回查询结果
                yield json.dumps({
                    'type': 'results',
                    'data': results
                }) + '\n'
                
                # 添加到对话历史
                add_to_conversation_history(session_id, user_question, sql_query)
                
                # 发送解释生成阶段状态
                yield json.dumps({
                    'type': 'status',
                    'data': '生成解释'
                }) + '\n'
                
                # 流式生成回答
                app.logger.info(f"开始生成解释")
                for chunk in stream_generate_answer(user_question, results):
                    yield json.dumps({
                        'type': 'answer_chunk',
                        'data': chunk
                    }) + '\n'
                
                # 发送完成状态
                yield json.dumps({
                    'type': 'status',
                    'data': '完成'
                }) + '\n'
                
                # 最后发送完成标记
                yield json.dumps({
                    'type': 'done'
                }) + '\n'
                
                cursor.close()
                app.logger.info(f"流式查询完成")
            except Exception as e:
                app.logger.error(f"流式查询过程中发生错误: {str(e)}", exc_info=True)
                yield json.dumps({
                    'type': 'error',
                    'data': f"处理查询时出错: {str(e)}"
                }) + '\n'
                raise
        
        return Response(stream_with_context(generate()), 
                        content_type='application/x-ndjson')
    
    except mysql.connector.Error as e:
        app.logger.error(f"数据库错误: {str(e)}", exc_info=True)
        return jsonify({'error': f'数据库错误: {str(e)}'}), 500
    except Exception as e:
        app.logger.error(f"流式查询错误: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-history', methods=['POST'])
@with_error_handling
def clear_history():
    """清除当前会话的对话历史"""
    session_id = get_session_id()
    if session_id in conversation_histories:
        conversation_histories[session_id] = []
    return jsonify({'success': True})

@app.route('/api/db-structure', methods=['POST'])
@with_error_handling
def get_db_structure():
    """获取数据库结构信息用于可视化"""
    try:
        config = request.json
        connection = get_or_create_connection(config)
        
        # 获取增强的数据库结构
        db_info = get_enhanced_database_structure(connection)
        
        return jsonify({
            'success': True,
            'db_structure': db_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/table-relationships', methods=['POST'])
@with_error_handling
def get_table_relationships():
    """获取表关系图谱数据"""
    try:
        config = request.json
        connection = get_or_create_connection(config)
        
        # 分析表关系
        relationships = analyze_table_relationships(connection)
        
        return jsonify({
            'success': True,
            'relationships': relationships
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/table-data', methods=['POST'])
@with_error_handling
def get_table_data():
    """获取表数据用于编辑"""
    try:
        data = request.json
        config = data.get('config')
        table_name = data.get('table')
        page = data.get('page', 1)
        limit = data.get('limit', 20)
        
        if not config or not table_name:
            return jsonify({'error': '缺少必要参数'}), 400
            
        connection = get_or_create_connection(config)
        cursor = connection.cursor(dictionary=True)
        
        # 获取总记录数
        cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        total = cursor.fetchone()['count']
        
        # 计算偏移量
        offset = (page - 1) * limit
        
        # 获取数据
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit} OFFSET {offset}")
        rows = cursor.fetchall()
        
        # 获取表结构
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()
        
        cursor.close()
        
        return jsonify({
            'success': True,
            'data': rows,
            'columns': columns,
            'total': total,
            'page': page,
            'limit': limit
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/update-row', methods=['POST'])
@with_error_handling
def update_row():
    """更新表中的一行数据"""
    try:
        data = request.json
        config = data.get('config')
        table_name = data.get('table')
        row_data = data.get('row')
        primary_key = data.get('primary_key')
        primary_value = data.get('primary_value')
        
        if not all([config, table_name, row_data, primary_key, primary_value]):
            return jsonify({'error': '缺少必要参数'}), 400
            
        connection = get_or_create_connection(config)
        cursor = connection.cursor()
        
        # 构建更新语句
        set_clauses = []
        values = []
        
        for key, value in row_data.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)
            
        values.append(primary_value)
        
        query = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {primary_key} = %s"
        
        # 执行更新
        cursor.execute(query, tuple(values))
        connection.commit()
        
        cursor.close()
        
        return jsonify({
            'success': True,
            'message': '数据更新成功'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/visualize-query', methods=['POST'])
@with_error_handling
def visualize_query():
    """为查询结果生成可视化数据"""
    try:
        data = request.json
        config = data.get('config')
        sql_query = data.get('query')
        
        if not config or not sql_query:
            return jsonify({'error': '缺少必要参数'}), 400
            
        connection = get_or_create_connection(config)
        cursor = connection.cursor(dictionary=True)
        
        # 执行查询
        cursor.execute(sql_query)
        results = cursor.fetchall()
        
        if not results:
            return jsonify({
                'success': True,
                'visualization_type': 'none',
                'message': '查询结果为空，无法生成可视化'
            })
            
        # 分析结果结构以推荐可视化类型
        visualization_type, chart_data = recommend_visualization(results)
        
        cursor.close()
        
        return jsonify({
            'success': True,
            'results': results,
            'visualization_type': visualization_type,
            'chart_data': chart_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/export-chart', methods=['POST'])
@with_error_handling
def export_chart():
    """导出图表数据为JSON格式"""
    try:
        data = request.json
        chart_data = data.get('chart_data')
        chart_type = data.get('chart_type')
        chart_title = data.get('chart_title', '数据图表')
        
        if not chart_data:
            return jsonify({'error': '缺少必要参数'}), 400
            
        # 构建导出格式
        export_data = {
            'title': chart_title,
            'type': chart_type,
            'data': chart_data,
            'exported_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify({
            'success': True,
            'export_data': export_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/close-connections', methods=['POST'])
@with_error_handling
def close_connections():
    """关闭当前会话的所有数据库连接"""
    session_id = get_session_id()
    if session_id in active_connections:
        for connection in active_connections[session_id].values():
            if connection.is_connected():
                connection.close()
        active_connections[session_id] = {}
    return jsonify({'success': True})

@app.before_request
def log_request_info():
    """记录每个请求的详细信息"""
    if request.path.startswith('/api/'):
        app.logger.info("=== 接收到API请求 ===")
        app.logger.info(f"请求路径: {request.path}")
        app.logger.info(f"请求方法: {request.method}")
        app.logger.info(f"请求头: {dict(request.headers)}")
        
        # 记录请求参数
        if request.is_json:
            app.logger.info(f"JSON数据: {request.json}")
        else:
            app.logger.info(f"表单数据: {request.form}")
            app.logger.info(f"查询参数: {request.args}")
            
        # 记录会话ID
        app.logger.info(f"会话ID: {session.get('session_id', '无')}")

@app.before_request
def cleanup_old_sessions():
    """定期清理长时间不活跃的会话"""
    current_time = time.time()
    # 每10分钟执行一次清理
    if not hasattr(app, 'last_cleanup') or current_time - getattr(app, 'last_cleanup', 0) > 600:
        app.last_cleanup = current_time
        
        # 清理超过2小时没有活动的会话
        # 这里简单实现，实际生产环境应该使用更复杂的会话管理
        for session_id in list(active_connections.keys()):
            if session_id not in session:
                for connection in active_connections[session_id].values():
                    if connection.is_connected():
                        connection.close()
                del active_connections[session_id]
                if session_id in conversation_histories:
                    del conversation_histories[session_id]

@app.teardown_appcontext
def cleanup_connections(exception=None):
    """应用上下文结束时的清理函数"""
    try:
        from flask import has_request_context
        if has_request_context():
            session_id = session.get('session_id')
            if session_id and session_id in active_connections:
                # 不在这里关闭连接，保持连接池活跃
                pass
    except Exception:
        # 在没有请求上下文的情况下忽略错误
        pass

def recommend_visualization(results):
    """
    根据查询结果推荐合适的可视化类型
    返回：推荐的可视化类型与处理后的图表数据
    """
    if not results:
        return 'none', {}
        
    # 分析返回的列数
    columns = list(results[0].keys())
    num_columns = len(columns)
    
    # 检查是否每列都是数值型
    numeric_columns = []
    categorical_columns = []
    temporal_columns = []
    
    for col in columns:
        # 检查所有行的这个列的值
        values = [row[col] for row in results if row[col] is not None]
        if not values:
            continue
            
        # 检查是否可能是日期列
        if isinstance(values[0], (str)) and len(values) > 0:
            # 尝试检测日期格式列
            date_patterns = [
                r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
                r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
                r'\d{4}/\d{2}/\d{2}'   # YYYY/MM/DD
            ]
            if any(re.search(pattern, values[0]) for pattern in date_patterns):
                temporal_columns.append(col)
                continue
        
        # 检查数值型
        if all(isinstance(val, (int, float)) for val in values):
            numeric_columns.append(col)
        else:
            categorical_columns.append(col)
    
    # 根据列特性推荐可视化类型
    chart_data = {}
    
    # 情况1: 一个分类列和一个数值列 -> 柱状图
    if len(categorical_columns) == 1 and len(numeric_columns) == 1:
        cat_col = categorical_columns[0]
        num_col = numeric_columns[0]
        
        labels = [str(row[cat_col]) for row in results]
        values = [row[num_col] for row in results]
        
        chart_data = {
            'labels': labels,
            'datasets': [{
                'label': num_col,
                'data': values
            }]
        }
        return 'bar', chart_data
        
    # 情况2: 两个数值列 -> 散点图
    elif len(numeric_columns) >= 2:
        x_col = numeric_columns[0]
        y_col = numeric_columns[1]
        
        points = [{'x': row[x_col], 'y': row[y_col]} for row in results]
        
        chart_data = {
            'datasets': [{
                'label': f'{x_col} vs {y_col}',
                'data': points
            }]
        }
        return 'scatter', chart_data
        
    # 情况3: 一个时间列和一个数值列 -> 折线图
    elif len(temporal_columns) >= 1 and len(numeric_columns) >= 1:
        time_col = temporal_columns[0]
        num_col = numeric_columns[0]
        
        labels = [str(row[time_col]) for row in results]
        values = [row[num_col] for row in results]
        
        chart_data = {
            'labels': labels,
            'datasets': [{
                'label': num_col,
                'data': values
            }]
        }
        return 'line', chart_data
        
    # 情况4: 只有一个数值列 -> 饼图
    elif len(numeric_columns) == 1 and len(results) <= 10:
        num_col = numeric_columns[0]
        
        if len(categorical_columns) > 0:
            cat_col = categorical_columns[0]
            labels = [str(row[cat_col]) for row in results]
        else:
            labels = [f'Item {i+1}' for i in range(len(results))]
            
        values = [row[num_col] for row in results]
        
        chart_data = {
            'labels': labels,
            'datasets': [{
                'data': values
            }]
        }
        return 'pie', chart_data
        
    # 情况5: 表格数据 -> 表格视图
    else:
        return 'table', {'data': results}

@app.route('/api/debug-logs', methods=['GET'])
def get_debug_logs():
    """获取最近的调试日志"""
    logs = memory_handler.get_logs()
    memory_handler.clear()  # 清除日志，避免无限增长
    return jsonify({'logs': logs})

@app.after_request
def log_response(response):
    """记录每个请求的响应状态"""
    app.logger.info(f"请求: {request.path} - 状态码: {response.status_code}")
    return response

@app.route('/api/test-llm-connection', methods=['GET'])
@with_error_handling
def test_llm_connection():
    """测试LLM API连接是否正常工作"""
    app.logger.info("收到/api/test-llm-connection请求")
    try:
        from config import test_api_connection
        success, message = test_api_connection()
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        app.logger.error(f"测试LLM连接失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/query', methods=['POST'])
@with_error_handling
def query():
    """执行SQL查询并返回结果"""
    connection = None
    cursor = None
    
    try:
        data = request.json
        sql = data.get('sql', '')
        config = data.get('config', {})
        
        app.logger.info("=====================")
        app.logger.info(f"收到 /api/query 请求: {sql}")
        app.logger.info(f"配置信息: {json.dumps({k: ('***' if k == 'password' else v) for k, v in config.items()})}")
        
        if not sql or not config:
            app.logger.warning("Query - 缺少SQL或数据库配置")
            return jsonify({'success': False, 'error': '缺少SQL或数据库配置'})
            
        # 记录搜索历史
        if 'user_id' in session:
            user_id = session['user_id']
            save_query_history(user_id, sql)
        
        # 直接创建新连接
        try:
            app.logger.info("Query - 正在创建新的数据库连接...")
            
            # 验证配置必要字段
            required_fields = ['username', 'password', 'host', 'port']
            for field in required_fields:
                if field not in config or not config[field]:
                    raise ValueError(f"配置缺少必要字段: {field}")
                    
            connection = mysql.connector.connect(
                user=config['username'],
                password=config['password'],
                host=config['host'],
                port=int(config['port']),
                database=config.get('database', ''),
                connect_timeout=30,
                use_pure=True,  # 使用纯Python实现，提高兼容性
                autocommit=False
            )
            
            # 确认连接有效
            if not connection.is_connected():
                raise Exception("连接创建后状态检查失败")
                
            app.logger.info("Query - 数据库连接创建成功")
            
            # 预热连接
            test_cursor = connection.cursor()
            test_cursor.execute("SELECT 1")
            test_cursor.fetchall()
            test_cursor.close()
            app.logger.info("Query - 连接预热测试成功")
            
        except Exception as e:
            app.logger.error(f"Query - 连接失败: {str(e)}")
            if connection:
                try:
                    connection.close()
                except:
                    pass
            return jsonify({
                'success': False,
                'error': f'数据库连接错误: {str(e)}'
            })
        
        # 执行SQL
        try:
            cursor = connection.cursor(dictionary=True)
            start_time = time.time()
            
            # 记录正在执行的SQL
            app.logger.info(f"Query - 执行SQL: {sql}")
            
            cursor.execute(sql)
            
            # 对于非SELECT语句，获取影响的行数
            if sql.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP')):
                result = {'rowCount': cursor.rowcount, 'rows': []}
                connection.commit()
                app.logger.info(f"Query - 非SELECT查询执行成功，影响行数: {cursor.rowcount}")
            else:
                rows = cursor.fetchall()
                # 将MySQL类型转换为JSON可序列化类型
                processed_rows = []
                for row in rows:
                    processed_row = {}
                    for key, value in row.items():
                        if isinstance(value, (datetime.date, datetime.datetime)):
                            processed_row[key] = value.isoformat()
                        elif isinstance(value, decimal.Decimal):
                            processed_row[key] = float(value)
                        else:
                            processed_row[key] = value
                    processed_rows.append(processed_row)
                
                result = {'rowCount': len(processed_rows), 'rows': processed_rows}
                app.logger.info(f"Query - SELECT查询执行成功，返回行数: {len(processed_rows)}")
                
            execution_time = time.time() - start_time
            
            return jsonify({
                'success': True,
                'result': result,
                'execution_time': execution_time
            })
        except Exception as e:
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            app.logger.error(f"Query - 执行SQL失败: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'SQL执行错误: {str(e)}'
            })
    finally:
        # 确保资源释放
        if cursor:
            try:
                cursor.close()
                app.logger.info("Query - 游标已关闭")
            except Exception as e:
                app.logger.error(f"Query - 关闭游标失败: {str(e)}")
                
        if connection:
            try:
                if connection.is_connected():
                    connection.close()
                    app.logger.info("Query - 数据库连接已关闭")
            except Exception as e:
                app.logger.error(f"Query - 关闭连接失败: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True) 