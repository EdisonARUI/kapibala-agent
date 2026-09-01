import os
import sys
import warnings
from dotenv import load_dotenv
import gradio as gr
from langchain_core.messages import HumanMessage, AIMessage

# 将父目录加入 sys.path 以支持从 graph 和 constraint 导入模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.workflow import create_workflow
from constraint.state_updater import reset_escalation_state

warnings.filterwarnings("ignore", message=".*automatic function calling.*")

# 初始化环境变量和全局应用
load_dotenv()
app = create_workflow()

def respond(message, history, state):
    # state 为保存到 gr.State 的状态字典
    if state is None:
        state = {
            "messages": [],
            "intent": "",
            "action": "",
            "is_unhappy": False,
            "abnormal_count": 0,
            "is_escalated": False,
            "message_timestamps": [],
            "reply_content": ""
        }
    
    # 每次请求前清空上一轮的回复内容
    state["reply_content"] = ""
    
    # 判断是否处于静默状态
    if state.get("intent") == "silent_escalated":
        return "系统提示: 当前处于静默状态，已接入人工客服，请稍候...", state
        
    state["messages"].append(HumanMessage(content=message))
    
    try:
        result_state = app.invoke(state)
        state.update(result_state)
        
        reply = state.get("reply_content")
        if reply:
            state["messages"].append(AIMessage(content=reply))
            return reply, state
        elif state.get("intent") == "silent_escalated":
            return "系统提示: 已为您接入人工客服，请稍候...", state
        else:
            return "系统提示: 没有返回内容", state
            
    except Exception as e:
        return f"[系统错误]: {e}", state

def reset_state():
    reset_data = reset_escalation_state()
    new_state = {
        "messages": [],
        "intent": "",
        "action": "",
        "is_unhappy": False,
        "abnormal_count": 0,
        "is_escalated": False,
        "message_timestamps": [],
        "reply_content": ""
    }
    new_state.update(reset_data)
    return [], new_state

# 构建 Gradio Web 界面
with gr.Blocks(title="Kapibala Agent MVP") as demo:
    gr.Markdown("# Kapibala Agent")
    gr.Markdown("本项目是基于 Gradio 模拟IM交互界面。请在左侧与 Agent 进行对话，在右侧可以实时查看其内部的研判状态。")
    
    agent_state = gr.State(None)
    timer = gr.Timer(1)
    
    with gr.Row():
        with gr.Column(scale=3):
            # 对话框
            chatbot = gr.Chatbot(
                value=[], 
                height=500, 
                label="Agent 对话",
                avatar_images=(
                    "https://api.dicebear.com/7.x/adventurer/svg?seed=User", 
                    "https://api.dicebear.com/7.x/bottts/svg?seed=Agent"
                )
            )
            with gr.Row():
                msg = gr.Textbox(show_label=False, container=False, placeholder="请输入...", scale=4)
                submit_btn = gr.Button("发送", variant="primary", scale=1)
                
        with gr.Column(scale=1):
            gr.Markdown("### 内部状态 (Agent State)")
            intent_box = gr.Textbox(label="当前意图 (Intent)", interactive=False)
            action_box = gr.Textbox(label="执行动作 (Action)", interactive=False)
            unhappy_box = gr.Checkbox(label="不满情绪 (Is Unhappy)", interactive=False)
            abnormal_box = gr.Number(label="异常计数 (Abnormal Count)", interactive=False)
            escalated_box = gr.Checkbox(label="转人工状态 (Is Escalated)", interactive=False)
            rate_limit_box = gr.Textbox(label="限流冷却 (Rate Limit CD)", interactive=False)
            
            gr.Markdown("---")
            gr.Markdown("**调试控制**")
            with gr.Row():
                reset_btn = gr.Button("重置状态 (Reset)", variant="stop")
                clear_btn = gr.Button("清除对话", variant="secondary")
            
    # 消息处理逻辑
    def add_user_message(user_msg, chat_history):
        if chat_history is None:
            chat_history = []
        if not user_msg.strip():
            return user_msg, chat_history
        chat_history.append({"role": "user", "content": user_msg})
        return "", chat_history

    def get_bot_response(chat_history, current_state):
        if not chat_history:
            return chat_history, current_state
        # 获取最新的一条用户消息内容
        last_msg = chat_history[-1]
        if hasattr(last_msg, "content"):
            user_msg = last_msg.content
        elif isinstance(last_msg, dict):
            user_msg = last_msg.get("content", "")
        elif isinstance(last_msg, (list, tuple)):
            user_msg = last_msg[0]
        else:
            user_msg = str(last_msg)
        
        bot_reply, new_state = respond(user_msg, chat_history, current_state)
        chat_history.append({"role": "assistant", "content": bot_reply})
        
        return chat_history, new_state
        
    def update_sidebar(state):
        if not state:
            return "", "", False, 0, False
            
        return (
            state.get("intent", ""),
            state.get("action", ""),
            state.get("is_unhappy", False),
            state.get("abnormal_count", 0),
            state.get("is_escalated", False)
        )
        
    def update_countdown(state):
        if not state:
            return "0s"
        import time
        timestamps = state.get("message_timestamps", [])
        now = time.time()
        valid_timestamps = [ts for ts in timestamps if now - ts < 60]
        if valid_timestamps:
            remaining = max(0, int(60 - (now - valid_timestamps[-1])))
            return f"{remaining}s"
        return "0s"
        
    timer.tick(
        update_countdown,
        inputs=[agent_state],
        outputs=[rate_limit_box]
    )
        
    # 绑定发送事件
    submit_btn.click(
        add_user_message,
        inputs=[msg, chatbot],
        outputs=[msg, chatbot]
    ).then(
        get_bot_response,
        inputs=[chatbot, agent_state],
        outputs=[chatbot, agent_state]
    ).then(
        update_sidebar,
        inputs=[agent_state],
        outputs=[intent_box, action_box, unhappy_box, abnormal_box, escalated_box]
    )
    
    msg.submit(
        add_user_message,
        inputs=[msg, chatbot],
        outputs=[msg, chatbot]
    ).then(
        get_bot_response,
        inputs=[chatbot, agent_state],
        outputs=[chatbot, agent_state]
    ).then(
        update_sidebar,
        inputs=[agent_state],
        outputs=[intent_box, action_box, unhappy_box, abnormal_box, escalated_box]
    )
    
    # 绑定重置和清除事件
    def do_reset():
        chat_hist, state = reset_state()
        return chat_hist, state
        
    reset_btn.click(
        do_reset,
        inputs=None,
        outputs=[chatbot, agent_state]
    ).then(
        update_sidebar,
        inputs=[agent_state],
        outputs=[intent_box, action_box, unhappy_box, abnormal_box, escalated_box]
    )
    
    clear_btn.click(
        do_reset,
        inputs=None,
        outputs=[chatbot, agent_state]
    ).then(
        update_sidebar,
        inputs=[agent_state],
        outputs=[intent_box, action_box, unhappy_box, abnormal_box, escalated_box]
    )
    
if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7861, theme=gr.themes.Soft())
