import yaml
import re

from config import INPUT_FILE, OUTPUT_FILE

def remove_openapi3_fields(spec):
    if 'components' in spec:
        del spec['components']

    for path in spec['paths'].values():
        for method in path.values():
            if 'requestBody' in method:
                del method['requestBody']
            if 'body' in method:  # Add this line
                del method['body']  # Add this line
            if 'responses' in method:
                for response in method['responses'].values():
                    if 'content' in response:
                        del response['content']
    return spec


def convert_request_body_to_parameters(method_details):
    body_param_added = False
    if 'requestBody' in method_details:
        request_body = method_details['requestBody']
        if 'content' in request_body:
            content = request_body['content']
            for content_type, content_schema in content.items():
                body_schema = content_schema.get('schema', {})
                body_param = {
                    'in': 'body',
                    'name': 'body',
                    'required': request_body.get('required', False),
                    'schema': body_schema
                }
                if 'parameters' not in method_details:
                    method_details['parameters'] = []
                if not body_param_added:
                    method_details['parameters'].append(body_param)
                    body_param_added = True
                break  # Only add the first content type as body parameter
        del method_details['requestBody']

    # Convert query parameters
    if 'parameters' in method_details:
        new_parameters = []
        for param in method_details['parameters']:
            if param.get('in') == 'query':
                if 'schema' in param:
                    param.update(param['schema'])
                    del param['schema']
            if param.get('in') != 'body' or (param.get('in') == 'body' and not body_param_added):
                new_parameters.append(param)
                if param.get('in') == 'body':
                    body_param_added = True
        method_details['parameters'] = new_parameters

    return method_details

def convert_type(type_value):
    if isinstance(type_value, str) and '|' in type_value:
        types = type_value.split('|')
        return types[0].strip()  # Choose the first type from the list
    return type_value

def process_schema(schema):
    if isinstance(schema, dict):
        # Remove 'writeOnly' field
        if 'writeOnly' in schema:
            del schema['writeOnly']

        # Handle 'nullable' field
        if 'nullable' in schema:
            if schema.get('type') == 'string':
                schema['type'] = ['string', 'null']
            elif schema.get('type') == 'integer':
                schema['type'] = ['integer', 'null']
            elif schema.get('type') == 'number':
                schema['type'] = ['number', 'null']
            elif schema.get('type') == 'boolean':
                schema['type'] = ['boolean', 'null']
            elif schema.get('type') == 'array':
                schema['type'] = ['array', 'null']
            elif schema.get('type') == 'object':
                schema['type'] = ['object', 'null']
            del schema['nullable']

        if 'type' in schema:
            schema['type'] = convert_type(schema['type'])
        for key, value in schema.items():
            schema[key] = process_schema(value)
        if 'required' in schema and isinstance(schema['required'], list):
            schema['required'] = list(dict.fromkeys(schema['required']))  # Remove duplicates
    elif isinstance(schema, list):
        return [process_schema(item) for item in schema]
    return schema

def escape_special_chars(text):
    return re.sub(r'([\\"])', r'\\\1', text)


def process_parameters(spec):
    for path in spec['paths'].values():
        for method in path.values():
            if 'parameters' in method:
                for param in method['parameters']:
                    if 'schema' in param:
                        param.update(param['schema'])
                        del param['schema']
    return spec

def deduplicate_parameters(spec):
    for path in spec['paths'].values():
        for method in path.values():
            if 'parameters' in method:
                seen = set()
                unique_params = []
                for param in method['parameters']:
                    param_key = (param.get('in'), param.get('name'))
                    if param_key not in seen:
                        seen.add(param_key)
                        unique_params.append(param)
                method['parameters'] = unique_params
    return spec


def convert_spectacular_to_swagger(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as file:
        spec = yaml.safe_load(file)

    # Convert OpenAPI 3 to Swagger 2
    spec['swagger'] = '2.0'
    del spec['openapi']

    # Process paths
    for path, path_item in spec['paths'].items():
        for method, method_details in path_item.items():
            method_details = convert_request_body_to_parameters(method_details)
            if 'responses' in method_details:
                for status_code, response in method_details['responses'].items():
                    if 'content' in response:
                        schema = response['content'].get('application/json', {}).get('schema', {})
                        response['schema'] = process_schema(schema)
                        del response['content']

    spec = process_parameters(spec)
    spec = deduplicate_parameters(spec)

    # Process definitions/components
    if 'components' in spec:
        spec['definitions'] = spec['components'].get('schemas', {})
        del spec['components']

    # Update $ref paths
    def update_refs(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == '$ref' and value.startswith('#/components/schemas/'):
                    obj[key] = value.replace('#/components/schemas/', '#/definitions/')
                else:
                    update_refs(value)
        elif isinstance(obj, list):
            for item in obj:
                update_refs(item)

    update_refs(spec)

    for definition in spec.get('definitions', {}).values():
        process_schema(definition)

    # Remove OpenAPI 3 specific fields
    remove_openapi3_fields(spec)

    # Write the converted spec to the output file
    with open(output_file, 'w') as file:
        yaml.dump(spec, file, default_flow_style=False)

# Usage
if __name__ == '__main__':
    convert_spectacular_to_swagger(INPUT_FILE, OUTPUT_FILE)
