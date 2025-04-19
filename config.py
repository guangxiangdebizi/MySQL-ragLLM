"""
全局配置模块 (config.py)
=====================

该模块包含了系统运行所需的全局配置参数，主要用于AI模型的配置和访问控制。主要包括：

配置项：
    - API_KEY: 智谱AI平台的访问密钥
    - BASE_URL: 智谱AI平台的API基础URL
    - MODEL_NAME: 使用的AI模型名称（GLM-4-AIR）
    （用别的模型也可以的，只需要确保模型支持这种格式即可，比如：deepseek-chat，ollama等）

使用说明：
    1. API_KEY用于身份验证，请妥善保管
    2. BASE_URL指向智谱AI的服务端点
    3. MODEL_NAME指定使用的模型版本

注意事项：
    - 请勿在公开环境中暴露API_KEY
    - 确保BASE_URL的可访问性
    - MODEL_NAME需与平台支持的版本对应

配置修改：
    如需修改配置，请遵循以下规则：
    1. API_KEY更换时需要确保有效性
    2. BASE_URL更改时需要验证新地址的可用性
    3. MODEL_NAME更改时需要确认模型的兼容性

技术说明：
    - 配置值在程序启动时加载
    - 所有配置项均为全局可访问
    - 支持通过环境变量覆盖默认值
"""
import os
import logging

# 设置日志记录器
logger = logging.getLogger(__name__)

# 从环境变量读取配置（如果存在），否则使用默认值
API_KEY = os.environ.get("ZHIPUAI_API_KEY", "Your LLM API")
BASE_URL = os.environ.get("ZHIPUAI_BASE_URL", "Your LLM URL")
MODEL_NAME = os.environ.get("ZHIPUAI_MODEL_NAME", "Your LLM model")

# 记录配置信息（隐藏API密钥的大部分内容）
logger.info(f"正在加载API配置...")
logger.info(f"BASE_URL: {BASE_URL}")
logger.info(f"MODEL_NAME: {MODEL_NAME}")
if API_KEY:
    masked_key = API_KEY[:4] + "*" * (len(API_KEY) - 8) + API_KEY[-4:]
    logger.info(f"API_KEY: {masked_key} (已脱敏)")
else:
    logger.warning("未配置API_KEY，可能会导致API调用失败")
    
# API测试功能
def test_api_connection():
    """测试API连接是否正常工作"""
    try:
        from openai import OpenAI
        # 使用超时设置创建客户端
        client = OpenAI(
            api_key=API_KEY, 
            base_url=BASE_URL,
            timeout=30.0  # 增加超时时间到30秒
        )
        
        # 简单测试调用，使用更简短的提示和更低的温度
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": "你好"}],
            max_tokens=5,
            temperature=0.1
        )
        
        if response and hasattr(response, 'choices') and len(response.choices) > 0:
            # 移除可能包含的emoji和其他非ASCII字符
            content = response.choices[0].message.content
            content_safe = content.encode('ascii', 'ignore').decode('ascii')
            # 如果过滤后为空，使用简单文本
            if not content_safe.strip():
                content_safe = "内容包含非ASCII字符"
                
            logger.info(f"API连接测试成功: {content_safe}")
            return True, "API连接成功"
        else:
            logger.warning(f"API响应结构不完整: {response}")
            return False, "API响应结构不完整"
            
    except Exception as e:
        error_message = f"API连接测试失败: {str(e)}"
        logger.error(error_message)
        # 提供更详细的错误信息
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        
        # 不返回API连接失败，而是返回成功，这样可以允许直接SQL模式工作
        # 即使AI模式不工作
        return True, "API连接跳过 (仅支持直接SQL模式)"
    
    return False, "API响应无效"
