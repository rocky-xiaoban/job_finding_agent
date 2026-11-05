import json
import os
from datetime import date

JOBS = [
    {
        "id": 1, "title": "AI New Grad", "japanese": "无", "min_years": 0, "salary_min": 504,
        "company": "Sakura Robotics（虚构）", "location": "东京",
        "skills": ["Python", "机器学习基础"],
        "remote": False,
        "description": "面向应届及少量经验者的AI研发岗位，入职后有3个月培训，工作语言为英语。",
    },
    {
        "id": 2, "title": "Junior AI Engineer", "japanese": "N2", "min_years": 0, "salary_min": 300,
        "company": "Kansai Data Lab（虚构）", "location": "大阪",
        "skills": ["Python", "SQL", "数据分析"],
        "remote": True,
        "description": "负责数据清洗和模型训练支持，需要与日本客户沟通。",
    },
    {
        "id": 3, "title": "LLM Engineer", "japanese": "N1", "min_years": 2, "salary_min": 648,
        "company": "Fuji Language AI（虚构）", "location": "东京",
        "skills": ["Python", "LLM应用开发", "RAG", "提示工程"],
        "remote": True,
        "description": "开发面向日本企业的大模型应用，需要用日语撰写技术文档和对客户讲解方案。",
    },
]

JP_RANK = {"无": 0, "N3": 3, "N2": 4, "N1": 5}

def job_summary(job):
    keys = ["id", "title", "japanese", "min_years", "salary_min"]
    return {k: job[k] for k in keys}
def search_jobs(my_japanese = None, my_years = None):
    if my_japanese is not None and my_japanese not in JP_RANK:
        raise ValueError(
            f"my_japanese 必须是 {list(JP_RANK.keys())} 之一，收到的是 '{my_japanese}'。"
            "如果用户的描述不明确，请先询问用户具体等级"
        )
    if my_japanese is None and my_years is None:
        return {
            "all_jobs": [job_summary(job) for job in JOBS],
            "note": "未提供求职者条件，以下为全部职位，未判断能否申请"
        }
    my_rank = JP_RANK[my_japanese]
    eligible = []
    rejected = []
    for job in JOBS:
        reasons = []
        if my_japanese is not None and JP_RANK[job["japanese"]] > my_rank:
            reasons.append(f"日语要求{job['japanese']},求职者为{my_japanese}")
        if my_years is not None and job["min_years"] > my_years:
            reasons.append(f"要求{job['min_years']}年经验，求职者为{my_years}年")

        if reasons:
            rejected.append({"id": job["id"], "title": job["title"], "reason": "; ".join(reasons)})
        else:
            eligible.append(job_summary(job))

    return {"eligible": eligible, "rejected": rejected}

def get_job_detail(job_id):
    for job in JOBS:
        if job["id"] == job_id:
            return job
    raise ValueError(                                   #给模型看
        f"找不到id为 {job_id} 的职位。现有职位的id是 {[j['id'] for j in JOBS]}。"
        "职位id应该来自search_jobs的返回结果"
    )
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APPLICATIONS_FILE = os.path.join(BASE_DIR, "applications.json")
PROFILE_FILE = os.path.join(BASE_DIR, "profile.json")

