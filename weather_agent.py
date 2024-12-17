# 代码有问题
import os
import requests
import streamlit as st
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

# 设置页面配置
st.set_page_config(
    page_title="天气查询助手",
    page_icon="🌤️",
    layout="wide"
)

# 从环境变量获取 API 密钥
try:
    WEATHER_API_KEY = os.environ['WEATHER_API_KEY']
except KeyError:
    st.error("请设置环境变量 WEATHER_API_KEY，包含和风天气的 API 密钥")
    st.stop()

async def get_weather(city: str) -> str:
    url = "https://devapi.qweather.com/v7/weather/now"
    geo_url = "https://geoapi.qweather.com/v2/city/lookup"
    
    geo_params = {
        "location": city,
        "key": WEATHER_API_KEY
    }
    
    try:
        # 获取城市 ID
        geo_response = requests.get(
            geo_url, 
            params=geo_params
        )
        geo_data = geo_response.json()
        
        if geo_data.get("code") != "200" or not geo_data.get("location"):
            return f"抱歉，未找到{city}的位置信息"
            
        location_id = geo_data["location"][0]["id"]
        
        # 获取天气信息
        weather_params = {
            "location": location_id,
            "key": WEATHER_API_KEY
        }
        
        weather_response = requests.get(
            url, 
            params=weather_params
        )
        weather_data = weather_response.json()
        
        if weather_data.get("code") == "200":
            weather_info = weather_data["now"]
            return f"{city}的天气是{weather_info['temp']}度，{weather_info['text']}，" \
                   f"体感温度{weather_info['feelsLike']}度，湿度{weather_info['humidity']}%，" \
                   f"风向{weather_info['windDir']}，风力{weather_info['windScale']}级"
        else:
            return f"抱歉，获取{city}的天气信息失败。错误代码：{weather_data.get('code')}"
            
    except Exception as e:
        return f"查询天气时发生错误：{str(e)}"

def create_weather_agent():
    return AssistantAgent(
        name="weather_assistant",
        model_client=OpenAIChatCompletionClient(
            model="gpt-3.5-turbo",
            api_key=os.environ['OPENAI_API_KEY']
        ),
        tools=[get_weather],  # 直接传入函数
        system_message="""你是一个天气助手。当用户询问天气时：
1. 使用 get_weather 工具获取天气信息
2. 用友好的语气向用户解释天气情况
3. 回答后请说'结束'来终止对话"""
    )

async def query_weather_with_agent(city: str):
    weather_agent = create_weather_agent()
    termination = TextMentionTermination("结束")
    
    agent_team = RoundRobinGroupChat(
        [weather_agent], 
        termination_condition=termination,
        max_turns=3
    )

    # 创建一个空的消息占位符
    message_placeholder = st.empty()
    messages_history = []

    try:
        stream = agent_team.run_stream(task=f"请告诉我{city}现在的天气情况")
        async for message in stream:
            if isinstance(message, dict):
                role = message.get('role', 'assistant')
                content = message.get('content', '')
                if content and not content.startswith("TERMINATE"):
                    # 根据角色添加不同的前缀
                    if role == "assistant":
                        prefix = "🤖 回复: "
                    else:
                        prefix = "💭 思考: "
                    messages_history.append(f"{prefix}{content}")
            elif isinstance(message, str) and not message.startswith("TERMINATE"):
                messages_history.append(f"🤖 回复: {message}")
            
            # 实时更新显示所有消息历史
            message_placeholder.markdown("\n\n".join(messages_history))
    except Exception as e:
        st.error(f"发生错误：{str(e)}")
        return []

    return messages_history

# Streamlit 界面
st.title("🌤️ 智能天气查询助手")

st.markdown("""
### 使用说明
1. 在下方输入框中输入城市名称（如：上海、北京、广州等）
2. 点击"查询天气"按钮
3. 等待 AI 助手为您查询天气信息
""")

# 创建两列布局
col1, col2 = st.columns([3, 1])

with col1:
    # 添加输入框，不设置默认值
    city = st.text_input("请输入要查询的城市名称：", value="", placeholder="例如：上海")

with col2:
    # 添加查询按钮，垂直对齐
    st.write("")  # 添加空行以对齐
    query_button = st.button("查询天气", use_container_width=True)

# 创建结果显示区域
result_container = st.container()

# 只有当点击按钮时才行查询
if query_button and city:
    with st.spinner('正在查询天气信息...'):
        try:
            messages = asyncio.run(query_weather_with_agent(city))
            if not messages:
                st.warning("未收到任何天气信息")
            else:
                st.success("查询完成！")
        except Exception as e:
            st.error(f"发生错误：{str(e)}")
elif query_button and not city:
    st.warning("请输入城市名称")

# 添加页脚
st.markdown("---")
st.markdown("powered by AutoGen & 和风天气")

# 移除所有默认的查���行为
if __name__ == "__main__":
    pass