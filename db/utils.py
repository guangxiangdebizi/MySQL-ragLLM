"""
数据库工具模块 (utils.py)
=======================

该模块提供了一系列数据库操作和管理的工具函数，用于数据库结构分析、交互操作和数据展示。主要功能包括：

核心功能：
    1. 数据库结构分析：获取并格式化数据库表结构和示例数据
    2. 表结构展示：以可视化方式展示数据库表结构
    3. 交互式Shell：提供原生SQL交互环境
    4. 增强数据库分析：提供深度数据库结构分析

主要组件：
    - get_database_structure_with_samples(): 获取数据库结构和示例数据
    - get_enhanced_database_structure(): 获取增强的数据库结构分析
    - display_table_structure(): 展示数据库表结构
    - interactive_shell(): 提供交互式SQL执行环境
    - analyze_table_relationships(): 分析表之间的关系

工作流程：
    1. 数据库结构分析
       - 获取当前数据库信息
       - 分析表结构和关系
       - 收集示例数据
       - 格式化输出结果

    2. 表结构可视化
       - 获取所有表信息
       - 分析字段属性
       - 格式化展示结果

    3. 交互式操作
       - 接收SQL命令
       - 执行查询操作
       - 格式化展示结果
       - 错误处理和反馈
       
    4. 表关系分析
       - 识别主键和外键
       - 建立表之间的关系图
       - 分析索引和约束
       - 提供优化建议

技术特点：
    - 使用字典游标提高数据处理效率
    - 表格化展示提升可读性
    - 完整的错误处理机制
    - 友好的用户交互界面
    - 增强的数据结构分析

依赖项：
    - mysql.connector: MySQL数据库连接
    - tabulate: 表格格式化输出
    - random: 随机数生成
"""

import mysql.connector
from tabulate import tabulate
import random
import json
from collections import defaultdict
import re

def get_database_structure_with_samples(connection):
    """
    获取数据库结构和示例数据，返回格式化的字符串
    """
    try:
        cursor = connection.cursor(dictionary=True)  # 使用字典游标
        
        # 获取当前数据库名称
        cursor.execute("SELECT DATABASE()")
        current_db = cursor.fetchone()['DATABASE()']
        if not current_db:
            return "未选择数据库，请先选择数据库"
        
        # 获取所有表
        cursor.execute("SHOW TABLES")
        tables = [table[f'Tables_in_{current_db}'] for table in cursor.fetchall()]
        
        structure_parts = [f"数据库名称: {current_db}\n"]
        
        for table_name in tables:
            # 获取表结构
            cursor.execute(f"SHOW CREATE TABLE {table_name}")
            create_table = cursor.fetchone()['Create Table']
            
            # 获取列信息
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            
            # 获取示例数据
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            samples = cursor.fetchall()
            
            # 格式化表信息
            table_info = [f"\n表名: {table_name}"]
            table_info.append("\n列信息:")
            for col in columns:
                col_desc = f"  - {col['Field']} ({col['Type']})"
                if col['Key'] == 'PRI':
                    col_desc += " [主键]"
                if col['Key'] == 'MUL':
                    col_desc += " [外键]"
                table_info.append(col_desc)
            
            if samples:
                table_info.append("\n示例数据:")
                for sample in samples:
                    sample_str = "  "
                    for key, value in sample.items():
                        sample_str += f"{key}: {value}, "
                    table_info.append(sample_str.rstrip(", "))
            
            structure_parts.append("\n".join(table_info))
        
        return "\n".join(structure_parts)
        
    except Exception as e:
        print(f"获取数据库结构时出错：{e}")
        return "数据库结构获取失败，请检查数据库连接"
    finally:
        if 'cursor' in locals():
            cursor.close()

