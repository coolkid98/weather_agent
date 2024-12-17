import streamlit as st
import asyncio
import os
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
import pandas as pd

# 定义天气工具函数
async def get_weather(city: str) -> str:
    return f"{city}的天气是23度，晴天。"

# 设置页面配置
st.set_page_config(
    page_title="智能天气助手",
    page_icon="🌤️",
    layout="wide"
)

async def run_weather_agent(query: str):
    # 创建两个列来显示对话过程
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🤖 AI助手思考过程")
        agent_thoughts = st.empty()
    
    with col2:
        st.markdown("### 📝 最终回答")
        final_response = st.empty()

    # 设置系统提示词
    system_message = """你是一个专业的天气助手。请以友好和自然的方式回答用户的天气查询。
    回答时请注意：
    1. 使用礼貌和亲切的语气
    2. 除了天气数据外，可以根据天气给出合适的建议
    3. 回答要简洁明了
    4. 全程使用中文回答
    5. 在思考过程中，请详细说明你的推理步骤
    
    当完成回答后，请说"结束"。
    """
    
    # 定义agent
    weather_agent = AssistantAgent(
        name="weather_agent",
        system_message=system_message,
        model_client=OpenAIChatCompletionClient(
            model="gpt-3.5-turbo",
            api_key=os.environ['OPENAI_API_KEY']
        ),
        tools=[get_weather],
    )

    # 定义终止条件
    termination = TextMentionTermination("结束")

    # 定义团队
    agent_team = RoundRobinGroupChat([weather_agent], termination_condition=termination)

    # 创建进度提示
    with st.spinner('正在查询天气信息...'):
        thoughts = []
        final_message = ""
        
        async for message in agent_team.run_stream(task=f"请查询{query}的天气情况"):
            message_text = str(message)
            
            # 只显示有意义的文本内容
            if 'content=' in message_text:
                # 提取content中的实际文本内容
                content = message_text.split('content=')[-1].strip("'[]")
                
                # 过滤掉FunctionCall和FunctionExecutionResult的技术细节
                if not content.startswith(('FunctionCall', 'FunctionExecutionResult')):
                    thoughts.append(content)
                    
                    # 更新思考过程
                    agent_thoughts.markdown("\n\n".join(thoughts))
                    
                    # 如果消息包含"结束"，则将其作为最终回答
                    if "结束" in content:
                        final_message = content.replace("结束", "")
                        final_response.markdown(f"""
                        ### 查询结果
                        ---
                        {final_message}
                        """)

# 添加会话历史记录
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# 主界面部分
st.title("🌤️ 智能天气助手")
st.markdown("### 让AI帮你查询任何城市的天气信息")

# 创建输入框和按钮
with st.form("weather_form"):
    user_input = st.text_input(
        "请输入要查询的城市名称:",
        placeholder="例如：北京、上海、广州...",
        help="输入任何城市名称，AI助手将为您查询天气信息"
    )
    
    submitted = st.form_submit_button("查询天气", type="primary")
    
    if submitted and user_input:
        # 添加到历史记录
        st.session_state.chat_history.append({"query": user_input, "timestamp": pd.Timestamp.now()})
        asyncio.run(run_weather_agent(user_input))
    elif submitted:
        st.warning("请先输入城市名称！")

# 显示历史查询记录
if st.session_state.chat_history:
    with st.expander("查看历史查询记录"):
        for item in reversed(st.session_state.chat_history):
            st.write(f"📍 {item['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - 查询城市：{item['query']}")

# 添加页面底部信息
st.markdown("---")
st.markdown("""
##### 💡 使用说明：
1. 在输入框中输入想要查询的城市名称
2. 点击"查询天气"按钮
3. 左侧将显示AI助手的思考过程
4. 右侧将显示最终的天气信息和建议
""")