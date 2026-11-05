import os
import json
import tools
import agent

#测试专用档案柜
TEST_DIR = os.path.join(tools.BASE_DIR, "test_data")
os.makedirs(TEST_DIR, exist_ok=True)
tools.PROFILE_FILE = os.path.join(TEST_DIR, "profile.json")
tools.APPLICATIONS_FILE = os.path.join(TEST_DIR, "applications.json")

#确认机制自动拒绝
agent.AUTO_CONFIRM = "n"

CASES = [
    {
        "name": "问公司不追问条件",
        "profile": {},
        "input": "LLM Engineer 是哪家公司的？",
        "expect_tools": ["search_jobs", "get_job_detail"],
        "forbid_tools": ["save_profile", "add_application"],
    },
    {
        "name": "假设不存档",
        "profile": {"japanese": "N3", "years": 1},
        "input": "如果我考到N2，能多投哪些岗位？",
        "expect_tools": ["search_jobs"],
        "forbid_tools": ["save_profile"],
        "expect_args": [
            ("search_jobs", {"my_japanese": "N2"})
        ]
    },
    {
        "name": "实时要存档",
        "profile": {"japanese": "N3", "years": 1},
        "input": "我上个月考过N2了",
        "expect_tools": ["save_profile"],
        "forbid_tools": [],
    },
    {
        "name": "不主动记录求职",
        "profile": {"japanese": "N2", "years": 1},
        "input": "我能投哪些岗位？",
        "expect_tools": ["search_jobs"],
        "forbid_tools": ["add_application"],
    },
    {
        "name": "日常说法改状态",
        "profile": {"japanese": "N2", "years": 1},
        "application": [
            {"job_id": 1, "title": "AI New Grad", "status": "已投递", "date": "2026-11-01"}
        ],
        "input": "我的 AI New Grad 收到面试通知了",
        "expect_tools": ["update_application_status"],
        "forbid_tools": ["add_application"],
        "expect_args": [
            ("update_application_status", {"job_id": 1, "ststua": "面试中"})
        ]
    }
]

N = 3  #叫模型跑几次

def called(tool_log, name, args=None):
    for call in tool_log:
        if call["name"] != name:
            continue
        if args is None:
            return True
        if all(call["args"].get(k) == v for k, v in args.items()):
            return True
    return False
def run_case(case):
    with open(tools.PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(case["profile"], f, ensure_ascii=False)
    with open(tools.APPLICATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(case.get("applications", []), f, ensure_ascii=False)

    messages = [
        {"role": "system", "content": agent.build_system_prompt()},
        {"role": "user", "content": case["input"]},
    ]
    tool_log = []
    answer = agent.run_turn(messages, tool_log=tool_log)
    names = [c["name"] for c in tool_log]
    problems = []
    for t in case["expect_tools"]:
        if not called(tool_log, t):
            problems.append(f"应该调用 {t}，但没有")
    for t in case["forbid_tools"]:
        if called(tool_log, t):
            problems.append(f"不应该调用 {t}，但调用了")
    for name, args in case.get("expect_args", []):
        if not called(tool_log, name, args):
            problems.append(f"应该用 {args} 调用 {name}，但没有")

    return problems, tool_log, answer

if __name__ == "__main__":
    summary = []
    for case in CASES:
        print(f"\n===== {case['name']} =====")
        passed = 0
        for i in range(N):
            problems, tool_log, answer = run_case(case)
            if problems:
                print(f"    ✗ 第{i + 1}次：{problems}，实际调用 {tool_log}")
            else:
                passed += 1
                print(f"  ✓ 第{i + 1}次，调用 {tool_log}")
        summary.append((case["name"], passed))

    print("\n===== 汇总 =====")
    for name, passed in summary:
        print(f"{name}：{passed}/{N}")