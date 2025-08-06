# Route Completion System Implementation

## Overview

The Dynamic Discoveries project now includes a comprehensive self-updating requirements registry with automatic route completion functionality. This system automatically scans HTML templates for undefined routes and prompts for their implementation.

## Features Implemented

### 1. Enhanced Requirements Tracker (`utils/requirements_tracker.py`)

**New Functionality:**
- `parse_template_links()`: Parses individual template files for Django URL tags, HTMX calls, and href attributes
- `scan_all_templates()`: Recursively scans all HTML templates in a directory
- `_identify_undefined_routes()`: Identifies routes that may be undefined
- `generate_route_completion_prompt()`: Creates user-friendly prompts for route implementation

**Key Capabilities:**
- Extracts Django URL template tags: `{% url 'namespace:view' %}`
- Detects HTMX calls: `hx-get="..."` and `hx-post="..."`
- Filters out external links, static files, and media files
- Identifies potentially undefined routes based on naming patterns

### 2. Management Command (`utils/management/commands/scan_routes.py`)

**Command Usage:**
```bash
# Scan all templates
python manage.py scan_routes

# Scan specific template with verbose output
python manage.py scan_routes --template templates/my_template.html --verbose

# Scan with implementation prompts
python manage.py scan_routes --implement

# Scan custom templates directory
python manage.py scan_routes --templates-dir my_templates
```

**Features:**
- Interactive route implementation prompts
- Detailed template analysis
- Implementation guidance for undefined routes
- File location suggestions for new routes

### 3. Enhanced Testing (`tests/test_requirements.py`)

**New Test Classes:**
- `RouteCompletionTest`: Tests template parsing and route detection
- Enhanced `RequirementsAcceptanceTests` with REQ-029 test

**Test Coverage:**
- Template link parsing accuracy
- HTMX call detection
- Undefined route identification
- Prompt generation functionality
- Cross-template scanning

### 4. Updated Configuration (`.cursor/config.json`)

**New Rules:**
- Automatic template scanning for undefined routes
- Requirements file updates for new features
- Test enforcement for all requirements
- Route completion prompts

**Configuration Sections:**
- `route_completion.enabled`: Enable/disable route completion
- `template_analysis.enabled`: Enable template analysis
- `auto_prompt_completion`: Automatic prompts for undefined routes

### 5. New Requirement (REQ-029)

**Added to `site_requirements.json`:**
```json
{
  "id": "REQ-029",
  "title": "Route Completion System",
  "description": "Self-updating requirements registry with automatic template parsing for undefined routes. System scans HTML templates for Django URL tags, HTMX calls, and href attributes, then prompts for implementation of missing routes",
  "status": "implemented"
}
```

## Usage Examples

### 1. Basic Template Scanning

```python
from utils.requirements_tracker import parse_template_links

# Parse a single template
result = parse_template_links("templates/my_template.html")
print(f"Found {len(result['undefined_routes'])} undefined routes")
```

### 2. Full Project Scan

```python
from utils.requirements_tracker import scan_templates_for_undefined_routes

# Scan all templates
result = scan_templates_for_undefined_routes("templates")
for route in result['undefined_routes']:
    print(f"Undefined route: {route}")
```

### 3. Management Command

```bash
# Interactive route completion
python manage.py scan_routes --implement

# Output:
# Found 4 undefined routes:
# 1. undefined:route1
# 2. missing:route2
# 3. htmx:undefined
# 4. api:submit
# 
# Would you like to implement any of these routes?
```

## Technical Implementation

### Template Parsing Logic

1. **Django URL Tags**: `{% url 'namespace:view' %}`
2. **HTMX Calls**: `hx-get="..."` and `hx-post="..."`
3. **Href Attributes**: `href="..."`
4. **Filtering**: Excludes external links, static files, media files

### Route Detection Algorithm

1. Extract all links from template content
2. Filter out external and static resources
3. Identify Django URL patterns
4. Flag potentially undefined routes
5. Generate implementation prompts

### Integration Points

- **Requirements Tracking**: Automatically updates `site_requirements.json`
- **Testing Framework**: Comprehensive test coverage
- **Management Commands**: User-friendly CLI interface
- **Cursor Configuration**: IDE integration for automatic prompts

## Benefits

1. **Automated Discovery**: Automatically finds undefined routes in templates
2. **User-Friendly Prompts**: Interactive guidance for route implementation
3. **Comprehensive Coverage**: Scans all HTML templates recursively
4. **Integration**: Works seamlessly with existing requirements tracking
5. **Testing**: Full test coverage ensures reliability

## Future Enhancements

1. **URL Pattern Validation**: Parse actual Django URL configuration files
2. **Auto-Implementation**: Generate basic views and URLs automatically
3. **Template Generation**: Create basic templates for new routes
4. **Integration with Django Admin**: Add route completion to admin interface
5. **Real-time Scanning**: Monitor template changes and prompt immediately

## Conclusion

The route completion system provides a robust foundation for maintaining route consistency across the Dynamic Discoveries project. It automatically detects undefined routes, provides implementation guidance, and integrates seamlessly with the existing requirements tracking system.

This implementation ensures that all templates are properly connected to their corresponding views and URLs, reducing broken links and improving the overall user experience. 