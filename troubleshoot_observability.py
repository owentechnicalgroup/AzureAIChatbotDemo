#!/usr/bin/env python3
"""
Azure OpenTelemetry Observability Troubleshooting Script

This script diagnoses common issues that prevent observability data from appearing
in Azure Log Analytics and Application Insights.
"""

import sys
import os
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from config.settings import get_settings
    from observability.telemetry_service import (
        initialize_dual_observability,
        route_log_by_type,
        get_application_logger,
        get_chat_observer,
        is_telemetry_initialized
    )
    from services.logging_service import setup_logging
    import structlog
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


class ObservabilityTroubleshooter:
    """Comprehensive troubleshooting for Azure OpenTelemetry observability."""
    
    def __init__(self):
        self.settings = None
        self.issues_found = []
        self.recommendations = []
        
    def run_full_diagnosis(self) -> Dict[str, Any]:
        """Run complete observability diagnosis."""
        print("🔍 Azure OpenTelemetry Observability Troubleshooting")
        print("=" * 60)
        
        results = {}
        
        # 1. Check Settings Configuration
        print("\n1️⃣ Checking Settings Configuration...")
        results['settings'] = self.check_settings_configuration()
        
        # 2. Check Environment Variables
        print("\n2️⃣ Checking Environment Variables...")
        results['environment'] = self.check_environment_variables()
        
        # 3. Check Application Insights Connection
        print("\n3️⃣ Checking Application Insights Connection...")
        results['app_insights'] = self.check_application_insights_connection()
        
        # 4. Test OpenTelemetry Initialization
        print("\n4️⃣ Testing OpenTelemetry Initialization...")
        results['opentelemetry'] = self.test_opentelemetry_initialization()
        
        # 5. Test Log Routing
        print("\n5️⃣ Testing Log Routing...")
        results['log_routing'] = self.test_log_routing()
        
        # 6. Check Azure Monitor Integration
        print("\n6️⃣ Checking Azure Monitor Integration...")
        results['azure_monitor'] = self.check_azure_monitor_integration()
        
        # 7. Test Live Data Transmission
        print("\n7️⃣ Testing Live Data Transmission...")
        results['live_transmission'] = self.test_live_data_transmission()
        
        return results
    
    def check_settings_configuration(self) -> Dict[str, Any]:
        """Check if settings are properly configured."""
        try:
            self.settings = get_settings()
            
            config_validation = self.settings.validate_configuration()
            print(f"✅ Settings loaded successfully")
            print(f"   Environment: {self.settings.environment}")
            print(f"   Key Vault configured: {config_validation['key_vault_configured']}")
            print(f"   Azure OpenAI configured: {config_validation['azure_openai_configured']}")
            print(f"   Application Insights configured: {config_validation['application_insights_configured']}")
            print(f"   Dual observability configured: {config_validation['dual_observability_configured']}")
            print(f"   Chat observability enabled: {config_validation['chat_observability_enabled']}")
            
            # Check connection strings
            app_insights_conn = bool(self.settings.applicationinsights_connection_string)
            chat_obs_conn = bool(self.settings.chat_observability_connection_string)
            
            print(f"   App Insights connection string: {'✅ Set' if app_insights_conn else '❌ Missing'}")
            print(f"   Chat observability connection string: {'✅ Set' if chat_obs_conn else '❌ Missing (will fallback)'}")
            
            if not app_insights_conn:
                self.issues_found.append("Application Insights connection string is missing")
                self.recommendations.append("Set APPLICATIONINSIGHTS_CONNECTION_STRING environment variable")
            
            return {
                'success': True,
                'validation': config_validation,
                'app_insights_connection': app_insights_conn,
                'chat_observability_connection': chat_obs_conn
            }
            
        except Exception as e:
            print(f"❌ Settings configuration failed: {e}")
            self.issues_found.append(f"Settings configuration error: {e}")
            return {'success': False, 'error': str(e)}
    
    def check_environment_variables(self) -> Dict[str, Any]:
        """Check critical environment variables."""
        critical_env_vars = [
            'APPLICATIONINSIGHTS_CONNECTION_STRING',
            'AZURE_OPENAI_ENDPOINT',
            'AZURE_OPENAI_API_KEY',
            'AZURE_OPENAI_DEPLOYMENT'
        ]
        
        optional_env_vars = [
            'CHAT_OBSERVABILITY_CONNECTION_STRING',
            'ENABLE_CHAT_OBSERVABILITY',
            'KEY_VAULT_URL',
            'AZURE_CLIENT_ID'
        ]
        
        results = {'critical': {}, 'optional': {}}
        
        print("   Critical environment variables:")
        for var in critical_env_vars:
            value = os.getenv(var)
            is_set = bool(value)
            results['critical'][var] = {'set': is_set, 'length': len(value) if value else 0}
            
            if var == 'APPLICATIONINSIGHTS_CONNECTION_STRING' and value:
                # Parse connection string to check format
                has_instrumentation_key = 'InstrumentationKey=' in value
                has_ingestion_endpoint = 'IngestionEndpoint=' in value
                print(f"   {var}: {'✅' if is_set else '❌'} {'(format looks good)' if has_instrumentation_key else '(check format)'}")
            else:
                print(f"   {var}: {'✅' if is_set else '❌'}")
            
            if not is_set and var == 'APPLICATIONINSIGHTS_CONNECTION_STRING':
                self.issues_found.append(f"Critical environment variable {var} is not set")
        
        print("   Optional environment variables:")
        for var in optional_env_vars:
            value = os.getenv(var)
            is_set = bool(value)
            results['optional'][var] = {'set': is_set}
            print(f"   {var}: {'✅' if is_set else '➖'}")
        
        return results
    
    def check_application_insights_connection(self) -> Dict[str, Any]:
        """Test Application Insights connection string format and validity."""
        if not self.settings or not self.settings.applicationinsights_connection_string:
            print("❌ No Application Insights connection string available")
            return {'success': False, 'error': 'No connection string'}
        
        conn_str = self.settings.applicationinsights_connection_string
        
        # Parse connection string
        try:
            parts = {}
            for part in conn_str.split(';'):
                if '=' in part:
                    key, value = part.split('=', 1)
                    parts[key] = value
            
            instrumentation_key = parts.get('InstrumentationKey')
            ingestion_endpoint = parts.get('IngestionEndpoint')
            
            print(f"   Instrumentation Key: {'✅ Present' if instrumentation_key else '❌ Missing'}")
            print(f"   Ingestion Endpoint: {'✅ Present' if ingestion_endpoint else '❌ Missing'}")
            
            if instrumentation_key:
                # Check if it looks like a valid GUID
                import re
                guid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                if re.match(guid_pattern, instrumentation_key):
                    print(f"   Key format: ✅ Valid GUID format")
                else:
                    print(f"   Key format: ❌ Invalid GUID format")
                    self.issues_found.append("Instrumentation key is not a valid GUID")
            
            if not ingestion_endpoint:
                self.recommendations.append("Consider using modern connection string with IngestionEndpoint")
            
            return {
                'success': True,
                'instrumentation_key_present': bool(instrumentation_key),
                'ingestion_endpoint_present': bool(ingestion_endpoint),
                'parsed_parts': len(parts)
            }
            
        except Exception as e:
            print(f"❌ Error parsing connection string: {e}")
            self.issues_found.append(f"Connection string parsing error: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_opentelemetry_initialization(self) -> Dict[str, Any]:
        """Test OpenTelemetry initialization."""
        if not self.settings:
            return {'success': False, 'error': 'No settings available'}
        
        try:
            # Test dual observability initialization
            result = initialize_dual_observability(self.settings)
            is_initialized = is_telemetry_initialized()
            
            print(f"   Dual observability initialization: {'✅' if result else '❌'}")
            print(f"   Telemetry system initialized: {'✅' if is_initialized else '❌'}")
            
            if not result:
                self.issues_found.append("Dual observability initialization failed")
                self.recommendations.append("Check Application Insights connection string and Azure Monitor package")
            
            # Check if azure-monitor-opentelemetry is installed
            try:
                import azure.monitor.opentelemetry
                print(f"   Azure Monitor OpenTelemetry package: ✅ Installed")
            except ImportError:
                print(f"   Azure Monitor OpenTelemetry package: ❌ Not installed")
                self.issues_found.append("azure-monitor-opentelemetry package not installed")
                self.recommendations.append("Run: pip install azure-monitor-opentelemetry")
            
            return {
                'success': result,
                'is_initialized': is_initialized,
                'azure_monitor_package_installed': True
            }
            
        except Exception as e:
            print(f"❌ OpenTelemetry initialization failed: {e}")
            self.issues_found.append(f"OpenTelemetry initialization error: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_log_routing(self) -> Dict[str, Any]:
        """Test log routing functionality."""
        try:
            # Test different log types
            test_logs = [
                ('SYSTEM', {'message': 'Test system log', 'component': 'troubleshooting'}),
                ('SECURITY', {'message': 'Test security log', 'credential_type': 'test'}),
                ('PERFORMANCE', {'message': 'Test performance log', 'response_time': 1.0}),
                ('AZURE_OPENAI', {'message': 'Test Azure OpenAI log', 'resource_type': 'openai'}),
                ('CONVERSATION', {'message': 'Test conversation log', 'conversation_id': 'test-conv-123'})
            ]
            
            routing_results = {}
            
            for log_type, log_data in test_logs:
                try:
                    # Add operation_id for correlation
                    log_data['operation_id'] = str(uuid.uuid4())
                    
                    route_log_by_type(log_type, log_data)
                    routing_results[log_type] = {'success': True}
                    print(f"   {log_type} routing: ✅")
                except Exception as e:
                    routing_results[log_type] = {'success': False, 'error': str(e)}
                    print(f"   {log_type} routing: ❌ {e}")
                    self.issues_found.append(f"{log_type} log routing failed: {e}")
            
            success_count = sum(1 for result in routing_results.values() if result['success'])
            total_count = len(routing_results)
            
            print(f"   Overall routing success: {success_count}/{total_count}")
            
            return {
                'success': success_count == total_count,
                'results': routing_results,
                'success_rate': success_count / total_count
            }
            
        except Exception as e:
            print(f"❌ Log routing test failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def check_azure_monitor_integration(self) -> Dict[str, Any]:
        """Check Azure Monitor integration details."""
        try:
            # Test Azure Monitor configuration
            from azure.monitor.opentelemetry import configure_azure_monitor
            import opentelemetry
            
            print(f"   OpenTelemetry version: {opentelemetry.__version__}")
            
            # Check if Azure Monitor is configured
            try:
                # This might give us info about current configuration
                print(f"   Azure Monitor integration: ✅ Package available")
                
                # Check for common configuration issues
                print(f"   Checking common configuration issues...")
                
                # Verify connection string format again
                if self.settings and self.settings.applicationinsights_connection_string:
                    conn_str = self.settings.applicationinsights_connection_string
                    if 'InstrumentationKey=' not in conn_str:
                        self.issues_found.append("Connection string missing InstrumentationKey")
                        print(f"   Connection string format: ❌ Missing InstrumentationKey")
                    else:
                        print(f"   Connection string format: ✅ Has InstrumentationKey")
                
                return {'success': True, 'package_available': True}
                
            except Exception as e:
                print(f"   Azure Monitor configuration: ❌ {e}")
                self.issues_found.append(f"Azure Monitor configuration error: {e}")
                return {'success': False, 'error': str(e)}
                
        except ImportError as e:
            print(f"❌ Azure Monitor package not available: {e}")
            self.issues_found.append("Azure Monitor OpenTelemetry package not installed")
            self.recommendations.append("Install: pip install azure-monitor-opentelemetry")
            return {'success': False, 'error': 'Package not available'}
    
    def test_live_data_transmission(self) -> Dict[str, Any]:
        """Test live data transmission and provide debugging info."""
        print("   Sending test telemetry data...")
        
        try:
            # Initialize logging system
            setup_logging(self.settings)
            
            # Send test data
            test_operation_id = str(uuid.uuid4())
            
            # Test application logging
            route_log_by_type('SYSTEM', {
                'message': 'Observability troubleshooting test - SYSTEM log',
                'operation_id': test_operation_id,
                'component': 'troubleshooting',
                'test_timestamp': time.time(),
                'success': True
            })
            
            # Test chat observability
            route_log_by_type('CONVERSATION', {
                'message': 'Observability troubleshooting test - CONVERSATION log',
                'operation_id': test_operation_id,
                'conversation_id': f'troubleshoot-{int(time.time())}',
                'test_timestamp': time.time(),
            })
            
            print(f"   Test data sent with operation_id: {test_operation_id}")
            print(f"   ⏱️  Data should appear in Azure within 2-5 minutes")
            
            # Provide Azure query suggestions
            print("\n   🔍 Azure Log Analytics Query Suggestions:")
            print(f"   Application Logs:")
            print(f"   traces | where operation_Id == '{test_operation_id}' | where customDimensions.log_type != 'CONVERSATION'")
            print(f"   ")
            print(f"   Chat Observability Logs:")
            print(f"   traces | where operation_Id == '{test_operation_id}' | where customDimensions.log_type == 'CONVERSATION'")
            print(f"   ")
            print(f"   All Test Logs:")
            print(f"   traces | where operation_Id == '{test_operation_id}'")
            
            return {
                'success': True,
                'test_operation_id': test_operation_id,
                'timestamp': time.time()
            }
            
        except Exception as e:
            print(f"❌ Live data transmission test failed: {e}")
            self.issues_found.append(f"Live data transmission error: {e}")
            return {'success': False, 'error': str(e)}
    
    def print_summary(self, results: Dict[str, Any]) -> None:
        """Print troubleshooting summary."""
        print("\n" + "=" * 60)
        print("📋 TROUBLESHOOTING SUMMARY")
        print("=" * 60)
        
        # Count successes
        total_checks = len(results)
        successful_checks = sum(1 for result in results.values() if isinstance(result, dict) and result.get('success', False))
        
        print(f"Checks completed: {successful_checks}/{total_checks}")
        
        if self.issues_found:
            print("\n❌ ISSUES FOUND:")
            for i, issue in enumerate(self.issues_found, 1):
                print(f"   {i}. {issue}")
        
        if self.recommendations:
            print("\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(self.recommendations, 1):
                print(f"   {i}. {rec}")
        
        if not self.issues_found:
            print("\n✅ No major issues detected!")
            print("   If data still isn't appearing, consider:")
            print("   1. Wait 2-5 minutes for data ingestion")
            print("   2. Check Azure Log Analytics workspace permissions")
            print("   3. Verify the correct workspace is being queried")
            print("   4. Check if there are any Azure service outages")
        
        # Additional troubleshooting steps
        print("\n🔧 ADDITIONAL TROUBLESHOOTING STEPS:")
        print("   1. Check Azure Portal Application Insights 'Live Metrics' for real-time data")
        print("   2. Verify your Application Insights resource is in the correct region")
        print("   3. Check if there are any firewall/network restrictions")
        print("   4. Ensure the application is actually running and generating logs")
        print("   5. Check Application Insights quota limits")
        
        if 'live_transmission' in results and results['live_transmission'].get('success'):
            print(f"\n🎯 Use this operation_id to track your test data:")
            print(f"   {results['live_transmission']['test_operation_id']}")


def main():
    """Main troubleshooting function."""
    troubleshooter = ObservabilityTroubleshooter()
    
    try:
        results = troubleshooter.run_full_diagnosis()
        troubleshooter.print_summary(results)
        
        # Return appropriate exit code
        if troubleshooter.issues_found:
            print(f"\n⚠️  Found {len(troubleshooter.issues_found)} issues that may prevent observability data from appearing.")
            return 1
        else:
            print(f"\n✅ Troubleshooting completed successfully!")
            return 0
            
    except KeyboardInterrupt:
        print("\n\n❌ Troubleshooting interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Troubleshooting failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)