"""Test that quotation and sales order routers are properly registered"""

import pytest
from app.api.v1.router import api_router


def test_quotation_routes_registered():
    """Test that quotation routes are properly registered"""
    all_routes = api_router.routes
    quotation_routes = [r for r in all_routes if '/quotations' in str(r.path)]
    
    # Should have at least 4 quotation route patterns
    assert len(quotation_routes) >= 4, f"Expected at least 4 quotation routes, found {len(quotation_routes)}"
    
    # Verify the routes exist
    route_paths = [str(r.path) for r in quotation_routes]
    assert any('/quotations' == path for path in route_paths), "Missing /quotations route"
    assert any('/quotations/{quotation_id}' in path for path in route_paths), "Missing /quotations/{quotation_id} route"


def test_sales_order_routes_registered():
    """Test that sales order routes are properly registered"""
    all_routes = api_router.routes
    sales_order_routes = [r for r in all_routes if '/sales-orders' in str(r.path)]
    
    # Should have at least 5 sales order route patterns
    assert len(sales_order_routes) >= 5, f"Expected at least 5 sales order routes, found {len(sales_order_routes)}"
    
    # Verify the routes exist
    route_paths = [str(r.path) for r in sales_order_routes]
    assert any('/sales-orders' == path for path in route_paths), "Missing /sales-orders route"
    assert any('/sales-orders/{sales_order_id}' in path for path in route_paths), "Missing /sales-orders/{sales_order_id} route"


def test_router_url_prefixes():
    """Test that routers have correct URL prefixes"""
    all_routes = api_router.routes
    
    # Check quotations prefix
    quotation_routes = [r for r in all_routes if '/quotations' in str(r.path)]
    for route in quotation_routes:
        assert str(route.path).startswith('/quotations'), f"Quotation route has incorrect prefix: {route.path}"
    
    # Check sales-orders prefix
    sales_order_routes = [r for r in all_routes if '/sales-orders' in str(r.path)]
    for route in sales_order_routes:
        assert str(route.path).startswith('/sales-orders'), f"Sales order route has incorrect prefix: {route.path}"


def test_all_expected_quotation_endpoints():
    """Test that all expected quotation endpoints are registered"""
    all_routes = api_router.routes
    quotation_routes = [r for r in all_routes if '/quotations' in str(r.path)]
    
    route_info = []
    for route in quotation_routes:
        path = str(route.path)
        methods = list(route.methods) if hasattr(route, 'methods') else []
        route_info.append((path, methods))
    
    # Expected endpoints
    expected = [
        ('/quotations', ['POST', 'GET']),
        ('/quotations/{quotation_id}', ['GET', 'PUT', 'DELETE']),
        ('/quotations/{quotation_id}/status', ['PUT']),
        ('/quotations/{quotation_id}/convert-to-sales-order', ['POST']),
    ]
    
    for expected_path, expected_methods in expected:
        matching_routes = [r for r in route_info if r[0] == expected_path]
        assert len(matching_routes) > 0, f"Missing route: {expected_path}"
        
        # Check that at least one of the expected methods exists
        all_methods = set()
        for _, methods in matching_routes:
            all_methods.update(methods)
        
        for method in expected_methods:
            assert method in all_methods, f"Missing method {method} for route {expected_path}"


def test_all_expected_sales_order_endpoints():
    """Test that all expected sales order endpoints are registered"""
    all_routes = api_router.routes
    sales_order_routes = [r for r in all_routes if '/sales-orders' in str(r.path)]
    
    route_info = []
    for route in sales_order_routes:
        path = str(route.path)
        methods = list(route.methods) if hasattr(route, 'methods') else []
        route_info.append((path, methods))
    
    # Expected endpoints
    expected = [
        ('/sales-orders', ['POST', 'GET']),
        ('/sales-orders/{sales_order_id}', ['GET', 'PUT', 'DELETE']),
        ('/sales-orders/{sales_order_id}/status', ['PUT']),
        ('/sales-orders/{sales_order_id}/convert-to-invoice', ['POST']),
        ('/sales-orders/{sales_order_id}/convert-to-delivery-note', ['POST']),
    ]
    
    for expected_path, expected_methods in expected:
        matching_routes = [r for r in route_info if r[0] == expected_path]
        assert len(matching_routes) > 0, f"Missing route: {expected_path}"
        
        # Check that at least one of the expected methods exists
        all_methods = set()
        for _, methods in matching_routes:
            all_methods.update(methods)
        
        for method in expected_methods:
            assert method in all_methods, f"Missing method {method} for route {expected_path}"



def test_rfq_routes_registered():
    """Test that RFQ routes are properly registered"""
    all_routes = api_router.routes
    rfq_routes = [r for r in all_routes if '/rfqs' in str(r.path)]
    
    # Should have at least 8 RFQ route patterns
    assert len(rfq_routes) >= 8, f"Expected at least 8 RFQ routes, found {len(rfq_routes)}"
    
    # Verify the routes exist
    route_paths = [str(r.path) for r in rfq_routes]
    assert any('/rfqs' == path for path in route_paths), "Missing /rfqs route"
    assert any('/rfqs/{rfq_id}' in path for path in route_paths), "Missing /rfqs/{rfq_id} route"


def test_all_expected_rfq_endpoints():
    """Test that all expected RFQ endpoints are registered"""
    all_routes = api_router.routes
    rfq_routes = [r for r in all_routes if '/rfqs' in str(r.path)]
    
    route_info = []
    for route in rfq_routes:
        path = str(route.path)
        methods = list(route.methods) if hasattr(route, 'methods') else []
        route_info.append((path, methods))
    
    # Expected endpoints
    expected = [
        ('/rfqs', ['POST', 'GET']),
        ('/rfqs/{rfq_id}', ['GET', 'PUT', 'DELETE']),
        ('/rfqs/{rfq_id}/send', ['POST']),
        ('/rfqs/{rfq_id}/quotes', ['POST']),
        ('/rfqs/{rfq_id}/close', ['POST']),
    ]
    
    for expected_path, expected_methods in expected:
        matching_routes = [r for r in route_info if r[0] == expected_path]
        assert len(matching_routes) > 0, f"Missing route: {expected_path}"
        
        # Check that at least one of the expected methods exists
        all_methods = set()
        for _, methods in matching_routes:
            all_methods.update(methods)
        
        for method in expected_methods:
            assert method in all_methods, f"Missing method {method} for route {expected_path}"


def test_material_request_routes_registered():
    """Test that Material Request routes are properly registered"""
    all_routes = api_router.routes
    mr_routes = [r for r in all_routes if '/material-requests' in str(r.path)]
    
    # Should have at least 6 Material Request route patterns
    assert len(mr_routes) >= 6, f"Expected at least 6 Material Request routes, found {len(mr_routes)}"
    
    # Verify the routes exist
    route_paths = [str(r.path) for r in mr_routes]
    assert any('/material-requests' == path for path in route_paths), "Missing /material-requests route"
    assert any('/material-requests/{material_request_id}' in path for path in route_paths), "Missing /material-requests/{material_request_id} route"
