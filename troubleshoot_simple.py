#!/usr/bin/env python3
"""
Simple Azure OpenTelemetry Observability Troubleshooting Script
"""

import sys
import os
import time
import uuid
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    print("Azure OpenTelemetry Observability Troubleshooting")
    print("=" * 60)
    
    # 1. Check Environment Variables
    print("\n1. Checking Environment Variables...")
    
    required_vars = [
        'APPLICATIONINSIGHTS_CONNECTION_STRING',
        'AZURE_OPENAI_ENDPOINT', 
        'AZURE_OPENAI_API_KEY',
        'AZURE_OPENAI_DEPLOYMENT'
    ]
    
    optional_vars = [
        'CHAT_OBSERVABILITY_CONNECTION_STRING',
        'ENABLE_CHAT_OBSERVABILITY'
    ]
    
    missing_required = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if var == 'APPLICATIONINSIGHTS_CONNECTION_STRING':
                print(f"   {var}: [OK] (length: {len(value)})")
                # Check connection string format
                if 'InstrumentationKey=' in value:
                    print("      Format: [OK] Has InstrumentationKey")
                else:
                    print("      Format: [WARNING] Missing InstrumentationKey")
            else:
                print(f"   {var}: [OK] (set)")
        else:
            print(f"   {var}: [MISSING]")
            missing_required.append(var)
    
    for var in optional_vars:
        value = os.getenv(var)
        print(f"   {var}: {'[OK]' if value else '[NOT SET]'} {'(optional)' if not value else ''}")
    
    if missing_required:
        print(f"\n[ERROR] Missing required environment variables: {missing_required}")
        return 1
    
    # 2. Test Azure Monitor Package
    print("\n2. Checking Azure Monitor Package...")
    try:
        import azure.monitor.opentelemetry
        print("   azure-monitor-opentelemetry: [OK]")
    except ImportError:
        print("   azure-monitor-opentelemetry: [MISSING]")
        print("   Fix: pip install azure-monitor-opentelemetry")
        return 1
    
    # 3. Test Settings Loading
    print("\n3. Testing Settings Loading...")
    try:
        from config.settings import get_settings
        settings = get_settings()
        print("   Settings loading: [OK]")
        
        validation = settings.validate_configuration()
        print(f"   Azure OpenAI configured: {'[OK]' if validation['azure_openai_configured'] else '[FAILED]'}")
        print(f"   Application Insights configured: {'[OK]' if validation['application_insights_configured'] else '[FAILED]'}")
        print(f"   Dual observability configured: {'[OK]' if validation['dual_observability_configured'] else '[FAILED]'}")
        
    except Exception as e:
        print(f"   Settings loading: [FAILED] {e}")
        return 1
    
    # 4. Test OpenTelemetry Initialization
    print("\n4. Testing OpenTelemetry Initialization...")
    try:
        from observability.telemetry_service import initialize_dual_observability, is_telemetry_initialized
        
        result = initialize_dual_observability(settings)
        print(f"   Dual observability init: {'[OK]' if result else '[FAILED]'}")
        
        initialized = is_telemetry_initialized()
        print(f"   Telemetry initialized: {'[OK]' if initialized else '[FAILED]'}")
        
        if not result or not initialized:
            print("   Issue: OpenTelemetry initialization failed")
            print("   This is the most likely cause of missing data in Azure Log Analytics")
            
    except Exception as e:
        print(f"   OpenTelemetry initialization: [FAILED] {e}")
        return 1
    
    # 5. Test Log Routing
    print("\n5. Testing Log Routing...")
    try:
        from observability.telemetry_service import route_log_by_type
        
        test_operation_id = str(uuid.uuid4())
        
        # Test system log
        route_log_by_type('SYSTEM', {
            'message': 'Troubleshooting test - SYSTEM log',
            'operation_id': test_operation_id,
            'component': 'troubleshooting',
            'success': True
        })
        print("   SYSTEM log routing: [OK]")
        
        # Test conversation log
        route_log_by_type('CONVERSATION', {
            'message': 'Troubleshooting test - CONVERSATION log', 
            'operation_id': test_operation_id,
            'conversation_id': f'troubleshoot-{int(time.time())}'
        })
        print("   CONVERSATION log routing: [OK]")
        
        print(f"\n   Test data sent with operation_id: {test_operation_id}")
        print("   Data should appear in Azure Log Analytics within 2-5 minutes")
        
    except Exception as e:
        print(f"   Log routing: [FAILED] {e}")
        return 1
    
    # 6. Azure Log Analytics Query Help
    print("\n6. Azure Log Analytics Query Suggestions:")
    print("   To find your test data, use this query in Azure Log Analytics:")
    print(f"   traces | where operation_Id == '{test_operation_id}'")
    print()
    print("   To find all recent traces:")
    print("   traces | where timestamp > ago(10m) | order by timestamp desc")
    print()
    print("   To find application logs:")
    print("   traces | where customDimensions.log_type in ('SYSTEM', 'SECURITY', 'PERFORMANCE', 'AZURE_OPENAI')")
    print()
    print("   To find conversation logs:")
    print("   traces | where customDimensions.log_type == 'CONVERSATION'")
    
    print("\n7. Common Issues and Solutions:")
    print("   - Data ingestion delay: Wait 2-5 minutes for data to appear")
    print("   - Connection string issues: Verify InstrumentationKey format")
    print("   - Permissions: Ensure you have read access to the Log Analytics workspace")
    print("   - Wrong workspace: Verify you're querying the correct Application Insights resource")
    print("   - Network issues: Check firewall/proxy settings")
    
    print("\n[SUCCESS] Troubleshooting completed!")
    print(f"Test operation_id for tracking: {test_operation_id}")
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)