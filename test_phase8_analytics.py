"""
Phase 8 Analytics & Reporting Dashboard Test Script
Tests all analytics endpoints and functionality.
"""

import requests
import json
from datetime import datetime, timedelta
import sys

# Base URL for the API
BASE_URL = "http://localhost:8000"

# Test user credentials (superadmin)
TEST_CREDENTIALS = {
    "phone": "1234567890",
    "password": "admin123"
}

class Phase8Tester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.user_id = None
    
    def authenticate(self):
        """Authenticate and get access token"""
        print("🔐 Authenticating...")
        
        response = self.session.post(
            f"{BASE_URL}/auth/login", 
            json=TEST_CREDENTIALS
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.user_id = data.get("user", {}).get("id")
            
            # Set authorization header for future requests
            self.session.headers.update({
                "Authorization": f"Bearer {self.token}"
            })
            
            print(f"✅ Authentication successful")
            print(f"   User ID: {self.user_id}")
            return True
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    def test_analytics_overview(self):
        """Test analytics dashboard overview"""
        print("\n📊 Testing Analytics Overview...")
        
        response = self.session.get(f"{BASE_URL}/analytics/overview")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Analytics overview retrieved successfully")
            print(f"   Key metrics: {list(data.get('key_metrics', {}).keys())}")
            print(f"   Growth metrics: {list(data.get('growth_metrics', {}).keys())}")
            return True
        else:
            print(f"❌ Analytics overview failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    def test_sales_trends(self):
        """Test sales trends endpoint"""
        print("\n📈 Testing Sales Trends...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "granularity": "day"
        }
        
        response = self.session.get(f"{BASE_URL}/analytics/sales/trends", params=params)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Sales trends retrieved successfully")
            print(f"   Period: {data.get('period', {})}")
            print(f"   Data points: {len(data.get('trend_data', []))}")
            return True
        else:
            print(f"❌ Sales trends failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    def test_vendor_performance(self):
        """Test vendor performance endpoint"""
        print("\n🏪 Testing Vendor Performance...")
        
        params = {
            "period_days": 30,
            "limit": 10
        }
        
        response = self.session.get(f"{BASE_URL}/analytics/vendors/performance", params=params)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Vendor performance retrieved successfully")
            print(f"   Vendors analyzed: {len(data.get('vendors', []))}")
            return True
        else:
            print(f"❌ Vendor performance failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    def test_dashboard_widgets(self):
        """Test dashboard widgets endpoints"""
        print("\n🔧 Testing Dashboard Widgets...")
        
        # Get widgets
        response = self.session.get(f"{BASE_URL}/reports/dashboard/widgets")
        
        if response.status_code == 200:
            widgets = response.json()
            print(f"✅ Retrieved {len(widgets)} dashboard widgets")
            
            # Test creating a new widget
            widget_data = {
                "widget_name": "test_widget",
                "widget_title": "Test Widget",
                "widget_type": "chart",
                "data_source": "orders",
                "query_config": {"metric": "test"},
                "chart_type": "bar"
            }
            
            create_response = self.session.post(
                f"{BASE_URL}/reports/dashboard/widgets",
                json=widget_data
            )
            
            if create_response.status_code == 200:
                widget_id = create_response.json().get("id")
                print(f"✅ Created test widget with ID: {widget_id}")
                
                # Test updating the widget
                update_data = {
                    "widget_title": "Updated Test Widget"
                }
                
                update_response = self.session.put(
                    f"{BASE_URL}/reports/dashboard/widgets/{widget_id}",
                    json=update_data
                )
                
                if update_response.status_code == 200:
                    print("✅ Widget updated successfully")
                    
                    # Clean up - delete the test widget
                    delete_response = self.session.delete(
                        f"{BASE_URL}/reports/dashboard/widgets/{widget_id}"
                    )
                    
                    if delete_response.status_code == 200:
                        print("✅ Test widget deleted successfully")
                        return True
                    else:
                        print(f"⚠ Widget deletion failed: {delete_response.status_code}")
                        return True  # Still consider test successful
                else:
                    print(f"❌ Widget update failed: {update_response.status_code}")
                    return False
            else:
                print(f"❌ Widget creation failed: {create_response.status_code}")
                return False
        else:
            print(f"❌ Widget retrieval failed: {response.status_code}")
            return False
    
    def test_business_metrics(self):
        """Test business metrics endpoint"""
        print("\n📋 Testing Business Metrics...")
        
        params = {
            "granularity": "DAY",
            "period_days": 7
        }
        
        response = self.session.get(f"{BASE_URL}/reports/metrics/business", params=params)
        
        if response.status_code == 200:
            metrics = response.json()
            print(f"✅ Retrieved {len(metrics)} business metrics")
            
            if metrics:
                print(f"   Sample metric: {metrics[0].get('metric_name')} = {metrics[0].get('value')}")
            
            return True
        else:
            print(f"❌ Business metrics failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    def test_saved_queries(self):
        """Test saved queries endpoints"""
        print("\n💾 Testing Saved Queries...")
        
        # Get existing queries
        response = self.session.get(f"{BASE_URL}/queries/queries")
        
        if response.status_code == 200:
            queries = response.json()
            print(f"✅ Retrieved {len(queries)} saved queries")
            
            # Test creating a new query
            query_data = {
                "query_name": "Test Query",
                "query_description": "A test analytics query",
                "query_type": "BUSINESS",
                "sql_query": "SELECT COUNT(*) as total_users FROM users",
                "is_public": True
            }
            
            create_response = self.session.post(
                f"{BASE_URL}/queries/queries",
                json=query_data
            )
            
            if create_response.status_code == 200:
                query_id = create_response.json().get("id")
                print(f"✅ Created test query with ID: {query_id}")
                
                # Test executing the query
                execute_response = self.session.post(
                    f"{BASE_URL}/queries/queries/{query_id}/execute"
                )
                
                if execute_response.status_code == 200:
                    result = execute_response.json()
                    print(f"✅ Query executed successfully, returned {result.get('row_count')} rows")
                    
                    # Clean up - delete the test query
                    delete_response = self.session.delete(
                        f"{BASE_URL}/queries/queries/{query_id}"
                    )
                    
                    if delete_response.status_code == 200:
                        print("✅ Test query deleted successfully")
                        return True
                    else:
                        print(f"⚠ Query deletion failed: {delete_response.status_code}")
                        return True  # Still consider test successful
                else:
                    print(f"❌ Query execution failed: {execute_response.status_code}")
                    return False
            else:
                print(f"❌ Query creation failed: {create_response.status_code}")
                return False
        else:
            print(f"❌ Query retrieval failed: {response.status_code}")
            return False
    
    def test_alert_rules(self):
        """Test alert rules endpoints"""
        print("\n🚨 Testing Alert Rules...")
        
        # Get existing alert rules
        response = self.session.get(f"{BASE_URL}/alerts/alerts")
        
        if response.status_code == 200:
            alerts = response.json()
            print(f"✅ Retrieved {len(alerts)} alert rules")
            
            # Test creating a new alert rule
            alert_data = {
                "rule_name": "Test Alert",
                "rule_description": "A test alert rule",
                "metric_name": "test_metric",
                "condition": "VALUE_ABOVE",
                "threshold_value": 100.0,
                "severity": "MEDIUM",
                "comparison_operator": ">=",
                "notification_channels": ["email"]
            }
            
            create_response = self.session.post(
                f"{BASE_URL}/alerts/alerts",
                json=alert_data
            )
            
            if create_response.status_code == 200:
                alert_id = create_response.json().get("id")
                print(f"✅ Created test alert with ID: {alert_id}")
                
                # Test testing the alert rule
                test_response = self.session.post(
                    f"{BASE_URL}/alerts/alerts/test/{alert_id}"
                )
                
                if test_response.status_code == 200:
                    result = test_response.json()
                    print(f"✅ Alert test completed, triggered: {result.get('is_triggered')}")
                    
                    # Clean up - delete the test alert
                    delete_response = self.session.delete(
                        f"{BASE_URL}/alerts/alerts/{alert_id}"
                    )
                    
                    if delete_response.status_code == 200:
                        print("✅ Test alert deleted successfully")
                        return True
                    else:
                        print(f"⚠ Alert deletion failed: {delete_response.status_code}")
                        return True  # Still consider test successful
                else:
                    print(f"❌ Alert test failed: {test_response.status_code}")
                    return False
            else:
                print(f"❌ Alert creation failed: {create_response.status_code}")
                return False
        else:
            print(f"❌ Alert retrieval failed: {response.status_code}")
            return False
    
    def test_data_exports(self):
        """Test data export endpoints"""
        print("\n📤 Testing Data Exports...")
        
        # Test creating a data export
        export_data = {
            "export_name": "Test Export",
            "data_source": "orders",
            "format": "JSON",
            "query_config": {"limit": 10}
        }
        
        response = self.session.post(
            f"{BASE_URL}/queries/exports",
            json=export_data
        )
        
        if response.status_code == 200:
            export_info = response.json()
            export_id = export_info.get("export_id")
            print(f"✅ Created data export with ID: {export_id}")
            print(f"   Status: {export_info.get('status')}")
            print(f"   Records: {export_info.get('record_count')}")
            
            # Get export details
            details_response = self.session.get(
                f"{BASE_URL}/queries/exports/{export_id}"
            )
            
            if details_response.status_code == 200:
                details = details_response.json()
                print(f"✅ Export details retrieved, file size: {details.get('file_size_bytes')} bytes")
                return True
            else:
                print(f"❌ Export details failed: {details_response.status_code}")
                return False
        else:
            print(f"❌ Data export creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    def test_report_generation(self):
        """Test report generation"""
        print("\n📄 Testing Report Generation...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        report_data = {
            "report_name": "Test Weekly Report",
            "report_type": "SALES",
            "date_range_start": start_date.isoformat(),
            "date_range_end": end_date.isoformat(),
            "format": "JSON"
        }
        
        response = self.session.post(
            f"{BASE_URL}/reports/reports/generate",
            json=report_data
        )
        
        if response.status_code == 200:
            report_info = response.json()
            report_id = report_info.get("report_id")
            print(f"✅ Generated report with ID: {report_id}")
            print(f"   Status: {report_info.get('status')}")
            print(f"   Execution time: {report_info.get('execution_time_ms')}ms")
            
            # Get report details
            details_response = self.session.get(
                f"{BASE_URL}/reports/reports/{report_id}"
            )
            
            if details_response.status_code == 200:
                details = details_response.json()
                print(f"✅ Report details retrieved, records: {details.get('record_count')}")
                return True
            else:
                print(f"❌ Report details failed: {details_response.status_code}")
                return False
        else:
            print(f"❌ Report generation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    def run_all_tests(self):
        """Run all Phase 8 tests"""
        print("🚀 Starting Phase 8 Analytics & Reporting Dashboard Tests")
        print("=" * 60)
        
        if not self.authenticate():
            print("❌ Authentication failed, cannot continue with tests")
            return False
        
        tests = [
            ("Analytics Overview", self.test_analytics_overview),
            ("Sales Trends", self.test_sales_trends),
            ("Vendor Performance", self.test_vendor_performance),
            ("Dashboard Widgets", self.test_dashboard_widgets),
            ("Business Metrics", self.test_business_metrics),
            ("Saved Queries", self.test_saved_queries),
            ("Alert Rules", self.test_alert_rules),
            ("Data Exports", self.test_data_exports),
            ("Report Generation", self.test_report_generation)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                print(f"❌ {test_name} test failed with exception: {str(e)}")
                results[test_name] = False
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 Test Results Summary")
        print("=" * 60)
        
        passed = sum(results.values())
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:<25} {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All Phase 8 Analytics & Reporting tests passed!")
            return True
        else:
            print("⚠ Some tests failed. Please check the API server and database.")
            return False

def main():
    """Main test runner"""
    print("Phase 8 Analytics & Reporting Dashboard Test Suite")
    print(f"Testing API at: {BASE_URL}")
    print("-" * 60)
    
    tester = Phase8Tester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ Phase 8 testing completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Phase 8 testing completed with failures!")
        sys.exit(1)

if __name__ == "__main__":
    main()