def get_enhanced_database_structure(connection):
    """
    获取增强的数据库结构分析，包括表关系、索引、约束和数据统计信息
    """
    try:
        cursor = connection.cursor(dictionary=True)
        
        # 获取当前数据库名称
        cursor.execute("SELECT DATABASE()")
        current_db_result = cursor.fetchone()
        if not current_db_result or not current_db_result['DATABASE()']:
            return "未选择数据库，请先选择数据库"
            
        current_db = current_db_result['DATABASE()']
        
        # 收集数据库结构信息
        db_info = {
            "database_name": current_db,
            "tables": [],
            "relationships": [],
            "database_stats": {}
        }
        
        # 获取所有表
        cursor.execute("SHOW TABLES")
        tables = [table[f'Tables_in_{current_db}'] for table in cursor.fetchall()]
        
        # 收集表详细信息
        for table_name in tables:
            table_info = {
                "name": table_name,
                "columns": [],
                "primary_key": None,
                "foreign_keys": [],
                "indexes": [],
                "row_count": 0,
                "sample_data": []
            }
            
            # 获取表结构
            cursor.execute(f"SHOW CREATE TABLE {table_name}")
            create_table = cursor.fetchone()['Create Table']
            
            # 解析创建表语句获取约束和索引
            # 提取主键
            pk_match = re.search(r'PRIMARY KEY \(`([^`]+)`\)', create_table)
            if pk_match:
                table_info["primary_key"] = pk_match.group(1)
                
            # 提取外键
            fk_matches = re.finditer(r'FOREIGN KEY \(`([^`]+)`\) REFERENCES `([^`]+)`\s*\(`([^`]+)`\)', create_table)
            for match in fk_matches:
                table_info["foreign_keys"].append({
                    "column": match.group(1),
                    "referenced_table": match.group(2),
                    "referenced_column": match.group(3)
                })
                
                # 添加到关系列表
                db_info["relationships"].append({
                    "from_table": table_name,
                    "from_column": match.group(1),
                    "to_table": match.group(2),
                    "to_column": match.group(3)
                })
                
            # 提取索引
            index_matches = re.finditer(r'(UNIQUE )?KEY `([^`]+)`\s*\(`([^`]+)`\)', create_table)
            for match in index_matches:
                table_info["indexes"].append({
                    "name": match.group(2),
                    "columns": match.group(3).split('`,`'),
                    "unique": bool(match.group(1))
                })
            
            # 获取列信息
            cursor.execute(f"DESCRIBE {table_name}")
            columns = cursor.fetchall()
            
            for col in columns:
                column_info = {
                    "name": col['Field'],
                    "type": col['Type'],
                    "nullable": col['Null'] == 'YES',
                    "key": col['Key'],
                    "default": col['Default'],
                    "extra": col['Extra']
                }
                table_info["columns"].append(column_info)
            
            # 获取行数
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                count_result = cursor.fetchone()
                if count_result:
                    table_info["row_count"] = count_result['count']
            except:
                # 如果计数失败，不中断程序
                pass
            
            # 获取示例数据
            try:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                samples = cursor.fetchall()
                if samples:
                    table_info["sample_data"] = samples
            except:
                # 如果获取示例失败，不中断程序
                pass
            
            db_info["tables"].append(table_info)
        
        # 添加统计信息
        db_info["database_stats"] = {
            "table_count": len(tables),
            "total_relationships": len(db_info["relationships"]),
            "largest_tables": []
        }
        
        # 获取最大的表（按行数）
        sorted_tables = sorted(db_info["tables"], key=lambda x: x["row_count"], reverse=True)
        db_info["database_stats"]["largest_tables"] = [
            {"name": t["name"], "row_count": t["row_count"]} 
            for t in sorted_tables[:3] if t["row_count"] > 0
        ]
        
        # 分析数据库和识别可能的架构模式
        db_info["schema_analysis"] = analyze_database_schema(db_info)
        
        # 生成格式化的输出
        output = json.dumps(db_info, indent=2, default=str)
        return db_info
        
    except Exception as e:
        print(f"获取增强数据库结构时出错：{e}")
        return get_database_structure_with_samples(connection)  # 回退到基本结构
    finally:
        if 'cursor' in locals():
            cursor.close()

