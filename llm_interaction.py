"""
LLM交互模块 (llm_interaction.py)
============================

该模块负责处理与大语言模型(LLM)的所有交互操作，是系统的AI核心组件。主要功能包括：

核心功能：
    1. SQL生成：将用户的自然语言问题转换为SQL查询
    2. 结果解释：将SQL查询结果转换为自然语言解释
    3. 交互式Shell：提供AI辅助的MySQL交互环境
    4. 流式输出：支持实时流式生成响应

主要组件：
    - generate_sql(): 负责SQL生成的核心函数
    - generate_answer(): 负责生成查询结果的自然语言解释
    - stream_generate_answer(): 提供流式结果解释
    - ai_interactive_shell(): 提供交互式的AI查询环境

工作流程：
    1. 接收用户输入 -> 理解意图 -> 生成SQL -> 执行查询 -> 解释结果
    2. 使用多级模板系统进行提示词管理
    3. 支持流式输出，提供实时反馈
    4. 维护对话历史，支持上下文理解

技术特点：
    - 使用GLM-4-AIR模型进行自然语言处理
    - 集成错误处理和异常管理
    - 支持数据库结构感知
    - 实现流式输出功能
    - 历史对话上下文理解
    - 深度数据库结构分析
    - 智能SQL生成优化

依赖项：
    - openai: OpenAI API客户端
    - mysql.connector: MySQL数据库连接
    - tabulate: 表格格式化输出
"""
from openai import OpenAI
from config import API_KEY, BASE_URL, MODEL_NAME
from utils.prompts import sql_prompt, extract_sql_prompt, clarify_prompt, answer_prompt, enhanced_clarify_prompt
from tabulate import tabulate
import mysql.connector
import time
import re
import traceback
from db.utils import get_database_structure_with_samples, get_enhanced_database_structure

# 全局变量，但不立即初始化
client = None

def get_client():
    """
    惰性初始化OpenAI客户端并返回
    只有在真正需要时才会初始化客户端
    """
    global client
    if client is None:
        try:
            print(f"[INFO] 正在初始化OpenAI客户端...")
            print(f"[INFO] API_KEY长度: {len(API_KEY) if API_KEY else 0}, BASE_URL: {BASE_URL}, MODEL_NAME: {MODEL_NAME}")
            client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
            print(f"[INFO] OpenAI客户端初始化成功")
        except Exception as e:
            print(f"[ERROR] OpenAI客户端初始化失败：{str(e)}")
            print(f"[ERROR] 错误堆栈：\n{traceback.format_exc()}")
            raise ValueError(f"OpenAI客户端初始化失败：{str(e)}")
    return client

