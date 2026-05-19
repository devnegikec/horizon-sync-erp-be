from app.main import app

outbound_routes = [r for r in app.routes if hasattr(r, 'path') and '/outbound' in r.path]
for r in outbound_routes:
    methods = ','.join(r.methods) if hasattr(r, 'methods') else 'N/A'
    print(f'{methods:8s} {r.path}')
