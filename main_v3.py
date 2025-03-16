import streamlit as st
import uuid
import random
from typing import Dict

from story_engine import STORY_SETTINGS, initialize_story, graph



DICE_PROMPTS = {
    1: "Your action is very weak and likely to fail.",
    2: "Your action has minimal chance of success.",
    3: "Your action has a modest possibility of working.",
    4: "Your action has a good chance of succeeding.",
    5: "Your action is strong and likely to succeed.",
    6: "Your action is extremely powerful and almost guaranteed to work!"
}



def init_session_state():
    """Initialize session state variables"""
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    if "story_started" not in st.session_state:
        st.session_state.story_started = False
    if "story_history" not in st.session_state:
        st.session_state.story_history = []
    if "current_setting" not in st.session_state:
        st.session_state.current_setting = None
    if "dice_num" not in st.session_state:
        st.session_state.dice_num = 0  # Initialize dice_num


def format_story_response(response: Dict) -> tuple:
    """Extract narrative, status, and choices from the response."""
    message = response.get("messages", [None])[0]

    if not message:
        return "", "", []

    if isinstance(message, str):
        content = message
    elif hasattr(message, "content"):
        content = message.content
    else:
        return "", "", []

    sections = content.split("[")
    narrative = ""
    status = ""
    choices = []

    for section in sections:
        if "Narrative]:" in section:
            narrative = section.split("Narrative]:")[1].strip()
        elif "Status]:" in section:
            status = section.split("Status]:")[1].strip()
        elif "Choices]:" in section:
            choices_text = section.split("Choices]:")[1].strip()
            choices = [choice.strip() for choice in choices_text.split('\n') if choice.strip()]

    return narrative, status, choices