def analyze_database_schema(db_info):
    """分析数据库架构识别常见模式"""
    analysis = {
        "schema_type": "未知",
        "potential_issues": [],
        "optimization_suggestions": []
    }
    
    tables = db_info["tables"]
    relationships = db_info["relationships"]
    
    # 检查是否为星型模式（一个事实表，多个维度表）
    if len(tables) > 2:
        # 计算每个表的参照次数
        references_count = defaultdict(int)
        for rel in relationships:
            references_count[rel["to_table"]] += 1
        
        # 寻找被多个表引用的表（可能的中心表）
        center_tables = [table for table, count in references_count.items() if count > 1]
        
        if center_tables and len(center_tables) < len(tables) / 3:
            analysis["schema_type"] = "星型模式或雪花模式"
    
    # 检查是否有没有主键的表
    tables_without_pk = [table["name"] for table in tables if not table["primary_key"]]
    if tables_without_pk:
        analysis["potential_issues"].append(f"以下表缺少主键: {', '.join(tables_without_pk)}")
    
    # 检查大表是否有足够的索引
    for table in tables:
        if table["row_count"] > 10000 and len(table["indexes"]) < 2:
            analysis["optimization_suggestions"].append(
                f"表 {table['name']} 包含 {table['row_count']} 行但只有 {len(table['indexes'])} 个索引，考虑添加更多索引"
            )
    
    # 检查是否有孤立表（没有关系的表）
    table_in_relationships = set()
    for rel in relationships:
        table_in_relationships.add(rel["from_table"])
        table_in_relationships.add(rel["to_table"])
    
    isolated_tables = [table["name"] for table in tables if table["name"] not in table_in_relationships]
    if isolated_tables:
        analysis["potential_issues"].append(f"以下表没有与其他表的关系: {', '.join(isolated_tables)}")
    
    return analysis

def format_db_structure_for_prompt(db_info):
    """格式化数据库结构信息，使其适合作为提示词的一部分"""
    output = []
    
    # 数据库基本信息
    output.append(f"数据库名称: {db_info['database_name']}")
    output.append(f"包含 {db_info['database_stats']['table_count']} 个表和 {db_info['database_stats']['total_relationships']} 个表间关系\n")
    
    # 架构分析
    if "schema_analysis" in db_info:
        output.append("架构分析:")
        output.append(f"- 架构类型: {db_info['schema_analysis']['schema_type']}")
        
        if db_info['schema_analysis']['potential_issues']:
            output.append("- 潜在问题:")
            for issue in db_info['schema_analysis']['potential_issues']:
                output.append(f"  * {issue}")
                
        if db_info['schema_analysis']['optimization_suggestions']:
            output.append("- 优化建议:")
            for suggestion in db_info['schema_analysis']['optimization_suggestions']:
                output.append(f"  * {suggestion}")
        output.append("")
    
    # 表结构信息
    for table in db_info["tables"]:
        output.append(f"表: {table['name']} ({table['row_count']} 行)")
        
        # 列信息
        output.append("  列:")
        for col in table["columns"]:
            col_desc = f"  - {col['name']} ({col['type']})"
            
            if col['name'] == table["primary_key"]:
                col_desc += " [主键]"
                
            # 检查此列是否为外键
            is_foreign_key = False
            for fk in table["foreign_keys"]:
                if fk["column"] == col["name"]:
                    col_desc += f" [外键 -> {fk['referenced_table']}.{fk['referenced_column']}]"
                    is_foreign_key = True
            
            if col["nullable"]:
                col_desc += " [可空]"
                
            if col["extra"]:
                col_desc += f" [{col['extra']}]"
                
            output.append(col_desc)
        
        # 索引信息
        if table["indexes"]:
            output.append("  索引:")
            for idx in table["indexes"]:
                idx_type = "唯一索引" if idx["unique"] else "索引"
                output.append(f"  - {idx_type} {idx['name']} 在列 {', '.join(idx['columns'])}")
        
        # 示例数据
        if table["sample_data"]:
            output.append("  示例数据:")
            for i, sample in enumerate(table["sample_data"], 1):
                output.append(f"  - 行 {i}: " + ", ".join([f"{k}={v}" for k, v in sample.items()]))
        
        output.append("")  # 空行分隔表
    
    # 表关系
    if db_info["relationships"]:
        output.append("表关系:")
        for rel in db_info["relationships"]:
            output.append(f"- {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']}")
    
    return "\n".join(output)

