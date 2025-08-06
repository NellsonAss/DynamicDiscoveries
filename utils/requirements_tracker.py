"""
Requirements tracking utility for Dynamic Discoveries project.

This module provides functions to manage project requirements stored in
site_requirements.json and validate their implementation status.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from urllib.parse import urlparse


class RequirementsTracker:
    """Manages project requirements tracking and validation."""
    
    def __init__(self, requirements_file: str = "site_requirements.json"):
        """Initialize the tracker with the requirements file path."""
        self.requirements_file = Path(requirements_file)
        self._requirements_data = None
    
    def load_requirements(self) -> Dict[str, Any]:
        """Load requirements from the JSON file."""
        if not self.requirements_file.exists():
            return {
                "requirements": [],
                "metadata": {
                    "version": "1.0",
                    "last_updated": datetime.now().isoformat(),
                    "description": "Dynamic Discoveries project requirements tracking"
                }
            }
        
        try:
            with open(self.requirements_file, 'r', encoding='utf-8') as f:
                self._requirements_data = json.load(f)
                return self._requirements_data
        except (json.JSONDecodeError, IOError) as e:
            raise ValueError(f"Error loading requirements file: {e}")
    
    def save_requirements(self, data: Optional[Dict[str, Any]] = None) -> None:
        """Save requirements to the JSON file."""
        if data is None:
            data = self._requirements_data
        
        if data is None:
            raise ValueError("No data to save")
        
        # Update metadata
        data["metadata"]["last_updated"] = datetime.now().isoformat()
        
        try:
            with open(self.requirements_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            raise ValueError(f"Error saving requirements file: {e}")
    
    def add_requirement(self, req_id: str, title: str, description: str, 
                       status: str = "required") -> Dict[str, Any]:
        """Add a new requirement to the tracking system."""
        if self._requirements_data is None:
            self._requirements_data = self.load_requirements()
        
        # Validate status
        valid_statuses = ["required", "implemented"]
        if status not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        
        # Check if requirement already exists
        existing_req = self.get_requirement_by_id(req_id)
        if existing_req:
            raise ValueError(f"Requirement with ID {req_id} already exists")
        
        # Create new requirement
        new_requirement = {
            "id": req_id,
            "title": title,
            "description": description,
            "status": status
        }
        
        # Ensure requirements list exists
        if "requirements" not in self._requirements_data:
            self._requirements_data["requirements"] = []
        
        self._requirements_data["requirements"].append(new_requirement)
        self.save_requirements()
        
        return new_requirement
    
    def update_requirement_status(self, req_id: str, status: str) -> Dict[str, Any]:
        """Update the status of an existing requirement."""
        if self._requirements_data is None:
            self._requirements_data = self.load_requirements()
        
        # Validate status
        valid_statuses = ["required", "implemented"]
        if status not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        
        # Find and update requirement
        for req in self._requirements_data["requirements"]:
            if req["id"] == req_id:
                req["status"] = status
                self.save_requirements()
                return req
        
        raise ValueError(f"Requirement with ID {req_id} not found")
    
    def get_requirement_by_id(self, req_id: str) -> Optional[Dict[str, Any]]:
        """Get a requirement by its ID."""
        if self._requirements_data is None:
            self._requirements_data = self.load_requirements()
        
        # Ensure requirements list exists
        if "requirements" not in self._requirements_data:
            return None
        
        for req in self._requirements_data["requirements"]:
            if req["id"] == req_id:
                return req
        return None
    
    def get_all_requirements(self) -> List[Dict[str, Any]]:
        """Get all requirements."""
        if self._requirements_data is None:
            self._requirements_data = self.load_requirements()
        
        # Ensure requirements list exists
        if "requirements" not in self._requirements_data:
            return []
        
        return self._requirements_data["requirements"]
    
    def get_requirements_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all requirements with a specific status."""
        if self._requirements_data is None:
            self._requirements_data = self.load_requirements()
        
        # Ensure requirements list exists
        if "requirements" not in self._requirements_data:
            return []
        
        return [req for req in self._requirements_data["requirements"] if req["status"] == status]
    
    def validate_all_implemented(self) -> bool:
        """Check if all requirements are implemented."""
        if self._requirements_data is None:
            self._requirements_data = self.load_requirements()
        
        # Ensure requirements list exists
        if "requirements" not in self._requirements_data:
            return True  # No requirements means all are implemented
        
        return all(req["status"] == "implemented" for req in self._requirements_data["requirements"])
    
    def parse_template_links(self, template_path: str) -> Dict[str, List[str]]:
        """Parse a Django template file for links and HTMX calls."""
        template_file = Path(template_path)
        if not template_file.exists():
            return {"links": [], "htmx_calls": [], "undefined_routes": []}
        
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except IOError:
            return {"links": [], "htmx_calls": [], "undefined_routes": []}
        
        # Extract Django URL template tags - improved pattern
        url_pattern = r'{%\s*url\s+[\'"]([^\'"]+)[\'"](?:\s+[^%]*)?\s*%}'
        url_matches = re.findall(url_pattern, content)
        
        # Extract href attributes
        href_pattern = r'href=[\'"]([^\'"]+)[\'"]'
        href_matches = re.findall(href_pattern, content)
        
        # Extract HTMX calls - improved patterns
        htmx_get_pattern = r'hx-get=[\'"]([^\'"]+)[\'"]'
        htmx_get_matches = re.findall(htmx_get_pattern, content)
        
        htmx_post_pattern = r'hx-post=[\'"]([^\'"]+)[\'"]'
        htmx_post_matches = re.findall(htmx_post_pattern, content)
        
        # Also extract HTMX calls that use Django URL tags
        htmx_url_pattern = r'hx-get=[\'"]\s*{%\s*url\s+[\'"]([^\'"]+)[\'"](?:\s+[^%]*)?\s*%}\s*[\'"]'
        htmx_url_matches = re.findall(htmx_url_pattern, content)
        
        htmx_post_url_pattern = r'hx-post=[\'"]\s*{%\s*url\s+[\'"]([^\'"]+)[\'"](?:\s+[^%]*)?\s*%}\s*[\'"]'
        htmx_post_url_matches = re.findall(htmx_post_url_pattern, content)
        
        all_links = url_matches + href_matches + htmx_get_matches + htmx_post_matches + htmx_url_matches + htmx_post_url_matches
        
        # Filter out external links and static files
        internal_links = []
        for link in all_links:
            # Skip empty or whitespace-only links
            if not link or link.strip() == '':
                continue
                
            # Skip external links
            if link.startswith(('http://', 'https://', '//', 'mailto:', 'tel:', '#')):
                continue
                
            # Skip static and media files
            if link.startswith(('static/', 'media/', 'admin/', '/static/', '/media/', '/admin/')):
                continue
                
            # Skip Django template tags that weren't properly parsed
            if link.startswith('{%') or link.endswith('%}'):
                continue
                
            internal_links.append(link)
        
        return {
            "links": internal_links,
            "htmx_calls": htmx_get_matches + htmx_post_matches + htmx_url_matches + htmx_post_url_matches,
            "undefined_routes": self._identify_undefined_routes(internal_links)
        }
    
    def _identify_undefined_routes(self, links: List[str]) -> List[str]:
        """Identify routes that may be undefined by checking URL patterns."""
        # This is a simplified check - in a real implementation, you'd want to
        # parse Django's URL configuration files
        undefined_routes = []
        
        # Common patterns that might indicate undefined routes
        suspicious_patterns = [
            r'^[a-zA-Z_][a-zA-Z0-9_]*:[a-zA-Z_][a-zA-Z0-9_]*$',  # namespace:view
            r'^[a-zA-Z_][a-zA-Z0-9_]*$',  # simple view name
        ]
        
        for link in links:
            # Skip obvious static/external links
            if link.startswith(('http', '//', 'static/', 'media/', 'admin/')):
                continue
            
            # Check if it matches Django URL patterns
            is_suspicious = False
            for pattern in suspicious_patterns:
                if re.match(pattern, link):
                    is_suspicious = True
                    break
            
            if is_suspicious:
                undefined_routes.append(link)
        
        return undefined_routes
    
    def scan_all_templates(self, templates_dir: str = "templates") -> Dict[str, List[str]]:
        """Scan all template files for undefined routes."""
        templates_path = Path(templates_dir)
        if not templates_path.exists():
            return {"undefined_routes": []}
        
        all_undefined_routes = []
        
        # Recursively find all HTML template files
        for template_file in templates_path.rglob("*.html"):
            template_links = self.parse_template_links(str(template_file))
            all_undefined_routes.extend(template_links["undefined_routes"])
        
        return {
            "undefined_routes": list(set(all_undefined_routes))  # Remove duplicates
        }
    
    def generate_route_completion_prompt(self, undefined_routes: List[str]) -> str:
        """Generate a prompt for completing undefined routes."""
        if not undefined_routes:
            return "No undefined routes found."
        
        routes_list = "\n".join([f"- {route}" for route in undefined_routes])
        
        return f"""The following routes appear to be undefined in your templates:

{routes_list}

Would you like to implement these routes now? Please specify which routes you'd like to create and I'll help you implement the corresponding views, URLs, and templates."""


# Convenience functions for easy access
def load_requirements() -> Dict[str, Any]:
    """Load requirements from the JSON file."""
    tracker = RequirementsTracker()
    return tracker.load_requirements()


def add_requirement(req_id: str, title: str, description: str, 
                   status: str = "required") -> Dict[str, Any]:
    """Add a new requirement to the tracking system."""
    tracker = RequirementsTracker()
    return tracker.add_requirement(req_id, title, description, status)


def update_requirement_status(req_id: str, status: str) -> Dict[str, Any]:
    """Update the status of an existing requirement."""
    tracker = RequirementsTracker()
    return tracker.update_requirement_status(req_id, status)


def validate_all_implemented() -> bool:
    """Check if all requirements are implemented."""
    tracker = RequirementsTracker()
    return tracker.validate_all_implemented()


def scan_templates_for_undefined_routes(templates_dir: str = "templates") -> Dict[str, List[str]]:
    """Scan all templates for undefined routes."""
    tracker = RequirementsTracker()
    return tracker.scan_all_templates(templates_dir)


def parse_template_links(template_path: str) -> Dict[str, List[str]]:
    """Parse a single template file for links and HTMX calls."""
    tracker = RequirementsTracker()
    return tracker.parse_template_links(template_path) 