def load_profile():
    if not os.path.exists(PROFILE_FILE):
        return {}
    with open(PROFILE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_profile(japanese=None, years=None):
    if japanese is not None and japanese not in JP_RANK:
        raise ValueError(f"japanese必须是 {list(JP_RANK.keys())} 之一，收到的是 '{japanese}'。")

    old = load_profile()
    new = dict(old)
    if japanese is not None:
        new["japanese"] = japanese
    if years is not None:
        new["years"] = years

    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(new, f, ensure_ascii=False, indent=2)

    return {"ok": True, "old": old, "new": new}

STATUSES = ["想投", "已投递", "面试中", "已拒绝", "已录取"]

def load_applications():
    if not os.path.exists(APPLICATIONS_FILE):
        return []
    with open(APPLICATIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_applications(apps):
    with open(APPLICATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(apps, f, ensure_ascii=False, indent=2)

def add_application(job_id, status="想投"):
    job = get_job_detail(job_id)
    apps = load_applications()

    for app in apps:
        if app["job_id"] == job_id:
            return {
                "ok": True,
                "already_exists": True,
                "message": (
                    f"{job['title']} 已在记录里，状态是 {app['status']}, 没有重复添加"
                    "如需修改状态请用 update_application_status"
                ),
            }

    apps.append({
        "job_id": job_id,
        "title": job["title"],
        "status": status,
        "date": date.today().isoformat(),
    })

    save_applications(apps)
    return {"ok": True, "message": f"已记录: {job['title']}, 状态{status}"}

def list_applications():
    apps = load_applications()
    return {"count": len(apps), "applications": apps}

def update_application_status(job_id, status):
    if status not in STATUSES:
        raise ValueError(f"status 必须是 {STATUSES} 之一，收到的是 {status}")

    apps = load_applications()
    for app in apps:
        if app["job_id"] == job_id:
            old_status = app["status"]

            if old_status == status:
                return {
                    "ok": True,
                    "unchanged": True,
                    "message": f"{app['title']} 的状态本来就是 {status}，无需修改",
                }

            app["status"] = status
            app["updated"] = date.today().isoformat()
            save_applications(apps)
            return {
                "ok": True,
                "title": app['title'],
                "old_status": old_status,
                "new_status": status,
                "message": f"已将 {app['title']} 的状态从 {old_status} 改为 {status} ",
            }
    raise ValueError(
        f"求职记录里没有 job_id 为 {job_id} 的岗位"
        "如果用户想新增这条记录，请改用add_application"
    )


TOOL_SCHEMAS = [
    {
        "type": "function",

        "function": {
            "name": "search_jobs",
            "description": (
                "搜索日本AI职位，有两种用法：\n"
                "1. 用户想了解可申请哪些职位时：输入my_japanese和my_years，返回eligible(可申请)和rejected(不可申请和原因)"
                "2. 用户只想了解职位本身(如某个职位是哪家公司、在哪里、有哪些职位等)：不传任何参数，只返回全部职位的简要信息，这种情况不需要询问客户的日语水平和工作年限。"
                "返回的结果只有简要信息，职位详情需调用get_job_detail"
                "3. 用户问假设情况（例如‘如果我考到N2’，‘假设我有3年经验’）：传入假设后的条件进行筛选"
                "如果用户问的是‘能多投哪些‘，同时使用当前条件和假设条件各查一次，在同一次回复中一起调用"
                "不要自己根据职位要求判断能否申请"
            ),
            "parameters": {
                "type": "object",
                "properties":{
                    "my_japanese": {
                        "type": "string",
                        "enum": ["无", "N3", "N2", "N1"],
                        "description": "求职者的日语水平（JLPT等级）。仅在需查询用户可申请职位时使用，如用户描述不明确先询问客户。如用户是假设提问则填写假设后的等级"
                    },
                    "my_years": {
                        "type": "number",
                        "description": "求职者工作年数，如用户是假设提问则填写假设后的年数",
                    },
                },
                #"required": ["my_japanese", "my_years"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_job_detail",
            "description": (
                "根据职位 id 查询单个职位的详细信息，包括公司、地点、技能要求、是否远程、职位描述。"
                "job_id 必须来自 search_jobs 的返回结果，不要自己猜测。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "integer",
                        "description": "职位 id，来自 search_jobs 返回结果中的 id 字段",
                    },
                },
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_application",
            "description": (
                "把一个职位加入用户的求职记录，会永久保存"
                "只有当用户明确要求记录，收藏或标记投递某个职位时才记录，不要主动调用"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "integer",
                        "description": "职业id, 来自 search_jobs 的返回结果",
                    },
                    "status": {
                        "type": "string",
                        "enum": STATUSES,
                        "description": "求职状态，用户没说明时用 “想投”"
                    },
                },
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_applications",
            "description": "查看用户已保存的求职记录，包括职位、状态和记录日期",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_profile",
            "description": (
                "保存用户本人的当前日语等级和工作年限，供以后的对话使用。"
                "只有在用户陈述自己真实的现状时调用，例如'我日语N3'，'我工作2年了'，'我刚考过N2'"
                "假设性说法，如'如果我考过N2了呢'，'假如我有三年工作经验'。这一类的说法就不要保存"
                "只传用户提到的那一项，没提到的不要传"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "japanese": {
                        "type": "string",
                        "enum": ["无", "N3", "N2", "N1"],
                        "description": "用户当前的日语等级",
                    },
                    "years": {
                        "type": "number",
                        "description": "用户当前的工作年数"
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_application_status",
            "description": (
                "修改用户已有求职记录的状态，例如从“想投”改为“已投递”、“面试中”等。"
                "只用于已经在记录里的岗位，如果岗位还没有记录，应该用add_application新增。"
                "用户的日常说法也算要求修改，例如‘我投了’‘收到面试通知了’‘被拒了’‘拿到offer了’。"
                "用户的说法和哪个状态不明确时，先询问用户。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "integer",
                        "description": "要修改对应岗位状态的id，可通过 list_applications 或 search_jobs 获得",
                    },
                    "status": {
                        "type": "string",
                        "enum": STATUSES,
                        "description": "新的求职状态",
                    },
                },
                "required": ["job_id", "status"]
            }
        }
    }
]

TOOL_FUNCTIONS = {
    "search_jobs": search_jobs,
    "get_job_detail": get_job_detail,
    "add_application": add_application,
    "list_applications": list_applications,
    "save_profile": save_profile,
    "update_application_status": update_application_status,
}

_schema_names = {t["function"]["name"] for t in TOOL_SCHEMAS}
_func_names = set(TOOL_FUNCTIONS)
assert _schema_names == _func_names, (
    f"说明书和名册不一致！只在一边出现的工具：{_schema_names ^ _func_names}"
)