def analyze_query_execution(connection, sql_query):
    """
    分析SQL查询执行计划，提供性能洞见
    
    Args:
        connection: 数据库连接
        sql_query: 要分析的SQL查询
        
    Returns:
        str: 格式化的执行计划和分析
    """
    try:
        cursor = connection.cursor(dictionary=True)
        
        # 执行EXPLAIN查询
        cursor.execute(f"EXPLAIN {sql_query}")
        explain_results = cursor.fetchall()
        
        output = ["查询执行计划分析:"]
        
        # 分析执行计划
        potential_issues = []
        for step in explain_results:
            # 检查是否有全表扫描
            if step.get('type') in ['ALL']:
                potential_issues.append(f"表 {step.get('table')} 上有全表扫描，考虑添加索引")
                
            # 检查是否有大量临时表创建
            if step.get('Extra') and 'Using temporary' in step.get('Extra'):
                potential_issues.append("查询使用临时表，可能影响性能")
                
            # 检查是否有文件排序
            if step.get('Extra') and 'Using filesort' in step.get('Extra'):
                potential_issues.append("查询使用文件排序，可能影响性能")
        
        # 格式化执行计划
        output.append(tabulate(explain_results, headers="keys", tablefmt="grid"))
        
        # 添加分析结果
        if potential_issues:
            output.append("\n优化建议:")
            for issue in potential_issues:
                output.append(f"- {issue}")
        else:
            output.append("\n查询执行计划看起来不错，没有明显的性能问题。")
        
        return "\n".join(output)
    except Exception as e:
        return f"分析查询执行计划时出错：{e}"
    finally:
        if 'cursor' in locals():
            cursor.close()

def display_table_structure(connection):
    try:
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()
        if not tables:
            print("\n没有找到任何表。")
            return
        print("\n数据库中的表及其结构：")
        for table in tables:
            print(f"\n表名：{table[0]}")
            cursor.execute(f"DESCRIBE {table[0]};")
            structure = cursor.fetchall()
            print(tabulate(structure, headers=["字段名", "类型", "是否为空", "主键", "默认值", "额外"], tablefmt="grid"))
    except mysql.connector.Error as e:
        print(f"操作失败，错误：{e}")
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()

def interactive_shell(connection):
    try:
        cursor = connection.cursor()
        print("\n欢迎进入 MySQL Shell 模式，输入 SQL 语句并按回车执行，输入 'exit' 或 'quit' 退出。\n")
        while True:
            sql = input("mysql> ").strip()
            if sql.lower() in ['exit', 'quit']:
                print("退出 MySQL Shell 模式")
                break
            try:
                start_time = time.time()
                cursor.execute(sql)
                execution_time = time.time() - start_time
                
                if sql.lower().startswith(("select", "show", "describe", "explain")):
                    rows = cursor.fetchall()
                    headers = [desc[0] for desc in cursor.description]
                    print(tabulate(rows, headers=headers, tablefmt="grid"))
                    print(f"查询完成，返回 {len(rows)} 行记录，耗时: {execution_time:.3f}秒")
                else:
                    rows_affected = cursor.rowcount
                    while cursor.nextset():
                        pass
                    connection.commit()
                    print(f"执行成功！影响了 {rows_affected} 行，耗时: {execution_time:.3f}秒")
            except mysql.connector.Error as e:
                print(f"SQL 错误：{e}")
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()

