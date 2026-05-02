import datetime
import gradio as gr
from workflow_engine import IntegratedState, integrated_app, load_user_profile
from core_state import check_ollama_status, DEFAULT_HIGHLIGHTS
from graph_engine import graph_engine
from utils_ui import UIHelper

class TrainingModule:
    def __init__(self):
        # QA Tab Components
        self.chatbot = None
        self.msg_input = None
        self.send_btn = None
        self.ui_lock_trigger = None # 新增：用于触发前端 UI 锁定的隐藏开关
        self.guided_questions_display = None
        self.report_display = None
        
        # Profile Components
        self.profile_level = None
        self.profile_goal = None
        self.profile_mileage = None
        self.profile_lthr = None
        self.profile_tpace = None
        self.profile_race_date = None
        self.profile_duration = None
        self.profile_injury = None
        self.profile_memory = None
        self.pb_800 = None
        self.pb_1500 = None
        self.pb_5k = None
        self.pb_10k = None
        self.pb_half = None
        self.pb_full = None
        self.z1_pace = None
        self.z2_pace = None
        self.z3_pace = None
        self.z4_pace = None
        self.z5_pace = None
        
        # Adaptive Plan Components
        self.adaptive_fatigue = None
        self.adaptive_missed = None
        self.adaptive_abnormal_hr = None
        self.adaptive_notes = None
        self.adaptive_btn = None
        
        # Status & Monitoring Components
        self.pipeline_status = None
        self.token_stats = None
        self.roi_chart = None
        self.risk_display = None
        self.reasoning_box = None
        
        # Graph Display Component in QA Tab
        self.mermaid_output = None
        self.refresh_graph_btn = None
        
        # Eval Tab Components
        self.eval_queries = None
        self.eval_btn = None
        self.eval_out = None
        
        # Helper group of outputs for events
        self.qa_outputs = []

    async def handle_qa(self, question, history, profile_level, profile_mileage, profile_goal, profile_injury, profile_memory,
                        profile_lthr, profile_tpace, pb_800, pb_1500, pb_5k, pb_10k, pb_half, pb_full,
                        profile_race_date, profile_duration,
                        z1, z2, z3, z4, z5,
                        mode="team", adaptive_feedback=None):
        normalized_history = []
        for item in (history or []):
            if isinstance(item, dict):
                role = item.get("role")
                content = item.get("content")
                if role in ("user", "assistant") and content is not None:
                    normalized_history.append({"role": role, "content": str(content)})
                continue
            if isinstance(item, (list, tuple)) and len(item) == 2:
                user_text, assistant_text = item
                normalized_history.append({"role": "user", "content": "" if user_text is None else str(user_text)})
                normalized_history.append({"role": "assistant", "content": "" if assistant_text is None else str(assistant_text)})
                continue
        # 限制历史记录长度，防止前端 Chatbot 渲染过慢
        if len(normalized_history) > 40:
            history = normalized_history[-40:]
        else:
            history = normalized_history
        
        def get_outputs(msg=gr.update(), hist=gr.update(), tokens=None, pipe=None, roi=gr.update(), risk=gr.update(), log=gr.update(), report=gr.update(), mermaid=gr.update(), guided=gr.update(), prof=None, minimal=False, interactive=None, ui_locked=None):
            # 按钮交互状态统一处理
            btns = gr.update(interactive=interactive) if interactive is not None else gr.update()
            
            # 核心锁逻辑：只有明确传参时才更新 Checkbox 触发 JS
            lock = gr.update(value=ui_locked) if ui_locked is not None else gr.update()
            
            # 流式极简模式：除了 Chatbot 和 Token，其余组件严禁任何实质性更新
            if minimal:
                token_html = UIHelper.generate_token_html(tokens) if tokens is not None else gr.update()
                # 在流式中不更新流水线动画，只更新 Token，极大减少 DOM 操作
                return (
                    msg, hist, token_html, gr.update(), 
                    gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(), # 按钮状态在流式中保持不变
                    gr.update() # 锁状态在流式中保持不变
                )

            # 全量同步模式 (用于节点切换或结束)
            if prof:
                p = prof
                hr_zones = p.get("hr_zones", {})
                exp = p.get("experience_level", gr.update())
                mileage = p.get("weekly_mileage", gr.update())
                goal = p.get("goal", gr.update())
                injury = p.get("injury_history", gr.update())
                memory = "\n".join(p.get("long_term_memory", [])) if isinstance(p.get("long_term_memory"), list) else p.get("long_term_memory", gr.update())
                lthr = p.get("lthr", gr.update())
                tpace = p.get("t_pace", gr.update())
                pb8 = p.get("pb_800m", gr.update())
                pb15 = p.get("pb_1500m", gr.update())
                pb5k = p.get("pb_5k", gr.update())
                pb10k = p.get("pb_10k", gr.update())
                pbh = p.get("pb_half", gr.update())
                pbf = p.get("pb_full", gr.update())
                race = p.get("target_race_date", gr.update())
                dur = p.get("plan_duration_weeks", gr.update())
                z1 = hr_zones.get("Z1 (轻松)", hr_zones.get("Z1", gr.update()))
                z2 = hr_zones.get("Z2 (有氧)", hr_zones.get("Z2", gr.update()))
                z3 = hr_zones.get("Z3 (马拉松)", hr_zones.get("Z3", gr.update()))
                z4 = hr_zones.get("Z4 (乳酸阈)", hr_zones.get("Z4", gr.update()))
                z5 = hr_zones.get("Z5 (间歇)", hr_zones.get("Z5", gr.update()))
            else:
                exp = mileage = goal = injury = memory = lthr = tpace = pb8 = pb15 = pb5k = pb10k = pbh = pbf = race = dur = z1 = z2 = z3 = z4 = z5 = gr.update()
            
            token_html = UIHelper.generate_token_html(tokens) if tokens is not None else gr.update()
            pipe_html = UIHelper.generate_pipeline_html(pipe) if pipe is not None else gr.update()

            return (
                msg, hist, token_html, pipe_html, 
                roi, risk, log, report, mermaid, guided,
                exp, mileage, goal, injury, memory, lthr, tpace,
                pb8, pb15, pb5k, pb10k, pbh, pbf, race, dur,
                z1, z2, z3, z4, z5,
                btns, btns, btns,
                lock
            )

        if not question:
            yield get_outputs(hist=history)
            return
        
        # 开始处理：锁定输入和所有功能按钮，并触发前端 UI 全局锁定
        yield get_outputs(msg=gr.update(interactive=False), interactive=False, ui_locked=True, log="正在检测服务状态...")
        if not await check_ollama_status():
            msg = "❌ Ollama 服务未在线，请确保本地 11434 端口服务已启动。"
            history.append({"role": "user", "content": str(question)})
            history.append({"role": "assistant", "content": msg})
            yield get_outputs(msg=gr.update(interactive=True), interactive=True, ui_locked=False, hist=history, risk=f"<div class='github-flash-error'>{msg}</div>")
            return

        state: IntegratedState = {
            "query": question,
            "mode": mode,
            "category": "",
            "subtasks": [],
            "draft_plan": "",
            "review_feedback": "",
            "is_approved": False,
            "iteration_count": 0,
            "final_report": "",
            "structured_report": None,
            "reasoning_log": [],
            "rag_sources": [],
            "graph_context": "",
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "audit_scores": {"consistency": 0, "safety": 0, "roi": 0, "summary": ""},
            "roi_history": [],
            "risk_alert": "",
            "entities": [],
            "mermaid_graph": "",
            "guided_questions": [],
            "user_profile": {
                "experience_level": profile_level,
                "weekly_mileage": float(profile_mileage),
                "goal": profile_goal,
                "injury_history": profile_injury if isinstance(profile_injury, list) else [profile_injury],
                "long_term_memory": [m.strip() for m in profile_memory.split('\n') if m.strip()] if profile_memory else [],
                "last_race_time": "未知",
                "pb_800m": pb_800,
                "pb_1500m": pb_1500,
                "pb_5k": pb_5k,
                "pb_10k": pb_10k,
                "pb_half": pb_half,
                "pb_full": pb_full,
                "lthr": int(profile_lthr) if profile_lthr else 0,
                "t_pace": profile_tpace,
                "target_race_date": profile_race_date,
                "plan_duration_weeks": int(profile_duration),
                "hr_zones": {
                    "Z1": z1, "Z2": z2, "Z3": z3, "Z4": z4, "Z5": z5
                }
            },
            "adaptive_feedback": adaptive_feedback or {}
        }
        
        history.append({"role": "user", "content": str(question)})
        history.append({"role": "assistant", "content": "🧠 思考中..."})
        yield get_outputs(pipe="router", log="正在规划决策路径...")
        
        current_reasoning = []
        final_answer = ""
        last_tokens = {"Prompt": 0, "Completion": 0, "Total": 0}
        last_structured = None
        last_mermaid = ""
        last_profile = state["user_profile"]
        
        token_counter = 0 # 令牌计数器，用于控制 yield 频率
        
        try:
            active_node = "router"
            log_html = gr.update()
            risk_alert = gr.update()
            
            async for event in integrated_app.astream_events(state, version="v2"):
                kind = event["event"]
                name = event.get("name", "")
                
                # 捕获节点切换
                if kind == "on_chain_start" and name in ["coach", "nutritionist", "therapist", "auditor", "formatter", "profiler", "router", "entity_extraction", "planner", "executor", "guided_questions_generator", "research_analyst", "adaptive_coach"]:
                    active_node = name
                    # 每当切换到新节点，我们在流式输出中插入一个空行分隔（如果是生成方案的节点）
                    if name in ["coach", "nutritionist", "therapist", "adaptive_coach", "formatter"]:
                        if history and history[-1]["role"] == "assistant" and history[-1]["content"] != "🧠 思考中...":
                            history[-1]["content"] += "\n\n"
                    
                    # 节点切换时，只更新流水线状态和历史记录，不更新画像以减轻压力
                    yield get_outputs(hist=history, tokens=last_tokens, pipe=active_node)
                
                # 捕获大模型流式打字输出
                elif kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        token_counter += 1
                        if history and history[-1]["role"] == "assistant":
                            if history[-1]["content"] == "🧠 思考中...":
                                history[-1]["content"] = chunk.content
                            else:
                                history[-1]["content"] += chunk.content
                            
                            # 每 50 个 token 或结束时才 yield，显著减轻前端压力
                            # 且在流式过程中，除了 Chatbot 和 Token 统计，其他组件保持 gr.update()
                            if token_counter % 50 == 0:
                                yield get_outputs(hist=history, tokens=last_tokens, minimal=True)
                
                # 捕获节点执行完成后的状态更新
                elif kind == "on_chain_end" and name in ["coach", "nutritionist", "therapist", "auditor", "formatter", "profiler", "router", "entity_extraction", "planner", "executor", "guided_questions_generator", "research_analyst", "adaptive_coach"]:
                    output = event["data"].get("output", {})
                    if not isinstance(output, dict):
                        continue
                        
                    current_prof_update = None
                    if "user_profile" in output:
                        last_profile = output["user_profile"]
                        current_prof_update = last_profile # 只有当节点明确返回画像时才更新前端

                    if "token_usage" in output:
                        usage = output["token_usage"]
                        last_tokens = {"Prompt": usage.get("prompt_tokens", 0), "Completion": usage.get("completion_tokens", 0), "Total": usage.get("total_tokens", 0)}

                    log_update = gr.update()
                    if "reasoning_log" in output:
                        current_reasoning.extend(output["reasoning_log"])
                        # 限制日志行数，防止前端 HTML 过大导致卡死
                        display_logs = current_reasoning[-100:] if len(current_reasoning) > 100 else current_reasoning
                            
                        formatted_log = ["<div class='reasoning-terminal'>"]
                        for log in display_logs:
                            prefix = "<span style='color: var(--info); opacity: 0.5;'>$ </span>"
                            if "[router]" in log: formatted_log.append(f"{prefix}<span style='color: var(--primary-color)'>{log}</span>")
                            elif "[entity_extraction]" in log: formatted_log.append(f"{prefix}<span style='color: #ffca28'>{log}</span>")
                            elif "[graph_traversal]" in log: formatted_log.append(f"{prefix}<span style='color: #00bcd4'>{log}</span>")
                            elif "[profiler]" in log: formatted_log.append(f"{prefix}<span style='color: #d2a8ff'>{log}</span>")
                            elif any(x in log for x in ["[coach]", "[nutritionist]", "[therapist]", "[adaptive_coach]"]): formatted_log.append(f"{prefix}<span style='color: var(--success)'>{log}</span>")
                            elif "[auditor]" in log: formatted_log.append(f"{prefix}<span style='color: var(--warning)'>{log}</span>")
                            else: formatted_log.append(f"<span style='color: var(--text-secondary); padding-left: 12px;'>{log}</span>")
                        formatted_log.append("</div>")
                        log_update = "".join(formatted_log)

                    risk_alert = output.get("risk_alert", gr.update())
                    
                    mermaid_update = gr.update()
                    if "mermaid_graph" in output and output['mermaid_graph']:
                        new_mermaid = f"```mermaid\n{output['mermaid_graph']}\n```"
                        if new_mermaid != last_mermaid:
                            mermaid_update = new_mermaid
                            last_mermaid = new_mermaid
                            
                    report_update = gr.update(value=UIHelper.render_structured_report(output["structured_report"], ""), visible=True) if "structured_report" in output else gr.update()
                    
                    if "final_report" in output:
                        final_answer = output["final_report"]
                        last_structured = output.get("structured_report")

                    # 节点结束时 yield 全量更新，确保状态同步
                    yield get_outputs(hist=history, tokens=last_tokens, pipe=name, risk=risk_alert, log=log_update, report=report_update, mermaid=mermaid_update, prof=current_prof_update, minimal=False)
        
            if final_answer:
                if history and history[-1].get("role") == "assistant":
                    history[-1]["content"] = final_answer
                else:
                    history.append({"role": "assistant", "content": final_answer})
                
                report_html = UIHelper.render_structured_report(last_structured, final_answer)
                guided_html = UIHelper.render_guided_questions(state.get("guided_questions", []))
                
                # 最终结束：恢复输入框和按钮互动，解锁前端 UI
                yield get_outputs(msg=gr.update(value="", interactive=True), interactive=True, ui_locked=False, hist=history, tokens=last_tokens, pipe="formatter", log="报告生成成功", report=gr.update(value=report_html, visible=True), guided=gr.update(value=guided_html, visible=True if guided_html else False), prof=last_profile)
            else:
                # 即使没有最终报告（例如中途停止），也要恢复输入框和按钮
                yield get_outputs(msg=gr.update(interactive=True), interactive=True, ui_locked=False)
                
        except Exception as e:
            error_msg = f"发生错误: {str(e)}"
            if history and history[-1].get("role") == "assistant": history[-1]["content"] = error_msg
            else: history.append({"role": "assistant", "content": error_msg})
            yield get_outputs(risk=f"<div class='github-flash-error'>{error_msg}</div>", ui_locked=False, interactive=True)

    async def handle_adaptive_plan(self, fatigue, missed, hr, notes, history, profile_level, profile_mileage, profile_goal, profile_injury, profile_memory,
                        profile_lthr, profile_tpace, pb_800, pb_1500, pb_5k, pb_10k, pb_half, pb_full,
                        profile_race_date, profile_duration,
                        z1, z2, z3, z4, z5):
        question = "【自适应调整请求】请求根据近期的疲劳度反馈和身体状态，动态自适应调整当前的训练计划。"
        adaptive_feedback = {
            "fatigue_level": fatigue,
            "missed_workouts": missed,
            "abnormal_hr": hr,
            "notes": notes
        }
        async for outputs in self.handle_qa(
            question, history, profile_level, profile_mileage, profile_goal, profile_injury, profile_memory,
            profile_lthr, profile_tpace, pb_800, pb_1500, pb_5k, pb_10k, pb_half, pb_full,
            profile_race_date, profile_duration,
            z1, z2, z3, z4, z5,
            mode="adaptive", adaptive_feedback=adaptive_feedback
        ):
            yield outputs

    async def run_batch(self, queries_text: str):
        queries = [x.strip() for x in (queries_text or "").splitlines() if x.strip()]
        if not queries:
            return {"error": "未输入任何问题"}
        results = []
        for q in queries:
            state: IntegratedState = {
                "query": q,
                "category": "",
                "draft_plan": "",
                "review_feedback": "",
                "is_approved": False,
                "iteration_count": 0,
                "final_report": "",
                "reasoning_log": [],
                "rag_sources": [],
                "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            }
            out = await integrated_app.ainvoke(state)
            results.append(
                {
                    "query": q,
                    "category": out.get("category", ""),
                    "iterations": out.get("iteration_count", 0),
                    "final_report": out.get("final_report", ""),
                }
            )
        return {"count": len(results), "results": results}

    def load_profile_to_ui(self):
        p = load_user_profile()
        hz = p.get("hr_zones", {})
        return (
            p.get("experience_level", "进阶"),
            p.get("weekly_mileage", 30.0),
            p.get("goal", "维持健康"),
            p.get("injury_history", ["无"]),
            "\n".join(p.get("long_term_memory", [])) if isinstance(p.get("long_term_memory"), list) else p.get("long_term_memory", ""),
            p.get("lthr", 0),
            p.get("t_pace", ""),
            p.get("pb_800m", ""),
            p.get("pb_1500m", ""),
            p.get("pb_5k", ""),
            p.get("pb_10k", ""),
            p.get("pb_half", ""),
            p.get("pb_full", ""),
            p.get("target_race_date", ""),
            p.get("plan_duration_weeks", 12),
            hz.get("Z1 (轻松)", hz.get("Z1", "")),
            hz.get("Z2 (有氧)", hz.get("Z2", "")),
            hz.get("Z3 (马拉松)", hz.get("Z3", "")),
            hz.get("Z4 (乳酸阈)", hz.get("Z4", "")),
            hz.get("Z5 (间歇)", hz.get("Z5", ""))
        )

    def build_ui(self):
        with gr.Tab("💬 Workspace", id="tab_qa"):
            with gr.Row(elem_classes="side-panel-container"):
                with gr.Column(scale=4, min_width=400):
                    self.chatbot = gr.Chatbot(
                        height=580, 
                        show_label=False,
                        avatar_images=(None, "https://avatars.githubusercontent.com/u/9919?s=200&v=4"),
                        elem_classes="chatbot-container",
                        placeholder="👋 你好！我是 GraphRAG Copilot，向我提问吧～"
                    )
                    self.ui_lock_trigger = gr.Checkbox(value=False, visible=False)
                    self.ui_lock_trigger.change(None, [self.ui_lock_trigger], js="(v) => window.toggleUILock(v)")
                    
                    self.guided_questions_display = gr.HTML(visible=False)
                    self.report_display = gr.HTML(visible=False)
                    with gr.Row():
                        self.msg_input = gr.Textbox(
                            placeholder="输入您的问题... (Enter 发送, Ctrl+Enter 换行)", 
                            scale=8, 
                            show_label=False,
                            container=False,
                            elem_id="input-box"
                        )
                        self.send_btn = gr.Button("Send", variant="primary", scale=1, elem_classes="primary-btn")
                
                with gr.Column(scale=3, min_width=300):
                    with gr.Accordion("👤 User Profile (Optional)", open=False, elem_classes="github-container"):
                        gr.HTML("<div style='font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;'>配置画像以获得更精准的个性化训练建议</div>")
                        with gr.Row():
                            self.profile_level = gr.Dropdown(label="Level", choices=["初学者", "进阶", "精英"], value="进阶", scale=1)
                            self.profile_goal = gr.Dropdown(label="Goal", choices=["完赛", "PB (破百/破三)", "恢复", "维持健康"], value="维持健康", scale=1)
                        
                        with gr.Row():
                            self.profile_mileage = gr.Number(label="Weekly Mileage (km)", value=30.0, scale=1)
                            self.profile_lthr = gr.Number(label="LTHR (乳酸阈心率)", value=0, precision=0, scale=1)
                            self.profile_tpace = gr.Textbox(label="T-Pace (乳酸阈配速)", placeholder="如 4:30", scale=1)
                        
                        with gr.Row():
                            self.profile_race_date = gr.Textbox(label="Target Race Date", placeholder="YYYY-MM-DD", value=(datetime.date.today() + datetime.timedelta(days=90)).strftime("%Y-%m-%d"), scale=1)
                            self.profile_duration = gr.Slider(label="Plan Duration (Weeks)", minimum=4, maximum=24, step=1, value=12, scale=1)
                        
                        self.profile_injury = gr.CheckboxGroup(label="Injury History", choices=["无", "膝盖", "踝关节", "足底筋膜", "腰椎"], value=["无"])
                        
                        self.profile_memory = gr.Textbox(label="Long-Term Memory (AI 自动提取与累积的个人习惯与历史偏好)", lines=3, placeholder="例如：不喜欢早起跑步\n经常肠胃不适...")
                        
                        with gr.Group():
                            gr.HTML("<div style='font-size: 11px; font-weight: 600; color: var(--primary-color); margin: 8px 0;'>Personal Bests (PB 成绩)</div>")
                            with gr.Row():
                                self.pb_800 = gr.Textbox(label="800m", placeholder="2:30", scale=1)
                                self.pb_1500 = gr.Textbox(label="1500m", placeholder="5:00", scale=1)
                                self.pb_5k = gr.Textbox(label="5k", placeholder="20:00", scale=1)
                            with gr.Row():
                                self.pb_10k = gr.Textbox(label="10k", placeholder="42:00", scale=1)
                                self.pb_half = gr.Textbox(label="Half", placeholder="1:35:00", scale=1)
                                self.pb_full = gr.Textbox(label="Full", placeholder="3:20:00", scale=1)
                        
                        with gr.Group():
                            gr.HTML("<div style='font-size: 11px; font-weight: 600; color: var(--primary-color); margin: 8px 0;'>Heart Rate Zones to Pace (5区心率配速映射)</div>")
                            with gr.Row():
                                self.z1_pace = gr.Textbox(label="Z1 (轻松)", placeholder="6:00-7:00", scale=1)
                                self.z2_pace = gr.Textbox(label="Z2 (有氧)", placeholder="5:30-6:00", scale=1)
                                self.z3_pace = gr.Textbox(label="Z3 (马拉松)", placeholder="5:00-5:30", scale=1)
                            with gr.Row():
                                self.z4_pace = gr.Textbox(label="Z4 (乳酸阈)", placeholder="4:30-5:00", scale=1)
                                self.z5_pace = gr.Textbox(label="Z5 (间歇)", placeholder="< 4:30", scale=1)
                        
                    with gr.Accordion("🔄 Adaptive Plan Adjustment", open=False, elem_classes="github-container"):
                        gr.HTML("<div style='font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;'>根据您近期的身体反馈，动态自适应调整接下来的训练计划</div>")
                        with gr.Row():
                            self.adaptive_fatigue = gr.Slider(minimum=1, maximum=10, step=1, value=5, label="Fatigue Level (1-10)")
                            self.adaptive_missed = gr.Checkbox(label="Missed recent workouts?", value=False)
                            self.adaptive_abnormal_hr = gr.Checkbox(label="Abnormal HR/Vitals?", value=False)
                        self.adaptive_notes = gr.Textbox(label="Additional Feedback", placeholder="例如：昨天没睡好，感觉大腿有点酸...", lines=2)
                        self.adaptive_btn = gr.Button("⚡ Generate Adaptive Plan", variant="primary")

                    with gr.Group(elem_classes="github-container"):
                        gr.HTML("<div class='github-header'>⚡ Pipeline Status</div>")
                        self.pipeline_status = gr.HTML(
                            value='<div class="pipeline-container"><div class="pipeline-item pending"><div class="pipeline-icon"></div><div class="pipeline-label">Router</div></div><div class="pipeline-item pending"><div class="pipeline-icon"></div><div class="pipeline-label">User Profile</div></div><div class="pipeline-item pending"><div class="pipeline-icon"></div><div class="pipeline-label">KG Extraction</div></div><div class="pipeline-item pending"><div class="pipeline-icon"></div><div class="pipeline-label">Plan Generation</div></div><div class="pipeline-item pending"><div class="pipeline-icon"></div><div class="pipeline-label">Safety Review</div></div><div class="pipeline-item pending"><div class="pipeline-icon"></div><div class="pipeline-label">Final Auditor</div></div></div>'
                        )
                        self.token_stats = gr.HTML(value="<div style='display: flex; gap: 4px; flex-wrap: wrap;'></div>")
                        self.roi_chart = gr.LinePlot(x="Iteration", y="ROI", title="Token ROI Trend", height=150, tooltip=["Iteration", "ROI"], container=False, visible=False)
                        self.risk_display = gr.HTML(label="Risk Alerts")
                    
                    with gr.Group(elem_classes="github-container"):
                        gr.HTML("<div class='github-header'>🛠️ Reasoning Logs</div>")
                        self.reasoning_box = gr.HTML(value="<div class='reasoning-terminal'>📝 等待分析任务启动...</div>", label="Reasoning Logs")

                with gr.Column(scale=4, min_width=400):
                    with gr.Group(elem_classes="github-container"):
                        gr.HTML("<div class='github-header'>📊 Dynamic Reasoning Trace</div>")
                        self.mermaid_output = gr.Markdown(value=f"```mermaid\n{graph_engine.generate_mermaid()}\n```", elem_classes="mermaid-container", height=600)
                        self.refresh_graph_btn = gr.Button("↻ Refresh Knowledge Graph", variant="secondary", size="sm")

        with gr.Tab("🧪 Evaluation", id="tab_eval"):
            with gr.Group(elem_classes="github-container"):
                gr.HTML("<div class='github-header'>⚡ Batch Processing</div>")
                self.eval_queries = gr.Textbox(label="Queries (one per line)", lines=10, placeholder="Query 1\nQuery 2...")
                self.eval_btn = gr.Button("Run Benchmark", variant="primary")
                self.eval_out = gr.JSON(label="Benchmark Results")

        # 定义用于处理事件的所有输入和输出集合
        self.qa_inputs = [
            self.msg_input, self.chatbot, self.profile_level, self.profile_mileage, self.profile_goal, self.profile_injury, self.profile_memory,
            self.profile_lthr, self.profile_tpace, self.pb_800, self.pb_1500, self.pb_5k, self.pb_10k, self.pb_half, self.pb_full,
            self.profile_race_date, self.profile_duration,
            self.z1_pace, self.z2_pace, self.z3_pace, self.z4_pace, self.z5_pace
        ]
        
        self.adaptive_inputs = [
            self.adaptive_fatigue, self.adaptive_missed, self.adaptive_abnormal_hr, self.adaptive_notes,
            self.chatbot, self.profile_level, self.profile_mileage, self.profile_goal, self.profile_injury, self.profile_memory,
            self.profile_lthr, self.profile_tpace, self.pb_800, self.pb_1500, self.pb_5k, self.pb_10k, self.pb_half, self.pb_full,
            self.profile_race_date, self.profile_duration,
            self.z1_pace, self.z2_pace, self.z3_pace, self.z4_pace, self.z5_pace
        ]
        
        self.qa_outputs = [
            self.msg_input, self.chatbot, self.token_stats, self.pipeline_status, self.roi_chart, self.risk_display, self.reasoning_box, self.report_display, self.mermaid_output, self.guided_questions_display,
            self.profile_level, self.profile_mileage, self.profile_goal, self.profile_injury, self.profile_memory,
            self.profile_lthr, self.profile_tpace, self.pb_800, self.pb_1500, self.pb_5k, self.pb_10k, self.pb_half, self.pb_full,
            self.profile_race_date, self.profile_duration,
            self.z1_pace, self.z2_pace, self.z3_pace, self.z4_pace, self.z5_pace,
            self.send_btn, self.adaptive_btn, self.refresh_graph_btn,
            self.ui_lock_trigger # 新增
        ]

        # 内部事件绑定
        self.send_btn.click(self.handle_qa, inputs=self.qa_inputs, outputs=self.qa_outputs, concurrency_limit=5)
        self.msg_input.submit(self.handle_qa, inputs=self.qa_inputs, outputs=self.qa_outputs, concurrency_limit=5)
        self.adaptive_btn.click(self.handle_adaptive_plan, inputs=self.adaptive_inputs, outputs=self.qa_outputs, concurrency_limit=5)
        self.eval_btn.click(self.run_batch, inputs=[self.eval_queries], outputs=[self.eval_out])
        self.refresh_graph_btn.click(lambda: f"```mermaid\n{graph_engine.generate_mermaid(highlight_phrases=DEFAULT_HIGHLIGHTS)}\n```", outputs=[self.mermaid_output])
