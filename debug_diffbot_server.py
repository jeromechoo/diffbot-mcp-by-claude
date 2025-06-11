#!/usr/bin/env python3
"""
Debug and test utilities for Diffbot MCP Server
"""

import os
import sys
import json
import asyncio
import httpx
from typing import Dict, Any

def check_environment():
    """Check if environment is properly configured"""
    print("🔍 Environment Check")
    print("=" * 30)
    
    # Check Python version
    python_version = sys.version_info
    print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    else:
        print("✅ Python version OK")
    
    # Check required packages
    required_packages = ['mcp', 'httpx', 'pydantic']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} installed")
        except ImportError:
            print(f"❌ {package} not installed")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\nInstall missing packages with:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    # Check environment variables
    diffbot_token = os.getenv('DIFFBOT_TOKEN')
    if diffbot_token:
        print(f"✅ DIFFBOT_TOKEN set (length: {len(diffbot_token)})")
        # Validate token format (should be alphanumeric)
        if diffbot_token.replace('_', '').replace('-', '').isalnum():
            print("✅ Token format looks valid")
        else:
            print("⚠️  Token format might be invalid")
    else:
        print("❌ DIFFBOT_TOKEN not set")
        print("Set it with: export DIFFBOT_TOKEN=your_token_here")
        return False
    
    # Check server file
    if os.path.exists('diffbot_mcp_server.py'):
        print("✅ diffbot_mcp_server.py found")
    else:
        print("❌ diffbot_mcp_server.py not found")
        return False
    
    return True


async def test_diffbot_api_directly():
    """Test Diffbot API directly without MCP"""
    print("\n🌐 Direct API Test")
    print("=" * 30)
    
    token = os.getenv('DIFFBOT_TOKEN')
    if not token:
        print("❌ No DIFFBOT_TOKEN set")
        return
    
    async with httpx.AsyncClient(timeout=10) as client:
        # Test DQL API
        print("Testing DQL API...")
        try:
            response = await client.get(
                "https://api.diffbot.com/v3/search",
                params={
                    "token": token,
                    "query": "type:article",
                    "num": 1
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ DQL API working - found {data.get('hits', 0)} results")
            elif response.status_code == 401:
                print("❌ Invalid API token")
            else:
                print(f"❌ DQL API error: {response.status_code} - {response.text}")
        
        except Exception as e:
            print(f"❌ DQL API connection error: {str(e)}")
        
        # Test Enhance API
        print("\nTesting Enhance API...")
        try:
            response = await client.get(
                "https://api.diffbot.com/v3/enhance",
                params={
                    "token": token,
                    "url": "https://example.com",
                    "fields": "meta"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Enhance API working")
                if 'objects' in data and data['objects']:
                    print(f"   Extracted data for: {data['objects'][0].get('pageUrl', 'unknown')}")
            elif response.status_code == 401:
                print("❌ Invalid API token")
            else:
                print(f"❌ Enhance API error: {response.status_code} - {response.text}")
        
        except Exception as e:
            print(f"❌ Enhance API connection error: {str(e)}")


def test_mcp_import():
    """Test MCP imports specifically"""
    print("\n📦 MCP Import Test")
    print("=" * 30)
    
    try:
        from mcp.server.fastmcp import FastMCP
        print("✅ FastMCP import successful")
        
        # Try creating a basic server
        mcp = FastMCP("test-server")
        print("✅ FastMCP server creation successful")
        
        # Test decorator
        @mcp.tool()
        def test_tool() -> str:
            """Test tool"""
            return "Hello from test tool"
        
        print("✅ MCP tool decorator working")
        return True
        
    except ImportError as e:
        print(f"❌ MCP import failed: {str(e)}")
        print("Try installing with: pip install mcp")
        return False
    except Exception as e:
        print(f"❌ MCP setup failed: {str(e)}")
        return False


def create_minimal_test_server():
    """Create a minimal MCP server for testing"""
    minimal_server_code = '''#!/usr/bin/env python3
"""Minimal MCP server for testing"""

import os
from mcp.server.fastmcp import FastMCP

# Check token
if not os.getenv('DIFFBOT_TOKEN'):
    print("ERROR: DIFFBOT_TOKEN environment variable required")
    exit(1)

# Create server
mcp = FastMCP("Minimal Test Server")

@mcp.tool()
def hello_world() -> str:
    """Simple hello world tool"""
    return "Hello from Diffbot MCP Server! Server is working correctly."

@mcp.tool()
def check_token() -> str:
    """Check if token is available"""
    token = os.getenv('DIFFBOT_TOKEN')
    if token:
        return f"Token is set (length: {len(token)} characters)"
    else:
        return "No token found"

def main():
    print("Starting minimal test server...")
    mcp.run()

if __name__ == "__main__":
    main()
'''
    
    with open('minimal_test_server.py', 'w') as f:
        f.write(minimal_server_code)
    
    print("\n🔧 Created minimal_test_server.py")
    print("Test it with: python minimal_test_server.py")


async def main():
    """Main debug function"""
    print("🐛 Diffbot MCP Server Debugger")
    print("=" * 50)
    
    # Step 1: Environment check
    env_ok = check_environment()
    
    if not env_ok:
        print("\n❌ Environment issues found. Please fix them and try again.")
        return
    
    # Step 2: Test MCP imports
    mcp_ok = test_mcp_import()
    
    if not mcp_ok:
        print("\n❌ MCP import issues found.")
        return
    
    # Step 3: Test APIs directly
    await test_diffbot_api_directly()
    
    # Step 4: Create minimal test server
    create_minimal_test_server()
    
    print("\n✅ All checks completed!")
    print("\nNext steps:")
    print("1. Test minimal server: python minimal_test_server.py")
    print("2. Test full server: python diffbot_mcp_server.py")
    print("3. Use the test client: python mcp_test_client.py")


if __name__ == "__main__":
    asyncio.run(main())
