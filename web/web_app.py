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
            "is_unhappy": False,
            "abnormal_count": 0,
            "is_escalated": False,
            "message_timestamps": [],
            "reply_content": ""
        }
    
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
        "is_unhappy": False,
        "abnormal_count": 0,
        "is_escalated": False,
        "message_timestamps": [],
        "reply_content": ""
    }
    new_state.update(reset_data)
    return [], new_state

# 构建 Gradio Web 界面
with gr.Blocks(title="Kapibala Agent MVP", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 获客初筛 Agent MVP (Web UI)")
    gr.Markdown("本项目是基于 Gradio 构建的交互界面。请在左侧与 Agent 进行对话，在右侧可以实时查看其内部的研判状态。")
    
    agent_state = gr.State(None)
    
    with gr.Row():
        with gr.Column(scale=3):
            # 对话框
            chatbot = gr.Chatbot(height=500, label="Agent 对话")
            with gr.Row():
                msg = gr.Textbox(label="输入消息", placeholder="请输入...", scale=4)
                submit_btn = gr.Button("发送", variant="primary", scale=1)
            clear_btn = gr.Button("清除对话")
                
        with gr.Column(scale=1):
            gr.Markdown("### 内部状态 (Agent State)")
            intent_box = gr.Textbox(label="当前意图 (Intent)", interactive=False)
            unhappy_box = gr.Checkbox(label="不满情绪 (Is Unhappy)", interactive=False)
            abnormal_box = gr.Number(label="异常计数 (Abnormal Count)", interactive=False)
            escalated_box = gr.Checkbox(label="转人工状态 (Is Escalated)", interactive=False)
            
            gr.Markdown("---")
            gr.Markdown("**调试控制**")
            reset_btn = gr.Button("重置状态 (Reset)", variant="stop")
            
    # 消息处理逻辑
    def handle_msg(user_msg, chat_history, current_state):
        if not user_msg.strip():
            return "", chat_history, current_state
            
        bot_reply, new_state = respond(user_msg, chat_history, current_state)
        chat_history.append([user_msg, bot_reply])
        
        return "", chat_history, new_state
        
    def update_sidebar(state):
        if not state:
            return "", False, 0, False
        return (
            state.get("intent", ""),
            state.get("is_unhappy", False),
            state.get("abnormal_count", 0),
            state.get("is_escalated", False)
        )
        
    # 绑定发送事件
    submit_btn.click(
        handle_msg, 
        inputs=[msg, chatbot, agent_state], 
        outputs=[msg, chatbot, agent_state]
    ).then(
        update_sidebar,
        inputs=[agent_state],
        outputs=[intent_box, unhappy_box, abnormal_box, escalated_box]
    )
    
    msg.submit(
        handle_msg, 
        inputs=[msg, chatbot, agent_state], 
        outputs=[msg, chatbot, agent_state]
    ).then(
        update_sidebar,
        inputs=[agent_state],
        outputs=[intent_box, unhappy_box, abnormal_box, escalated_box]
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
        outputs=[intent_box, unhappy_box, abnormal_box, escalated_box]
    )
    
    clear_btn.click(
        do_reset,
        inputs=None,
        outputs=[chatbot, agent_state]
    ).then(
        update_sidebar,
        inputs=[agent_state],
        outputs=[intent_box, unhappy_box, abnormal_box, escalated_box]
    )
    
if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)
