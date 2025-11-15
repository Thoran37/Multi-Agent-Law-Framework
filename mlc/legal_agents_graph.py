from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
# from langchain_groq import ChatGroq # <<< MODIFIED (No longer needed)
from dotenv import load_dotenv
import os
from typing import List, Literal

# <<< MODIFIED (New imports for local model)
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

load_dotenv()

# -------------------------------------------------------------------
# 1. Load Local Model (Replaces Groq LLM)
# -------------------------------------------------------------------
MODEL_PATH = "./t5_finetuned" # Path to your model folder

print(f"Loading local model from {MODEL_PATH}...")
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    # T5 is a sequence-to-sequence model
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH)
    print("...Local model loaded successfully.")
except Exception as e:
    print(f"Error loading model: {e}")
    print("Please make sure the 't5_finetuned' folder is in the same directory.")
    exit()

# --- This section is no longer needed ---
# llm = ChatGroq(
#     groq_api_key=os.getenv("GROQ_API_KEY"),
#     model="llama-3.1-8b-instant",
#     temperature=0.2
# )
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# 2. Shared State
# -------------------------------------------------------------------
# (This remains exactly the same)
class CaseState(dict):
    messages: List[HumanMessage | AIMessage | SystemMessage]
    round: int 

# -------------------------------------------------------------------
# 3. Utility agent wrapper
# -------------------------------------------------------------------
# <<< MODIFIED (This is the *only* function logic that changes)
# This function now formats a string for T5 and uses model.generate()
def call_agent(system_prompt: str, messages: List):
    """
    Formats the prompt and calls the local T5 model.
    """
    
    # 1. Format the input for the T5 model
    # We combine the system prompt (the task) and the history
    input_text = f"{system_prompt}\n\n"
    
    for msg in messages:
        role = "USER" if isinstance(msg, HumanMessage) else "AGENT"
        input_text += f"{role}: {msg.content}\n"
        
    # Add a final cue for the agent to respond
    input_text += "AGENT:"

    # 2. Use your model's generation code
    try:
        inputs = tokenizer(input_text, return_tensors="pt", max_length=1024, truncation=True)
        # Give it a reasonable length to generate
        outputs = model.generate(**inputs, max_length=512, num_beams=4, early_stopping=True)
        response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
    except Exception as e:
        print(f"Error during model generation: {e}")
        response_text = "Error: Could not generate response."

    # 3. Return the same AIMessage object
    return AIMessage(content=response_text)

# -------------------------------------------------------------------
# 4. Agents
# -------------------------------------------------------------------
# (This remains exactly the same)
def plaintiff_node(state: CaseState):
    """The plaintiff node, presents complaint or rebuttal."""
    current_round = state.get("round", 0)
    
    # Dynamic prompt based on the round
    if current_round == 0:
        prompt = "You are the PLAINTIFF. Present your complaint concisely and factually."
    else:
        prompt = "You are the PLAINTIFF. Review the defendant's last statement and provide a concise rebuttal. Focus only on new points or disagreements."

    new_message = call_agent(prompt, state["messages"])
    return {"messages": state["messages"] + [new_message]}

# (This remains exactly the same)
def defendant_node(state: CaseState):
    """The defendant node, presents defense or rebuttal."""
    current_round = state.get("round", 0)

    if current_round == 0:
        prompt = "You are the DEFENDANT. Present your defense clearly and logically."
    else:
        prompt = "You are the DEFENDANT. Review the plaintiff's rebuttal and provide your counter-rebuttal. Be concise."

    new_message = call_agent(prompt, state["messages"])
    
    return {
        "messages": state["messages"] + [new_message],
        "round": current_round + 1 
    }

# (This remains exactly the same)
def judge_node(state: CaseState):
    """The judge node, provides the final ruling."""
    prompt = ("You are the JUDGE. The debate is concluded. Review the *entire* transcript. "
              "Provide:\n"
              "1. Summary of arguments\n"
              "2. Findings of fact\n"
              "3. Legal reasoning\n"
              "4. Final ruling.")
    
    new_message = call_agent(prompt, state["messages"])
    return {"messages": state["messages"] + [new_message]}

# (This remains exactly the same)
def auditor_node(state: CaseState):
    """The auditor node, reviews the judge's ruling."""
    prompt = "You are the AUDITOR. Review the judge's ruling for fairness and logical soundness."
    new_message = call_agent(prompt, state["messages"])
    return {"messages": state["messages"] + [new_message]}

# -------------------------------------------------------------------
# 5. Build Graph
# -------------------------------------------------------------------
# (This all remains exactly the same)

def round_logic(state: CaseState):
    """Determines if the debate should continue or go to the judge."""
    current_round = state.get("round", 0)
    
    if current_round < 3: 
        print(f"--- (ROUND {current_round + 1} - CONTINUING DEBATE) ---")
        return "plaintiff"
    else:
        print("--- (DEBATE CONCLUDED - MOVING TO JUDGE) ---")
        return "judge"

graph = StateGraph(CaseState)

graph.add_node("plaintiff", plaintiff_node)
graph.add_node("defendant", defendant_node)
graph.add_node("judge", judge_node)
graph.add_node("auditor", auditor_node)

graph.set_entry_point("plaintiff")
graph.add_edge("plaintiff", "defendant")

graph.add_conditional_edges(
    "defendant",
    round_logic,
    {
        "plaintiff": "plaintiff", 
        "judge": "judge"          
    }
)

graph.add_edge("judge", "auditor")
graph.add_edge("auditor", END)

legal_graph = graph.compile()

# -------------------------------------------------------------------
# 6. Run Example
# -------------------------------------------------------------------
# (This remains exactly the same)
if __name__ == "__main__":
    case_details = """
    Tenant claims landlord refused heater repair for 3 weeks.
    Tenant requests ₹50,000 compensation.
    Landlord claims tenant denied access and misused heater.
    """

    initial_state = CaseState(
        messages=[HumanMessage(content="CASE DETAILS:\n" + case_details)],
        round=0
    )

    print("--- (STARTING CASE) ---")
    
    result = legal_graph.invoke(initial_state)

    print("\n========== FINAL TRANSCRIPT ==========\n")
    for msg in result["messages"]:
        role = "USER" if isinstance(msg, HumanMessage) else "AGENT"
        print(f"{role}:\n{msg.content}\n")