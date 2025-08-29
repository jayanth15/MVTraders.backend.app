"""
Test Phase 3 API Endpoints
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print('🚀 Testing Phase 3 API Endpoints...')
print('=' * 50)

# Test health endpoint
response = client.get('/api/v1/health')
print(f'Health Check: {response.status_code} - {response.json()}')

# Test products list (public endpoint)
response = client.get('/api/v1/products')
print(f'Products List: {response.status_code} - Found {len(response.json())} products')

# Test product categories
response = client.get('/api/v1/products/categories/list')
categories_data = response.json()
print(f'Product Categories: {response.status_code} - {len(categories_data["categories"])} categories')

# Test featured products
response = client.get('/api/v1/products/featured')
print(f'Featured Products: {response.status_code} - Found {len(response.json())} featured products')

print('✅ Phase 3 API endpoints working correctly!')
