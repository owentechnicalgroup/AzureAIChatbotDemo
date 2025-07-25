#!/usr/bin/env python3
"""
Direct test of observability system bypassing Key Vault authentication
"""

import sys
import os
import time
import uuid
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

def main():
    print("Direct Observability Test (Bypassing Key Vault)")
    print("=" * 60)
    
    # 1. Check if we have the minimum required config
    app_insights_conn = os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING')
    if not app_insights_conn:
        print("[ERROR] APPLICATIONINSIGHTS_CONNECTION_STRING not found")
        return 1
    
    print(f"[OK] Application Insights connection string found")
    print(f"     Length: {len(app_insights_conn)} characters")
    
    # Check connection string format
    if 'InstrumentationKey=' in app_insights_conn:
        print("[OK] Connection string has InstrumentationKey")
    else:
        print("[ERROR] Connection string missing InstrumentationKey")
        return 1
    
    # 2. Test Azure Monitor package
    try:
        import azure.monitor.opentelemetry
        print("[OK] Azure Monitor OpenTelemetry package available")
    except ImportError as e:
        print(f"[ERROR] Azure Monitor package not available: {e}")
        return 1
    
    # 3. Create a minimal settings object for testing
    print("\n[INFO] Creating minimal settings for observability testing...")
    
    class MinimalSettings:
        def __init__(self):
            self.applicationinsights_connection_string = app_insights_conn
            self.chat_observability_connection_string = os.getenv('CHAT_OBSERVABILITY_CONNECTION_STRING')
            self.enable_chat_observability = os.getenv('ENABLE_CHAT_OBSERVABILITY', 'true').lower() == 'true'
            self.enable_cross_correlation = True
    
    settings = MinimalSettings()
    print(f"[OK] Minimal settings created")
    print(f"     Chat observability enabled: {settings.enable_chat_observability}")
    
    # 4. Test OpenTelemetry initialization
    print("\n[INFO] Testing OpenTelemetry initialization...")
    
    try:
        from observability.telemetry_service import initialize_dual_observability, is_telemetry_initialized
        
        result = initialize_dual_observability(settings)
        print(f"[{'OK' if result else 'ERROR'}] Dual observability initialization: {result}")
        
        if not result:
            print("[ERROR] OpenTelemetry initialization failed - this is why no data appears in Azure")
            return 1
        
        initialized = is_telemetry_initialized()
        print(f"[{'OK' if initialized else 'ERROR'}] Telemetry system initialized: {initialized}")
        
    except Exception as e:
        print(f"[ERROR] OpenTelemetry initialization error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 5. Test log routing
    print("\n[INFO] Testing log routing and data transmission...")
    
    try:
        from observability.telemetry_service import route_log_by_type
        
        test_operation_id = str(uuid.uuid4())
        current_time = int(time.time())
        
        # Send test logs
        test_logs = [
            ('SYSTEM', {
                'message': 'OBSERVABILITY TEST - System log',
                'operation_id': test_operation_id,
                'component': 'troubleshooting',
                'test_timestamp': current_time,
                'success': True
            }),
            ('SECURITY', {
                'message': 'OBSERVABILITY TEST - Security log',
                'operation_id': test_operation_id,
                'credential_type': 'test',
                'test_timestamp': current_time,
            }),
            ('PERFORMANCE', {
                'message': 'OBSERVABILITY TEST - Performance log',
                'operation_id': test_operation_id,
                'response_time': 1.5,
                'test_timestamp': current_time,
            }),
            ('AZURE_OPENAI', {
                'message': 'OBSERVABILITY TEST - Azure OpenAI log',
                'operation_id': test_operation_id,
                'resource_type': 'openai',
                'test_timestamp': current_time,
            }),
            ('CONVERSATION', {
                'message': 'OBSERVABILITY TEST - Conversation log',
                'operation_id': test_operation_id,
                'conversation_id': f'test-conv-{current_time}',
                'test_timestamp': current_time,
            })
        ]
        
        for log_type, log_data in test_logs:
            try:
                route_log_by_type(log_type, log_data)
                print(f"[OK] {log_type} log sent successfully")
            except Exception as e:
                print(f"[ERROR] {log_type} log failed: {e}")
                return 1
        
        print(f"\n[SUCCESS] All test logs sent successfully!")
        print(f"Test operation_id: {test_operation_id}")
        print(f"Test timestamp: {current_time}")
        
    except Exception as e:
        print(f"[ERROR] Log routing test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # 6. Provide Azure Log Analytics queries
    print("\n" + "=" * 60)
    print("AZURE LOG ANALYTICS QUERIES")
    print("=" * 60)
    
    print(f"\n1. Find your test data (use this first):")
    print(f"traces | where operation_Id == '{test_operation_id}'")
    
    print(f"\n2. Find all recent logs:")
    print(f"traces | where timestamp > ago(10m) | order by timestamp desc")
    
    print(f"\n3. Find application infrastructure logs:")
    print(f"traces | where customDimensions.log_type in ('SYSTEM', 'SECURITY', 'PERFORMANCE', 'AZURE_OPENAI')")
    
    print(f"\n4. Find conversation logs:")
    print(f"traces | where customDimensions.log_type == 'CONVERSATION'")
    
    print(f"\n5. Check for your specific test timestamp:")
    print(f"traces | where customDimensions.test_timestamp == {current_time}")
    
    print("\n" + "=" * 60)
    print("TROUBLESHOOTING NEXT STEPS")
    print("=" * 60)
    
    print("\n1. Wait 2-5 minutes for data ingestion")
    print("2. Check Azure Portal Application Insights > Live Metrics for real-time data")
    print("3. Verify you're querying the correct Application Insights workspace")
    print("4. Check Application Insights workspace permissions")
    print("5. Verify Azure Monitor OpenTelemetry exporter is working")
    
    print(f"\n[SUCCESS] Observability test completed!")
    print(f"If data still doesn't appear after 5 minutes, there may be an issue with:")
    print("- Azure Monitor OpenTelemetry exporter configuration")
    print("- Application Insights workspace connectivity")
    print("- Network/firewall restrictions")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())