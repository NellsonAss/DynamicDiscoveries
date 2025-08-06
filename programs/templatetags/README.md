# Custom Template Filters

This directory contains custom Django template filters for mathematical operations.

## Available Filters

### multiply
Multiplies two values.
```django
{{ value|multiply:arg }}
```
Example: `{{ 5|multiply:3 }}` → `15.0`

### divide
Divides the first value by the second value.
```django
{{ value|divide:arg }}
```
Example: `{{ 15|divide:3 }}` → `5.0`

### subtract
Subtracts the second value from the first value.
```django
{{ value|subtract:arg }}
```
Example: `{{ 10|subtract:3 }}` → `7.0`

### percentage
Calculates percentage: (value / arg) * 100
```django
{{ value|percentage:arg }}
```
Example: `{{ 25|percentage:100 }}` → `25.0`

## Usage in Templates

To use these filters in a template, first load them:

```django
{% load math_filters %}
```

Then use them in your template:

```django
<li><strong>Total Sessions:</strong> {{ buildout.num_days|multiply:buildout.sessions_per_day }}</li>
<li><strong>Percentage:</strong> {{ value|percentage:total }}%</li>
```

## Error Handling

All filters include error handling and will return `0` if:
- The input values cannot be converted to numbers
- Division by zero is attempted
- Any other error occurs during calculation

## Testing

The filters are tested in `tests/test_requirements.py` in the `test_REQ_026_custom_template_math_filters` method. 