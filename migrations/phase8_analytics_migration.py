"""
Phase 8 Analytics and Reporting Database Migration
Creates all necessary tables for the analytics and reporting system.
"""

import sqlite3
from datetime import datetime
import os

def create_phase8_tables():
    """Create Phase 8 analytics and reporting tables"""
    
    # Database path
    db_path = os.path.join(os.path.dirname(__file__), '..', 'mvtraders.db')
    
    # SQL statements for creating Phase 8 tables
    analytics_reports_sql = """
    CREATE TABLE IF NOT EXISTS analytics_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_name VARCHAR(200) NOT NULL,
        report_description TEXT,
        report_type VARCHAR(50) NOT NULL,
        date_range_start DATETIME NOT NULL,
        date_range_end DATETIME NOT NULL,
        filters JSON,
        generated_by_user_id CHAR(32),
        format VARCHAR(20) NOT NULL DEFAULT 'JSON',
        status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
        report_data JSON,
        summary_metrics JSON,
        file_path VARCHAR(500),
        record_count INTEGER DEFAULT 0,
        execution_time_ms INTEGER,
        expires_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (generated_by_user_id) REFERENCES users (id)
    );
    """
    
    dashboard_widgets_sql = """
    CREATE TABLE IF NOT EXISTS dashboard_widgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        widget_name VARCHAR(200) NOT NULL,
        widget_title VARCHAR(300) NOT NULL,
        widget_description TEXT,
        widget_type VARCHAR(50) NOT NULL,
        chart_type VARCHAR(50),
        data_source VARCHAR(100) NOT NULL,
        query_config JSON NOT NULL,
        position_x INTEGER DEFAULT 0,
        position_y INTEGER DEFAULT 0,
        width INTEGER DEFAULT 4,
        height INTEGER DEFAULT 4,
        refresh_interval_minutes INTEGER DEFAULT 30,
        is_public BOOLEAN DEFAULT 0,
        is_active BOOLEAN DEFAULT 1,
        cached_data JSON,
        last_updated DATETIME,
        owner_user_id CHAR(32),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_user_id) REFERENCES users (id)
    );
    """
    
    business_metrics_sql = """
    CREATE TABLE IF NOT EXISTS business_metrics (
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
        dimensions JSON,
        calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    analytics_queries_sql = """
    CREATE TABLE IF NOT EXISTS analytics_queries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query_name VARCHAR(200) NOT NULL,
        query_description TEXT,
        query_type VARCHAR(50) NOT NULL,
        sql_query TEXT NOT NULL,
        parameters JSON,
        is_public BOOLEAN DEFAULT 0,
        execution_count INTEGER DEFAULT 0,
        last_executed_at DATETIME,
        avg_execution_time_ms INTEGER,
        owner_user_id CHAR(32),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_user_id) REFERENCES users (id)
    );
    """
    
    data_exports_sql = """
    CREATE TABLE IF NOT EXISTS data_exports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        export_name VARCHAR(200) NOT NULL,
        data_source VARCHAR(100) NOT NULL,
        format VARCHAR(20) NOT NULL,
        query_config JSON NOT NULL,
        filters JSON,
        status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
        file_path VARCHAR(500),
        file_size_bytes BIGINT,
        record_count INTEGER DEFAULT 0,
        processing_time_ms INTEGER,
        error_message TEXT,
        expires_at DATETIME,
        requested_by_user_id CHAR(32),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (requested_by_user_id) REFERENCES users (id)
    );
    """
    
    alert_rules_sql = """
    CREATE TABLE IF NOT EXISTS alert_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_name VARCHAR(200) NOT NULL,
        rule_description TEXT,
        metric_name VARCHAR(200) NOT NULL,
        condition VARCHAR(50) NOT NULL,
        threshold_value DECIMAL(15,2) NOT NULL,
        comparison_operator VARCHAR(10) NOT NULL DEFAULT '>=',
        time_window_minutes INTEGER DEFAULT 60,
        severity VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
        notification_channels JSON,
        is_active BOOLEAN DEFAULT 1,
        trigger_count INTEGER DEFAULT 0,
        last_triggered_at DATETIME,
        last_checked_at DATETIME,
        owner_user_id CHAR(32),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_user_id) REFERENCES users (id)
    );
    """
    
    # Index creation statements
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_analytics_reports_type ON analytics_reports(report_type);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_reports_status ON analytics_reports(status);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_reports_user ON analytics_reports(generated_by_user_id);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_reports_created ON analytics_reports(created_at);",
        
        "CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_owner ON dashboard_widgets(owner_user_id);",
        "CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_public ON dashboard_widgets(is_public);",
        "CREATE INDEX IF NOT EXISTS idx_dashboard_widgets_active ON dashboard_widgets(is_active);",
        
        "CREATE INDEX IF NOT EXISTS idx_business_metrics_name ON business_metrics(metric_name);",
        "CREATE INDEX IF NOT EXISTS idx_business_metrics_type ON business_metrics(metric_type);",
        "CREATE INDEX IF NOT EXISTS idx_business_metrics_category ON business_metrics(category);",
        "CREATE INDEX IF NOT EXISTS idx_business_metrics_period ON business_metrics(period_start, period_end);",
        "CREATE INDEX IF NOT EXISTS idx_business_metrics_granularity ON business_metrics(granularity);",
        
        "CREATE INDEX IF NOT EXISTS idx_analytics_queries_owner ON analytics_queries(owner_user_id);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_queries_type ON analytics_queries(query_type);",
        "CREATE INDEX IF NOT EXISTS idx_analytics_queries_public ON analytics_queries(is_public);",
        
        "CREATE INDEX IF NOT EXISTS idx_data_exports_user ON data_exports(requested_by_user_id);",
        "CREATE INDEX IF NOT EXISTS idx_data_exports_status ON data_exports(status);",
        "CREATE INDEX IF NOT EXISTS idx_data_exports_source ON data_exports(data_source);",
        "CREATE INDEX IF NOT EXISTS idx_data_exports_created ON data_exports(created_at);",
        
        "CREATE INDEX IF NOT EXISTS idx_alert_rules_owner ON alert_rules(owner_user_id);",
        "CREATE INDEX IF NOT EXISTS idx_alert_rules_active ON alert_rules(is_active);",
        "CREATE INDEX IF NOT EXISTS idx_alert_rules_metric ON alert_rules(metric_name);",
        "CREATE INDEX IF NOT EXISTS idx_alert_rules_severity ON alert_rules(severity);"
    ]
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Creating Phase 8 Analytics and Reporting tables...")
        
        # Create tables
        cursor.execute(analytics_reports_sql)
        print("✓ Created analytics_reports table")
        
        cursor.execute(dashboard_widgets_sql)
        print("✓ Created dashboard_widgets table")
        
        cursor.execute(business_metrics_sql)
        print("✓ Created business_metrics table")
        
        cursor.execute(analytics_queries_sql)
        print("✓ Created analytics_queries table")
        
        cursor.execute(data_exports_sql)
        print("✓ Created data_exports table")
        
        cursor.execute(alert_rules_sql)
        print("✓ Created alert_rules table")
        
        # Create indexes
        print("\nCreating indexes...")
        for index_sql in indexes_sql:
            cursor.execute(index_sql)
        print("✓ Created all indexes")
        
        # Insert some sample data
        print("\nInserting sample analytics data...")
        
        # Sample dashboard widgets
        sample_widgets = [
            (
                'sales_overview', 'Sales Overview', 'Key sales metrics and trends', 
                'chart', 'line', 'orders', 
                '{"metric": "total_sales", "period": "30d"}',
                0, 0, 6, 4, 15, 1, 1, None, None, '9283292d71494a33a48ba6162ec956bd'
            ),
            (
                'vendor_count', 'Active Vendors', 'Number of active vendors', 
                'metric', 'number', 'vendors', 
                '{"metric": "active_count"}',
                6, 0, 3, 2, 60, 1, 1, None, None, '9283292d71494a33a48ba6162ec956bd'
            ),
            (
                'order_status', 'Order Status Distribution', 'Breakdown of orders by status', 
                'chart', 'pie', 'orders', 
                '{"metric": "status_distribution"}',
                9, 0, 3, 4, 30, 1, 1, None, None, '9283292d71494a33a48ba6162ec956bd'
            )
        ]
        
        cursor.executemany("""
            INSERT INTO dashboard_widgets (
                widget_name, widget_title, widget_description, widget_type, chart_type, 
                data_source, query_config, position_x, position_y, width, height, 
                refresh_interval_minutes, is_public, is_active, cached_data, last_updated, owner_user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_widgets)
        
        # Sample business metrics
        sample_metrics = [
            ('total_revenue', 'REVENUE', 'Sales', 25000.00, 22000.00, 13.64, 30000.00, -16.67, 'USD', 
             '2024-01-01 00:00:00', '2024-01-31 23:59:59', 'MONTH', '{}'),
            ('order_count', 'COUNT', 'Orders', 150, 135, 11.11, 200, -25.00, 'orders', 
             '2024-01-01 00:00:00', '2024-01-31 23:59:59', 'MONTH', '{}'),
            ('avg_order_value', 'AVERAGE', 'Orders', 166.67, 162.96, 2.27, 150.00, 11.11, 'USD', 
             '2024-01-01 00:00:00', '2024-01-31 23:59:59', 'MONTH', '{}')
        ]
        
        cursor.executemany("""
            INSERT INTO business_metrics (
                metric_name, metric_type, category, value, previous_value, growth_rate, 
                target_value, variance, unit, period_start, period_end, granularity, dimensions
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_metrics)
        
        # Sample alert rules
        sample_alerts = [
            ('Low Sales Alert', 'Alert when daily sales drop below threshold', 'daily_sales', 
             'VALUE_BELOW', 500.00, '<', 60, 'HIGH', '["email", "sms"]', 1, 0, None, None, '9283292d71494a33a48ba6162ec956bd'),
            ('High Order Volume', 'Alert when order volume exceeds capacity', 'hourly_orders', 
             'VALUE_ABOVE', 20.00, '>', 60, 'MEDIUM', '["email"]', 1, 0, None, None, '9283292d71494a33a48ba6162ec956bd')
        ]
        
        cursor.executemany("""
            INSERT INTO alert_rules (
                rule_name, rule_description, metric_name, condition, threshold_value, 
                comparison_operator, time_window_minutes, severity, notification_channels, 
                is_active, trigger_count, last_triggered_at, last_checked_at, owner_user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_alerts)
        
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
        
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        conn.rollback()
        return False
    
    finally:
        if conn:
            conn.close()
    
    return True


if __name__ == "__main__":
    success = create_phase8_tables()
    if success:
        print("\n✅ Phase 8 database migration completed successfully!")
    else:
        print("\n❌ Phase 8 database migration failed!")