def generate_sql(user_question, conversation_history=None, connection=None):
    """
    根据用户问题、数据库结构和历史对话生成SQL查询。
    Args:
        user_question: 用户当前问题。
        conversation_history: 对话历史。
        connection: 数据库连接对象。

    Returns:
        str: 生成的 SQL 查询。
    Raises:
        ValueError: 如果无法获取数据库结构或构建提示。
        RuntimeError: 如果LLM调用失败或发生其他运行时错误。
        ConnectionError: 如果数据库连接无效。
    """
    if conversation_history is None:
        conversation_history = []
    if connection is None or not connection.is_connected():
        raise ConnectionError("有效的数据库连接是必需的。")
    
    # 获取OpenAI客户端实例
    try:
        openai_client = get_client()
    except Exception as e:
        print(f"[ERROR] 获取OpenAI客户端失败: {str(e)}")
        raise RuntimeError(f"无法初始化AI客户端: {str(e)}")

    try:
        print(f"\n[INFO] 开始生成SQL，用户问题: {user_question}")
        # 获取数据库结构 (优先使用增强版)
        database_structure = ""
        try:
            print(f"[INFO] 尝试获取增强数据库结构...")
            database_structure = get_enhanced_database_structure(connection)
            print(f"[INFO] 成功获取增强数据库结构")
        except Exception as e:
            print(f"[WARNING] 获取增强数据库结构失败: {str(e)}. 尝试基础版...")
            try:
                database_structure = get_database_structure_with_samples(connection)
                print(f"[INFO] 成功获取基础数据库结构")
            except Exception as e2:
                print(f"[ERROR] 基础数据库结构获取也失败: {str(e2)}")
                raise ValueError(f"无法获取数据库结构: {str(e2)}")
            
        if not database_structure or database_structure == "数据库结构获取失败，请检查数据库连接":
            raise ValueError("无法获取有效的数据库结构信息。")

        # 构造对话历史
        history_prompt = "\n".join(
            [f"用户：{entry['user']}\nLLM：{entry['response']}" for entry in conversation_history]
        ) if conversation_history else "无历史对话"

        # --- 核心提示构建 --- 
        # TODO: 实际项目中，强烈建议将这个复杂的提示移到 utils/prompts.py
        # 并进行更细致的优化 (加入Few-shot示例等)
        
        # 临时直接在这里构建增强提示，强调输出格式
        core_prompt = f"""
        任务：根据用户问题、数据库结构和历史对话，生成一个单一、可直接执行的MySQL查询语句。

        数据库结构 (包括示例数据):
        {database_structure}

        历史对话:
        {history_prompt}

        当前用户问题:
        {user_question}

        重要规则:
        1. **请只输出最终的MySQL查询语句本身。**
        2. **不要包含任何解释、说明、注释、代码块标记 (例如 ```sql ... ```) 或其他非SQL文本。**
        3. 确保生成的SQL语法正确，并与上述数据库结构兼容。
        4. 如果用户问题不清晰或无法安全地转换为SQL，请只输出：ERROR: Ambiguous Query

        生成的MySQL查询语句:
        """
        
        # 使用 prompts.py 中的 SQL 生成提示 (如果可用且优化过，否则使用上面的 core_prompt)
        # try:
        #     prompt = sql_prompt.format(
        #         database_structure=database_structure,
        #         user_question=user_question, # 或 clarified_user_question 如果保留澄清步骤
        #         # 可能还需要加入 history_prompt 等
        #     )
        #     print(f"[INFO] 使用 prompts.py 中的 sql_prompt 构建提示...")
        # except Exception as e:
        #     print(f"[WARNING] 无法使用 prompts.py 中的 sql_prompt: {e}. 使用内置提示。")
        prompt = core_prompt # 使用我们上面定义的临时核心提示

        print(f"[INFO] 构建SQL生成提示完成，长度: {len(prompt)}")
        # print(f"[DEBUG] Prompt: \n{prompt[:500]}...") # Debug: 输出部分提示

        print(f"[INFO] 开始调用LLM生成SQL...")
        try:
            completion = openai_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,  # 稍降温度以提高SQL生成的准确性
                timeout=45,  # 适当增加超时
                stop=["```"] # 尝试让模型在代码块结束时停止 (如果它不听话)
            )
            llm_output = completion.choices[0].message.content
            print(f"[INFO] LLM返回原始输出: {llm_output[:200]}...")
        except Exception as e:
            print(f"[ERROR] LLM SQL生成调用失败: {str(e)}")
            raise RuntimeError(f"LLM API调用失败: {str(e)}")

        # 清理LLM输出 (移除提取步骤)
        print(f"[INFO] 清理LLM输出...")
        sql_query = clean_sql_query(llm_output)
        print(f"[INFO] 清理后的SQL: {sql_query}")

        # 检查是否返回了错误标记
        if sql_query.startswith("ERROR:"):
             print(f"[WARNING] LLM返回错误标记: {sql_query}")
             raise ValueError(f"无法生成SQL: {sql_query.split(':', 1)[1].strip()}")
             
        # 检查清理后是否为空
        if not sql_query:
             print("[ERROR] LLM输出清理后为空或无效。原始输出: ", llm_output)
             raise ValueError("AI未能生成有效的SQL查询。")

        # 安全性检查 (保持不变)
        print(f"[INFO] 执行SQL安全性检查...")
        if is_dangerous_sql(sql_query):
            print(f"[WARNING] 检测到危险SQL操作，已拒绝: {sql_query}")
            raise ValueError("生成的SQL查询包含危险操作，已被系统拒绝")
            
        print(f"[INFO] SQL生成成功: {sql_query}")
        return sql_query

    except (ValueError, ConnectionError, RuntimeError) as e:
         # 直接重新抛出已知类型的错误，以便上层处理
         print(f"[ERROR] SQL 生成过程中捕获到错误: {type(e).__name__} - {e}")
         raise
    except Exception as e:
        # 捕获任何其他意外错误
        print(f"[ERROR] SQL 生成过程中发生未知错误：{e}")
        import traceback
        print(f"[ERROR] 错误堆栈：\n{traceback.format_exc()}")
        # 抛出一般性运行时错误
        raise RuntimeError(f"SQL生成过程中发生意外错误: {e}")

