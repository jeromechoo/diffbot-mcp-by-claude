#!/usr/bin/env python3
"""
Simple MCP client to test the Diffbot MCP server
"""

import asyncio
import json
import subprocess
import sys
from typing import Any, Dict

class MCPTestClient:
    """Simple MCP client for testing"""
    
    def __init__(self, server_command: list):
        self.server_command = server_command
        self.process = None
    
    async def start(self):
        """Start the MCP server process"""
        self.process = await asyncio.create_subprocess_exec(
            *self.server_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        print("✅ MCP server started")
    
    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict:
        """Send a JSON-RPC request to the server"""
        if not self.process:
            raise Exception("Server not started")
        
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        message = json.dumps(request) + "\n"
        self.process.stdin.write(message.encode())
        await self.process.stdin.drain()
        
        # Read response
        response_line = await self.process.stdout.readline()
        if not response_line:
            stderr_output = await self.process.stderr.read()
            raise Exception(f"No response from server. Stderr: {stderr_output.decode()}")
        
        try:
            response = json.loads(response_line.decode().strip())
            return response
        except json.JSONDecodeError as e:
            print(f"Failed to decode response: {response_line.decode()}")
            raise e
    
    async def initialize(self):
        """Initialize the MCP session"""
        response = await self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        })
        print("✅ Initialized MCP session")
        return response
    
    async def list_tools(self):
        """List available tools"""
        response = await self.send_request("tools/list")
        return response
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]):
        """Call a specific tool"""
        response = await self.send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        return response
    
    async def stop(self):
        """Stop the server"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            print("✅ Server stopped")


async def test_diffbot_server():
    """Test the Diffbot MCP server"""
    print("🚀 Testing Diffbot MCP Server")
    print("=" * 50)
    
    # Start the client
    client = MCPTestClient([sys.executable, "diffbot_mcp_server.py"])
    
    try:
        # Start server
        await client.start()
        
        # Initialize
        init_response = await client.initialize()
        print(f"📋 Server capabilities: {init_response.get('result', {}).get('capabilities', {})}")
        print()
        
        # List tools
        print("🔍 Available tools:")
        tools_response = await client.list_tools()
        tools = tools_response.get('result', {}).get('tools', [])
        
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        print()
        
        # Test DQL help
        print("📚 Testing DQL Help:")
        help_response = await client.call_tool("dql_help", {})
        if 'result' in help_response:
            content = help_response['result'][0]['text']
            print(content[:500] + "..." if len(content) > 500 else content)
        else:
            print(f"❌ Error: {help_response}")
        print()
        
        # Test DQL search (if token is available)
        print("🔎 Testing DQL Search:")
        search_response = await client.call_tool("dql_search", {
            "query": "type:article",
            "num": 3
        })
        
        if 'result' in search_response:
            content = search_response['result'][0]['text']
            print(content[:800] + "..." if len(content) > 800 else content)
        else:
            print(f"❌ Error: {search_response}")
        print()
        
        # Test URL enhancement
        print("🌐 Testing URL Enhancement:")
        enhance_response = await client.call_tool("enhance_url", {
            "url": "https://example.com",
            "fields": "meta"
        })
        
        if 'result' in enhance_response:
            content = enhance_response['result'][0]['text']
            print(content[:800] + "..." if len(content) > 800 else content)
        else:
            print(f"❌ Error: {enhance_response}")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
    
    finally:
        await client.stop()


def test_simple_communication():
    """Simple test to check if server responds"""
    import subprocess
    import os
    
    print("🧪 Simple Communication Test")
    print("=" * 30)
    
    # Check if server script exists
    if not os.path.exists("diffbot_mcp_server.py"):
        print("❌ diffbot_mcp_server.py not found in current directory")
        return
    
    # Check if token is set
    if not os.getenv('DIFFBOT_TOKEN'):
        print("⚠️  DIFFBOT_TOKEN not set - API calls will fail")
    else:
        print("✅ DIFFBOT_TOKEN is set")
    
    try:
        # Test server startup
        process = subprocess.Popen(
            [sys.executable, "diffbot_mcp_server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send a simple initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test", "version": "1.0.0"}
            }
        }
        
        # Send request and wait for response
        stdout, stderr = process.communicate(
            input=json.dumps(init_request) + "\n",
            timeout=10
        )
        
        if stdout:
            print("✅ Server responded:")
            try:
                response = json.loads(stdout.strip())
                print(f"   Response: {json.dumps(response, indent=2)}")
            except json.JSONDecodeError:
                print(f"   Raw output: {stdout}")
        else:
            print("❌ No response from server")
            if stderr:
                print(f"   Error: {stderr}")
        
        process.terminate()
        
    except subprocess.TimeoutExpired:
        print("❌ Server timed out")
        process.kill()
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    print("Choose test method:")
    print("1. Simple communication test (basic)")
    print("2. Full async test (advanced)")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        test_simple_communication()
    elif choice == "2":
        asyncio.run(test_diffbot_server())
    else:
        print("Invalid choice. Running simple test...")
        test_simple_communication()
