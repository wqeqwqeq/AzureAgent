import os
import asyncio
import streamlit as st
from DAPEAgent.github.github_mcp_agent import GitHubAgent
from DAPEAgent.azure.triage_agent import run_triage_agent
from DAPEAgent.azure.config import AzureCtx
from DAPEAgent.utils import extract_token_usage
from azure_tools.auth import AzureAuthentication

# set up mlflow
import mlflow
from mlflow.openai._agent_tracer import add_mlflow_trace_processor

# Configure MLflow
# mlflow.openai.autolog() #type: ignore
mlflow.openai.autolog(log_traces=False) #type: ignore
add_mlflow_trace_processor()             
mlflow.set_tracking_uri("http://127.0.0.1:5000")
mlflow.set_experiment("OpenAI-Agents-only")


def initialize_agent(service_type):
    """Initialize the selected agent type."""
    try:
        if service_type == "GitHub":
            if "github_agent" not in st.session_state:
                st.session_state.github_agent = None
            st.session_state.selected_service = "GitHub"
            st.session_state.agent_initialized = True
            return True
        elif service_type == "Azure":
            if "azure_ctx" not in st.session_state:
                auth = AzureAuthentication()
                azure_ctx = AzureCtx(auth=auth)
                
                # Apply custom subscription settings if available
                if hasattr(st.session_state, 'azure_subscription_id'):
                    azure_ctx.subscription_id = st.session_state.azure_subscription_id
                if hasattr(st.session_state, 'azure_resource_group'):
                    azure_ctx.resource_group_name = st.session_state.azure_resource_group
                if hasattr(st.session_state, 'azure_resource_name'):
                    azure_ctx.resource_name = st.session_state.azure_resource_name
                    
                st.session_state.azure_ctx = azure_ctx
            st.session_state.selected_service = "Azure"
            st.session_state.agent_initialized = True
            return True
        else:
            return False
    except Exception as e:
        st.error(f"Failed to initialize {service_type} agent: {e}")
        return False

def is_agent_initialized():
    """Check if an agent is initialized."""
    return st.session_state.get("agent_initialized", False)

def get_agent_response(prompt):
    """Get response from the initialized agent."""
    service_type = st.session_state.get("selected_service")
    
    if service_type == "GitHub":
        return get_github_response(prompt)
    elif service_type == "Azure":
        return get_azure_response(prompt)
    else:
        raise ValueError(f"Unknown service type: {service_type}")

def get_github_response(prompt):
    """Get response from GitHub agent."""
    async def get_response():
        async with GitHubAgent() as github_agent:
            # Get chat history from session state
            chat_history = st.session_state.get("chat_history", [])
            return await github_agent.get_response(prompt, chat_history)
    
    return asyncio.run(get_response())

def get_azure_response(prompt):
    """Get response from Azure agent."""
    azure_ctx = st.session_state.get("azure_ctx")
    
    # Update context with current session state values if they exist
    if azure_ctx:
        if hasattr(st.session_state, 'azure_subscription_id'):
            azure_ctx.subscription_id = st.session_state.azure_subscription_id
        if hasattr(st.session_state, 'azure_resource_group'):
            azure_ctx.resource_group_name = st.session_state.azure_resource_group
        if hasattr(st.session_state, 'azure_resource_name'):
            azure_ctx.resource_name = st.session_state.azure_resource_name
    
    # Build context with chat history similar to GitHub agent
    chat_history = st.session_state.get("chat_history", [])
    if chat_history:
        context = "Previous conversation:\n"
        for msg in chat_history[-10:]:  # Keep last 10 exchanges
            context += f"User: {msg['user']}\nAssistant: {msg['assistant']}\n\n"
        context += f"Current question: {prompt}"
        full_input = context
    else:
        full_input = prompt
    
    result = asyncio.run(run_triage_agent(full_input, azure_ctx))
    return result

