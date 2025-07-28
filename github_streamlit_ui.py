import streamlit as st
import asyncio
import os
from DAPEAgent.github.github_mcp_agent import GitHubAgent

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Streamlit UI
st.set_page_config(
    page_title="GitHub Agent Chat",
    page_icon="🐙",
    layout="wide"
)

st.title("🐙 GitHub Agent Chat")
st.markdown("Ask questions about GitHub repositories and get intelligent responses!")

# Sidebar with controls
with st.sidebar:
    st.header("Controls")
    if st.button("Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()
    
    st.markdown("---")
    st.markdown("### GitHub Token")
    github_token = os.getenv('GITHUB_PAT')
    if github_token:
        st.success("✅ GitHub token configured")
    else:
        st.error("❌ GitHub token not found in environment")
        st.markdown("Set `GITHUB_PAT` environment variable")

# Display chat history
for msg in st.session_state.chat_history:
    with st.chat_message("user"):
        st.write(msg["user"])
    with st.chat_message("assistant"):
        st.write(msg["assistant"])

# Chat input
if prompt := st.chat_input("Ask about GitHub..."):
    # Add user message to chat
    with st.chat_message("user"):
        st.write(prompt)
    
    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                async def get_github_response():
                    async with GitHubAgent() as github_agent:
                        return await github_agent.get_response(prompt, st.session_state.chat_history)
                
                response = asyncio.run(get_github_response())
                st.write(response)
                
                # Add to chat history
                st.session_state.chat_history.append({
                    "user": prompt,
                    "assistant": response
                })
                
            except Exception as e:
                st.error(f"Error: {e}")
                st.markdown("**Possible issues:**")
                st.markdown("- GitHub token not configured")
                st.markdown("- Docker not running")
                st.markdown("- Network connectivity issues")

# Example questions
with st.expander("💡 Example Questions"):
    st.markdown("""
    - List repositories in an organization
    - Show me recent commits in a repository
    - What are the open issues in a specific repo?
    - Show me pull requests that need review
    - List contributors to a repository
    - Show repository statistics
    """)

# Information about GitHub context
with st.expander("ℹ️ About GitHub Agent"):
    st.markdown("""
    **GitHub Agent Features:**
    - Access to GitHub repositories via MCP server
    - Can query repository information, issues, pull requests
    - Maintains conversation context across interactions
    - Uses Docker-based GitHub MCP server for secure access
    
    **Requirements:**
    - GitHub Personal Access Token (`GITHUB_PAT` environment variable)
    - Docker running locally
    - Azure OpenAI API access
    """)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
        GitHub Agent Assistant - Powered by OpenAI and GitHub MCP Server
    </div>
    """,
    unsafe_allow_html=True
)