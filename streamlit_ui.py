import asyncio,re 
import subprocess
import streamlit as st
from agents import Runner, trace
from DAPEAgent.triage_agent import get_triage_agent
from DAPEAgent.config import AzureCtx
from azure_tools.auth import AzureAuthentication
import mlflow

# Configure MLflow
mlflow.set_tracking_uri("http://127.0.0.1:5000")
mlflow.set_experiment("OpenAI-Agents-only")

# Streamlit page configuration
st.set_page_config(
    page_title="Azure Agent Assistant",
    page_icon="☁️",
    layout="wide"
)

async def az_login():
    """
    Start az login with device code and return verification details.
    Does not wait for completion - just gets the code and returns.
    """
    # Create subprocess with asyncio
    proc = await asyncio.create_subprocess_exec(
        "az", "login", "--use-device-code", "--output", "none",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    
    # Check if stdout is available
    if proc.stdout is None:
        print("Error: Unable to read subprocess output")
        return None, None
    
    # Read output line by line asynchronously
    async for line in proc.stdout:
        line = line.decode('utf-8').strip()
        if not line:
            continue
            
        if "https://" in line and "code" in line:
            url_match = re.search(r"https://\S+", line)
            code_match = re.search(r"code ([A-Z0-9-]{8,})", line)
            
            if url_match and code_match:
                verification_uri = url_match.group(0)
                user_code = code_match.group(1)
                return verification_uri, user_code
    
    # Don't wait for completion - let it run in background
    return None, None

def az_account_show():
    """
    Check if Azure CLI authentication is successful by running 'az account show'.
    Returns True if authenticated, False otherwise.
    """
    try:
        proc = subprocess.run(
            ["az", "account", "show", "--output", "json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if proc.returncode == 0:
            # Successfully got account info, user is authenticated
            account_info = proc.stdout.strip()
            if account_info:
                print("Azure CLI authentication verified successfully")
                return True
        else:
            print(f"Azure CLI authentication failed: {proc.stderr}")
            return False
            
    except Exception as e:
        print(f"Error checking Azure CLI authentication: {str(e)}")
        return False
    
    return False

# Initialize session state
if 'cli_auth' not in st.session_state:
    st.session_state.cli_auth = False
if 'verification_uri' not in st.session_state:
    st.session_state.verification_uri = None
if 'user_code' not in st.session_state:
    st.session_state.user_code = None

st.title("☁️ Azure Agent Assistant")

# Authentication flow
if not st.session_state.cli_auth:
    if st.session_state.verification_uri is None:
        # Start authentication automatically
        try:
            # Get verification details
            verification_uri, user_code = asyncio.run(az_login())
            
            if verification_uri and user_code:
                # Store in session state
                st.session_state.verification_uri = verification_uri
                st.session_state.user_code = user_code
                st.rerun()
            else:
                st.error("❌ Failed to start authentication process")
        except Exception as e:
            st.error(f"❌ Authentication error: {str(e)}")
    else:
        # Show verification UI
        st.markdown("## 🔐 Azure CLI Authentication")
        st.markdown("### 📱 Complete authentication in your browser:")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**1. Open this URL:**")
            st.code(st.session_state.verification_uri)
        with col2:
            st.markdown("**2. Enter this code:**")
            st.code(st.session_state.user_code)
        
        st.warning("⏰ Code expires in 900 seconds (15 minutes)")
        st.info("💡 After completing authentication in your browser, click 'Check Authentication' below")
        
        # Check authentication button
        if st.button("🔍 Check Authentication", type="primary"):
            with st.spinner("Checking authentication status..."):
                is_authenticated = az_account_show()
                if is_authenticated:
                    # Set cli_auth = True and clear verification data
                    st.session_state.cli_auth = True
                    st.session_state.verification_uri = None
                    st.session_state.user_code = None
                    st.success("✅ Authentication successful!")
                    st.rerun()  # Clean UI and show chat page
                else:
                    st.error("❌ Authentication not complete. Please complete the authentication process and try again.")
                    
        # Reset button to start over
        if st.button("🔄 Start Over", type="secondary"):
            st.session_state.verification_uri = None
            st.session_state.user_code = None
            st.rerun()

else:
    # Main chat interface
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
        triage_agent, azure_mcp_server = get_triage_agent()
        await azure_mcp_server.connect()
        
        # Run the agent
        result = await Runner.run(
            triage_agent,
            input=[{"content": question, "role": "user"}],
            context=azure_ctx
        )
        await azure_mcp_server.cleanup()
        
        # Get token usage from OpenAI raw responses
        try:
            total_tokens = 0
            input_tokens = 0
            output_tokens = 0
            cache_tokens = 0
            
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