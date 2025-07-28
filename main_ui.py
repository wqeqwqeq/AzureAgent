import os
import streamlit as st
from agent_service import initialize_agent, get_agent_response, is_agent_initialized

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
                
                # Check Azure environment variables
                # azure_vars = [
                #     "AZURE_OPENAI_DEPLOYMENT_NAME",
                #     "AZURE_OPENAI_ENDPOINT", 
                #     "AZURE_OPENAI_API_KEY"
                # ]
                
                # missing_azure_vars = []
                # for var in azure_vars:
                #     if not os.getenv(var):
                #         missing_azure_vars.append(var)
                
                # if missing_azure_vars:
                #     st.error(f"Missing Azure environment variables: {', '.join(missing_azure_vars)}")
                #     st.info("Please set these variables in your .env file")
                # else:
                #     st.success("✅ All Azure environment variables are set")
                
                # Subscription selection (placeholder - you can populate this with actual subscriptions)
                subscription_options = ["EDW", "EDL", "MDM Vehicle", "MDM Customer"]
                selected_subscription = st.selectbox(
                    "Select Azure Subscription:",
                    options=subscription_options,
                    index=None,
                    placeholder="Choose subscription..."
                )
                
                if selected_subscription:
                    st.info(f"Selected: {selected_subscription}")
                
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
                    try:
                        initialize_agent()
                        st.success(f"✅ {selected_service} agent initialized successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to initialize {selected_service} agent: {e}")
        
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
    
    # Main chat interface
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
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
                        response = get_agent_response(prompt)
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
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