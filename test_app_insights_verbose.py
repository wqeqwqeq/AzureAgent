#!/usr/bin/env python3
"""
Verbose test script for Application Insights with detailed logging
"""

import time
import logging
import os
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor

# Your Application Insights connection string
CONNECTION_STRING = "InstrumentationKey=50e22f50-2549-4406-8f03-36306f3044e4;IngestionEndpoint=https://eastus-8.in.applicationinsights.azure.com/;LiveEndpoint=https://eastus.livediagnostics.monitor.azure.com/;ApplicationId=be35853a-d163-4c42-96ae-f484da5eca06"

def test_verbose():
    # Enable debug logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    print("🔍 VERBOSE Application Insights Test")
    print(f"Connection String: {CONNECTION_STRING[:80]}...")
    print(f"Instrumentation Key: {CONNECTION_STRING.split(';')[0]}")
    print(f"Ingestion Endpoint: https://eastus-8.in.applicationinsights.azure.com/")
    
    try:
        # Configure Azure Monitor
        configure_azure_monitor(
            connection_string=CONNECTION_STRING,
            instrumentation_options={
                "azure_sdk": {"enabled": True},
                "requests": {"enabled": True},
                "urllib": {"enabled": True},
                "urllib3": {"enabled": True},
            }
        )
        print("✅ Azure Monitor configured successfully")
        
        tracer = trace.get_tracer(__name__)
        
        # Send test traces with detailed information
        for i in range(3):
            print(f"\n📊 Sending test trace #{i+1}")
            with tracer.start_as_current_span(f"verbose_test_operation_{i+1}") as span:
                span.set_attribute("test.iteration", i+1)
                span.set_attribute("test.type", "verbose_debug")
                span.set_attribute("test.timestamp", time.time())
                span.set_attribute("service.name", "verbose-test-service")
                
                # Log message
                logger.info(f"Test log message #{i+1} - This should appear in Application Insights")
                logger.warning(f"Test warning #{i+1} - This is a warning message")
                
                # Add events
                span.add_event(f"Test event #{i+1}", {
                    "event.type": "test_event",
                    "iteration": i+1,
                    "message": f"This is test event #{i+1}"
                })
                
                time.sleep(0.1)
            
            print(f"✅ Test trace #{i+1} completed")
        
        # Create an exception trace
        print("\n⚠️ Creating exception trace")
        try:
            with tracer.start_as_current_span("exception_test") as span:
                span.set_attribute("operation", "exception_test")
                raise Exception("This is a deliberate test exception for Application Insights")
        except Exception as e:
            logger.exception("Test exception: %s", str(e))
            print("✅ Exception trace created")
        
        print(f"\n⏰ Waiting 10 seconds for telemetry to be sent...")
        time.sleep(10)
        
        print("\n🎯 Test completed! Data should now be visible in Application Insights.")
        print("\n📋 What to check in Azure Portal:")
        print("1. Application Insights → Live Metrics (should show activity)")
        print("2. Application Insights → Logs → Run this query:")
        print("   traces | where timestamp > ago(1h) | project timestamp, message, severityLevel | order by timestamp desc")
        print("3. Look for service name: 'verbose-test-service'")
        print("4. Look for operations: 'verbose_test_operation_1', 'verbose_test_operation_2', 'verbose_test_operation_3', 'exception_test'")
        
        print(f"\n🔗 Direct link to your Application Insights:")
        print(f"https://portal.azure.com/#@/resource/subscriptions/[YOUR_SUBSCRIPTION]/resourceGroups/[YOUR_RG]/providers/Microsoft.Insights/components/[YOUR_APP_INSIGHTS]/logs")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.exception("Failed to send telemetry")

if __name__ == "__main__":
    test_verbose() 