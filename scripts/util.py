from langchain_core.messages import BaseMessage

def get_msg_content(result): 
    # NOTE: for langchain create_agent agent.invoke, dict is the default response. 
    # The other cases are left in case we want to experiment 
    if isinstance(result, dict):
        if "output" in result and isinstance(result["output"], str):
            return result["output"]

        msgs = result.get("messages", None)
        if isinstance(msgs, list) and len(msgs) > 0:
            last = msgs[-1]
            if isinstance(last, BaseMessage):
                return getattr(last, "content", str(last))
            if isinstance(last, dict):
                return last.get("content", str(last))

        return str(result)
    
    if isinstance(result, BaseMessage):
        return getattr(result, "content", str(result))

    if isinstance(result, list) and len(result) > 0:
        last = result[-1]
        if isinstance(last, BaseMessage):
            return getattr(last, "content", str(last))
        if isinstance(last, dict):
            return last.get("content", str(last))
        return str(last)

    return str(result)

def print_trace(result, verbose=False): 
    print(f"=== FULL TRACE {'--VERBOSE' if verbose else ''} ===") 
    if isinstance(result, dict) and "messages" in result:
        messages = result["messages"]
        if not isinstance(messages, list) or len(messages) == 0:
            print("No messages")
            return
         
        if verbose: 
            for i, msg in enumerate(messages, start=1):
                if isinstance(msg, BaseMessage):
                    role = msg.type  # "human", "ai", "system", "tool"
                    content = msg.content
                elif isinstance(msg, dict):
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                else:
                    role = type(msg).__name__
                    content = str(msg)

                print(f"\n--- Message {i} ({role.upper()}) ---")
                print(content)
        else: 
            last = messages[-1]
            if isinstance(last, BaseMessage):
                print(last.content)
            elif isinstance(last, dict):
                print(last.get("content", last))
            else:
                print(last)
    else:
        print(result)
    print("\n=== END TRACE ===\n")

    