def clean_sql_query(sql_query):
    """清理SQL查询字符串，移除markdown、注释和多余空格"""
    if not isinstance(sql_query, str):
        return "" # Handle cases where input is not a string

    # 移除markdown代码块标记
    sql_query = re.sub(r'^```sql\s*', '', sql_query, flags=re.IGNORECASE).strip()
    sql_query = re.sub(r'\s*```$', '', sql_query).strip()

    # 按行分割并移除注释行
    lines = sql_query.splitlines()
    clean_lines = []
    for line in lines:
        stripped_line = line.strip()
        if not stripped_line.startswith("--") and stripped_line:
            # 移除行内注释 (虽然不常见，但可能出现)
            line_no_inline_comment = re.sub(r'\s*--.*$', '', line)
            if line_no_inline_comment.strip():
                clean_lines.append(line_no_inline_comment)

    # 重新组合并清理多余空格
    sql_query = " ".join(clean_lines)
    sql_query = re.sub(r'\s+', ' ', sql_query).strip()

    # 可选：移除末尾分号 (如果执行器不需要)
    if sql_query.endswith(';'):
       sql_query = sql_query[:-1].strip()

    return sql_query

def is_dangerous_sql(sql_query):
    """检查SQL是否包含危险操作"""
    # 转换为小写进行检查
    sql_lower = sql_query.lower()
    
    # 检查是否包含数据修改或结构修改操作
    dangerous_patterns = [
        r'\bdrop\s+database\b', 
        r'\bdrop\s+table\b',
        r'\btruncate\s+table\b',
        r'\bdelete\s+from\b(?!.*\bwhere\b)',  # DELETE无WHERE条件
        r'\balter\s+table\b.*\bdrop\b',
        r'\bupdate\b(?!.*\bwhere\b)'  # UPDATE无WHERE条件
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, sql_lower):
            return True
    
    return False

def generate_answer(user_question, query_results):
    """
    生成对查询结果的自然语言解释。
    
    Args:
        user_question: 用户问题
        query_results: 查询结果数据
        
    Returns:
        str: 生成的解释文本
    """
    # 获取OpenAI客户端实例
    try:
        openai_client = get_client()
    except Exception as e:
        print(f"[ERROR] 获取OpenAI客户端失败: {str(e)}")
        return f"回答生成失败。错误: 无法初始化AI客户端"
        
    prompt = answer_prompt.format(user_question=user_question, query_results=query_results)
    print("\n[DEBUG] Sending prompt to LLM for answer generation:")
    print(prompt)  # 输出发送给 LLM 的完整 Prompt
    
    # 初始化生成结果
    answer = ""
    
    # 调用 OpenAI 接口并开启流式输出
    try:
        response = openai_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            stream=True
        )
        print("\nAI 正在生成回答...")  # 提示生成开始
        
        # 逐步接收流式输出
        for chunk in response:
            if chunk.choices[0].delta.content:
                delta = chunk.choices[0].delta.content
                print(delta, end="")
                answer += delta
                
        print("\n\n[DEBUG] Final Generated Answer:\n", answer)  # 输出完整回答
        return answer
    except Exception as e:
        print("\n[ERROR] LLM 流式输出过程中发生错误：", e)
        return f"回答生成失败。错误: {str(e)}"

def stream_generate_answer(user_question, query_results):
    """
    生成对查询结果的自然语言解释，并以流式方式返回。
    
    Args:
        user_question: 用户问题
        query_results: 查询结果数据
        
    Returns:
        generator: 生成的解释文本块的生成器
    """
    # 获取OpenAI客户端实例
    try:
        openai_client = get_client()
    except Exception as e:
        print(f"[ERROR] 获取OpenAI客户端失败: {str(e)}")
        yield f"回答生成失败。错误: 无法初始化AI客户端"
        return
        
    print("\n[INFO] 开始流式生成回答")
    prompt = answer_prompt.format(user_question=user_question, query_results=query_results)
    print(f"[INFO] 构建回答提示完成，长度: {len(prompt)}")
    
    try:
        print(f"[INFO] 开始调用LLM流式生成...")
        response = openai_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            stream=True
        )
        print(f"[INFO] 已开始流式接收回答...")
        
        total_content = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                delta = chunk.choices[0].delta.content
                total_content += delta
                yield delta
                
        print(f"[INFO] 流式回答生成完成，总长度: {len(total_content)}")
                
    except Exception as e:
        error_msg = f"回答生成失败。错误: {str(e)}"
        print(f"[ERROR] LLM 流式输出过程中发生错误：{e}")
        yield error_msg

