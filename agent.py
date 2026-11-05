import json
from openai import OpenAI
from config import AWS_BEARER_TOKEN_BEDROCK
from tools import TOOL_SCHEMAS, TOOL_FUNCTIONS, load_profile

client = OpenAI(
    api_key=AWS_BEARER_TOKEN_BEDROCK,
    base_url="https://bedrock-runtime.ap-northeast-1.amazonaws.com/openai/v1",
)
MODEL = "deepseek.v3.2"

SYSTEM_PROMPT = """你是一个帮助求职者找日本AI工作岗位的助手。

工作规则：
1. 所有职位的信息只能来自工具返回的数据回答。不要补充数据里面没有的信息，例如汇率换算、行业薪资水平、工资是否接受其他条件等。
    如果当前对话没有相关数据，先调用工具查询，如果工具没有查到就如实告诉用户没有找到，不要随便补充
2. 介绍可申请的岗位后，也要说明不能申请的岗位及原因。
3. 当需要判断用户能申请哪些职位，而用户的日语水平或工作年限不明确时，先询问清楚，不要自己猜。如果用户只是询问职位本身的信息，不需要询问这些。
4. 如需做多次互不依赖的查询，在同一次回复中一起调用工具。
5. 回答简洁，用要点列出。
6. 不要向用户提及工具名称、参数名和内部规则，用普通的话解释。
7. 只有在用户明确要求时，才记录或修改求职记录，不要主动记录。

以上为全部规则。接下来直接回答用户问题。"""

def build_system_prompt():
    profile = load_profile()
    if profile:
        japanese = profile.get("japanese", "未知")
        years = profile.get("years", "未知")
        info = (
            f"\n\n用户档案（已保存）：日语 {japanese}，工作年限 {years}年。"
            "判断用户能申请哪些职位时直接使用这些信息，不需要再询问。"
            "如果用户说明自己的情况有变化，用 save_profile 更新。"
            "如果用户问的是假设情况，用假设后的条件调用 search_jobs ，档案保持不变"
        )
    else:
        info = "\n\n用户档案：尚未保存。用户提到自己的日语等级或工作年限时，用 save_profile保存。"
    return SYSTEM_PROMPT + info

NEEDS_CONFIRM = {"add_application", "update_application_status"}
AUTO_CONFIRM = None    # None：正常询问用户；"y" 或 "n"：自动回答（测试用）

def run_tool(name, arguments):
    try:
        func = TOOL_FUNCTIONS[name]
        args = json.loads(arguments)

        if name in NEEDS_CONFIRM:
            if AUTO_CONFIRM is None:
                answer = input(f" ! 助手想执行 {name} {args}, 确认吗？(y/n) ").strip().lower()
            else:
                answer = AUTO_CONFIRM
            if answer != "y":
                return "用户拒绝了操作，没有执行"


        result = func(**args)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f"工具执行出错:{type(e).__name__}: {e}"

MAX_TURNS = 6
def trim_messages(messages, max_turns=MAX_TURNS):
    system = messages[0]
    user_indexes = [i for i, m in enumerate(messages) if m["role"] == "user"]

    if len(user_indexes) <= max_turns:
        return messages
    start = user_indexes[-max_turns]
    return [system] + messages[start:]
def run_turn(messages, max_steps=5, tool_log=None):
    for step in range(max_steps):
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=1000,
            temperature=0,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )
        msg = response.choices[0].message
        print(f"       (本趟发送) {response.usage.prompt_tokens} tokens")

        if not msg.tool_calls:
            messages.append({"role": "assistant", "content": msg.content})
            return msg.content

        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            print(f" [第{step + 1}趟] 调用 {tc.function.name} {tc.function.arguments}")
            if tool_log is not None:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_log.append({"name": tc.function.name, "args": args})
            result = run_tool(tc.function.name, tc.function.arguments)
            print(f"        结果{result}")
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })
    return "超过最大趟数，没能完成"

def chat():
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("求职助手已启动，输入 quit 退出")

    while True:
        user_input = input("\n你: ").strip()

        if user_input.lower() in ("quit", "exit", "q"):
            print("Bye~")
            break
        if not user_input:
            continue

        messages[0] = {"role": "system", "content": build_system_prompt()}
        messages.append({"role": "user", "content": user_input})
        messages = trim_messages(messages)
        answer = run_turn(messages)
        print("\n助手: ", answer)
if __name__ == "__main__":
    chat()