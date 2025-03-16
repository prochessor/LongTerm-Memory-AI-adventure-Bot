import json
from typing import List, Literal, Optional
import uuid

import tiktoken
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.messages import get_buffer_string
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_core.vectorstores import InMemoryVectorStore
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq

# Initialize vector store and model jahan pe memories store hongi and baad men conversation context ke base pe lookup kren gay
recall_vector_store = InMemoryVectorStore(HuggingFaceEmbeddings())  


model = ChatGroq(
    temperature=0.8,
    model="llama3-70b-8192",
    api_key="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"
)

# Story settings
STORY_SETTINGS = {
    "fantasy": "A medieval world of magic, dragons, and epic quests",
    "sci_fi": "A futuristic universe with advanced technology, space travel, and alien civilizations",
    "horror": "A dark and mysterious world filled with supernatural creatures and eerie encounters",
    "cyberpunk": "A dystopian future where advanced technology meets gritty urban environments",
    "western": "The wild frontier of the American Old West, filled with cowboys and outlaws"
}

def get_user_id(config: RunnableConfig) -> str:
    user_id = config["configurable"].get("user_id")
    if user_id is None:
        raise ValueError("User ID needs to be provided to save a memory.")
    return user_id

@tool
def save_recall_memory(memory: str, config: RunnableConfig) -> str:
    """Save memory to vectorstore for later semantic retrieval."""
    user_id = get_user_id(config)
    
    document = Document(
        page_content=memory, 
        id=str(uuid.uuid4()), 
        metadata={"user_id": user_id}
    )
    recall_vector_store.add_documents([document])
    return memory

@tool
def search_recall_memories(query: str, config: RunnableConfig) -> List[str]:
    """Search for relevant memories."""
    user_id = get_user_id(config)
    
    
    # jb semantic search kren gay to usmen yeh help krega, ke user specific memory day based on the user id
    def _filter_function(doc: Document) -> bool:
        return doc.metadata.get("user_id") == user_id
    

    documents = recall_vector_store.similarity_search(
        query, k=3, filter=_filter_function
    )
    return [document.page_content for document in documents]

tools = [save_recall_memory, search_recall_memories]

class StoryState(MessagesState):
    recall_memories: List[str]
    setting: str = ""

# Story prompt template
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert storyteller and game master running an interactive narrative experience. 
        You must create engaging, dynamic stories that respond to the player's choices while maintaining 
        narrative consistency and remembering important details about the story and player's past actions.

        Setting: {setting_description}

        STRICT RESPONSE FORMAT:
        You must ALWAYS format your responses exactly like this:
        [Narrative]: (Describe what happens in the story)
        [Status]: (Brief status update about location, health, inventory, etc)
        [Choices]: (List 2-4 possible actions, one per line)

        Example correct format:
        [Narrative]: You find yourself in the bustling market square of Silverleaf.
        [Status]: Location: Silverleaf Market, Health: Healthy, Gold: 10
        [Choices]: 
        Approach the merchant selling exotic goods
        Visit the local tavern for information
        Head to the city gates

        Memory Usage Guidelines:
        1. Store key plot points, character introductions, and major decisions
        2. Remember player's choices and their consequences
        3. Track important items, abilities, or relationships acquired
        4. Maintain consistency with previously established world elements
        5. Record significant location details and environmental changes
        6. Note character development and emotional moments
        7. Keep track of any ongoing quests or objectives
        8. Remember important NPCs and their relationships to the player

        ## Recall Memories
        Previous story elements and choices:
        {recall_memories}

        ## Instructions
        1. If this is a new story, generate an engaging opening scene that sets up the world and initial situation
        2. For continuing stories, acknowledge previous events and maintain continuity
        3. End each response with a situation that requires player choice
        4. Describe scenes vividly but concisely
        5. Incorporate consequences of previous choices
        6. Include occasional random events to keep the story unpredictable
        7. Maintain appropriate tone for the chosen setting
        8. ALWAYS use the exact format specified above with [Narrative], [Status], and [Choices] sections

        Remember to save important story elements using the memory tools."""
    ),
    ("placeholder", "{messages}"),
])

model_with_tools = model.bind_tools(tools)

tokenizer = tiktoken.get_encoding("cl100k_base")


def initialize_story(setting: str) -> dict:
    """Initialize a new story with the chosen setting."""
    if setting not in STORY_SETTINGS:
        raise ValueError(f"Invalid setting. Choose from: {', '.join(STORY_SETTINGS.keys())}")
    
    initial_message = f"Let's begin a new story in a {setting} setting!"
    return {
        "messages": [("user", initial_message)],
        "setting": setting,
        "recall_memories": []
    }

def load_memories(state: StoryState, config: RunnableConfig) -> StoryState:
    """Load memories for the current conversation."""
    convo_str = get_buffer_string(state["messages"])
    convo_str = tokenizer.decode(tokenizer.encode(convo_str)[:2048]) # we can call multiple times for the other tokens not in this round to get more efficient memories
    recall_memories = search_recall_memories.invoke(convo_str, config)
    return {
        "recall_memories": recall_memories,
    }

def agent(state: StoryState) -> StoryState:
    """Process the current state and generate the next story segment."""
    bound = prompt | model_with_tools
    recall_str = "<recall_memory>\n" + "\n".join(state["recall_memories"]) + "\n</recall_memory>"
    
    setting_description = STORY_SETTINGS.get(state["setting"], "A mysterious world of adventure")
    
    prediction = bound.invoke({
        "messages": state["messages"],
        "recall_memories": recall_str,
        "setting_description": setting_description,
    })
    return {
        "messages": [prediction],
    }

def route_tools(state: StoryState) -> Literal["tools", END]:
    """Route based on whether tools are needed."""
    msg = state["messages"][-1]
    # Check for tool calls in the correct way
    if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs.get('tool_calls'):
        return "tools"
    return END



# Create and expose the graph
builder = StateGraph(StoryState)
builder.add_node("load_memories", load_memories)
builder.add_node("agent", agent)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "load_memories")
builder.add_edge("load_memories", "agent")
builder.add_conditional_edges("agent", route_tools, ["tools", END])
builder.add_edge("tools", "agent")

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)