def main():
    st.set_page_config(layout="wide", page_title="AI Story Adventure", page_icon="🎮")
    
    # Updated CSS with improved color scheme and layout
    st.markdown("""
        <style>
        /* Modern color palette - more subtle */
        :root {
            --bg-primary: #1a1a1a;
            --bg-secondary: rgb(38 39 48);
            --accent: #4a4a4a;
            --text-primary: #e0e0e0;
            --text-secondary: #a0a0a0;
            --border: #333333;
        }

        .main-title { 
            font-size: 2.8rem; 
            font-weight: 700; 
            margin-bottom: 0.5rem;
        }

        .subtitle { 
            font-size: 1.1rem; 
            margin-bottom: 2rem;
            color: var(--text-secondary);
        }

        .narrative-text {
            background-color: var(--bg-secondary);
            color: var(--text-primary);
            padding: 1.5rem;
            border-radius: 8px;
            line-height: 1.6;
            border: 1px solid var(--border);
            margin-bottom: 1rem;
        }

        .status-box { 
            background-color: var(--bg-secondary);
            color: var(--text-primary);
            padding: 1.5rem; 
            border-radius: 8px;
            margin-bottom: 1rem;
            border: 1px solid var(--border);
        }

        .status-lines {
            font-family: 'Courier New', monospace;
            line-height: 1.8;
            margin-top: 0.5rem;
        }

        .status-box h4 {
            color: var(--text-secondary);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.75rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.5rem;
        }

        .choices-box { 
            color: var(--text-primary);
            padding: 0.5rem 1rem ; 
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border: 1px solid var(--border);
            height: 100%;
        }

        .choices-box .button-container {
            padding: 0.5rem 0;
        }

        .stButton button {
            background-color: var(--bg-secondary);
            color: var(--text-primary);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 0.5rem 1rem;
            font-size: 0.9rem;
            transition: all 0.2s ease;
        }

        .stButton button:hover {
                transform: translateY(-1px);
        }

        .user-action {
            background-color: var(--bg-secondary);
            color: var(--text-primary);
            padding: 1.25rem;
            border-radius: 12px;
            margin: 1rem 0;
            border-left: 4px solid var(--accent);
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        /* Custom styling for story type selection cards */
        [data-testid="stHorizontalBlock"] > div > div {
            background-color: var(--bg-secondary);
            border-radius: 12px;
            padding: 1rem;
            transition: transform 0.2s ease;
            border: 1px solid var(--border);
        }

        [data-testid="stHorizontalBlock"] > div > div:hover {
            transform: translateY(-4px);
        }

        /* Improve text input and text area styling */
        .stTextInput input, .stTextArea textarea {
            background-color: var(--bg-secondary);
            border: 1px solid var(--border);
            color: var(--text-primary);
            border-radius: 8px;
            padding: 0.75rem;
        }

        .stTextInput input:focus, .stTextArea textarea:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.2);
        }

        /* Headers styling */
        h1, h2, h3, h4 {
            color: var(--text-primary);
            font-weight: 600;
        }

        /* Sidebar improvements */
        .sidebar .sidebar-content {
            background-color: var(--bg-primary);
        }
        </style>
    """, unsafe_allow_html=True)

    # Main title with custom styling
    st.markdown('<h1 class="main-title">🎮 AI Story Adventure</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Embark on an epic interactive storytelling journey</p>', unsafe_allow_html=True)

    init_session_state()

    # Story type selection in main area if not started
    if not st.session_state.story_started:
        st.markdown("### Choose Your Adventure")
        
        # Define expanded story settings with images
        EXPANDED_SETTINGS = {
            "fantasy": {
                "desc": "A magical realm of dragons and wizards", 
                "img": "https://placehold.co/600x400/9c27b0/ffffff?text=Fantasy"
            },
            "sci_fi": {
                "desc": "Explore distant galaxies and advanced technology", 
                "img": "https://placehold.co/600x400/2196f3/ffffff?text=Sci-Fi"
            },
            "horror": {
                "desc": "Face your darkest fears in spine-chilling tales", 
                "img": "https://placehold.co/600x400/f44336/ffffff?text=Horror"
            },
            "cyberpunk": {
                "desc": "Navigate a high-tech dystopian future", 
                "img": "https://placehold.co/600x400/ff9800/ffffff?text=Cyberpunk"
            },
            "western": {
                "desc": "Adventure in the wild frontier", 
                "img": "https://placehold.co/600x400/795548/ffffff?text=Western"
            },
            "mystery": {
                "desc": "Solve intricate puzzles and crimes", 
                "img": "https://placehold.co/600x400/607d8b/ffffff?text=Mystery"
            }
        }

        # Display settings in a grid
        cols = st.columns(3)
        for idx, (setting, details) in enumerate(EXPANDED_SETTINGS.items()):
            with cols[idx % 3]:
                with st.container(border=True):
                    st.image(details['img'], use_container_width=True)
                    st.markdown(f"### {setting.title()}")
                    st.write(details['desc'])
                    if st.button("Choose Setting", key=f"btn_{setting}"):
                        st.session_state.story_started = True
                        st.session_state.current_setting = setting
                        st.rerun()

    # Main story area
    else:
        # Move sidebar content to st.sidebar
        with st.sidebar:
            st.markdown("### Current Setting")
            st.info(f"🌍 {st.session_state.current_setting.title()}")
            
            if st.button("Start New Story", type="secondary"):
                st.session_state.story_started = False
                st.session_state.story_history = []
                st.rerun()

        # Ensure initial story generation
        if not st.session_state.story_history:
            config = {
                "configurable": {
                    "user_id": st.session_state.user_id,
                    "thread_id": st.session_state.user_id,
                }
            }
            initial_state = initialize_story(st.session_state.current_setting)

            with st.spinner("Creating your story..."):
                try:
                    story_generated = False
                    for chunk in graph.stream(initial_state, config=config):
                        for node, updates in chunk.items():
                            if "messages" in updates:
                                narrative, status, choices = format_story_response(updates)
                                if narrative:
                                    st.session_state.story_history.append({
                                        "type": "system",
                                        "narrative": narrative,
                                        "status": status,
                                        "choices": choices,
                                    })
                                    story_generated = True
                    
                    if not story_generated:
                        st.error("No story was generated. Please try again.")
                        st.session_state.story_started = False
                        return
                    st.rerun()

                except Exception as e:
                    st.error(f"Error generating initial story: {str(e)}")
                    st.session_state.story_started = False
                    return

        # Display existing story history
        if st.session_state.story_history:
            for entry in st.session_state.story_history:
                if entry["type"] == "system":
                    st.markdown(f"<div class='narrative-text'>{entry['narrative']}</div>", 
                              unsafe_allow_html=True)
                    
                    # Create two columns for status and choices
                    choices_col, status_col = st.columns(2)
                    
                    with choices_col:
                        if entry['choices']:  # Only show choices if they exist
                            with st.container():
                                # Create a div that will contain both header and buttons
                                st.markdown("""
                                    <div class='choices-box'>
                                        <h4>Available Actions</h4>
                                    </div>
                                """, unsafe_allow_html=True)
                                
                                # Add custom CSS to style the button container
                                st.markdown("""
                                    <style>
                                        .choices-box + div [data-testid="stVerticalBlock"] {
                                            background-color: #1a1a1a !important;
                                            padding: 0 1rem 1rem 1rem;
                                            margin-top: -1rem;
                                            border-radius: 0 0 8px 8px;
                                        }
                                    </style>
                                """, unsafe_allow_html=True)
                                
                                # Add the buttons
                                for choice in entry['choices']:
                                    if choice.strip():
                                        if st.button(choice.strip(), key=f"choice_{hash(choice)}"):
                                            process_user_action(choice.strip())
                    
                    with status_col:
                        if entry['status']:  # Only show status if it exists
                            status_lines = entry['status'].split(',')  # Split by comma
                            st.markdown("""
                                <div class='status-box'>
                                    <h4>Current Status</h4>
                                    <div class='status-lines'>
                                        {}
                                    </div>
                                </div>
                            """.format('<br>'.join(line.strip() for line in status_lines)), 
                            unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='user-action'>🎮 Your Action: {entry['action']}</div>", 
                              unsafe_allow_html=True)

        # Only show custom action input if there's already a story
        if st.session_state.story_history:
            with st.container():
                st.markdown("### Custom Action")
                user_action = st.text_area("Type your own action:", key="action_input")
                if st.button("Take Custom Action", type="primary"):
                    if user_action:
                        st.session_state.story_history.append({
                            "type": "user",
                            "action": user_action
                        })

                        config = {
                            "configurable": {
                                "user_id": st.session_state.user_id,
                                "thread_id": st.session_state.user_id,
                            }
                        }

                        with st.spinner("Processing your action..."):
                            for chunk in graph.stream(
                                {"messages": [("user", user_action)]}, config=config
                            ):
                                for node, updates in chunk.items():
                                    if "messages" in updates:
                                        narrative, status, choices = format_story_response(updates)
                                        if(len(narrative) > 0):
                                            st.session_state.story_history.append({
                                                "type": "system",
                                                "narrative": narrative,
                                                "status": status,
                                                "choices": choices,
                                            })
                        st.rerun()


# Add this new helper function to handle user actions
def process_user_action(action: str):
    st.session_state.story_history.append({
        "type": "user",
        "action": action
    })

    config = {
        "configurable": {
            "user_id": st.session_state.user_id,
            "thread_id": st.session_state.user_id,
        }
    }

    with st.spinner("Processing your action..."):
        try:
            for chunk in graph.stream({"messages": [("user", action)]}, config=config):
                for node, updates in chunk.items():
                    if "messages" in updates:
                        narrative, status, choices = format_story_response(updates)
                        if narrative:
                            st.session_state.story_history.append({
                                "type": "system",
                                "narrative": narrative,
                                "status": status,
                                "choices": choices,
                            })
            st.rerun()
        except Exception as e:
            st.error(f"Error processing action: {str(e)}")


if __name__ == "__main__":
    main()
