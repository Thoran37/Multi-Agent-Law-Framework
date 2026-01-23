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
        if isinstance(msg, HumanMessage):
            role = "USER"
        elif isinstance(msg, SystemMessage):
            role = "SYSTEM"
        else:
            role = "AGENT"
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
    # Dynamic decision based on simple weights computed from the transcript.
    # We compute a lightweight score for each lawyer (plaintiff/defendant)
    # using keyword matches and message length. The party with the lower
    # score is asked to speak next (they should rebut the stronger position).
    current_round = state.get("round", 0)

    MAX_ROUNDS = 6
    if current_round >= MAX_ROUNDS:
        print("--- (DEBATE CONCLUDED - MOVING TO JUDGE) ---")
        return "judge"

    def compute_scores(s: CaseState):
        plaintiff_kws = [
            'prove', 'evidence', 'liable', 'damages', 'injury', 'breach', 'violation', 'compensation'
        ]
        defendant_kws = [
            'deny', 'no evidence', 'innocent', 'dismiss', 'acquitt', 'compliance', 'not proved', 'access', 'misuse'
        ]

        msgs = s.get('messages', [])
        # Skip the initial human message(s) when assigning AI messages to speakers.
        ai_messages = [m for m in msgs if isinstance(m, AIMessage)]

        scores = {'plaintiff': 0.0, 'defendant': 0.0}

        for idx, m in enumerate(ai_messages):
            text = (m.content or '').lower()
            # Heuristic: even-indexed AI messages -> plaintiff, odd -> defendant
            speaker = 'plaintiff' if idx % 2 == 0 else 'defendant'

            # Keyword counts
            kw_count = 0
            for kw in (plaintiff_kws + defendant_kws):
                if kw in text:
                    kw_count += text.count(kw)

            # Length contribution (longer arguments -> higher score)
            length_score = max(0, len(text) / 200.0)

            # Combine
            scores[speaker] += kw_count * 2.0 + length_score

        return scores

    scores = compute_scores(state)
    p_score = scores['plaintiff']
    d_score = scores['defendant']

    print(f"[round_logic] round={current_round} scores -> plaintiff={p_score:.2f}, defendant={d_score:.2f}")

    # If scores are very close, alternate based on last speaker
    if abs(p_score - d_score) < 0.5:
        # Determine last AI speaker (if any)
        ai_msgs = [m for m in state.get('messages', []) if isinstance(m, AIMessage)]
        if not ai_msgs:
            next_speaker = 'plaintiff'
        else:
            last_idx = len(ai_msgs) - 1
            last_speaker = 'plaintiff' if last_idx % 2 == 0 else 'defendant'
            # alternate: if last was plaintiff, ask defendant next, else plaintiff
            next_speaker = 'defendant' if last_speaker == 'plaintiff' else 'plaintiff'
    else:
        # Ask the weaker party (lower score) to respond / rebut
        next_speaker = 'plaintiff' if p_score < d_score else 'defendant'

    print(f"--- (ROUND {current_round + 1} - NEXT SPEAKER: {next_speaker.upper()}) ---")

    # Map to graph edge keys: allow defendant to be chosen again, or go to judge
    return next_speaker

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
        # allow the defender to speak again if weights choose it
        "defendant": "defendant",
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

    # Allow selecting jurisdiction at the first step so the debate uses
    # jurisdiction-specific laws and reasoning. Options: india, us, paris,
    # england, australia (case-insensitive). Default is India.
    COUNTRIES = ["India", "US", "Paris", "England", "Australia"]
    print("Select jurisdiction for this case:")
    for i, c in enumerate(COUNTRIES, start=1):
        print(f"  {i}) {c}")
    sel = input("Enter number (default 1): ").strip()
    try:
        idx = int(sel) - 1 if sel else 0
        if idx < 0 or idx >= len(COUNTRIES):
            idx = 0
    except Exception:
        idx = 0
    jurisdiction = COUNTRIES[idx]

    # Put the jurisdiction as a SystemMessage so call_agent will include it
    # in the prompt as a system-level instruction for all agents.
    initial_state = CaseState(
        messages=[
            SystemMessage(content=f"JURISDICTION: {jurisdiction}. Apply legal standards and precedents relevant to {jurisdiction}."),
            HumanMessage(content="CASE DETAILS:\n" + case_details)
        ],
        round=0
    )

    print("--- (STARTING CASE) ---")
    
    result = legal_graph.invoke(initial_state)

    print("\n========== FINAL TRANSCRIPT ==========\n")
    for msg in result["messages"]:
        role = "USER" if isinstance(msg, HumanMessage) else "AGENT"
        print(f"{role}:\n{msg.content}\n")