import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from graph.workflow import create_workflow
from Constraint.state_updater import reset_escalation_state

def main():
    # 强制加载 .env.local 中的环境变量
    load_dotenv(".env.local")
    
    # 校验 API Key
    if not os.environ.get("gemini_api_key") and not os.environ.get("GEMINI_API_KEY"):
        print("错误: 无法在 env.local 找到 gemini_api_key！请检查配置。")
        return
        
    print("="*50)
    print("欢迎使用 获客初筛 Agent MVP (CLI 模式)")
    print("系统命令: 输入 '/reset' 重置静默状态，输入 '/quit' 退出")
    print("="*50)
    
    # 初始化工作流和状态
    app = create_workflow()
    
    state = {
        "messages": [],
        "intent": "",
        "is_unhappy": False,
        "abnormal_count": 0,
        "is_escalated": False,
        "message_timestamps": [],
        "reply_content": ""
    }
    
    while True:
        try:
            user_input = input("\n[客户]: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
            
        if not user_input:
            continue
            
        if user_input.lower() == '/quit':
            print("系统已退出。")
            break
            
        if user_input.lower() == '/reset':
            print(">> 执行外部命令: 重置系统的静默和异常状态...")
            reset_data = reset_escalation_state()
            state.update(reset_data)
            print(">> 重置完成，可以继续对话。")
            continue
            
        # 将用户消息追加到历史
        state["messages"].append(HumanMessage(content=user_input))
        
        # 运行图
        try:
            # 每次 invoke 都会返回最新的 state 字典，我们用它覆盖当前 state
            result_state = app.invoke(state)
            
            # 由于 reducer 的存在，LangGraph 可能将 messages 处理得不同
            # 对于简单的 typed dict (非 checkpoint)，它直接返回完整结构
            state.update(result_state)
            
            # 显示 Agent 的思考过程 (调试信息)
            print(f"  [Agent 意图]: {state.get('intent')} | [不满情绪]: {state.get('is_unhappy')}")
            print(f"  [异常计数]: {state.get('abnormal_count')} | [转人工状态]: {state.get('is_escalated')}")
            
            # 显示最终的外发回复
            reply = state.get("reply_content")
            if reply:
                print(f"[Agent]: {reply}")
                # 追加到历史消息，以便下一轮大模型有上下文
                # 但如果是动作标记或限流提示，不一定要作为 AI 消息加入。为简单起见，加进去。
                state["messages"].append(AIMessage(content=reply))
            elif state.get("intent") == "silent_escalated":
                print("[系统]: (处于静默状态，忽略用户输入)")
                
        except Exception as e:
            print(f"[系统错误]: {e}")

if __name__ == "__main__":
    main()
