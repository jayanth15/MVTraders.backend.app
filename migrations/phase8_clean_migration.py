"""
Clean Phase 8 Analytics Database Migration
Drops existing analytics tables and recreates them with correct structure.
"""

import sqlite3
from datetime import datetime
import os

def clean_and_create_phase8_tables():
    """Drop existing analytics tables and create new ones"""
    
    db_path = os.path.join(os.path.dirname(__file__), '..', 'mvtraders.db')
    
    # Tables to drop and recreate
    tables_to_drop = [
        'analytics_reports', 'dashboard_widgets', 'business_metrics',
        'analytics_queries', 'data_exports', 'alert_rules'
    ]
    
    # SQL statements for creating Phase 8 tables
    tables_sql = [
        """
        CREATE TABLE analytics_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_name VARCHAR(200) NOT NULL,
            report_description TEXT,
            report_type VARCHAR(50) NOT NULL,
            date_range_start DATETIME NOT NULL,
            date_range_end DATETIME NOT NULL,
            filters TEXT,
            generated_by_user_id CHAR(32),
            format VARCHAR(20) NOT NULL DEFAULT 'JSON',
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            report_data TEXT,
            summary_metrics TEXT,
            file_path VARCHAR(500),
            record_count INTEGER DEFAULT 0,
            execution_time_ms INTEGER,
            expires_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """,
        
        """
        CREATE TABLE dashboard_widgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            widget_name VARCHAR(200) NOT NULL,
            widget_title VARCHAR(300) NOT NULL,
            widget_description TEXT,
            widget_type VARCHAR(50) NOT NULL,
            chart_type VARCHAR(50),
            data_source VARCHAR(100) NOT NULL,
            query_config TEXT NOT NULL,
            position_x INTEGER DEFAULT 0,
            position_y INTEGER DEFAULT 0,
            width INTEGER DEFAULT 4,
            height INTEGER DEFAULT 4,
            refresh_interval_minutes INTEGER DEFAULT 30,
            is_public BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            cached_data TEXT,
            last_updated DATETIME,
            owner_user_id CHAR(32),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """,
        
        """
        CREATE TABLE business_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name VARCHAR(200) NOT NULL,
            metric_type VARCHAR(50) NOT NULL,
            category VARCHAR(100),
            value DECIMAL(15,2) NOT NULL,
            previous_value DECIMAL(15,2),
            growth_rate DECIMAL(10,4),
            target_value DECIMAL(15,2),
            variance DECIMAL(10,4),
            unit VARCHAR(20),
            period_start DATETIME NOT NULL,
            period_end DATETIME NOT NULL,
            granularity VARCHAR(20) NOT NULL,
            dimensions TEXT,
            calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """,
        
        """
        CREATE TABLE analytics_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_name VARCHAR(200) NOT NULL,
            query_description TEXT,
            query_type VARCHAR(50) NOT NULL,
            sql_query TEXT NOT NULL,
            parameters TEXT,
            is_public BOOLEAN DEFAULT 0,
            execution_count INTEGER DEFAULT 0,
            last_executed_at DATETIME,
            avg_execution_time_ms INTEGER,
            owner_user_id CHAR(32),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """,
        
        """
        CREATE TABLE data_exports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            export_name VARCHAR(200) NOT NULL,
            data_source VARCHAR(100) NOT NULL,
            format VARCHAR(20) NOT NULL,
            query_config TEXT NOT NULL,
            filters TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            file_path VARCHAR(500),
            file_size_bytes BIGINT,
            record_count INTEGER DEFAULT 0,
            processing_time_ms INTEGER,
            error_message TEXT,
            expires_at DATETIME,
            requested_by_user_id CHAR(32),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """,
        
        """
        CREATE TABLE alert_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name VARCHAR(200) NOT NULL,
            rule_description TEXT,
            metric_name VARCHAR(200) NOT NULL,
            condition VARCHAR(50) NOT NULL,
            threshold_value DECIMAL(15,2) NOT NULL,
            comparison_operator VARCHAR(10) NOT NULL DEFAULT '>=',
            time_window_minutes INTEGER DEFAULT 60,
            severity VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
            notification_channels TEXT,
            is_active BOOLEAN DEFAULT 1,
            trigger_count INTEGER DEFAULT 0,
            last_triggered_at DATETIME,
            last_checked_at DATETIME,
            owner_user_id CHAR(32),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    ]
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Cleaning existing Phase 8 tables...")
        
        # Drop existing tables
        for table in tables_to_drop:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                print(f"✓ Dropped {table} table")
            except Exception as e:
                print(f"⚠ Warning dropping {table}: {str(e)}")
        
        print("\nCreating Phase 8 Analytics and Reporting tables...")
        
        # Create tables
        table_names = ['analytics_reports', 'dashboard_widgets', 'business_metrics', 
                      'analytics_queries', 'data_exports', 'alert_rules']
        
        for i, table_sql in enumerate(tables_sql):
            cursor.execute(table_sql)
            print(f"✓ Created {table_names[i]} table")
        
        # Create indexes
        print("\nCreating indexes...")
        
        indexes_sql = [
            "CREATE INDEX idx_analytics_reports_type ON analytics_reports(report_type)",
            "CREATE INDEX idx_analytics_reports_status ON analytics_reports(status)",
            "CREATE INDEX idx_analytics_reports_user ON analytics_reports(generated_by_user_id)",
            "CREATE INDEX idx_analytics_reports_created ON analytics_reports(created_at)",
            
            "CREATE INDEX idx_dashboard_widgets_owner ON dashboard_widgets(owner_user_id)",
            "CREATE INDEX idx_dashboard_widgets_public ON dashboard_widgets(is_public)",
            "CREATE INDEX idx_dashboard_widgets_active ON dashboard_widgets(is_active)",
            
            "CREATE INDEX idx_business_metrics_name ON business_metrics(metric_name)",
            "CREATE INDEX idx_business_metrics_type ON business_metrics(metric_type)",
            "CREATE INDEX idx_business_metrics_category ON business_metrics(category)",
            "CREATE INDEX idx_business_metrics_period ON business_metrics(period_start, period_end)",
            "CREATE INDEX idx_business_metrics_granularity ON business_metrics(granularity)",
            
            "CREATE INDEX idx_analytics_queries_owner ON analytics_queries(owner_user_id)",
            "CREATE INDEX idx_analytics_queries_type ON analytics_queries(query_type)",
            "CREATE INDEX idx_analytics_queries_public ON analytics_queries(is_public)",
            
            "CREATE INDEX idx_data_exports_user ON data_exports(requested_by_user_id)",
            "CREATE INDEX idx_data_exports_status ON data_exports(status)",
            "CREATE INDEX idx_data_exports_source ON data_exports(data_source)",
            "CREATE INDEX idx_data_exports_created ON data_exports(created_at)",
            
            "CREATE INDEX idx_alert_rules_owner ON alert_rules(owner_user_id)",
            "CREATE INDEX idx_alert_rules_active ON alert_rules(is_active)",
            "CREATE INDEX idx_alert_rules_metric ON alert_rules(metric_name)",
            "CREATE INDEX idx_alert_rules_severity ON alert_rules(severity)"
        ]
        
        for index_sql in indexes_sql:
            cursor.execute(index_sql)
        print("✓ Created all indexes")
        
        # Insert sample data
        print("\nInserting sample analytics data...")
        
        # Sample dashboard widgets
        cursor.execute("""
            INSERT INTO dashboard_widgets (
                widget_name, widget_title, widget_description, widget_type, chart_type, 
                data_source, query_config, position_x, position_y, width, height, 
                refresh_interval_minutes, is_public, is_active, owner_user_id
            ) VALUES 
            ('sales_overview', 'Sales Overview', 'Key sales metrics and trends', 'chart', 'line', 'orders', 
             '{"metric": "total_sales", "period": "30d"}', 0, 0, 6, 4, 15, 1, 1, '9283292d71494a33a48ba6162ec956bd'),
            ('vendor_count', 'Active Vendors', 'Number of active vendors', 'metric', 'number', 'vendors', 
             '{"metric": "active_count"}', 6, 0, 3, 2, 60, 1, 1, '9283292d71494a33a48ba6162ec956bd'),
            ('order_status', 'Order Status Distribution', 'Breakdown of orders by status', 'chart', 'pie', 'orders', 
             '{"metric": "status_distribution"}', 9, 0, 3, 4, 30, 1, 1, '9283292d71494a33a48ba6162ec956bd')
        """)
        
        # Sample business metrics
        cursor.execute("""
            INSERT INTO business_metrics (
                metric_name, metric_type, category, value, previous_value, growth_rate, 
                target_value, variance, unit, period_start, period_end, granularity, dimensions
            ) VALUES 
            ('total_revenue', 'REVENUE', 'Sales', 25000.00, 22000.00, 13.64, 30000.00, -16.67, 'USD', 
             '2024-01-01 00:00:00', '2024-01-31 23:59:59', 'MONTH', '{}'),
            ('order_count', 'COUNT', 'Orders', 150, 135, 11.11, 200, -25.00, 'orders', 
             '2024-01-01 00:00:00', '2024-01-31 23:59:59', 'MONTH', '{}'),
            ('avg_order_value', 'AVERAGE', 'Orders', 166.67, 162.96, 2.27, 150.00, 11.11, 'USD', 
             '2024-01-01 00:00:00', '2024-01-31 23:59:59', 'MONTH', '{}')
        """)
        
        # Sample alert rules
        cursor.execute("""
            INSERT INTO alert_rules (
                rule_name, rule_description, metric_name, condition, threshold_value, 
                comparison_operator, time_window_minutes, severity, notification_channels, 
                is_active, trigger_count, owner_user_id
            ) VALUES 
            ('Low Sales Alert', 'Alert when daily sales drop below threshold', 'daily_sales', 
             'VALUE_BELOW', 500.00, '<', 60, 'HIGH', '["email", "sms"]', 1, 0, '9283292d71494a33a48ba6162ec956bd'),
            ('High Order Volume', 'Alert when order volume exceeds capacity', 'hourly_orders', 
             'VALUE_ABOVE', 20.00, '>', 60, 'MEDIUM', '["email"]', 1, 0, '9283292d71494a33a48ba6162ec956bd')
        """)
        
        # Sample saved queries
        cursor.execute("""
            INSERT INTO analytics_queries (
                query_name, query_description, query_type, sql_query, parameters, 
                is_public, owner_user_id
            ) VALUES 
            ('Top Selling Products', 'Products with highest sales volume', 'BUSINESS', 
             'SELECT name, COUNT(*) as sales FROM products p JOIN order_items oi ON p.id = oi.product_id GROUP BY p.id ORDER BY sales DESC', 
             '{}', 1, '9283292d71494a33a48ba6162ec956bd'),
            ('Monthly Revenue Trend', 'Revenue breakdown by month', 'BUSINESS', 
             'SELECT strftime("%Y-%m", created_at) as month, SUM(total_amount) as revenue FROM orders GROUP BY month ORDER BY month', 
             '{}', 1, '9283292d71494a33a48ba6162ec956bd')
        """)
        
        # Commit changes
        conn.commit()
        print("✓ Inserted sample data")
        
        print(f"\n🎉 Phase 8 Analytics and Reporting migration completed successfully!")
        print(f"Database: {db_path}")
        print(f"Migration completed at: {datetime.now()}")
        
        # Show table counts
        tables = ['analytics_reports', 'dashboard_widgets', 'business_metrics', 
                 'analytics_queries', 'data_exports', 'alert_rules']
        
        print("\nTable Status:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} records")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        if conn:
            conn.rollback()
        return False
    
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    success = clean_and_create_phase8_tables()
    if success:
        print("\n✅ Phase 8 database migration completed successfully!")
    else:
        print("\n❌ Phase 8 database migration failed!")
