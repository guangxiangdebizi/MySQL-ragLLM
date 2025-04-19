"""
提示词模板模块 (prompts.py)
========================

该模块定义了系统中所有用于与LLM交互的提示词模板，是AI交互的核心配置组件。主要功能包括：

核心功能：
    1. SQL生成提示：引导LLM生成准确的SQL查询语句
    2. SQL提取优化：从LLM输出中提取和优化SQL语句
    3. 查询意图澄清：理解和明确用户的查询需求
    4. 结果解释生成：将查询结果转换为自然语言描述

主要组件：
    - sql_prompt: SQL查询生成模板
    - extract_sql_prompt: SQL提取和优化模板
    - clarify_prompt: 查询意图澄清模板
    - enhanced_clarify_prompt: 增强版查询意图澄清模板
    - answer_prompt: 结果解释生成模板

工作流程：
    1. 使用clarify_prompt或enhanced_clarify_prompt明确用户意图
    2. 使用sql_prompt生成初始SQL
    3. 使用extract_sql_prompt优化SQL
    4. 使用answer_prompt生成结果解释

技术特点：
    - 模板化提示词管理
    - 多级处理流程
    - 结构化的提示词设计
    - 清晰的输入输出定义
    - 深度数据库结构感知

依赖项：
    - langchain.prompts: 提示词模板管理
"""

from langchain.prompts import PromptTemplate

sql_prompt = PromptTemplate(template='''
你是一个专业的 SQL 查询生成器。请根据以下数据库结构和用户需求生成最优的 SQL 查询语句：

数据库结构：
{database_structure}

用户需求：{user_question}

生成 SQL 时请注意：
1. 优先使用 LEFT JOIN 而不是 INNER JOIN，以避免数据丢失
2. 为每个表添加有意义的别名，提高可读性，例如 users AS u
3. 使用 COALESCE 或 IFNULL 处理可能的 NULL 值
4. 对于模糊查询，使用 LIKE 搭配通配符 %
5. 添加适当的 LIMIT 子句避免返回过多数据
6. 优化查询性能，避免不必要的表连接和字段选择
7. 使用 GROUP BY 和聚合函数处理统计需求
8. 确保字段名和表名的大小写与数据库结构一致
9. 对于文本比较，考虑使用 LOWER() 或 UPPER() 以实现不区分大小写的比较
10. 使用有意义的列别名使结果更易理解
11. 对于复杂条件，使用括号明确逻辑优先级

请直接输出SQL语句，不要包含任何注释、标记或解释。
''')

extract_sql_prompt = PromptTemplate(template='''
请从以下内容中提取并优化 SQL 查询语句：

输入内容：{llm_output}

优化要求：
1. 移除所有注释、标记和解释文本
2. 确保语法的完整性和正确性
3. 添加适当的别名提高可读性
4. 优化JOIN操作顺序
5. 确保WHERE条件的逻辑清晰
6. 使用标准的SQL格式规范
7. 合理设置查询限制，避免返回过多数据

请只返回优化后的SQL语句，不要包含任何解释、注释或markdown标记。
''')

clarify_prompt = PromptTemplate(template='''
作为数据库查询专家，请分析并明确用户的查询需求：

历史对话：
{conversation_history}

数据库结构：
{database_structure}

用户问题：
{user_question}

请提供：
1. 查询目标的具体定义
2. 需要查询的表和字段
3. 查询条件和过滤要求
4. 结果排序和分组需求
5. 是否需要聚合函数
6. 是否需要分页处理
7. 可能的边界情况处理

请用专业的数据库术语描述需求，以便生成精确的 SQL。
''')

enhanced_clarify_prompt = PromptTemplate(template='''
作为高级数据库查询专家，请深入分析用户的查询需求，考虑数据库结构和历史上下文：

历史对话：
{conversation_history}

数据库结构：
{database_structure}

用户问题：
{user_question}

请进行全面的需求分析：

1. 核心查询目标：
   - 用户真正想要了解的信息是什么
   - 查询的业务意义和价值

2. 表和字段分析：
   - 主要表（FROM哪些表）
   - 关键字段（SELECT哪些字段）
   - 表间关系（如何JOIN）
   - 是否需要子查询或视图

3. 条件和过滤：
   - 筛选条件（WHERE子句）
   - 条件的逻辑关系（AND/OR）
   - 是否需要高级过滤（HAVING）

4. 数据处理需求：
   - 排序要求（ORDER BY）
   - 分组需求（GROUP BY）
   - 聚合计算（COUNT/SUM/AVG等）
   - 去重需求（DISTINCT）

5. 结果集控制：
   - 数据量限制（LIMIT）
   - 分页参数（OFFSET）
   - 输出格式要求

6. 特殊考虑：
   - 性能优化方向
   - 可能的NULL值处理
   - 可能的数据类型转换
   - 边界条件处理

7. 重点澄清：
   - 用户问题中的模糊之处
   - 可能的歧义项
   - 查询是否与历史对话相关

请用简洁专业的数据库术语提供深度分析，为后续SQL生成奠定基础。
''')

answer_prompt = PromptTemplate(template='''
作为一个专业而友好的数据库分析助手，请根据用户问题和查询结果提供有见解的回答。

用户问题：{user_question}
查询结果：{query_results}

回答要求：
1. 使用自然、友好且专业的语言直接回答用户问题
2. 首先简明扼要地总结结果的核心要点
3. 提供对数据的有价值见解和分析，说明数据告诉我们什么
4. 如果查询结果为空，分析可能的原因并提供建议
5. 如果结果数量很多，总结主要模式和趋势
6. 精确描述数值（如总数、平均值、最大/最小值等），但要确保易于理解
7. 不要逐行解释每个结果，而是提供整体分析
8. 不要解释技术实现或SQL查询本身
9. 使用清晰的段落结构和自然的过渡
10. 确保回答专业且有信息价值，同时保持对话语气

直接开始回答，无需任何引言或结语：
''')