def main():
    st.set_page_config(
        page_title="Azure DAP Copilot",
        page_icon="🚗",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    
    /* Overlay to ensure text readability */
    .main::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(255, 255, 255, 0.9);
        z-index: -1;
    }
    
    
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        border-left: 4px solid;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
    }
    .user-message {
        background-color: rgba(227, 242, 253, 0.95);
        border-left-color: #2196f3;
    }
    .assistant-message {
        background-color: rgba(243, 229, 245, 0.95);
        border-left-color: #9c27b0;
    }
    .stTextInput > div > div > input {
        border-radius: 20px;
        background: rgba(255, 255, 255, 0.95);
    }
    .status-indicator {
        padding: 0.5rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
        font-weight: bold;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
    }
    .status-ready {
        background-color: rgba(212, 237, 218, 0.95);
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    .status-warning {
        background-color: rgba(255, 243, 205, 0.95);
        color: #856404;
        border: 1px solid #ffeaa7;
    }
    .service-config {
        background-color: rgba(248, 249, 250, 0.95);
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 4px solid #007bff;
        backdrop-filter: blur(10px);
    }
    
    /* Sidebar styling for better contrast */
    .css-1d391kg {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
    }
    
    /* Chat container styling */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    
    /* Footer styling */
    .footer {
        background: rgba(255, 255, 255, 0.9);
        padding: 1rem;
        border-radius: 0.5rem;
        margin-top: 2rem;
        backdrop-filter: blur(10px);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 class="main-header">Azure DAP Copilot</h1>', unsafe_allow_html=True)
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Service Selection
        st.markdown("### 🔗 Service Connection")
        service_options = ["Azure", "Snowflake", "Azure DevOps", "GitHub"]
        selected_service = st.selectbox(
            "Choose your service:",
            options=service_options,
            index=None,
            placeholder="Select a service..."
        )
        
        # Conditional configuration based on selected service
        if selected_service:
            # st.markdown('<div class="service-config">', unsafe_allow_html=True)
            # st.markdown(f"**{selected_service} Configuration**")
            
            if selected_service == "Azure":
                # Azure-specific configuration
                # st.markdown("#### Azure Settings")
                
                # Custom subscription toggle
                use_custom_subscription = st.checkbox("Use custom subscription settings")
                
                if use_custom_subscription:
                    # Custom Azure Context inputs (moved from streamlit_ui.py)
                    st.markdown("#### Custom Azure Context")
                    subscription_id = st.text_input(
                        "Subscription ID",
                        placeholder="e.g., ee5f77a1-2e59-4335-8bdf-f7ea476f6523",
                        help="Enter your Azure subscription ID"
                    )
                    resource_group_name = st.text_input(
                        "Resource Group Name",
                        placeholder="e.g., SQL-RG",
                        help="Enter your Azure resource group name"
                    )
                    resource_name = st.text_input(
                        "Resource Name",
                        placeholder="e.g., adf-stanley",
                        help="Enter your Azure resource name"
                    )
                    
                    # Store custom values in session state
                    if subscription_id:
                        st.session_state.azure_subscription_id = subscription_id.strip()
                    if resource_group_name:
                        st.session_state.azure_resource_group = resource_group_name.strip()
                    if resource_name:
                        st.session_state.azure_resource_name = resource_name.strip()
                else:
                    # Predefined subscription selection
                    subscription_options = ["EDW", "EDL", "MDM Vehicle", "MDM Customer"]
                    selected_subscription = st.selectbox(
                        "Select Azure Subscription:",
                        options=subscription_options,
                        index=None,
                        placeholder="Choose subscription..."
                    )
                    
                    if selected_subscription:
                        st.info(f"Selected: {selected_subscription}")
                        st.session_state.azure_selected_subscription = selected_subscription
                    
                    # Environment selection for Azure
                    azure_environments = ["NonProd", "Prod"]
                    selected_azure_environment = st.selectbox(
                        "Select Azure Environment:",
                        options=azure_environments,
                        index=None,
                        placeholder="Choose environment..."
                    )
                    
                    if selected_azure_environment:
                        st.info(f"Selected: {selected_azure_environment}")
                        st.session_state.azure_selected_environment = selected_azure_environment
                
            elif selected_service == "Snowflake":
                # Snowflake-specific configuration
                # st.markdown("#### Snowflake Settings")
                
                # Environment selection for Snowflake
                snowflake_environments = ["Sandbox", "Dev", "QA", "Prod"]
                selected_environment = st.selectbox(
                    "Select Snowflake Environment:",
                    options=snowflake_environments,
                    index=None,
                    placeholder="Choose environment..."
                )
                
                if selected_environment:
                    st.info(f"Selected: {selected_environment}")
                
                # Check Snowflake environment variables (you can customize these)
                # snowflake_vars = [
                #     "SNOWFLAKE_ACCOUNT",
                #     "SNOWFLAKE_USER",
                #     "SNOWFLAKE_PASSWORD"
                # ]
                
                # missing_snowflake_vars = []
                # for var in snowflake_vars:
                #     if not os.getenv(var):
                #         missing_snowflake_vars.append(var)
                
                # if missing_snowflake_vars:
                #     st.warning(f"Missing Snowflake environment variables: {', '.join(missing_snowflake_vars)}")
                #     st.info("Please set these variables in your .env file")
                # else:
                #     st.success("✅ All Snowflake environment variables are set")
                    
            elif selected_service == "Azure DevOps":
                # Azure DevOps - no additional configuration needed
                # st.markdown("#### Azure DevOps Settings")
                st.info("✅ Azure DevOps connection ready - no additional configuration required")
                
            elif selected_service == "GitHub":
                # GitHub - no additional configuration needed
                # st.markdown("#### GitHub Settings")
                st.info("✅ GitHub connection ready - no additional configuration required")
            
            # st.markdown('</div>', unsafe_allow_html=True) # This line was causing the empty box issue
        
        # Initialize button (only show if service is selected)
        if selected_service:
            if st.button("🚀 Initialize Agent", type="primary"):
                with st.spinner(f"Initializing {selected_service} agent..."):
                    if initialize_agent(selected_service):
                        st.success(f"✅ {selected_service} agent initialized successfully!")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to initialize {selected_service} agent")
        
        # Status indicator
        st.markdown("### 📊 Agent Status")
        if selected_service:
            if is_agent_initialized():
                st.markdown(f'<div class="status-indicator status-ready">🟢 {selected_service} Agent is ready</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="status-indicator status-warning">🟡 {selected_service} Agent not initialized</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-indicator status-warning">🟡 No service selected</div>', unsafe_allow_html=True)
        
        # Clear chat button
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.session_state.chat_history = []
            st.rerun()
        
        # Information section
        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.markdown("""
        This AI Assistant supports:
        - **Azure** - Azure resource management
        - **Snowflake** - Data warehouse operations
        - **Azure DevOps** - CI/CD and project management
        - **GitHub** - Repository and code management
        
        Select your service above to get started.
        """)
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "agent_initialized" not in st.session_state:
        st.session_state.agent_initialized = False
    if "selected_service" not in st.session_state:
        st.session_state.selected_service = None
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me about your selected service..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get response from agent
        with st.chat_message("assistant"):
            with st.spinner("🤖 Thinking..."):
                try:
                    if not selected_service:
                        st.warning("Please select a service first using the sidebar.")
                    elif not is_agent_initialized():
                        st.warning(f"Please initialize the {selected_service} agent first using the sidebar button.")
                    else:
                        # Get agent result
                        result = get_agent_response(prompt)
                        response = result.final_output
                        
                        # Display response
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        
                        # Extract and display token usage for both GitHub and Azure
                        token_usage = extract_token_usage(result)
                        with st.expander("📊 Token Usage Details"):
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("Input Tokens", token_usage['input_tokens'])
                            
                            with col2:
                                st.metric("Output Tokens", token_usage['output_tokens'])
                            
                            with col3:
                                st.metric("Cache Tokens", token_usage['cache_tokens'])
                            
                            with col4:
                                st.metric("Total Tokens", token_usage['total_tokens'])
                        
                        # Update chat history for both GitHub and Azure agents
                        if st.session_state.get("selected_service") in ["GitHub", "Azure"]:
                            st.session_state.chat_history.append({
                                "user": prompt,
                                "assistant": response
                            })
                except Exception as e:
                    error_msg = f"Error getting response: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div class="footer" style='text-align: center; color: #666;'>
        <p>Powered by Semantic Kernel and Azure MCP | Built with Streamlit</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()