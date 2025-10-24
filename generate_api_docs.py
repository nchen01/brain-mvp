#!/usr/bin/env python3
"""
Generate API documentation for DocForge Brain MVP.

This script creates comprehensive API documentation including:
- Endpoint descriptions
- Request/response schemas
- Authentication requirements
- Usage examples
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from api.app import create_app


def generate_openapi_spec():
    """Generate OpenAPI specification."""
    app = create_app()
    return app.openapi()


def generate_markdown_docs(openapi_spec):
    """Generate markdown documentation from OpenAPI spec."""
    
    docs = f"""# DocForge Brain MVP API Documentation

**Version:** {openapi_spec['info']['version']}  
**Description:** {openapi_spec['info']['description']}

## Base URL
```
http://localhost:8000
```

## Authentication

The API uses JWT Bearer token authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

### Getting a Token

1. Get available test users:
   ```bash
   curl -X GET "http://localhost:8000/api/v1/auth/test/users"
   ```

2. Login with test credentials:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/login" \\
     -H "Content-Type: application/json" \\
     -d '{{"username": "testuser", "password": "password"}}'
   ```

## Endpoints

"""
    
    # Group endpoints by tags
    endpoints_by_tag = {}
    
    for path, methods in openapi_spec.get('paths', {}).items():
        for method, details in methods.items():
            if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                tags = details.get('tags', ['Other'])
                tag = tags[0] if tags else 'Other'
                
                if tag not in endpoints_by_tag:
                    endpoints_by_tag[tag] = []
                
                endpoints_by_tag[tag].append({
                    'path': path,
                    'method': method.upper(),
                    'summary': details.get('summary', ''),
                    'description': details.get('description', ''),
                    'parameters': details.get('parameters', []),
                    'requestBody': details.get('requestBody', {}),
                    'responses': details.get('responses', {})
                })
    
    # Generate documentation for each tag
    for tag, endpoints in endpoints_by_tag.items():
        docs += f"### {tag.title()}\n\n"
        
        for endpoint in endpoints:
            docs += f"#### {endpoint['method']} {endpoint['path']}\n\n"
            
            if endpoint['summary']:
                docs += f"**Summary:** {endpoint['summary']}\n\n"
            
            if endpoint['description']:
                docs += f"{endpoint['description']}\n\n"
            
            # Parameters
            if endpoint['parameters']:
                docs += "**Parameters:**\n\n"
                for param in endpoint['parameters']:
                    param_name = param.get('name', '')
                    param_type = param.get('schema', {}).get('type', 'string')
                    param_desc = param.get('description', '')
                    param_required = param.get('required', False)
                    
                    required_text = " (required)" if param_required else " (optional)"
                    docs += f"- `{param_name}` ({param_type}){required_text}: {param_desc}\n"
                docs += "\n"
            
            # Request body
            if endpoint['requestBody']:
                docs += "**Request Body:**\n\n"
                content = endpoint['requestBody'].get('content', {})
                if 'application/json' in content:
                    schema = content['application/json'].get('schema', {})
                    docs += "```json\n"
                    docs += json.dumps(schema, indent=2)
                    docs += "\n```\n\n"
            
            # Example curl command
            docs += "**Example:**\n\n"
            curl_cmd = f"curl -X {endpoint['method']} \"http://localhost:8000{endpoint['path']}\""
            
            if endpoint['method'] in ['POST', 'PUT', 'PATCH']:
                curl_cmd += " \\\\\n  -H \"Content-Type: application/json\""
                if endpoint['requestBody']:
                    curl_cmd += " \\\\\n  -d '{}'"
            
            # Add auth header for protected endpoints
            if endpoint['path'].startswith('/api/v1/documents') and endpoint['method'] != 'GET':
                curl_cmd += " \\\\\n  -H \"Authorization: Bearer <your-token>\""
            
            docs += f"```bash\n{curl_cmd}\n```\n\n"
            
            docs += "---\n\n"
    
    # Add examples section
    docs += """## Usage Examples

### Complete Workflow Example

1. **Login and get token:**
   ```bash
   # Get test users
   curl -X GET "http://localhost:8000/api/v1/auth/test/users"
   
   # Login
   TOKEN=$(curl -X POST "http://localhost:8000/api/v1/auth/login" \\
     -H "Content-Type: application/json" \\
     -d '{"username": "testuser", "password": "password"}' \\
     | jq -r '.access_token')
   ```

2. **Upload a document:**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/documents/upload" \\
     -H "Authorization: Bearer $TOKEN" \\
     -F "file=@document.pdf" \\
     -F 'metadata={"author": "John Doe", "category": "research"}'
   ```

3. **Check processing status:**
   ```bash
   curl -X GET "http://localhost:8000/api/v1/documents/{document_id}/status" \\
     -H "Authorization: Bearer $TOKEN"
   ```

4. **Get document versions:**
   ```bash
   curl -X GET "http://localhost:8000/api/v1/documents/{document_id}/versions" \\
     -H "Authorization: Bearer $TOKEN"
   ```

5. **Download processed document:**
   ```bash
   curl -X GET "http://localhost:8000/api/v1/documents/{document_id}/download?format=original" \\
     -H "Authorization: Bearer $TOKEN" \\
     -o downloaded_document.pdf
   ```

### Error Handling

The API returns standard HTTP status codes:

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

Error responses include details:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "filename",
      "issue": "Required field missing"
    }
  }
}
```

## Interactive Documentation

When the API server is running, you can access interactive documentation at:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Support

For issues and questions:
- Check the interactive documentation
- Review the test files for usage examples
- Run the test suite: `python run_api_tests.py`
"""
    
    return docs


def main():
    """Generate API documentation."""
    print("📚 Generating DocForge Brain MVP API Documentation...")
    
    try:
        # Generate OpenAPI spec
        openapi_spec = generate_openapi_spec()
        
        # Save OpenAPI spec as JSON
        openapi_file = Path("api_openapi.json")
        with open(openapi_file, 'w') as f:
            json.dump(openapi_spec, f, indent=2)
        
        print(f"✅ OpenAPI specification saved: {openapi_file}")
        
        # Generate markdown documentation
        markdown_docs = generate_markdown_docs(openapi_spec)
        
        # Save markdown docs
        docs_file = Path("API_DOCUMENTATION.md")
        with open(docs_file, 'w') as f:
            f.write(markdown_docs)
        
        print(f"✅ API documentation saved: {docs_file}")
        
        print("\n📖 Documentation generated successfully!")
        print(f"   - OpenAPI spec: {openapi_file}")
        print(f"   - Markdown docs: {docs_file}")
        print("\n🌐 Interactive docs available when server is running:")
        print("   - Swagger UI: http://localhost:8000/docs")
        print("   - ReDoc: http://localhost:8000/redoc")
        
    except Exception as e:
        print(f"❌ Error generating documentation: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())