def ai_interactive_shell(connection):
    """
    AI 辅助的 MySQL Shell 模式，支持通过自然语言生成 SQL 并执行。
    """
    conversation_history = []
    try:
        print("\n欢迎使用AI辅助MySQL交互Shell。输入自然语言问题，AI会为您翻译成SQL并执行。")
        print("输入 'exit' 或 'quit' 可退出。\n")
        
        while True:
            user_question = input("ai-mysql> ").strip()
            if user_question.lower() in ['exit', 'quit']:
                print("退出 AI 辅助的 MySQL Shell 模式")
                break
            
            if not user_question:
                continue

            try:
                # 显示思考中提示
                print("AI正在思考中...", end="\r")
                
                # 调用 SQL 生成逻辑
                sql_query = generate_sql(user_question, conversation_history, connection=connection)
                if not sql_query:
                    print("无法生成有效的SQL查询")
                    continue

                print(f"\n生成的SQL查询：\n{sql_query}\n")
                print("执行中...", end="\r")

                # 执行 SQL 查询
                start_time = time.time()
                cursor = connection.cursor()
                cursor.execute(sql_query)
                
                if sql_query.lower().startswith(("select", "show", "describe", "explain")):
                    rows = cursor.fetchall()
                    headers = [desc[0] for desc in cursor.description]
                    
                    # 显示执行时间和结果数量
                    execution_time = time.time() - start_time
                    print(f"查询完成 ({execution_time:.2f}秒) - 返回 {len(rows)} 条结果：\n")
                    
                    # 显示结果表格
                    print(tabulate(rows, headers=headers, tablefmt="grid"))

                    # 调用回答生成逻辑
                    query_results = [dict(zip(headers, row)) for row in rows]
                    print("\nAI正在解释结果...\n")
                    answer = generate_answer(user_question, query_results)
                    print(f"\n{answer}")
                else:
                    rows_affected = cursor.rowcount
                    while cursor.nextset():
                        pass
                    connection.commit()
                    execution_time = time.time() - start_time
                    print(f"执行成功! ({execution_time:.2f}秒) - 影响了 {rows_affected} 行")

                # 保存对话到历史
                conversation_history.append({"user": user_question, "response": sql_query})
                
                # 限制历史长度为10条
                if len(conversation_history) > 10:
                    conversation_history = conversation_history[-10:]
                    
            except mysql.connector.Error as e:
                print(f"SQL 错误：{e}")
            except Exception as e:
                print(f"执行查询时发生错误：{e}")
                
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
            
def analyze_query_complexity(sql_query):
    """
    分析SQL查询的复杂性
    
    Args:
        sql_query: SQL查询字符串
        
    Returns:
        dict: 包含复杂性分析的字典
    """
    sql_lower = sql_query.lower()
    
    analysis = {
        "complexity": "简单",
        "joins": 0,
        "conditions": 0,
        "aggregations": False,
        "grouping": False,
        "sorting": False,
        "limit": False,
        "subqueries": 0
    }
    
    # 计算JOIN次数
    analysis["joins"] = len(re.findall(r'\bjoin\b', sql_lower))
    
    # 计算WHERE条件数(粗略估计)
    if 'where' in sql_lower:
        conditions = sql_lower.split('where')[1].split('group by')[0].split('order by')[0].split('limit')[0]
        analysis["conditions"] = len(re.findall(r'\band\b|\bor\b', conditions)) + 1
    
    # 检查聚合函数
    if re.search(r'\b(count|sum|avg|min|max)\s*\(', sql_lower):
        analysis["aggregations"] = True
    
    # 检查GROUP BY
    if 'group by' in sql_lower:
        analysis["grouping"] = True
    
    # 检查ORDER BY
    if 'order by' in sql_lower:
        analysis["sorting"] = True
    
    # 检查LIMIT
    if 'limit' in sql_lower:
        analysis["limit"] = True
    
    # 检查子查询
    analysis["subqueries"] = len(re.findall(r'\(\s*select', sql_lower))
    
    # 综合评估复杂性
    complexity_score = (
        analysis["joins"] * 2 + 
        analysis["conditions"] + 
        (3 if analysis["aggregations"] else 0) + 
        (2 if analysis["grouping"] else 0) + 
        (1 if analysis["sorting"] else 0) + 
        analysis["subqueries"] * 3
    )
    
    if complexity_score > 10:
        analysis["complexity"] = "复杂"
    elif complexity_score > 5:
        analysis["complexity"] = "中等"
    
    return analysis
