import yaml
import jsonschema
import os

def apply_defaults(schema, config):
    """Recursively apply default values from the schema to the configuration."""
    if config is None:
        config = {}

    # Handle 'allOf' - iterate over all sub-schemas and merge defaults if conditions match
    if 'allOf' in schema:
        for subschema in schema['allOf']:
            # Handle conditional (if-then) logic
            if 'if' in subschema and 'then' in subschema:
                condition_key = list(subschema['if']['properties'].keys())[0]
                condition_value = subschema['if']['properties'][condition_key]['const']

                # Check if the condition is met
                if config.get(condition_key) == condition_value:
                    schema = {**schema, **subschema['then']}

    if isinstance(schema, dict):
        for key, value in schema.get('properties', {}).items():
            # If the key is not present in the config and has a default, apply it
            if key not in config and 'default' in value:
                config[key] = value['default']

            # If the key is an object type, apply defaults recursively
            elif value.get('type') == 'object':
                if key not in config:
                    config[key] = {}  # Create the object if it doesn't exist
                config[key] = apply_defaults(value, config.get(key, {}))  # Recursively apply defaults

            # If the key is an array type and a default is defined, apply it if missing or empty
            elif value.get('type') == 'array' and 'default' in value:
                if key not in config:
                    config[key] = value['default']

    return config



class InputFile:
    def __init__(self, input_filename):
        # Load YAML configuration
        with open(input_filename, 'r') as f:
            self.config = yaml.safe_load(f)

        # Load the schema
        current_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(current_dir, 'schema.yml')
        with open(schema_path, 'r') as schema_file:
            schema = yaml.safe_load(schema_file)

        # Apply defaults recursively
        self.config = apply_defaults(schema, self.config)

        # Validate against schema after applying defaults
        jsonschema.validate(instance=self.config, schema=schema)

    def get_parameters(self):
        return self.config
