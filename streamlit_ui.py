import asyncio
import streamlit as st
from agents import Runner, trace
from DAPEAgent.triage_agent import get_triage_agent
from DAPEAgent.config import AzureCtx
from azure_tools.auth import AzureAuthentication
import mlflow
from mlflow.openai._agent_tracer import add_mlflow_trace_processor

# Configure MLflow
mlflow.openai.autolog(log_traces=False)    
add_mlflow_trace_processor()             
mlflow.set_tracking_uri("http://127.0.0.1:5000")
mlflow.set_experiment("OpenAI-Agents-only")

# Streamlit page configuration
st.set_page_config(
    page_title="Azure Agent Assistant",
    page_icon="☁️",
    layout="wide"
)

def streamlit_device_code_callback(verification_uri, user_code, expires_in):
    """
    Streamlit version of device code authentication callback.
    Displays authentication instructions in the UI that can be cleared after completion.
    """
    # Create empty placeholders that can be cleared later
    if 'auth_placeholder' not in st.session_state:
        st.session_state.auth_placeholder = st.empty()
    
    # Mark authentication as in progress
    st.session_state.auth_in_progress = True
    
    with st.session_state.auth_placeholder.container():
        st.info("🔐 Azure Device Code Authentication Required")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📱 Authentication Steps:")
            st.markdown(f"1. Open this URL in your browser:")
            st.code(verification_uri)
            st.markdown(f"2. Enter this code:")
            st.code(user_code, language="text")
            st.markdown(f"3. Complete authentication in your browser")
        
        with col2:
            st.markdown("### ⏰ Important Notes:")
            st.warning(f"Code expires in {expires_in} seconds")
            st.info("💡 You can use any device with a web browser")
            st.info("💡 After entering the code, return to this app")

def clear_auth_ui():
    """Clear the authentication UI after successful authentication."""
    if 'auth_placeholder' in st.session_state:
        st.session_state.auth_placeholder.empty()
    st.session_state.auth_in_progress = False
    st.session_state.auth_completed = True

# Initialize Azure Authentication at the beginning of the app
if 'auth' not in st.session_state:
    st.session_state.auth = AzureAuthentication(device_code_callback=streamlit_device_code_callback)

auth = st.session_state.auth

# Check if authentication was completed and clear UI if needed
if hasattr(st.session_state, 'auth_in_progress') and st.session_state.auth_in_progress:
    # Check if authentication is now complete
    try:
        # Try to get a token to see if authentication is complete
        if auth.is_authenticated:
            clear_auth_ui()
            st.success("✅ Authentication completed successfully!")
            st.rerun()  # Refresh the page to show the cleared UI
    except Exception:
        # Authentication still in progress or failed
        pass

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

async def run_agent(question: str, azure_ctx: AzureCtx):
    """Run the triage agent with the given question and context."""
    triage_agent = get_triage_agent()
    
    # Run the agent - MLflow logging is handled automatically
    result = await Runner.run(
        triage_agent,
        input=[{"content": question, "role": "user"}],
        context=azure_ctx
    )
    
    # Get actual token usage from OpenAI raw responses
    try:
        total_tokens = 0
        input_tokens = 0
        output_tokens = 0
        cache_tokens = 0
        
        # Loop through all raw responses and aggregate token usage
        for response in result.raw_responses:
            total_tokens += response.usage.total_tokens
            input_tokens += response.usage.input_tokens
            output_tokens += response.usage.output_tokens
            cache_tokens += response.usage.input_tokens_details.cached_tokens
        
        token_usage = {
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cache_tokens': cache_tokens,
            'total_tokens': total_tokens
        }
    except Exception as e:
        # Fallback if token extraction fails
        token_usage = {
            'input_tokens': 0,
            'output_tokens': 0,
            'cache_tokens': 0,
            'total_tokens': 0
        }
    
    return result.final_output, token_usage

# Submit button and processing
if st.button("🚀 Submit Question", type="primary", use_container_width=True):
    if not user_question.strip():
        st.error("Please enter a question!")
    else:
        with st.spinner("Processing your question..."):
            # Create Azure context with authentication
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
                result, token_usage = asyncio.run(run_agent(user_question, azure_ctx))
                
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