import streamlit as st
import asyncio
import os
import httpx  # 新增：用于异步HTTP请求
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
import pandas as pd

# 定义获取天气的真实工具函数
async def get_weather(city: str) -> str:
    async with httpx.AsyncClient() as client:
        # 根据您的订阅类型，选择正确的API Host
        # 如果是免费订阅，请使用 'devapi.qweather.com'
        api_host = "https://devapi.qweather.com"  # 或者 "https://api.qweather.com" 根据您的订阅类型

        # 步骤1：通过Geo API获取location ID
        geo_url = f"https://geoapi.qweather.com/v2/city/lookup"
        params_geo = {
            "location": city,
            "key": os.environ.get('WEATHER_API_KEY')  # 使用.get以避免KeyError
        }
        try:
            geo_response = await client.get(geo_url, params=params_geo, timeout=10.0)
            geo_response.raise_for_status()
            geo_data = geo_response.json()
        except httpx.RequestError as exc:
            return f"请求错误：{exc}"
        except httpx.HTTPStatusError as exc:
            return f"HTTP错误：{exc.response.status_code} - {exc.response.text}"

        if geo_data.get('code') != "200":
            return f"错误：{geo_data.get('msg', '无法获取地理信息')}"

        locations = geo_data.get('location')
        if not locations:
            return f"未找到城市 '{city}' 的位置信息。"

        # 假设取第一个匹配的结果
        location_id = locations[0].get('id')
        if not location_id:
            return f"无法获取城市 '{city}' 的位置ID。"

        # 步骤2：通过天气API获取实时天气
        weather_url = f"{api_host}/v7/weather/now"
        headers = {
            "X-QW-Api-Key": os.environ.get('WEATHER_API_KEY')  # 使用.get以避免KeyError
        }
        params_weather = {
            "location": location_id,
            "unit": "m"  # 使用公制单位
        }
        try:
            weather_response = await client.get(weather_url, headers=headers, params=params_weather, timeout=10.0)
            weather_response.raise_for_status()
            weather_data = weather_response.json()
        except httpx.RequestError as exc:
            return f"请求错误：{exc}"
        except httpx.HTTPStatusError as exc:
            return f"HTTP错误：{exc.response.status_code} - {exc.response.text}"

        if weather_data.get('code') != "200":
            return f"错误：{weather_data.get('msg', '无法获取天气信息')}"

        now = weather_data.get('now', {})
        if not now:
            return f"未找到城市 '{city}' 的实时天气信息。"

        # 提取所需的天气信息
        temp = now.get('temp', '未知')
        feels_like = now.get('feelsLike', '未知')
        text = now.get('text', '未知')
        wind_dir = now.get('windDir', '未知')
        wind_speed = now.get('windSpeed', '未知')
        humidity = now.get('humidity', '未知')

        # 构建响应字符串
        weather_info = (
            f"**{city}** 当前天气状况：{text}。"
            f"温度：{temp}°C，体感温度：{feels_like}°C。"
            f"风向：{wind_dir}，风速：{wind_speed} km/h。"
            f"相对湿度：{humidity}%。"
            # f"建议：{get_weather_advice(text)}"
        )

        return weather_info


def get_weather_advice(weather_text: str) -> str:
    """
    根据天气状况提供简单建议。
    """
    advice = {
        "晴": "天气晴朗，适合外出活动，别忘了防晒哦！",
        "多云": "天气多云，出行请带上轻薄的外套。",
        "阴": "天气阴沉，适合在室内安排活动。",
        "小雨": "有小雨，记得携带雨具。",
        "中雨": "有中雨，尽量减少户外活动，注意安全。",
        "大雨": "有大雨，建议待在室内，避免出行。",
        "雪": "有降雪，注意保暖，出行小心路滑。",
        # 添加更多天气状况及建议
    }
    return advice.get(weather_text, "请根据实际天气情况安排您的活动。")

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
            # model="gpt-3.5-turbo",
            model="gpt-4o",
            api_key=os.environ.get('OPENAI_API_KEY')  # 使用.get以避免KeyError
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
            
            if 'content=' in message_text:
                # 提取content中的实际文本内容
                content = message_text.split('content=')[-1].strip("'[]")
                
                # 修改：添加去重逻辑
                if (not content.startswith(('FunctionCall', 'FunctionExecutionResult')) and 
                    content not in thoughts):  # 添加这个检查
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
        try:
            asyncio.run(run_weather_agent(user_input))
        except Exception as e:
            st.error(f"发生错误：{e}")
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
