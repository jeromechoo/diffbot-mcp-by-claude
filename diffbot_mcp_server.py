#!/usr/bin/env python3
"""
Diffbot MCP Server

This server provides access to Diffbot's DQL (Diffbot Query Language) and Enhance APIs
through the Model Context Protocol (MCP).
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Diffbot API configuration
DIFFBOT_BASE_URL = "https://api.diffbot.com"
DQL_ENDPOINT = f"{DIFFBOT_BASE_URL}/v3/search"
ENHANCE_ENDPOINT = f"{DIFFBOT_BASE_URL}/v3/enhance"


class DiffbotConfig(BaseModel):
    """Configuration for Diffbot API"""
    token: str = Field(..., description="Diffbot API token")
    timeout: int = Field(default=30, description="Request timeout in seconds")


class DQLQuery(BaseModel):
    """DQL query parameters"""
    query: str = Field(..., description="DQL query string")
    num: Optional[int] = Field(default=10, description="Number of results to return")
    start: Optional[int] = Field(default=0, description="Starting index for results")
    format: Optional[str] = Field(default="json", description="Response format")


class EnhanceQuery(BaseModel):
    """Enhance API query parameters"""
    url: str = Field(..., description="URL to enhance")
    fields: Optional[str] = Field(default="meta,links,breadcrumb", description="Fields to extract")


# Get Diffbot token from environment variable
DIFFBOT_TOKEN = os.getenv('DIFFBOT_TOKEN')
if not DIFFBOT_TOKEN:
    raise ValueError("DIFFBOT_TOKEN environment variable is required")

# Create FastMCP server
mcp = FastMCP("Diffbot Server")

# HTTP client for API calls
client = httpx.AsyncClient(timeout=30)
    
@mcp.tool()
async def dql_search(query: str, num: int = 10, start: int = 0) -> str:
    """
    Execute a DQL (Diffbot Query Language) search query.
    
    Args:
        query: DQL query string (e.g., 'type:article author:"John Doe"')
        num: Number of results to return (default: 10, max: 100)
        start: Starting index for pagination (default: 0)
    
    Returns:
        Formatted search results
    """
    # Validate parameters
    if num < 1 or num > 100:
        raise ValueError("num must be between 1 and 100")
    if start < 0:
        raise ValueError("start must be >= 0")
    
    params = {
        "token": DIFFBOT_TOKEN,
        "query": query,
        "num": num,
        "start": start,
        "format": "json"
    }
    
    try:
        response = await client.get(DQL_ENDPOINT, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Format the response
        result_text = f"DQL Search Results for: {query}\n"
        result_text += f"Total results: {data.get('hits', 0)}\n"
        result_text += f"Showing {start + 1}-{start + len(data.get('objects', []))}\n\n"
        
        for i, obj in enumerate(data.get('objects', []), 1):
            result_text += f"Result {i}:\n"
            result_text += f"  Title: {obj.get('title', 'N/A')}\n"
            result_text += f"  URL: {obj.get('pageUrl', 'N/A')}\n"
            result_text += f"  Type: {obj.get('type', 'N/A')}\n"
            result_text += f"  Date: {obj.get('date', 'N/A')}\n"
            
            if obj.get('text'):
                # Truncate text for readability
                text = obj['text'][:300] + "..." if len(obj['text']) > 300 else obj['text']
                result_text += f"  Text: {text}\n"
            
            result_text += "\n"
        
        return result_text
        
    except httpx.HTTPError as e:
        raise Exception(f"HTTP error during DQL search: {str(e)}")

@mcp.tool()
async def enhance_entity(
    type: str,
    name: str = None,
    url: str = None,
    location: str = None,
    phone: str = None,
    employer: str = None,
    title: str = None,
    school: str = None,
    ip: str = None,
    id: str = None,
    threshold: float = None,
    size: int = 1,
    refresh: bool = False,
    search: bool = False
) -> str:
    """
    Enhance a person or organization using Diffbot's Enhance API.
    
    Args:
        type: Entity type - either "Person" or "Organization" (required)
        name: Name of the entity
        url: URL associated with the entity
        location: Location/address (supports various formats like "New York City, U.S.A.")
        phone: Phone number
        employer: Employer name (for Person type)
        title: Job title (for Person type)
        school: School name (for Person type)
        ip: IP address
        id: Diffbot Knowledge Graph entity ID
        threshold: Confidence threshold for matches (0.0-1.0)
        size: Maximum number of results to return (default: 1)
        refresh: Force refresh of data from origins (default: False)
        search: Search web in addition to Knowledge Graph (default: False)
    
    Returns:
        Formatted enhanced entity data
        
    Note:
        - For Organizations: at least 'name' or 'url' is required
        - For Persons: at least 'name' is required
        - Additional input parameters improve match confidence
    """
    # Validate required parameters
    if type not in ["Person", "Organization"]:
        raise ValueError("type must be either 'Person' or 'Organization'")
    
    # Check minimum requirements
    if type == "Organization" and not (name or url):
        raise ValueError("For Organizations, either 'name' or 'url' is required")
    elif type == "Person" and not name:
        raise ValueError("For Persons, 'name' is required")
    
    # Build parameters
    params = {
        "token": DIFFBOT_TOKEN,
        "type": type
    }
    
    # Add input parameters (only include non-None values)
    input_params = {
        "name": name,
        "url": url,
        "location": location,
        "phone": phone,
        "employer": employer,
        "title": title,
        "school": school,
        "ip": ip,
        "id": id
    }
    
    for key, value in input_params.items():
        if value is not None:
            params[key] = value
    
    # Add optional parameters
    if threshold is not None:
        params["threshold"] = threshold
    if size != 1:
        params["size"] = size
    if refresh:
        params["refresh"] = "true"
    if search:
        params["search"] = "true"
    
    # Construct the correct endpoint URL
    enhance_url = "https://kg.diffbot.com/kg/v3/enhance"
    
    try:
        response = await client.get(enhance_url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Debug: Let's see the actual response structure
        print(f"DEBUG - Full response keys: {list(data.keys())}")
        if 'data' in data:
            print(f"DEBUG - Data length: {len(data['data'])}")
            if data['data']:
                print(f"DEBUG - First entity keys: {list(data['data'][0].keys())}")
        
        # Format the response
        entity_type = "Organization" if type == "Organization" else "Person"
        result_text = f"Enhanced {entity_type} Data:\n"
        result_text += "=" * 50 + "\n\n"
        
        # Handle different possible response structures
        entities = []
        if 'data' in data and data['data']:
            entities = data['data']
        elif 'results' in data and data['results']:
            entities = data['results']
        elif isinstance(data, list):
            entities = data
        
        if entities:
            for i, match in enumerate(entities, 1):
                if i > 1:
                    result_text += "\n" + "-" * 40 + "\n\n"
                
                result_text += f"Match #{i}:\n"
                
                # Display confidence score if available
                if 'score' in match:
                    result_text += f"  Confidence Score: {match['score']:.3f}\n"
                
                # Check if there are any errors
                if 'errors' in match and match['errors']:
                    result_text += f"  Errors: {match['errors']}\n"
                
                # Extract the actual entity data
                entity = match.get('entity', {})
                if not entity:
                    result_text += "  No entity data found in this match.\n"
                    continue
                
                # Display all available fields for debugging
                result_text += f"  Entity fields: {list(entity.keys())}\n"
                
                # Display basic information
                if 'name' in entity:
                    result_text += f"  Name: {entity['name']}\n"
                
                if type == "Organization":
                    # Organization-specific fields - try multiple possible field names
                    website_fields = ['homepageUri', 'website', 'url', 'homepage']
                    for field in website_fields:
                        if field in entity:
                            result_text += f"  Website: {entity[field]}\n"
                            break
                    
                    # Location can be in different formats
                    if 'location' in entity:
                        if isinstance(entity['location'], dict) and 'name' in entity['location']:
                            result_text += f"  Location: {entity['location']['name']}\n"
                        elif isinstance(entity['location'], str):
                            result_text += f"  Location: {entity['location']}\n"
                    elif 'locations' in entity and entity['locations']:
                        loc = entity['locations'][0]
                        if isinstance(loc, dict) and 'name' in loc:
                            result_text += f"  Location: {loc['name']}\n"
                        elif isinstance(loc, str):
                            result_text += f"  Location: {loc}\n"
                    
                    # Revenue and employee fields
                    revenue_fields = ['revenue', 'annualRevenue', 'yearlyRevenue']
                    for field in revenue_fields:
                        if field in entity:
                            result_text += f"  Revenue: {entity[field]}\n"
                            break
                    
                    employee_fields = [
                        ('nbEmployeesMin', 'nbEmployeesMax'),
                        ('employeesMin', 'employeesMax'),
                        ('employeeCountMin', 'employeeCountMax')
                    ]
                    for min_field, max_field in employee_fields:
                        if min_field in entity or max_field in entity:
                            min_emp = entity.get(min_field, 'N/A')
                            max_emp = entity.get(max_field, 'N/A')
                            result_text += f"  Employees: {min_emp} - {max_emp}\n"
                            break
                        elif 'nbEmployees' in entity:
                            result_text += f"  Employees: {entity['nbEmployees']}\n"
                    
                    # Industry and description
                    industry_fields = ['industry', 'industries', 'category', 'categories']
                    for field in industry_fields:
                        if field in entity:
                            if isinstance(entity[field], list):
                                result_text += f"  Industry: {', '.join(entity[field])}\n"
                            else:
                                result_text += f"  Industry: {entity[field]}\n"
                            break
                    
                    desc_fields = ['description', 'summary', 'about']
                    for field in desc_fields:
                        if field in entity:
                            desc = str(entity[field])
                            desc = desc[:200] + "..." if len(desc) > 200 else desc
                            result_text += f"  Description: {desc}\n"
                            break
                
                else:  # Person
                    # Person-specific fields
                    if 'location' in entity:
                        if isinstance(entity['location'], dict) and 'name' in entity['location']:
                            result_text += f"  Location: {entity['location']['name']}\n"
                        elif isinstance(entity['location'], str):
                            result_text += f"  Location: {entity['location']}\n"
                    elif 'locations' in entity and entity['locations']:
                        loc = entity['locations'][0]
                        if isinstance(loc, dict) and 'name' in loc:
                            result_text += f"  Location: {loc['name']}\n"
                        elif isinstance(loc, str):
                            result_text += f"  Location: {loc}\n"
                    
                    # Employment information
                    employment_fields = ['employments', 'employment', 'jobs', 'currentEmployment']
                    for field in employment_fields:
                        if field in entity and entity[field]:
                            if isinstance(entity[field], list):
                                current_job = entity[field][0]  # Most recent employment
                            else:
                                current_job = entity[field]
                            
                            if isinstance(current_job, dict):
                                if 'employer' in current_job:
                                    if isinstance(current_job['employer'], dict) and 'name' in current_job['employer']:
                                        result_text += f"  Current Employer: {current_job['employer']['name']}\n"
                                    elif isinstance(current_job['employer'], str):
                                        result_text += f"  Current Employer: {current_job['employer']}\n"
                                
                                title_fields = ['title', 'position', 'role']
                                for title_field in title_fields:
                                    if title_field in current_job:
                                        result_text += f"  Title: {current_job[title_field]}\n"
                                        break
                            break
                    
                    # Education information
                    education_fields = ['educations', 'education', 'schools']
                    for field in education_fields:
                        if field in entity and entity[field]:
                            if isinstance(entity[field], list):
                                schools = []
                                for edu in entity[field][:2]:  # First 2 schools
                                    if isinstance(edu, dict):
                                        if 'institution' in edu and isinstance(edu['institution'], dict) and 'name' in edu['institution']:
                                            schools.append(edu['institution']['name'])
                                        elif 'school' in edu:
                                            schools.append(str(edu['school']))
                                        elif 'name' in edu:
                                            schools.append(edu['name'])
                                if schools:
                                    result_text += f"  Education: {', '.join(schools)}\n"
                            break
                
                # Common fields for both types
                uri_fields = ['diffbotUri', 'uri', 'id', 'diffbotId']
                for field in uri_fields:
                    if field in entity:
                        result_text += f"  Diffbot URI: {entity[field]}\n"
                        break
                
                # Social media links - try multiple field name variations
                social_mappings = {
                    'twitterUri': 'Twitter',
                    'twitter': 'Twitter', 
                    'twitterUrl': 'Twitter',
                    'linkedInUri': 'LinkedIn',
                    'linkedin': 'LinkedIn',
                    'linkedinUri': 'LinkedIn',
                    'linkedInUrl': 'LinkedIn',
                    'facebookUri': 'Facebook',
                    'facebook': 'Facebook',
                    'facebookUrl': 'Facebook'
                }
                
                social_links = []
                for field, platform in social_mappings.items():
                    if field in entity and entity[field]:
                        social_links.append(f"{platform}: {entity[field]}")
                
                if social_links:
                    result_text += f"  Social Media: {', '.join(social_links)}\n"
                
                # Add any remaining interesting fields
                interesting_fields = ['founded', 'foundedYear', 'ticker', 'stock', 'ceo', 'headquarters']
                for field in interesting_fields:
                    if field in entity and entity[field]:
                        field_name = field.replace('foundedYear', 'Founded').replace('ticker', 'Stock Ticker').replace('ceo', 'CEO').replace('headquarters', 'Headquarters')
                        result_text += f"  {field_name.title()}: {entity[field]}\n"
                
                result_text += "\n"
        
        else:
            result_text += f"No {entity_type.lower()} found matching the provided criteria.\n"
            result_text += "Try:\n"
            result_text += "- Adding more input parameters (location, url, etc.)\n"
            result_text += "- Lowering the threshold parameter\n"
            result_text += "- Using search=True to search beyond the Knowledge Graph\n"
        
        return result_text.strip()
        
    except httpx.HTTPError as e:
        raise Exception(f"HTTP error during entity enhancement: {str(e)}")
    except KeyError as e:
        raise Exception(f"Unexpected response format from Diffbot API: {str(e)}")
    except Exception as e:
        raise Exception(f"Error enhancing entity: {str(e)}")


# Optional: Keep a simplified wrapper for backward compatibility
@mcp.tool()
async def enhance_organization(name: str = None, url: str = None, location: str = None) -> str:
    """
    Simplified wrapper to enhance an organization.
    
    Args:
        name: Organization name
        url: Organization website URL
        location: Organization location
        
    Returns:
        Enhanced organization data
    """
    return await enhance_entity(
        type="Organization",
        name=name,
        url=url,
        location=location
    )


@mcp.tool()
async def enhance_person(name: str, employer: str = None, title: str = None, location: str = None) -> str:
    """
    Simplified wrapper to enhance a person.
    
    Args:
        name: Person's name (required)
        employer: Current or past employer
        title: Job title
        location: Person's location
        
    Returns:
        Enhanced person data
    """
    return await enhance_entity(
        type="Person",
        name=name,
        employer=employer,
        title=title,
        location=location
    )

@mcp.tool()
async def dql_help() -> str:
    """Get help and examples for DQL (Diffbot Query Language) syntax."""
    help_text = """