def analyze_table_relationships(connection):
    """
    分析数据库中表之间的关系，生成关系图谱数据
    
    返回:
        dict: 包含节点和边的图谱数据
    """
    try:
        cursor = connection.cursor(dictionary=True)
        
        # 获取当前数据库名称
        cursor.execute("SELECT DATABASE()")
        current_db_result = cursor.fetchone()
        if not current_db_result or not current_db_result['DATABASE()']:
            return {"error": "未选择数据库"}
            
        current_db = current_db_result['DATABASE()']
        
        # 获取所有表
        cursor.execute("SHOW TABLES")
        tables = [table[f'Tables_in_{current_db}'] for table in cursor.fetchall()]
        
        # 图谱数据
        graph_data = {
            "nodes": [],
            "edges": []
        }
        
        # 添加表节点
        for table_name in tables:
            # 获取表的行数信息
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                row_count = cursor.fetchone()['count']
            except:
                row_count = 0
                
            # 添加表节点
            graph_data["nodes"].append({
                "id": table_name,
                "label": table_name,
                "size": min(30 + (row_count // 100), 100),  # 基于行数的节点大小
                "type": "table"
            })
            
            # 获取表的创建语句来提取外键关系
            cursor.execute(f"SHOW CREATE TABLE {table_name}")
            create_table = cursor.fetchone()['Create Table']
            
            # 提取外键约束
            fk_constraints = []
            for line in create_table.split('\n'):
                line = line.strip()
                if 'FOREIGN KEY' in line:
                    fk_constraints.append(line)
            
            # 解析外键并添加边
            for constraint in fk_constraints:
                # 提取外键列名
                fk_col_match = re.search(r'FOREIGN KEY \(`([^`]+)`\)', constraint)
                if not fk_col_match:
                    continue
                fk_column = fk_col_match.group(1)
                
                # 提取引用表和列
                ref_match = re.search(r'REFERENCES `([^`]+)`\s*\(`([^`]+)`\)', constraint)
                if not ref_match:
                    continue
                    
                ref_table = ref_match.group(1)
                ref_column = ref_match.group(2)
                
                # 添加边
                graph_data["edges"].append({
                    "source": table_name,
                    "target": ref_table,
                    "label": f"{fk_column} -> {ref_column}",
                    "type": "foreign_key"
                })
        
        # 添加列节点和边（较少的表时可启用，表太多会导致图谱太复杂）
        if len(tables) <= 10:  # 限制只在表较少时显示列
            for table_name in tables:
                # 获取表的列信息
                cursor.execute(f"SHOW COLUMNS FROM {table_name}")
                columns = cursor.fetchall()
                
                for column in columns:
                    column_name = column['Field']
                    column_type = column['Type']
                    is_primary = column['Key'] == 'PRI'
                    is_index = column['Key'] in ('MUL', 'UNI')
                    
                    # 创建列节点ID
                    column_id = f"{table_name}.{column_name}"
                    
                    # 添加列节点
                    node_type = "primary_key" if is_primary else "index" if is_index else "column"
                    graph_data["nodes"].append({
                        "id": column_id,
                        "label": column_name,
                        "size": 15,  # 列节点较小
                        "type": node_type,
                        "parent": table_name,  # 父表信息
                        "data_type": column_type
                    })
                    
                    # 添加表到列的边
                    graph_data["edges"].append({
                        "source": table_name,
                        "target": column_id,
                        "type": "has_column"
                    })
        
        return graph_data
                
    except Exception as e:
        print(f"分析表关系时出错：{e}")
        return {"error": str(e)}
    finally:
        if 'cursor' in locals():
            cursor.close()
