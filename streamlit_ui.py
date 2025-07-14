import asyncio,re, time
import subprocess
from typing import Optional
import streamlit as st
from agents import Runner, trace
from DAPEAgent.triage_agent import run_triage_agent
from DAPEAgent.config import AzureCtx
from azure_tools.auth import AzureAuthentication, start_az_login
import mlflow
from mlflow.openai._agent_tracer import add_mlflow_trace_processor

# Configure MLflow
# mlflow.openai.autolog() #type: ignore
mlflow.openai.autolog(log_traces=False) #type: ignore
add_mlflow_trace_processor()             
mlflow.set_tracking_uri("http://127.0.0.1:5000")
mlflow.set_experiment("OpenAI-Agents-only")

# Streamlit page configuration
st.set_page_config(
    page_title="Azure Agent Assistant",
    page_icon="☁️",
    layout="wide"
)

# 1️⃣  Initialise session state keys once
if "login_proc" not in st.session_state:
    st.session_state.login_proc = None          # handle returned by Popen
if "verification_uri" not in st.session_state:
    st.session_state.verification_uri = None
if "user_code" not in st.session_state:
    st.session_state.user_code = None
if "cli_auth" not in st.session_state:
    st.session_state.cli_auth = False


# 2️⃣  Kick off login the *first* time around
if st.session_state.login_proc is None:
    print("Starting Azure CLI authentication...")
    has_authed, uri, code, proc = start_az_login() #type: ignore
    if has_authed:
        st.success("✅ Logged in successfully!")
        st.session_state.cli_auth = True
        st.session_state.login_proc = True
        st.rerun()
    elif uri and code:
        st.session_state.update(
            {"verification_uri": uri, "user_code": code, "login_proc": proc}
        )
        st.rerun()                 # show the code immediately
    else:
        st.error("Failed to start 'az login'")


# 3️⃣  UI: show URL + code until login is done
if not st.session_state.cli_auth:
    st.title("☁️ Azure Agent Assistant")
    st.info("🔐 Azure Device Code Authentication Required")
    st.markdown("Open the URL below, enter the code, and sign in.")

    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📱 Authentication Steps:")
        st.markdown(f"1. Open this URL in your browser:")
        st.code(st.session_state.verification_uri)
        st.markdown(f"2. Enter this code:")
        st.code(st.session_state.user_code, language="text")
    
    with col2:
        st.markdown("### ⏰ Important Notes:")
        st.markdown("")
        st.info("💡 Authorize with your '-cl' cloud account")
        st.info("💡 You can use any device with a web browser")
        st.info("💡 After entering the code, return to this app")

    # Poll the process every rerun
    proc: subprocess.Popen = st.session_state.login_proc #type: ignore
    if proc.poll() is None:
        st.info("Waiting for sign-in to complete...")
        time.sleep(2)
        st.rerun()
    else:
        if proc.returncode == 0:
            st.success("✅ Logged in successfully!")
            st.session_state.cli_auth = True
            st.rerun()
        else:
            st.error("❌ Login failed – start over.")
            if st.button("🔄 Try again"):
                for k in ["login_proc", "verification_uri", "user_code"]:
                    st.session_state[k] = None
                st.rerun()


else:
    # Main chat interface
    st.title("☁️ Azure Agent Assistant")
    st.markdown("Ask questions about your Azure resources and get intelligent responses!")
    
    # Sidebar for Azure Context
    st.sidebar.header("Azure Context (Optional)")
    subscription_id = st.sidebar.text_input(
        "Subscription ID",
        placeholder="e.g., ee5f77a1-2e59-4335-8bdf-f7ea476f6523",
        help="Enter your Azure subscription ID"
    )
    resource_group_name = st.sidebar.text_input(
        "Resource Group Name",
        placeholder="e.g., SQL-RG",
        help="Enter your Azure resource group name"
    )
    resource_name = st.sidebar.text_input(
        "Resource Name",
        placeholder="e.g., adf-stanley",
        help="Enter your Azure resource name"
    )

    # Main interface
    user_question = st.text_area(
        "Ask your question:",
        placeholder="e.g., Show me all resource groups in my subscription",
        height=100
    )


    # Submit button and processing
    if st.button("🚀 Submit Question", type="primary", use_container_width=True):
        if not user_question.strip():
            st.error("Please enter a question!")
        else:
            with st.spinner("Processing your question..."):
                # Create Azure context
                auth = AzureAuthentication()
                azure_ctx = AzureCtx(auth=auth)
                
                # Set context values if provided
                if subscription_id.strip():
                    azure_ctx.subscription_id = subscription_id.strip()
                if resource_group_name.strip():
                    azure_ctx.resource_group_name = resource_group_name.strip()
                if resource_name.strip():
                    azure_ctx.resource_name = resource_name.strip()
                
                try:
                    # Run the agent
                    result, token_usage = asyncio.run(run_triage_agent(user_question, azure_ctx))
                    
                    # Display the response
                    st.markdown("## 🤖 Agent Response")
                    st.markdown("---")
                    
                    # Format the response nicely
                    if isinstance(result, dict):
                        st.json(result)
                    elif isinstance(result, list):
                        for i, item in enumerate(result):
                            st.markdown(f"**Response {i+1}:**")
                            if isinstance(item, dict):
                                st.json(item)
                            else:
                                st.write(item)
                            st.markdown("---")
                    else:
                        st.write(result)
                    
                    # Show token usage in an expandable dropdown
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
                    
                    # Success message
                    st.success("✅ Question processed successfully!")
                    
                except Exception as e:
                    st.error(f"❌ Error processing question: {str(e)}")
                    st.exception(e)

    # Example questions in an expander
    with st.expander("💡 Example Questions"):
        st.markdown("""
        - Show me all resource groups in my subscription
        - List all linked services in adf-stanley
        - What are the available resources in my resource group?
        - Show me the status of my Azure Data Factory
        - List all storage accounts in my subscription
        """)

    # Information about Azure context
    with st.expander("ℹ️ About Azure Context"):
        st.markdown("""
        **Azure Context Fields:**
        - **Subscription ID**: Your Azure subscription identifier
        - **Resource Group Name**: The name of your resource group
        - **Resource Name**: The name of a specific resource (e.g., Data Factory name)
        
        These fields are optional but providing them helps the agent give more targeted responses.
        """)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
        Azure Agent Assistant - Powered by OpenAI and MLflow
    </div>
    """,
    unsafe_allow_html=True
) 