DQL (Diffbot Query Language) Help

DQL allows you to search Diffbot's Knowledge Graph using a simple query syntax.

Basic Syntax:
- Field searches: field:value
- Exact phrases: "exact phrase"
- OR operator: query1 OR query2
- AND operator: query1 AND query2 (default)
- NOT operator: NOT query

Common Fields:
- type: Content type (article, product, image, video, etc.)
- title: Article/page title
- author: Author name
- text: Body text content
- tags: Associated tags
- date: Publication date
- site: Website domain
- language: Content language

Date Ranges:
- date:>2023-01-01 (after date)
- date:<2023-12-31 (before date)
- date:2023-01-01..2023-12-31 (date range)

Examples:
1. Find articles by author:
   type:article author:"John Smith"

2. Find recent tech articles:
   type:article tags:technology date:>2023-01-01

3. Find products under $100:
   type:product price:<100

4. Find articles about AI or machine learning:
   type:article (text:"artificial intelligence" OR text:"machine learning")

5. Find content from specific site:
   site:techcrunch.com type:article

6. Complex query:
   type:article author:"Jane Doe" date:>2023-06-01 NOT tags:opinion

Tips:
- Use quotes for exact phrases
- Combine multiple conditions with AND/OR
- Use parentheses to group conditions
- Field names are case-sensitive
- Use wildcards (*) for partial matches
"""
    
    return help_text.strip()


def main():
    """Main entry point"""
    # FastMCP handles the async event loop internally
    mcp.run()


if __name__ == "__main__":
    main()