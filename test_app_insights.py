#!/usr/bin/env python3
"""
Simple test script to send dummy logs and traces directly to Application Insights
to verify the connection string is working.
"""

import time
import logging
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider

# Your Application Insights connection string
CONNECTION_STRING = "InstrumentationKey=50e22f50-2549-4406-8f03-36306f3044e4;IngestionEndpoint=https://eastus-8.in.applicationinsights.azure.com/;LiveEndpoint=https://eastus.livediagnostics.monitor.azure.com/;ApplicationId=be35853a-d163-4c42-96ae-f484da5eca06"

def test_application_insights():
    print("🧪 Testing Application Insights connection...")
    print(f"Connection String: {CONNECTION_STRING[:50]}...")
    
    # Configure Azure Monitor with your connection string
    configure_azure_monitor(
        connection_string=CONNECTION_STRING,
        instrumentation_options={
            "azure_sdk": {"enabled": True},
            "django": {"enabled": False},
            "fastapi": {"enabled": False},
            "flask": {"enabled": False},
            "requests": {"enabled": True},
            "urllib": {"enabled": True},
            "urllib3": {"enabled": True},
        }
    )
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Get tracer and meter
    tracer = trace.get_tracer(__name__)
    meter = metrics.get_meter(__name__)
    
    print("\n✅ Azure Monitor configured successfully!")
    
    # Test 1: Send some log messages
    print("\n📝 Sending test log messages...")
    logger.info("Test INFO log message from Python script")
    logger.warning("Test WARNING log message from Python script")
    logger.error("Test ERROR log message from Python script")
    
    # Test 2: Create custom traces
    print("\n🔍 Creating test traces...")
    with tracer.start_as_current_span("test_banking_operation") as span:
        span.set_attribute("operation.name", "account_balance_check")
        span.set_attribute("account.id", "test-12345")
        span.set_attribute("user.id", "test-user")
        
        # Simulate some work
        time.sleep(0.1)
        
        with tracer.start_as_current_span("database_query") as child_span:
            child_span.set_attribute("db.statement", "SELECT balance FROM accounts WHERE id = ?")
            child_span.set_attribute("db.name", "banking_db")
            time.sleep(0.05)
            child_span.add_event("Query completed", {"rows_returned": 1})
        
        with tracer.start_as_current_span("api_call") as api_span:
            api_span.set_attribute("http.method", "POST")
            api_span.set_attribute("http.url", "https://api.bank.com/balance")
            api_span.set_attribute("http.status_code", 200)
            time.sleep(0.03)
            api_span.add_event("API response received", {"response_time_ms": 30})
        
        span.add_event("Banking operation completed", {"balance": 5432.10})
    
    # Test 3: Create custom metrics
    print("\n📊 Creating test metrics...")
    counter = meter.create_counter(
        name="banking_operations_total",
        description="Total number of banking operations",
    )
    counter.add(1, {"operation_type": "balance_check", "status": "success"})
    counter.add(1, {"operation_type": "transfer", "status": "success"})
    counter.add(1, {"operation_type": "loan_calculation", "status": "success"})
    
    histogram = meter.create_histogram(
        name="operation_duration_ms",
        description="Duration of banking operations in milliseconds",
    )
    histogram.record(150, {"operation_type": "balance_check"})
    histogram.record(300, {"operation_type": "transfer"})
    histogram.record(75, {"operation_type": "loan_calculation"})
    
    # Test 4: Create exception trace
    print("\n⚠️  Creating test exception trace...")
    try:
        with tracer.start_as_current_span("error_simulation") as error_span:
            error_span.set_attribute("operation", "test_error")
            # Simulate an error
            raise ValueError("This is a test error for Application Insights")
    except ValueError as e:
        logger.exception("Test exception caught: %s", str(e))
    
    print("\n🚀 All test data sent to Application Insights!")
    print("\n⏱️  Waiting 5 seconds for data to be transmitted...")
    time.sleep(5)
    
    print("\n✨ Test completed! Check your Application Insights dashboard:")
    print("1. Go to Azure Portal → Your Application Insights resource")
    print("2. Check 'Live Metrics' for real-time data")
    print("3. Check 'Logs' and run this query:")
    print("   traces | where timestamp > ago(10m) | order by timestamp desc")
    print("4. Check 'Transaction search' for individual operations")
    print("5. Look for these custom operations:")
    print("   - test_banking_operation")
    print("   - database_query") 
    print("   - api_call")
    print("   - error_simulation")

if __name__ == "__main__":
    test_application_insights() 