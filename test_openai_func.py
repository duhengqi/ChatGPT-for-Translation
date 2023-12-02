import json
import openai
import requests
from tenacity import retry, wait_random_exponential, stop_after_attempt
from termcolor import colored

GPT_MODEL = "gpt-3.5-turbo-0613"
API_KEY ="sk-R5VhE7pR88Dm0xZmMAl17NtvKJgRbuB2NDbXp8hKR2hxUeOv"
BASE_URL ="https://api.openai-proxy.org/v1"
#定义了一个装饰器@retry，用于在请求失败时重试这个装饰器使用了tenacity库提供的功能，它指定了重试的等待时间和尝试次数。
@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
#chat_completion_request函数是用于向OpenAI Chat API发送请求的函数。
#它接收一个messages参数，其中包含对话的消息列表。还可以指定tools和tool_choice参数，用于传递工具的信息
def chat_completion_request(messages, tools=None, tool_choice=None, model=GPT_MODEL):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-R5VhE7pR88Dm0xZmMAl17NtvKJgRbuB2NDbXp8hKR2hxUeOv",
    }
    json_data = {"model": model, "messages": messages}
    if tools is not None:
        json_data.update({"tools": tools})
    if tool_choice is not None:
        json_data.update({"tool_choice": tool_choice})
    try:
        response = requests.post(
            "https://api.openai-proxy.org/v1/chat/completions",
            headers=headers,
            json=json_data,
        )
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return e

#pretty_print_conversation函数用于漂亮地打印对话。它根据消息的角色使用不同的颜色打印消息。
def pretty_print_conversation(messages):
    role_to_color = {
        "system": "red",
        "user": "green",
        "assistant": "blue",
        "tool": "magenta",
    }
    
    for message in messages:
        if message["role"] == "system":
            print(colored(f"system: {message['content']}\n", role_to_color[message["role"]]))
        elif message["role"] == "user":
            print(colored(f"user: {message['content']}\n", role_to_color[message["role"]]))
        elif message["role"] == "assistant" and message.get("function_call"):
            print(colored(f"assistant: {message['function_call']}\n", role_to_color[message["role"]]))
        elif message["role"] == "assistant" and not message.get("function_call"):
            print(colored(f"assistant: {message['content']}\n", role_to_color[message["role"]]))
        elif message["role"] == "tool":
            print(colored(f"function ({message['name']}): {message['content']}\n", role_to_color[message["role"]]))
#接下来，我们定义了一个tools列表，其中包含了两个工具的信息。每个工具都是一个字典，包含type和function字段。
# type字段指定了工具的类型，这里是"function"。function字段是一个字典，包含了工具的详细信息，如名称、描述和参数。
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The temperature unit to use. Infer this from the users location.",
                    },
                },
                "required": ["location", "format"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_n_day_weather_forecast",
            "description": "Get an N-day weather forecast",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The temperature unit to use. Infer this from the users location.",
                    },
                    "num_days": {
                        "type": "integer",
                        "description": "The number of days to forecast",
                    }
                },
                "required": ["location", "format", "num_days"]
            },
        }
    },
]
#然后，我们创建了一个空的messages列表，用于存储对话的消息。
#接下来，我们向messages列表中添加了一个系统消息，提示助手不要对用户请求进行假设，需要对请求进行澄清。
messages = []
messages.append({"role": "system", "content": "Don't make assumptions about what values to plug into functions. Ask for clarification if a user request is ambiguous."})
#然后，我们向messages列表中添加了一个用户消息，表示用户想要获取今天的天气信息。
messages.append({"role": "user", "content": "What's the weather like today"})
chat_response = chat_completion_request(
    messages, tools=tools
)
assistant_message = chat_response.json()["choices"][0]["message"]
messages.append(assistant_message)
print(assistant_message)

messages.append({"role": "user", "content": "I'm in Glasgow, Scotland."})
chat_response = chat_completion_request(
    messages, tools=tools
)
assistant_message = chat_response.json()["choices"][0]["message"]
messages.append(assistant_message)
print(assistant_message)
